from concurrent.futures import ThreadPoolExecutor

import pytest
from conftest import selected_model

from renderguard.documents import money_minor, valid_iban
from renderguard.gateway import Denied, Principal


def actor(env, role="operator"):
    return Principal(env[3]["workspace"], role, "test-" + role)


def update(env, mutate):
    g = env[0].state.gateway
    p = g.catalog.get(env[3]["workspace"])[0].model_dump()
    mutate(p)
    g.catalog.update(env[3]["workspace"], p)


def test_dlp_redaction_and_block_toggle(env):
    g = env[0].state.gateway
    payload = {
        "model": selected_model(env),
        "text": "buyer@example.test sk-secret123456789012 DE59999999990000001001",
    }
    redacted = g.evaluate(actor(env), "model.request", payload)
    assert redacted["verdict"] == "allow"
    assert "sk-secret" not in redacted["payload"]["text"] and "buyer@" not in redacted["payload"]["text"]
    update(env, lambda p: p["controls"].update({"pii_action": "block"}))
    assert g.evaluate(actor(env), "model.request", payload)["verdict"] == "block"


@pytest.mark.parametrize(
    "kind,payload",
    [
        ("tool.call", {"tool": "execute_payment", "role": "reviewer"}),
        ("tool.call", {"tool": "send_email"}),
        ("model.request", {"model": "unapproved:latest", "text": "hi"}),
        ("resource.read", {"workspace": "other-workspace"}),
        ("mcp.discovery", {"url": "https://evil.example/mcp"}),
        (
            "mcp.discovery",
            {
                "url": "https://approved-mcp.example/mcp",
                "authorization_endpoint": "file:/c:/windows/system32/calc.exe",
            },
        ),
        ("model.load", {"format": "pickle", "path": "malicious.pkl"}),
    ],
)
def test_negative_interactions(env, kind, payload):
    assert env[0].state.gateway.evaluate(actor(env, "admin"), kind, payload)["verdict"] == "block"


def test_signature_removal_leaves_independent_endpoint_control(env):
    g = env[0].state.gateway
    g.catalog.update_feed(env[3]["workspace"], {"version": "empty-judge-edit", "entries": []})
    result = g.evaluate(
        actor(env, "admin"),
        "mcp.discovery",
        {"url": "file:/unsafe", "authorization_endpoint": "file:/unsafe"},
    )
    assert result["verdict"] == "block"
    assert next(c for c in result["checks"] if c["control"] == "signatures")["verdict"] == "pass"


def test_approved_mcp_and_registered_tool_positive(env):
    g = env[0].state.gateway
    assert (
        g.evaluate(
            actor(env, "admin"),
            "mcp.discovery",
            {"authorization_endpoint": "https://approved-mcp.example/authorize"},
        )["verdict"]
        == "allow"
    )
    assert g.evaluate(actor(env, "agent"), "tool.call", {"tool": "propose_payment"})["verdict"] == "allow"


@pytest.mark.parametrize("budget", ["model", "token", "cost", "concurrency"])
def test_resource_reservations_block_before_dispatch(env, budget):
    g = env[0].state.gateway
    if budget == "model":
        update(env, lambda p: p["budgets"].update({"max_model_calls": 0}))
    elif budget == "token":
        update(env, lambda p: p["budgets"].update({"max_tokens": 100}))
    elif budget == "cost":
        update(
            env,
            lambda p: (
                p["rates"][p["allowed_models"][0]].update({"input_microusd_per_token": 1000}),
                p["budgets"].update({"max_cost_microusd": 1}),
            ),
        )
    else:
        g.reserve(actor(env), selected_model(env), 100, 100)
    with pytest.raises(Denied):
        g.reserve(actor(env), selected_model(env), 200, 100)
    assert env[2].calls == 0


def test_parallel_budget_reservations_do_not_overspend(env):
    g = env[0].state.gateway

    def request(_):
        try:
            return g.reserve(actor(env), selected_model(env), 100, 100)
        except Denied:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        reservations = list(pool.map(request, range(8)))
    assert sum(x is not None for x in reservations) == 1


def test_accounting_uses_rates_frozen_at_dispatch(env):
    g = env[0].state.gateway
    update(
        env,
        lambda p: p["rates"][p["allowed_models"][0]].update(
            {"input_microusd_per_token": 10, "output_microusd_per_token": 20}
        ),
    )
    model = selected_model(env)
    reservation = g.reserve(actor(env), model, 100, 100)
    update(
        env,
        lambda p: p["rates"][p["allowed_models"][0]].update(
            {"input_microusd_per_token": 0, "output_microusd_per_token": 0}
        ),
    )
    g.settle(reservation, 50, 20, model)
    assert env[1].get("/api/session").json()["usage"]["cost"] == 900


def test_tool_budget(env):
    update(env, lambda p: p["budgets"].update({"max_tool_calls": 1}))
    g = env[0].state.gateway
    assert g.evaluate(actor(env), "tool.call", {"tool": "propose_payment"})["verdict"] == "allow"
    assert g.evaluate(actor(env), "tool.call", {"tool": "propose_payment"})["verdict"] == "block"


def test_invalid_policy_is_atomic_and_mandatory_release_controls_remain(env):
    app, client, _, session, _ = env
    client.post("/api/session/persona", json={"role": "admin"})
    original = client.get("/api/policy").json()
    broken = {**original["policy"], "invented_control": True}
    assert client.put("/api/policy", json=broken).status_code == 422
    assert client.get("/api/policy").json()["version"] == original["version"]
    broken = original["policy"]
    broken["controls"]["require_approval"] = False
    assert client.put("/api/policy", json=broken).status_code == 422


def test_executable_signature_fields_are_rejected(env):
    g = env[0].state.gateway
    with pytest.raises(ValueError):
        g.catalog.update_feed(
            env[3]["workspace"],
            {
                "version": "bad",
                "entries": [
                    {"id": "x", "kind": "model.request", "field": "text", "expression": '__import__("os")'}
                ],
            },
        )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1240.00", 124000),
        ("1,240.00", 124000),
        ("1.240,00", 124000),
        ("1240,00", 124000),
        ("1,240", None),
        ("1240.001", None),
        ("1e3", None),
    ],
)
def test_exact_decimal_amounts(value, expected):
    assert money_minor(value) == expected


def test_iban_normalization_does_not_repair_ocr_characters():
    assert valid_iban("DE59 9999 9999 0000 0010 01")
    assert not valid_iban("DE59999999990000001O01")
