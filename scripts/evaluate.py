"""Reproducible PDF evidence corpus; optional full live-model / approval / release run."""

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path

import httpx

from renderguard.documents import process_pdf
from renderguard.gateway import Gateway, OllamaProvider
from renderguard.masterdata import seed_workspace
from renderguard.payments import Payments
from renderguard.policy import PolicyCatalog
from renderguard.privacy import safe_log
from renderguard.store import Store, now, uid

ROOT = Path(__file__).resolve().parents[1]


def source_hash():
    from renderguard.provenance import source_hash as current_source_hash

    return current_source_hash()


def offline(item, root):
    workspace = uid()
    store = Store(root / "state")
    seed_workspace(store, workspace)
    gateway = Gateway(
        store,
        PolicyCatalog(store, ROOT / "policies/default.yaml", ROOT / "signatures/catalog.json"),
        OllamaProvider("http://127.0.0.1:11434"),
    )
    payments = Payments(store, gateway, root / "documents")
    folder = payments.documents / uid()
    folder.mkdir(parents=True)
    shutil.copy(ROOT / "fixtures" / item["filename"], folder / "input.pdf")
    evidence = process_pdf(folder)
    doc = {
        "id": folder.name,
        "workspace": workspace,
        "supplier_id": item["supplier_id"],
        "obligation_id": item["obligation_id"],
        "status": "ready",
        "sha": evidence["source_hash"],
        "data": evidence,
    }
    return payments.evidence_checks(workspace, doc), {
        "document_ms": evidence["processing_ms"],
        "render_hash": evidence["pages"][0]["render_hash"],
    }


def request(client, method, path, **kwargs):
    result = client.request(method, path, **kwargs)
    result.raise_for_status()
    return result.json()


def live(item, url):
    started = time.monotonic()
    with httpx.Client(base_url=url, timeout=120) as client:
        session = request(client, "POST", "/api/demo/start")
        doc = request(client, "POST", "/api/documents/import-fixture", json={"fixture_id": item["id"]})
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            doc = request(client, "GET", "/api/documents/" + doc["id"])
            if doc["status"] in ("ready", "failed"):
                break
            time.sleep(0.6)
        proposal = request(client, "POST", "/api/documents/" + doc["id"] + "/prepare")
        result = proposal["decision"]
        telemetry = {
            "agent_mode": proposal["agent"]["mode"],
            "document_ms": doc["data"].get("processing_ms"),
            "release_sha": session["release_sha"],
            "provider_calls": request(client, "GET", "/api/session")["usage"]["model_calls"],
        }
        if result["verdict"] == "allow":
            request(client, "POST", "/api/session/persona", json={"role": "reviewer"})
            approval = request(client, "POST", "/api/proposals/" + proposal["id"] + "/approve")
            receipt = request(
                client,
                "POST",
                "/api/proposals/" + proposal["id"] + "/execute",
                json={"approval_token": approval["approval_token"]},
            )
            replay = request(
                client,
                "POST",
                "/api/proposals/" + proposal["id"] + "/execute",
                json={"approval_token": approval["approval_token"]},
            )
            assert receipt["id"] == replay["id"] and replay["idempotent_replay"]
            assert receipt["bank_connected"] is False
            telemetry.update({"sandbox_receipt": receipt["id"], "idempotent_verified": True})
        telemetry["stage_latency"] = request(client, "GET", "/api/metrics").get("stage_latency", {})
        telemetry["end_to_end_ms"] = round((time.monotonic() - started) * 1000)
        return result, telemetry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        help="Run full real-model / isolated-worker / reviewer / sandbox-release flow against this URL",
    )
    parser.add_argument("--output", default="evals/results.json")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "fixtures/manifest.json").read_text())
    cases = []
    with tempfile.TemporaryDirectory(prefix="renderguard-evidence-") as tmp:
        for item in manifest:
            expected = item["expected"] if args.url else item.get("evidence_expected", item["expected"])
            try:
                result, telemetry = live(item, args.url) if args.url else offline(item, Path(tmp))
                case = {
                    "id": item["id"],
                    "title": item["title"],
                    "expected": expected,
                    "full_workflow_expected": item["expected"],
                    "verdict": result["verdict"],
                    "passed": result["verdict"] == expected,
                    "failures": [
                        {k: v for k, v in c.items() if k != "telemetry"}
                        for c in result["checks"]
                        if c["verdict"] in ("block", "review")
                    ],
                    **telemetry,
                }
            except Exception as exc:
                case = {
                    "id": item["id"],
                    "expected": expected,
                    "verdict": "error",
                    "passed": False,
                    "error": type(exc).__name__ + ": " + str(exc)[:300],
                }
            cases.append(safe_log(case))
            print(item["id"], case["verdict"], "PASS" if case["passed"] else "FAIL", flush=True)
    values = [c["end_to_end_ms"] for c in cases if "end_to_end_ms" in c]
    values.sort()
    report = {
        "status": "complete",
        "mode": "full_live_workflow" if args.url else "offline_evidence_only",
        "generated_at": now(),
        "source_sha": source_hash(),
        "total": len(cases),
        "passed": sum(c["passed"] for c in cases),
        "provider_note": "Real local Qwen2.5:3b, deployed PDF worker and sandbox releases"
        if args.url
        else "Actual PDFium raster, Tesseract OCR and EPC decoding; no model was dispatched",
        "scope": "Synthetic corpus only; this is not a general fraud detection benchmark.",
        "false_blocks_on_positive_cases": sum(
            c["expected"] == "allow" and c["verdict"] != "allow" for c in cases
        ),
        "unsafe_allows_on_negative_cases": sum(
            c["expected"] != "allow" and c["verdict"] == "allow" for c in cases
        ),
        "p95_end_to_end_ms": values[min(len(values) - 1, int(len(values) * 0.95))] if values else None,
        "cases": cases,
    }
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Saved {report['passed']}/{len(cases)} to {output}")
    raise SystemExit(0 if report["passed"] == len(cases) else 1)


if __name__ == "__main__":
    main()
