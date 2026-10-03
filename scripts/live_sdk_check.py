"""Verify the proposal-only capability against the actual hosted gateway and local semantic model."""

import argparse
import json
import time
from pathlib import Path

import httpx

from scripts.evaluate import request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://renderguard.vvitovec.com")
    parser.add_argument("--output", default="evals/live-sdk.json")
    args = parser.parse_args()
    checks = []
    with httpx.Client(base_url=args.url, timeout=120) as human:
        session = request(human, "POST", "/api/demo/start")
        doc = request(human, "POST", "/api/documents/import-fixture", json={"fixture_id": "clean"})
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            doc = request(human, "GET", "/api/documents/" + doc["id"])
            if doc["status"] in ("ready", "failed"):
                break
            time.sleep(0.6)
        assert doc["status"] == "ready"
        request(human, "POST", "/api/session/persona", json={"role": "admin"})
        issued = request(human, "POST", "/api/agent/capability")
        with httpx.Client(
            base_url=args.url, headers={"Authorization": "Bearer " + issued["agent_token"]}, timeout=120
        ) as agent:
            evidence = request(agent, "GET", "/api/agent/evidence/" + doc["id"])
            assert evidence["visible_payment"]["account_ref"] == "account_1"
            assert "iban" not in evidence["visible_payment"]
            assert "DE99999999" not in json.dumps(evidence)
            checks.append("Agent receives minimized evidence and opaque account handle")
            assert agent.get("/api/suppliers").status_code == 403
            checks.append("Agent cannot read full supplier bank records")
            switched = agent.post("/api/session/persona", json={"role": "reviewer"})
            assert switched.status_code >= 400
            checks.append("Agent cannot switch into a human reviewer persona")
            proposal = request(
                agent,
                "POST",
                "/api/sdk/propose",
                json={"document_id": doc["id"], "payment": evidence["visible_payment"]},
            )
            assert proposal["decision"]["verdict"] == "allow"
            assert proposal["payment"]["account_ref"] == "account_1"
            assert "iban" not in proposal["payment"]
            checks.append("Real semantic guard accepts grounded proposal; bank account remains private")
            assert agent.post("/api/proposals/" + proposal["id"] + "/approve").status_code == 403
            checks.append("Agent cannot approve its own proposal")
            assert (
                agent.post(
                    "/api/proposals/" + proposal["id"] + "/execute", json={"approval_token": "forged"}
                ).status_code
                == 403
            )
            checks.append("Agent cannot release a payment using a forged approval")
        request(human, "POST", "/api/session/persona", json={"role": "reviewer"})
        approval = request(human, "POST", "/api/proposals/" + proposal["id"] + "/approve")
        receipt = request(
            human,
            "POST",
            "/api/proposals/" + proposal["id"] + "/execute",
            json={"approval_token": approval["approval_token"]},
        )
        assert receipt["bank_connected"] is False
        replay = request(
            human,
            "POST",
            "/api/proposals/" + proposal["id"] + "/execute",
            json={"approval_token": approval["approval_token"]},
        )
        assert receipt["id"] == replay["id"] and replay["idempotent_replay"]
        checks.append("Independent reviewer completes sandbox release with idempotent replay")
        report = {
            "recorded_at": time.time(),
            "base_url": args.url,
            "source_sha": session["source_sha"],
            "release_sha": session["release_sha"],
            "passed": len(checks),
            "total": 7,
            "scope": "Actual hosted capability API, isolated worker and real local semantic model; synthetic invoice and sandbox effect only",
            "checks": checks,
        }
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(f"Passed {len(checks)}/7 hosted SDK checks; no credentials recorded")


if __name__ == "__main__":
    main()
