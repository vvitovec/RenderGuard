"""A small proposal-only SDK client. Needs a scoped agent capability issued by an administrator."""

import argparse
import json
import os

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://renderguard.vvitovec.com")
    parser.add_argument("--document", required=True)
    args = parser.parse_args()
    token = os.environ.get("RENDERGUARD_AGENT_TOKEN")
    if not token:
        raise SystemExit(
            "Set RENDERGUARD_AGENT_TOKEN to the private capability issued by POST /api/agent/capability as Administrator."
        )
    with httpx.Client(base_url=args.url, headers={"Authorization": "Bearer " + token}, timeout=120) as client:
        response = client.get("/api/agent/evidence/" + args.document)
        response.raise_for_status()
        evidence = response.json()
        response = client.post(
            "/api/sdk/propose", json={"document_id": args.document, "payment": evidence["visible_payment"]}
        )
        response.raise_for_status()
        proposal = response.json()
    print(json.dumps({key: proposal[key] for key in ("id", "status", "payment", "decision")}, indent=2))
    print("Proposal only. Independent reviewer approval is required; this client cannot approve or release.")


if __name__ == "__main__":
    main()
