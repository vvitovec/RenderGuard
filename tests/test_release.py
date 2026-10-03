import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import approve, import_case, prepare

from renderguard.gateway import Principal
from renderguard.store import canonical, now


@pytest.mark.parametrize("case", ["clean", "no-qr", "spaced-iban", "linden", "atlas", "scanned", "ocr-layer"])
def test_positive_evidence_and_real_raster(env, case):
    doc = import_case(env, case)
    assert doc["status"] == "ready"
    assert doc["data"]["renderer"] == "PDFium (no V8)"
    assert doc["data"]["pages"][0]["lines"]
    assert doc["evidence_decision"]["verdict"] == "allow", doc["evidence_decision"]


@pytest.mark.parametrize(
    "case",
    ["hidden-account", "qr-swap", "qr-amount", "bank-change", "hidden-total", "ambiguous", "overbilling"],
)
def test_negative_evidence_never_dispatches_model(env, case):
    _, proposal = prepare(env, case)
    assert proposal["decision"]["verdict"] == "block"
    assert proposal["agent"]["mode"] == "held_before_model"
    assert env[2].calls == 0
    env[1].post("/api/session/persona", json={"role": "reviewer"})
    assert env[1].post("/api/proposals/" + proposal["id"] + "/approve").status_code == 403


def test_complete_release_and_idempotent_retry(env):
    doc, proposal = prepare(env)
    assert proposal["status"] == "awaiting_approval"
    assert env[2].calls == 2
    assert "DE59999999990000001001" not in json.dumps(env[2].messages)
    token = approve(env, proposal)
    url = "/api/proposals/" + proposal["id"] + "/execute"
    first = env[1].post(url, json={"approval_token": token})
    assert first.status_code == 200, first.text
    assert first.json()["bank_connected"] is False
    replay = env[1].post(url, json={"approval_token": token})
    assert replay.json()["id"] == first.json()["id"]
    assert replay.json()["idempotent_replay"]
    assert len(env[1].get("/api/receipts").json()) == 1
    env[1].post("/api/session/persona", json={"role": "operator"})
    duplicate = env[1].post("/api/documents/" + doc["id"] + "/prepare").json()
    assert duplicate["decision"]["verdict"] == "block"


def test_operator_cannot_self_approve_or_change_master(env):
    _, p = prepare(env)
    assert env[1].post("/api/proposals/" + p["id"] + "/approve").status_code == 403
    assert (
        env[1]
        .post(
            "/api/suppliers/nordlicht/verify-bank",
            json={"iban": p["payment"]["iban"], "verification_note": "Independent saved-contact callback."},
        )
        .status_code
        == 403
    )


def test_agent_cannot_approve_execute_or_switch_role(env):
    app, client, _, session, _ = env
    _, p = prepare(env)
    token = app.state.store.sign(
        {
            "aud": "session",
            "workspace": session["workspace"],
            "role": "agent",
            "sub": "invoice-agent",
            "exp": now() + 300,
        }
    )
    headers = {"Authorization": "Bearer " + token}
    assert client.post("/api/session/persona", json={"role": "reviewer"}, headers=headers).status_code == 403
    assert client.post("/api/proposals/" + p["id"] + "/approve", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/proposals/" + p["id"] + "/execute", json={"approval_token": "forged"}, headers=headers
        ).status_code
        == 403
    )


@pytest.mark.parametrize("change", ["payment", "supplier", "policy", "signature", "source", "render"])
def test_approval_bound_to_exact_mutable_authorities(env, change):
    app, client, _, session, _ = env
    doc, p = prepare(env)
    token = approve(env, p)
    store = app.state.store
    workspace = session["workspace"]
    if change == "payment":
        store.execute(
            "UPDATE proposals SET payment=? WHERE id=?",
            (canonical({**p["payment"], "amount_minor": 124001}), p["id"]),
        )
    elif change == "supplier":
        s = app.state.payments.supplier(workspace, "nordlicht")
        s["version"] += 1
        store.execute(
            "UPDATE suppliers SET data=? WHERE workspace=? AND id=?", (canonical(s), workspace, "nordlicht")
        )
    elif change == "policy":
        policy = app.state.gateway.catalog.get(workspace)[0].model_dump()
        policy["controls"]["semantic_threshold"] = 0.6
        app.state.gateway.catalog.update(workspace, policy)
    elif change == "signature":
        app.state.gateway.catalog.update_feed(workspace, {"version": "judge-edit", "entries": []})
    else:
        f = app.state.payments.documents / doc["id"] / ("input.pdf" if change == "source" else "page-1.png")
        f.write_bytes(f.read_bytes() + b"changed")
    response = client.post("/api/proposals/" + p["id"] + "/execute", json={"approval_token": token})
    assert response.status_code == 403, response.text
    assert client.get("/api/receipts").json() == []


def test_expired_approval(env):
    _, p = prepare(env)
    token = approve(env, p)
    env[0].state.store.execute("UPDATE approvals SET expires=? WHERE proposal=?", (now() - 1, p["id"]))
    assert (
        env[1].post("/api/proposals/" + p["id"] + "/execute", json={"approval_token": token}).status_code
        == 403
    )


def test_post_approval_payment_override_is_not_accepted(env):
    _, p = prepare(env)
    token = approve(env, p)
    response = env[1].post(
        "/api/proposals/" + p["id"] + "/execute", json={"approval_token": token, "amount_minor": 1}
    )
    assert response.status_code == 422


def test_parallel_execution_has_one_effect(env):
    app, _, _, session, _ = env
    _, p = prepare(env)
    token = approve(env, p)
    actor = Principal(session["workspace"], "reviewer", "parallel-reviewer")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: app.state.payments.execute(actor, p["id"], token), range(8)))
    assert len({r["id"] for r in results}) == 1
    assert sum(not r["idempotent_replay"] for r in results) == 1


def test_workspace_document_and_receipt_isolation(env):
    doc, p = prepare(env)
    old = env[3]["workspace"]
    env[1].post("/api/demo/start")
    assert env[1].get("/api/documents/" + doc["id"]).status_code == 403
    assert env[1].get("/api/documents/" + doc["id"] + "/pages/1").status_code == 403
    assert env[1].post("/api/proposals/" + p["id"] + "/approve").status_code == 403
    assert env[1].get("/api/documents").json() == []
    assert env[1].get("/api/session").json()["workspace"] != old


def test_semantic_injection_holds_an_otherwise_valid_invoice(env):
    env[2].injection = True
    _, p = prepare(env)
    assert p["decision"]["verdict"] == "block"
    assert env[2].calls == 1


def test_sdk_does_not_bypass_semantic_control(env):
    doc = import_case(env)
    env[2].injection = True
    payment = env[0].state.payments.candidate(doc)
    response = env[1].post("/api/sdk/propose", json={"document_id": doc["id"], "payment": payment})
    assert response.status_code == 200
    assert response.json()["decision"]["verdict"] == "block"


def test_sdk_action_mismatch_blocked_without_model(env):
    doc = import_case(env)
    payment = {**env[0].state.payments.candidate(doc), "amount_minor": 1}
    p = env[1].post("/api/sdk/propose", json={"document_id": doc["id"], "payment": payment}).json()
    assert p["decision"]["verdict"] == "block"
    assert env[2].calls == 0


def test_provider_failure_fails_closed_and_accounts_reservation(env):
    env[2].fail = True
    _, p = prepare(env)
    assert p["decision"]["verdict"] == "review"
    usage = env[1].get("/api/session").json()["usage"]
    assert usage["tokens"] > 0 and usage["reserved_tokens"] == 0 and usage["active_calls"] == 0


def test_invalid_model_json_fails_closed(env):
    env[2].output = "{invalid"
    _, p = prepare(env)
    assert p["decision"]["verdict"] == "review"


def test_observe_policy_cannot_execute(env):
    app, client, _, session, _ = env
    policy = app.state.gateway.catalog.get(session["workspace"])[0].model_dump()
    policy["profile"] = "observe"
    app.state.gateway.catalog.update(session["workspace"], policy)
    _, p = prepare(env)
    client.post("/api/session/persona", json={"role": "reviewer"})
    assert client.post("/api/proposals/" + p["id"] + "/approve").status_code == 403


def test_failed_or_missing_evidence_is_never_an_allow(env):
    doc = import_case(env)
    env[0].state.store.execute(
        "UPDATE documents SET status='failed',data=? WHERE id=?",
        (canonical({"error": "unreadable"}), doc["id"]),
    )
    p = env[1].post("/api/documents/" + doc["id"] + "/prepare").json()
    assert p["decision"]["verdict"] == "review"


def test_audit_export_redacts_secrets_and_approval_tokens(env):
    _, p = prepare(env)
    token = approve(env, p)
    env[0].state.store.event(
        env[3]["workspace"],
        "probe",
        "block",
        "privacy",
        {"approval_token": token, "text": "sk-testcredential123456789 buyer@example.test"},
    )
    text = env[1].get("/api/audit/export").text
    assert token not in text and "sk-testcredential123456789" not in text and "buyer@example.test" not in text


def test_cross_origin_write_denied(env):
    assert env[1].post("/api/demo/start", headers={"Origin": "https://attacker.example"}).status_code == 403


def test_no_capability_no_private_data(env):
    env[1].cookies.clear()
    assert env[1].get("/api/documents").status_code == 401


def test_malformed_and_forged_capabilities(env):
    for token in ["junk", "e30.invalid", "a.b.c"]:
        assert env[1].get("/api/documents", headers={"Authorization": "Bearer " + token}).status_code == 401
