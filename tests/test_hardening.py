from conftest import approve, import_case, prepare
from starlette.testclient import TestClient

from renderguard.body_limit import BodyLimitMiddleware
from renderguard.documents import process_pdf
from renderguard.gateway import Principal
from renderguard.privacy import redact_text, safe_log


def test_large_declared_json_body_rejected_before_parsing(env):
    response = env[1].post(
        "/api/playground",
        content=b"{}",
        headers={"Content-Length": "1000000", "Content-Type": "application/json"},
    )
    assert response.status_code == 413


async def test_chunked_body_is_bounded_without_content_length():
    called = False

    async def downstream(scope, receive, send):
        nonlocal called
        called = True

    chunks = iter(
        [
            {"type": "http.request", "body": b"x" * 40000, "more_body": True},
            {"type": "http.request", "body": b"x" * 40000, "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    output = []

    async def send(message):
        output.append(message)

    await BodyLimitMiddleware(downstream)(
        {"type": "http", "method": "POST", "path": "/api/playground", "headers": []}, receive, send
    )
    assert not called
    assert output[0]["status"] == 413


def test_upload_size_limit_precedes_multipart_parser(env):
    response = env[1].post(
        "/api/documents/upload",
        content=b"",
        headers={"Content-Length": str(9 * 1024 * 1024), "Content-Type": "multipart/form-data; boundary=x"},
    )
    assert response.status_code == 413


def test_all_supported_account_spacing_is_redacted():
    value = "Recipient DE59 9999 9999 0000 0010 01. Contact buyer@example.test."
    redacted, kinds = redact_text(value)
    assert "9999" not in redacted and "buyer@" not in redacted and "bank_account" in kinds
    # A supported country not present in the original five-country compact regex.
    redacted, _ = redact_text("FR76 3000 6000 0112 3456 7890 189")
    assert "3456" not in redacted


def test_sensitive_key_spellings_do_not_leak():
    result = safe_log(
        {
            "apiKey": "arbitrary-private-value",
            "access_token": "private-value",
            "input_tokens": 123,
            "iban": "DE59999999990000001001",
        }
    )
    assert result["apiKey"] == "[REDACTED]" and result["access_token"] == "[REDACTED]"
    assert result["input_tokens"] == 123 and "99999999" not in result["iban"]


def test_wrong_structured_guard_schema_holds_the_action(env):
    env[2].output = '{"unexpected":true}'
    _, p = prepare(env)
    assert p["decision"]["verdict"] == "review"


def test_missing_render_at_execution_is_held(env):
    doc, p = prepare(env)
    token = approve(env, p)
    (env[0].state.payments.documents / doc["id"] / "page-1.png").unlink()
    response = env[1].post("/api/proposals/" + p["id"] + "/execute", json={"approval_token": token})
    assert response.status_code == 403 and response.json()["error"] == "evidence_missing"


def test_supplier_verification_invalidates_previous_approval(env):
    _, p = prepare(env)
    token = approve(env, p)
    client = env[1]
    client.post("/api/session/persona", json={"role": "admin"})
    change = client.post(
        "/api/suppliers/nordlicht/verify-bank",
        json={
            "iban": p["payment"]["iban"],
            "verification_note": "Saved-contact independent verification demonstration.",
        },
    )
    assert change.status_code == 200
    client.post("/api/session/persona", json={"role": "reviewer"})
    assert (
        client.post("/api/proposals/" + p["id"] + "/execute", json={"approval_token": token}).status_code
        == 403
    )


def test_worker_evidence_hash_is_checked_before_acceptance(env):
    doc = import_case(env)
    folder = env[0].state.payments.documents / doc["id"]
    (folder / "page-1.png").write_bytes(b"tampered")
    env[0].state.store.execute("UPDATE documents SET status='queued' WHERE id=?", (doc["id"],))
    value = env[1].get("/api/documents/" + doc["id"]).json()
    assert value["status"] == "failed"
    assert "hash mismatch" in value["data"]["error"]


def test_policy_page_limit_is_applied_by_worker(env):
    # Two-page file rejected under a one-page policy before raster/OCR work.
    from pypdf import PdfWriter

    folder = env[0].state.payments.documents / "page-limit-test"
    folder.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(595, 842)
    writer.add_blank_page(595, 842)
    writer.write(folder / "input.pdf")
    try:
        process_pdf(folder, max_pages=1)
        raise AssertionError("Expected page bound rejection")
    except ValueError as exc:
        assert "1–1 pages" in str(exc)


def test_output_reservation_overrun_is_accounted_and_held(env):
    g = env[0].state.gateway
    actor = Principal(env[3]["workspace"], "operator", "overrun-test")
    reservation = g.reserve(actor, "qwen2.5:3b", 100, 100)
    g.settle(reservation, 10000, 1000, "qwen2.5:3b")
    assert g.store.one("SELECT status FROM reservations WHERE id=?", (reservation,))["status"] == "overrun"
    assert env[1].get("/api/session").json()["usage"]["tokens"] == 11000


def test_restart_preserves_receipt_session_and_budget(env):
    app, client, provider, _, _ = env
    _, p = prepare(env)
    token = approve(env, p)
    receipt = client.post("/api/proposals/" + p["id"] + "/execute", json={"approval_token": token}).json()
    cookie = client.cookies.get("rg_session")
    before = client.get("/api/session").json()["usage"]
    from renderguard.api import create_app

    restarted = create_app(
        app.state.store.root, app.state.payments.documents, provider=provider, embedded_worker=False
    )
    with TestClient(restarted) as second:
        second.cookies.set("rg_session", cookie)
        assert second.get("/api/receipts").json()[0]["id"] == receipt["id"]
        assert second.get("/api/session").json()["usage"] == before


def test_reference_assets_and_nonce_are_self_hosted(env):
    response = env[1].get("/docs")
    assert response.status_code == 200
    assert "/swagger-assets/swagger-ui-bundle.js" in response.text
    assert "'nonce-" in response.headers["Content-Security-Policy"]
    assert "cdn.jsdelivr" not in response.text
    assert env[1].get("/openapi.json").json()["info"]["title"] == "RenderGuard"


def test_hidden_purchase_order_is_compared(env):
    doc = import_case(env)
    doc["data"]["machine"]["obligation_ids"] = ["PO-9999-999"]
    assert env[0].state.payments.evidence_checks(env[3]["workspace"], doc)["verdict"] == "block"


def test_stale_authority_is_visible_before_reviewer_clicks(env):
    doc, p = prepare(env)
    assert not p["stale"]
    policy = env[0].state.gateway.catalog.get(env[3]["workspace"])[0].model_dump()
    policy["controls"]["semantic_threshold"] = 0.6
    env[0].state.gateway.catalog.update(env[3]["workspace"], policy)
    assert env[1].get("/api/documents/" + doc["id"]).json()["proposal"]["stale"]


def test_semantic_pdf_fields_agree_before_guard_intervention(env):
    for case in ("hidden-instruction", "visible-instruction"):
        doc = import_case(env, case)
        assert doc["evidence_decision"]["verdict"] == "allow"
        assert "execute_payment" in doc["data"]["machine_text"]
        env[2].injection = True
        p = env[1].post("/api/documents/" + doc["id"] + "/prepare").json()
        assert p["decision"]["verdict"] == "block"
        assert p["agent"]["mode"] == "held_by_semantic_guard"


def test_sdk_agent_only_receives_handles_and_cannot_read_full_master(env):
    doc = import_case(env)
    client = env[1]
    assert client.post("/api/agent/capability").status_code == 403
    client.post("/api/session/persona", json={"role": "admin"})
    issued = client.post("/api/agent/capability").json()
    headers = {"Authorization": "Bearer " + issued["agent_token"]}
    for route in [
        "/api/suppliers",
        "/api/obligations",
        "/api/documents/" + doc["id"],
        "/api/documents/" + doc["id"] + "/pages/1",
    ]:
        assert client.get(route, headers=headers).status_code == 403
    evidence = client.get("/api/agent/evidence/" + doc["id"], headers=headers)
    assert evidence.status_code == 200
    assert "DE59999999990000001001" not in evidence.text
    assert evidence.json()["visible_payment"]["account_ref"] == "account_1"
    proposal = client.post(
        "/api/sdk/propose",
        headers=headers,
        json={"document_id": doc["id"], "payment": evidence.json()["visible_payment"]},
    )
    assert proposal.status_code == 200 and proposal.json()["decision"]["verdict"] == "allow"
    assert "DE59999999990000001001" not in proposal.text
    assert proposal.json()["payment"]["account_ref"] == "account_1"
    assert (
        client.post("/api/proposals/" + proposal.json()["id"] + "/approve", headers=headers).status_code
        == 403
    )
    assert client.post("/api/session/persona", headers=headers, json={"role": "reviewer"}).status_code == 403


def test_agent_sdk_cannot_select_unrecognized_handle(env):
    doc = import_case(env)
    client = env[1]
    client.post("/api/session/persona", json={"role": "admin"})
    headers = {"Authorization": "Bearer " + client.post("/api/agent/capability").json()["agent_token"]}
    evidence = client.get("/api/agent/evidence/" + doc["id"], headers=headers).json()
    evidence["visible_payment"]["account_ref"] = "account_999"
    proposal = client.post(
        "/api/sdk/propose",
        headers=headers,
        json={"document_id": doc["id"], "payment": evidence["visible_payment"]},
    )
    assert proposal.status_code == 200 and proposal.json()["decision"]["verdict"] == "block"
