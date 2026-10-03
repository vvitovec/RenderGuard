"""Measure actual deterministic gateway overhead, including policy/catalog reads and SQLite audit."""

import argparse
import json
import platform
import tempfile
import time
from pathlib import Path

from renderguard.gateway import Gateway, OllamaProvider, Principal
from renderguard.masterdata import seed_workspace
from renderguard.policy import PolicyCatalog
from renderguard.store import Store, uid
from scripts.evaluate import ROOT, source_hash


def percentiles(values):
    values = sorted(values)
    return {
        "count": len(values),
        "p50_ms": round(values[len(values) // 2], 3),
        "p95_ms": round(values[min(len(values) - 1, int(len(values) * 0.95))], 3),
        "max_ms": round(max(values), 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--requests", type=int, default=300)
    parser.add_argument("--output", default="evals/performance.json")
    args = parser.parse_args()
    if not 20 <= args.requests <= 5000:
        raise SystemExit("Use 20–5000 bounded requests")
    samples = {"allowed": [], "blocked": []}
    with tempfile.TemporaryDirectory(prefix="renderguard-performance-") as tmp:
        store = Store(Path(tmp))
        workspace = uid()
        seed_workspace(store, workspace)
        provider = OllamaProvider("http://127.0.0.1:1")
        gateway = Gateway(
            store,
            PolicyCatalog(store, ROOT / "policies/default.yaml", ROOT / "signatures/catalog.json"),
            provider,
        )
        principal = Principal(workspace, "admin", "benchmark-only")
        for i in range(args.requests):
            negative = bool(i % 2)
            started = time.perf_counter()
            result = gateway.evaluate(
                principal,
                "mcp.discovery" if negative else "model.request",
                {"authorization_endpoint": "javascript:synthetic-metadata-only"}
                if negative
                else {
                    "model": "qwen2.5:7b",
                    "text": "Ordinary invoice payment terms; independent review required.",
                },
            )
            elapsed = (time.perf_counter() - started) * 1000
            assert result["verdict"] == ("block" if negative else "allow")
            samples["blocked" if negative else "allowed"].append(elapsed)
        assert provider.calls == 0
    report = {
        "recorded_at": time.time(),
        "source_sha": source_hash(),
        "host": platform.system() + " " + platform.machine(),
        "requests": args.requests,
        "passed": args.requests,
        "provider_calls": 0,
        "scope": "Sequential synthetic deterministic gateway checks, including policy/catalog reads, privacy/permissions and SQLite audit persistence. No model, OCR, payment execution or network request. Not a throughput/load benchmark.",
        "gateway": percentiles(samples["allowed"] + samples["blocked"]),
        "allowed": percentiles(samples["allowed"]),
        "blocked": percentiles(samples["blocked"]),
    }
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"requests": args.requests, "gateway": report["gateway"], "provider_calls": 0}))


if __name__ == "__main__":
    main()
