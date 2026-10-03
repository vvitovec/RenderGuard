# Final verification evidence

Recorded on 3 October 2026 against the actual hosted RenderGuard gateway, isolated Linux PDF worker and dedicated local Qwen2.5:3b model. The final application-content hash is `9eaf8897f6de38407c68d7d369ea52972a91e0e66363a71983238049118f8567`.

| Check | Result | Evidence and scope |
|---|---|---|
| Python controls/integration suite | 83/83 passed | `evals/unit-tests.xml`; includes actual OCR, policy/resource boundaries, role/SDK restrictions, exact approval, persistence and concurrent release; provider doubles are explicitly labelled |
| Same suite in restricted Linux runtime | 83/83 passed | `evals/linux-unit-tests.xml`; actual deployment image, isolated disposable test state |
| Actual evidence-only PDF corpus | 16/16 passed on macOS and Linux | `evals/results.json`, `evals/linux-evidence.json`; raster/OCR/text/EPC checks only; two instruction-only invoices correctly pass evidence checks and are blocked later by the semantic control |
| Full hosted workflow | 16/16 passed | `evals/live-pipeline.json`; seven legitimate variants completed real-model preparation, human review, sandbox release and idempotent replay; nine unsafe cases held/blocked |
| Real semantic prompts | 6/6 passed | `evals/live-semantic.json`; three benign and three behavioral override prompts through the actual local model |
| Desktop/mobile browser flow | 8/8 passed, zero runtime errors | `evals/browser.json`; actual browser/API/model, rendered evidence, release, export, live policy/feed edits, mobile layout and self-hosted API reference |
| Deployment and persistence | Passed | `evals/deployment.json`; exact public health SHA, pre-existing signed session and supplier records survive container recreation, real inference through a dedicated supervised private forward |
| Hosted external-agent SDK | 7/7 passed | `evals/live-sdk.json`; actual bank-handle-only evidence/proposal, denied authority escalation and independent reviewer release |

The hosted 16-case run had **zero false blocks among seven positive cases** and **zero unsafe allows among nine negative cases**. Recorded p95 end-to-end time was **27,473 ms** and includes upload/import, queue/OCR, guard/proposal inference and, where allowed, reviewer release/replay; it is not isolated gateway overhead. These are finite synthetic tests, not a general fraud-detection benchmark or production load test.

## Version and environment interpretation

Reports retain the actual tested release SHA. The final application-content hash combines `renderguard`, `src`, `policies`, `signatures` and `fixtures`; it excludes documentation, package archives and CI templates. The hosted tested code and final source share this hash. The final deployment health is checked against the latest pushed Git commit after packaging; no older SHA is silently rewritten into a report.

The Linux runtime image contains compiled frontend assets rather than TypeScript source, so its evidence evaluator hashes the runtime subset and produces a different `source_sha`. The Linux suite runs the same committed Python code and fixture corpus. The earlier `local-live-pipeline.json` records a pre-final local development run; prefer `live-pipeline.json` for the final hosted result.

All effects are synthetic sandbox ledger receipts. No bank, submission portal or personal application is involved. The optional CI YAML is a template, not an active or claimed GitHub Actions run. Reproduction commands are in README; deployment/restart commands are in `docs/operations.md`.
