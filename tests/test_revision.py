import asyncio
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from conftest import approve, import_case, prepare, selected_model
from pypdf import PdfWriter

from renderguard.documents import process_pdf, write_result
from renderguard.gateway import Denied, OpenAICompatibleProvider, Principal
from renderguard.masterdata import seed_workspace
from renderguard.policy import PolicyCatalog
from renderguard.store import Store, canonical, now, uid


def actor(env, role="operator"):
    return Principal(env[3]["workspace"], role, "revision-" + role)


def policy_update(env, change):
    catalog = env[0].state.gateway.catalog
    policy = catalog.get(env[3]["workspace"])[0].model_dump()
    change(policy)
    catalog.update(env[3]["workspace"], policy)


def distinct_invoice(env, number):
    """A second synthetic source with another invoice id and the same full PO."""
    from reportlab.pdfgen import canvas

    response = env[1].post("/api/documents/import-fixture", json={"fixture_id": "clean"})
    folder = env[0].state.payments.documents / response.json()["id"]
    c = canvas.Canvas(str(folder / "input.pdf"), pagesize=(595, 842))
    c.setFont("Helvetica", 15)
    for i, text in enumerate(("Nordlicht Facilities GmbH", f"INVOICE {number}",
                              "Purchase order PO-2609-014", "TOTAL EUR 1240.00",
                              "IBAN DE59999999990000001001")):
        c.drawString(45, 760 - i * 50, text)
    c.save()
    source_hash = hashlib.sha256((folder / "input.pdf").read_bytes()).hexdigest()
    env[0].state.store.execute("UPDATE documents SET sha=? WHERE id=?", (source_hash, folder.name))
    write_result(folder, {"ok": True, "evidence": process_pdf(folder)})
    return env[1].get("/api/documents/" + folder.name).json()


def test_second_invoice_cannot_reuse_full_obligation(env):
    _, first = prepare(env)
    token = approve(env, first)
    assert env[1].post("/api/proposals/" + first["id"] + "/execute", json={"approval_token": token}).status_code == 200
    env[1].post("/api/session/persona", json={"role": "operator"})
    second = distinct_invoice(env, "NF-2026-105")
    result = env[1].post("/api/documents/" + second["id"] + "/prepare").json()
    assert result["decision"]["verdict"] == "block"
    assert any(c["control"] == "obligation_consumed" and c["verdict"] == "block"
               for c in result["decision"]["checks"])
    assert len(env[1].get("/api/receipts").json()) == 1


def test_two_preapproved_invoice_ids_have_one_concurrent_obligation_effect(env):
    _, first = prepare(env)
    second_doc = distinct_invoice(env, "NF-2026-105")
    second = env[1].post("/api/documents/" + second_doc["id"] + "/prepare").json()
    first_token = approve(env, first)
    second_token = approve(env, second)
    payments = env[0].state.payments

    def execute(item):
        proposal, token = item
        try:
            return payments.execute(actor(env, "reviewer"), proposal["id"], token)
        except Denied as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, ((first, first_token), (second, second_token))))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert len(env[1].get("/api/receipts").json()) == 1
    winner = next(result for result in results if isinstance(result, dict))
    proposal, token = (first, first_token) if winner["proposal_id"] == first["id"] else (second, second_token)
    assert payments.execute(actor(env, "reviewer"), proposal["id"], token)["idempotent_replay"]


def test_receipt_migration_preserves_ambiguous_history_and_locks_obligation(env):
    store = env[0].state.store
    ws = env[3]["workspace"]
    for i in range(2):
        store.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)",
                      (f"legacy-{i}", ws, f"legacy-proposal-{i}", f"legacy-invoice-{i}", now(),
                       canonical({"payment": {"obligation_id": "PO-2609-014", "amount_minor": 124000}})))
    restarted = Store(store.root)
    assert len(restarted.all("SELECT * FROM receipts WHERE workspace=?", (ws,))) == 2
    row = restarted.one("SELECT * FROM obligation_consumption WHERE workspace=?", (ws,))
    assert row["status"] == "ambiguous" and row["receipt"] is None
    doc = import_case(env)
    assert env[0].state.payments.evidence_checks(ws, doc)["verdict"] == "block"


async def test_both_representations_reach_semantic_guard_and_sdk(env):
    doc = import_case(env)
    doc["data"]["visible_text"] += "\nVisible-only harmless annotation."
    env[0].state.store.execute("UPDATE documents SET data=? WHERE id=?", (canonical(doc["data"]), doc["id"]))
    proposal = await env[0].state.payments.propose(actor(env), doc["id"], env[0].state.payments.candidate(doc))
    assert proposal["decision"]["verdict"] == "allow"
    classified = json.loads(env[2].messages[0][-1]["content"])["document_to_classify"]
    assert set(classified) == {"visible_ocr", "machine_text"}
    assert "Visible-only harmless annotation" in classified["visible_ocr"]
    assert "Visible-only harmless annotation" not in classified["machine_text"]
    response = env[1].get("/api/agent/evidence/" + doc["id"]).json()
    assert response["representations"] == classified
    assert "DE59999999990000001001" not in canonical(response)


def test_sdk_resolves_known_handle_other_than_account_one(env):
    doc = import_case(env)
    env[1].post("/api/session/persona", json={"role": "admin"})
    headers = {"Authorization": "Bearer " + env[1].post("/api/agent/capability").json()["agent_token"]}
    account = env[0].state.payments.candidate(doc)["iban"]
    with patch.object(env[0].state.payments, "handles", return_value={account: "account_2"}):
        evidence = env[1].get("/api/agent/evidence/" + doc["id"], headers=headers).json()
        response = env[1].post("/api/sdk/propose", headers=headers,
                              json={"document_id": doc["id"], "payment": evidence["visible_payment"]})
    assert response.status_code == 200 and response.json()["decision"]["verdict"] == "allow"
    assert response.json()["payment"]["account_ref"] == "account_2" and account not in response.text


async def test_signature_edit_during_sdk_guard_holds_original_authority(env):
    doc = import_case(env)
    g = env[0].state.gateway
    original = g.catalog.authority(env[3]["workspace"])
    old_chat = env[2].chat

    async def change_feed(*args):
        g.catalog.update_feed(env[3]["workspace"], {"version": "during-guard", "entries": [
            {"id": "deny-propose", "kind": "tool.call", "field": "tool", "forbidden_values": ["propose_payment"]}
        ]})
        return await old_chat(*args)

    env[2].chat = change_feed
    proposal = await env[0].state.payments.propose(actor(env), doc["id"], env[0].state.payments.candidate(doc))
    assert proposal["decision"]["verdict"] == "review" and proposal["stale"]
    assert proposal["binding"]["signature_hash"] == original["signature_hash"]
    with pytest.raises(Denied):
        env[0].state.payments.approve(actor(env, "reviewer"), proposal["id"])
    assert not env[0].state.store.all("SELECT * FROM receipts")


@pytest.mark.parametrize("usage", [None, {}, {"prompt_tokens": 10}, {"completion_tokens": 2},
                                    {"prompt_tokens": None, "completion_tokens": 2},
                                    {"prompt_tokens": "10", "completion_tokens": 2},
                                    {"prompt_tokens": -1, "completion_tokens": 2},
                                    {"prompt_tokens": True, "completion_tokens": 2}])
async def test_compatible_adapter_unknown_usage_is_pessimistic(env, usage):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": '{"ok":true}'}}], "usage": usage}

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return Response()

    policy_update(env, lambda p: p["rates"][p["allowed_models"][0]].update(
        {"input_microusd_per_token": 10, "output_microusd_per_token": 20}))
    g = env[0].state.gateway
    g.provider = OpenAICompatibleProvider("https://never-contacted.invalid", "synthetic-key")
    with patch("renderguard.gateway.httpx.AsyncClient", Client):
        await g.model(actor(env), [{"role": "user", "content": "hello"}], {}, "test", 100)
    row = g.store.one("SELECT * FROM reservations WHERE workspace=?", (env[3]["workspace"],))
    usage = env[1].get("/api/session").json()["usage"]
    assert row["status"] == "unknown"
    assert usage["tokens"] == row["tokens"] and usage["cost"] == row["cost"] > 0


async def test_explicit_zero_usage_is_distinct_from_unknown(env):
    g = env[0].state.gateway
    model = selected_model(env)
    reservation = g.reserve(actor(env), model, 100, 100)
    g.settle(reservation, 0, 0, model)
    assert g.store.one("SELECT status FROM reservations WHERE id=?", (reservation,))["status"] == "complete"
    assert env[1].get("/api/session").json()["usage"]["tokens"] == 0


@pytest.mark.parametrize("cause", ["timeout", "cancel", "authority"])
async def test_no_dispatch_queue_failure_refunds_holds_but_counts_attempt(env, cause):
    g = env[0].state.gateway
    policy_update(env, lambda p: (p["budgets"].update({"timeout_seconds": 1}),
                                  p["rates"][p["allowed_models"][0]].update({"input_microusd_per_token": 10})))
    await g.semaphore.acquire()
    task = asyncio.create_task(g.model(actor(env), [{"role": "user", "content": "hello"}], {}, "test", 100))
    await asyncio.sleep(0.02)
    if cause == "cancel":
        task.cancel()
    elif cause == "authority":
        g.catalog.update_feed(env[3]["workspace"], {"version": "queued-edit", "entries": []})
        g.semaphore.release()
    try:
        with pytest.raises((Denied, asyncio.CancelledError)):
            await task
    finally:
        if cause != "authority":
            g.semaphore.release()
    usage = env[1].get("/api/session").json()["usage"]
    assert env[2].calls == 0 and usage["model_calls"] == 1
    assert usage["tokens"] == usage["cost"] == usage["reserved_tokens"] == usage["reserved_cost"] == usage["active_calls"] == 0


async def test_shared_model_admission_is_bounded_without_dispatch(env):
    g = env[0].state.gateway
    g.admission_limit = 1
    await g.semaphore.acquire()
    first = asyncio.create_task(g.model(actor(env), [{"role": "user", "content": "hello"}], {}, "test", 100))
    await asyncio.sleep(0.02)
    other = uid()
    seed_workspace(g.store, other)
    with pytest.raises(Denied) as denied:
        await g.model(Principal(other, "operator", "other"), [{"role": "user", "content": "hello"}], {}, "test", 100)
    assert denied.value.code == "global_admission"
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    g.semaphore.release()
    assert env[2].calls == 0 and g.admitted == 0
    assert g.store.one("SELECT reserved_tokens,tokens FROM workspaces WHERE id=?", (other,)) == {"reserved_tokens": 0, "tokens": 0}


@pytest.mark.parametrize("overrun", ["input", "output"])
async def test_provider_overrun_is_accounted_and_response_held(env, overrun):
    g = env[0].state.gateway

    async def chat(*args):
        return {"content": '{"ok":true}', "input_tokens": 10000 if overrun == "input" else 10,
                "output_tokens": 1000 if overrun == "output" else 10}

    g.provider.chat = chat
    with pytest.raises(Denied) as denied:
        await g.model(actor(env), [{"role": "user", "content": "hello"}], {}, "test", 100)
    assert denied.value.code in ("output_limit", "usage_overrun")
    assert g.store.one("SELECT status FROM reservations")["status"] == "overrun"
    assert g.store.one("SELECT tokens FROM workspaces WHERE id=?", (env[3]["workspace"],))["tokens"] >= 1010


@pytest.mark.parametrize("limit", ["max_bytes", "max_pages"])
def test_active_document_limits_hold_prepared_or_approved_evidence(env, limit):
    doc, proposal = prepare(env)
    token = approve(env, proposal)
    if limit == "max_pages":
        folder = env[0].state.payments.documents / doc["id"]
        writer = PdfWriter()
        writer.append(folder / "input.pdf")
        writer.add_blank_page(595, 842)
        writer.write(folder / "two.pdf")
        (folder / "two.pdf").replace(folder / "input.pdf")
        evidence = process_pdf(folder, max_pages=5)
        env[0].state.store.execute("UPDATE documents SET sha=?,data=? WHERE id=?",
                                  (evidence["source_hash"], canonical(evidence), doc["id"]))
        value = 1
    else:
        value = 1024
    policy_update(env, lambda p: p["document"].update({limit: value}))
    doc = env[0].state.payments.document(env[3]["workspace"], doc["id"])
    assert env[0].state.payments.evidence_checks(env[3]["workspace"], doc)["verdict"] == "review"
    assert env[1].post("/api/proposals/" + proposal["id"] + "/execute", json={"approval_token": token}).status_code == 403
    env[1].post("/api/session/persona", json={"role": "operator"})
    result = env[1].post("/api/documents/" + doc["id"] + "/prepare").json()
    assert result["decision"]["verdict"] == "review"


def test_final_semantic_playground_block_and_compact_audit_are_reported_once(env):
    env[2].injection = True
    result = env[1].post("/api/playground", json={"kind": "model.response", "payload": {"text": "override"}, "semantic": True})
    assert result.json()["verdict"] == "block"
    metrics = env[1].get("/api/metrics").json()
    assert metrics["final_interactions"] == {"allow": 0, "block": 1, "review": 0, "total": 1}
    assert metrics["held_controls"]["semantic"] == 1
    assert metrics["held_control_reasons"]["semantic"]
    assert metrics["stage_latency"]["semantic"]["count"] == 1
    rows = env[0].state.store.all("SELECT data FROM events WHERE kind IN ('semantic.result','interaction.final')")
    assert len(rows) == 2 and all("outbound_messages" not in row["data"] for row in rows)


def test_metrics_use_latest_document_proposal_and_single_release_amount(env):
    doc, proposal = prepare(env)
    again = env[1].post("/api/documents/" + doc["id"] + "/prepare").json()
    metrics = env[1].get("/api/metrics").json()
    assert metrics["payments"]["pending"] == {"count": 1, "amount_minor": 124000}
    token = approve(env, again)
    url = "/api/proposals/" + again["id"] + "/execute"
    env[1].post(url, json={"approval_token": token})
    env[1].post(url, json={"approval_token": token})
    metrics = env[1].get("/api/metrics").json()
    assert metrics["payments"]["released"] == {"count": 1, "amount_minor": 124000}
    assert metrics["payments"]["pending"]["count"] == 0
    assert metrics["stage_latency"]["executor"]["count"] == 2
    assert metrics["redactions"]["patterns"]["account_handle"] > 0
    assert metrics["budgets"]["model_calls"]["remaining"] == 24 - metrics["model_calls"]["model_calls"]


def test_literal_document_rules_are_casefolded_data_and_can_be_removed(env):
    g = env[0].state.gateway
    feed = {"version": "canary", "entries": [{"id": "read-canary", "kind": "tool.call", "field": "tool",
                                              "forbidden_values": ["READ_EVIDENCE"]}]}
    assert g.evaluate(actor(env), "tool.call", {"tool": "read_evidence"})["verdict"] == "allow"
    g.catalog.update_feed(env[3]["workspace"], feed)
    assert g.evaluate(actor(env), "tool.call", {"tool": "read_evidence"})["verdict"] == "block"
    g.catalog.update_feed(env[3]["workspace"], {"version": "removed", "entries": []})
    assert g.evaluate(actor(env), "tool.call", {"tool": "read_evidence"})["verdict"] == "allow"
    feed["entries"] = [{"id": "document-rule", "kind": "document.text", "field": "text",
                        "forbidden_substrings": ["STRASSE BYPASS"]}]
    g.catalog.update_feed(env[3]["workspace"], feed)
    assert g.evaluate(actor(env), "document.text", {"text": "Straße bypass"})["verdict"] == "block"
    with pytest.raises(ValueError):
        g.catalog.update_feed(env[3]["workspace"], {"version": "bad", "entries": [
            {"id": "bad", "kind": "document.text", "field": "text", "forbidden_substrings": [""]}
        ]})


@pytest.mark.parametrize("profile,expected", [("strict", "pass"), ("balanced", "review")])
async def test_balanced_profile_has_a_real_semantic_review_band(env, profile, expected):
    policy_update(env, lambda p: p.update({"profile": profile}))
    env[2].output = '{"risk":0.65,"reason":"Uncertain behavioral instruction"}'
    result = await env[0].state.gateway.semantic(actor(env), "ordinary test input")
    assert result["verdict"] == expected


def test_workspace_delta_inherits_changed_baseline_and_exposes_override_keys(env, tmp_path):
    import yaml

    catalog = env[0].state.gateway.catalog
    path = tmp_path / "baseline.yaml"
    path.write_text(catalog.path.read_text())
    catalog.path = path
    policy_update(env, lambda p: p["controls"].update({"semantic_threshold": 0.8}))
    row = catalog.store.one("SELECT policy FROM workspaces WHERE id=?", (env[3]["workspace"],))
    assert json.loads(row["policy"]) == {"controls": {"semantic_threshold": 0.8}}
    base = yaml.safe_load(path.read_text())
    base["budgets"]["max_tool_calls"] = 20
    path.write_text(yaml.safe_dump(base))
    response = env[1].get("/api/policy").json()
    assert response["policy"]["budgets"]["max_tool_calls"] == 20
    assert response["policy"]["controls"]["semantic_threshold"] == 0.8
    assert response["overridden_keys"] == ["controls.semantic_threshold"]
    assert response["baseline_version"]


def test_legacy_full_policy_migrates_without_losing_differing_values(env):
    catalog = env[0].state.gateway.catalog
    ws = env[3]["workspace"]
    old = catalog.get(ws)[0].model_dump()
    old["controls"]["semantic_threshold"] = 0.9
    catalog.store.execute("UPDATE workspaces SET policy=? WHERE id=?", (canonical(old), ws))
    restarted = PolicyCatalog(catalog.store, catalog.path, catalog.signature_path)
    assert restarted.get(ws)[0].controls.semantic_threshold == 0.9
    assert json.loads(catalog.store.one("SELECT policy FROM workspaces WHERE id=?", (ws,))["policy"]) == {
        "controls": {"semantic_threshold": 0.9}
    }


def test_provenance_reports_current_digest_without_rewriting_recorded_sha(env):
    from renderguard.api import ROOT

    target = ROOT / "evals/live-pipeline.json"
    if not target.exists():
        target = ROOT / "evals/results.json"
    recorded = json.loads(target.read_text()) if target.exists() else {}
    evaluation = env[1].get("/api/evaluation").json()
    assert evaluation["current_source_sha"] == env[1].get("/api/session").json()["source_sha"]
    assert evaluation.get("source_sha") == recorded.get("source_sha")


@pytest.mark.parametrize("case", ["hybrid-benign", "alternate-layout"])
def test_new_legitimate_templates_complete_real_evidence_and_sandbox_flow(env, case):
    doc, proposal = prepare(env, case)
    assert doc["evidence_decision"]["verdict"] == proposal["decision"]["verdict"] == "allow"
    token = approve(env, proposal)
    result = env[1].post("/api/proposals/" + proposal["id"] + "/execute", json={"approval_token": token})
    assert result.status_code == 200 and result.json()["bank_connected"] is False


def test_real_visible_only_attack_reaches_guard_when_literal_rule_removed(env):
    doc = import_case(env, "hybrid-visible-instruction")
    assert doc["evidence_decision"]["verdict"] == "allow"
    assert "execute_payment" in doc["data"]["visible_text"] and "execute_payment" not in doc["data"]["machine_text"]
    env[0].state.gateway.catalog.update_feed(env[3]["workspace"], {"version": "semantic-only", "entries": []})
    env[2].injection = True
    result = env[1].post("/api/documents/" + doc["id"] + "/prepare").json()
    assert result["decision"]["verdict"] == "block" and result["agent"]["mode"] == "held_by_semantic_guard"
    payload = json.loads(env[2].messages[0][-1]["content"])["document_to_classify"]
    assert "execute_payment" in payload["visible_ocr"] and "execute_payment" not in payload["machine_text"]


def test_hidden_nonbehavioral_prose_is_reviewed_with_configurable_action(env):
    doc = import_case(env, "hidden-prose")
    result = env[1].post("/api/documents/" + doc["id"] + "/prepare").json()
    assert result["decision"]["verdict"] == "review" and env[2].calls == 0
    policy_update(env, lambda p: p["controls"].update({"hidden_text_action": "block"}))
    assert env[0].state.payments.evidence_checks(env[3]["workspace"], doc)["verdict"] == "block"
    policy_update(env, lambda p: p["controls"].update({"hidden_text_min_tokens": 1000}))
    assert env[0].state.payments.evidence_checks(env[3]["workspace"], doc)["verdict"] == "allow"


def test_oversized_prose_is_held_by_bounded_comparison_before_model(env):
    doc = import_case(env)
    doc["data"]["machine_text"] += "\n" + "unseencontract " * 10000
    decision = env[0].state.payments.evidence_checks(env[3]["workspace"], doc)
    assert decision["verdict"] == "review"
    check = next(item for item in decision["checks"] if item["control"] == "hidden_text")
    assert not check["comparison_bounded"]


def test_literal_instruction_rule_does_not_block_ordinary_invoice_replacement(env):
    result = env[0].state.gateway.evaluate(actor(env), "document.text", {
        "text": "Please replace the previous invoice and include this invoice number in the payment reference."
    })
    assert result["verdict"] == "allow"


def test_unreadable_document_is_held_without_model_or_release(env):
    doc, proposal = prepare(env, "unreadable")
    assert doc["status"] == "ready" and proposal["decision"]["verdict"] in ("block", "review")
    assert env[2].calls == 0
    env[1].post("/api/session/persona", json={"role": "reviewer"})
    assert env[1].post("/api/proposals/" + proposal["id"] + "/approve").status_code == 403


def test_malformed_pdf_worker_failure_never_becomes_ready(env, tmp_path):
    from renderguard.worker import run_one

    folder = tmp_path / "malformed"
    folder.mkdir()
    (folder / "input.pdf").write_bytes(b"%PDF-1.7\nmalformed synthetic parser test")
    (folder / "request.json").write_text(canonical({"max_pages": 5}))
    run_one(folder)
    assert json.loads((folder / "result.json").read_text())["ok"] is False


def test_receipt_keeps_approver_and_executor_attribution_through_replay(env):
    _, proposal = prepare(env)
    payments = env[0].state.payments
    workspace = env[3]["workspace"]
    approval = payments.approve(Principal(workspace, "reviewer", "reviewer-A"), proposal["id"])
    receipt = payments.execute(Principal(workspace, "reviewer", "reviewer-B"), proposal["id"], approval["approval_token"])
    assert receipt["approver"] == "reviewer-A" and receipt["executor"] == "reviewer-B"
    replay = payments.execute(Principal(workspace, "reviewer", "reviewer-C"), proposal["id"], approval["approval_token"])
    assert replay["id"] == receipt["id"] and replay["idempotent_replay"]
    assert replay["approver"] == "reviewer-A" and replay["executor"] == "reviewer-B"
    audit = env[0].state.store.one("SELECT data FROM events WHERE workspace=? AND kind='payment.released'", (workspace,))
    effect = json.loads(audit["data"])
    assert effect["approver"] == "reviewer-A" and effect["executor"] == "reviewer-B"


@pytest.mark.parametrize("status", ["queued", "failed"])
def test_agent_sdk_holds_unready_evidence_before_handle_resolution(env, status):
    client = env[1]
    doc = client.post("/api/documents/import-fixture", json={"fixture_id": "clean"}).json()
    if status == "failed":
        env[0].state.store.execute("UPDATE documents SET status='failed',data=? WHERE id=?",
                                  (canonical({"error": "Synthetic worker failure"}), doc["id"]))
    client.post("/api/session/persona", json={"role": "admin"})
    token = client.post("/api/agent/capability").json()["agent_token"]
    response = client.post("/api/sdk/propose", headers={"Authorization": "Bearer " + token}, json={
        "document_id": doc["id"], "payment": {
            "supplier_id": "nordlicht", "obligation_id": "PO-2609-014",
            "invoice_number": "NF-2026-104", "account_ref": "account_1",
            "amount_minor": 124000, "currency": "EUR",
        }
    })
    assert response.status_code == 409 and response.json()["error"] == "evidence_not_ready"
    assert response.json()["verdict"] == "review" and env[2].calls == 0
    assert not env[0].state.store.all("SELECT * FROM proposals")
    assert not env[0].state.store.all("SELECT * FROM receipts")
