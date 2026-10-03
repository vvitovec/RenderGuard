import json
import shutil

import pytest
from fastapi.testclient import TestClient

from renderguard.api import ROOT, create_app
from renderguard.documents import process_pdf, write_result


class FakeProvider:
    """A named deterministic test double; never used by the demo or recorded live-model tests."""

    def __init__(self):
        self.calls = 0
        self.fail = False
        self.injection = False
        self.output = None
        self.messages = []

    async def chat(self, model, messages, schema, max_output, timeout):
        self.calls += 1
        self.messages.append(messages)
        if self.fail:
            raise TimeoutError("simulated provider failure")
        if "risk" in schema.get("properties", {}):
            value = {
                "risk": 0.99 if self.injection else 0.02,
                "reason": "Deterministic classifier test double.",
            }
        else:
            data = json.loads(messages[-1]["content"])["visible_payment"]
            value = {**data, "reason": "Deterministic proposal test double."}
        return {
            "content": self.output or json.dumps(value),
            "input_tokens": 400,
            "output_tokens": 60,
            "provider": "deterministic-test-double",
            "duration_ms": 1,
        }

    async def health(self):
        return {"available": True, "models": ["qwen2.5:3b"]}


@pytest.fixture(scope="session")
def evidence_cache(tmp_path_factory):
    root = tmp_path_factory.mktemp("actual-raster-ocr")
    cache = {}
    for item in json.loads((ROOT / "fixtures/manifest.json").read_text()):
        folder = root / item["id"]
        folder.mkdir()
        shutil.copy(ROOT / "fixtures" / item["filename"], folder / "input.pdf")
        try:
            evidence = process_pdf(folder)
        except Exception as exc:
            evidence = {"error": str(exc)[:400]}
        cache[item["id"]] = (folder, evidence)
    return cache


@pytest.fixture
def env(tmp_path, evidence_cache):
    provider = FakeProvider()
    app = create_app(tmp_path / "state", tmp_path / "documents", provider=provider, embedded_worker=False)
    with TestClient(app) as client:
        session = client.post("/api/demo/start").json()
        yield app, client, provider, session, evidence_cache


def import_case(env, case="clean"):
    app, client, _, _, cache = env
    response = client.post("/api/documents/import-fixture", json={"fixture_id": case})
    assert response.status_code == 200, response.text
    doc = response.json()
    folder = app.state.payments.documents / doc["id"]
    source, evidence = cache[case]
    for page in evidence.get("pages", []):
        shutil.copy(source / f"page-{page['page']}.png", folder / f"page-{page['page']}.png")
    write_result(folder, {"ok": True, "evidence": evidence} if "error" not in evidence
                 else {"ok": False, "error": evidence["error"]})
    response = client.get("/api/documents/" + doc["id"])
    assert response.status_code == 200, response.text
    return response.json()


def prepare(env, case="clean"):
    doc = import_case(env, case)
    response = env[1].post("/api/documents/" + doc["id"] + "/prepare")
    assert response.status_code == 200, response.text
    return doc, response.json()


def approve(env, proposal):
    client = env[1]
    assert client.post("/api/session/persona", json={"role": "reviewer"}).status_code == 200
    response = client.post("/api/proposals/" + proposal["id"] + "/approve")
    assert response.status_code == 200, response.text
    return response.json()["approval_token"]
