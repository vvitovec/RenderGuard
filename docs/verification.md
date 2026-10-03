# Verification of the revised entry

The previous packages remain frozen at their recorded baseline. Revised results are regenerated after the critique-driven changes; source hashes and actual tested release identifiers are retained. The revision is not considered ready until executable controls, real PDF evidence, actual hosted model/workflow, browser and deployment checks pass.

## Evidence files and scopes

| File | What it establishes |
|---|---|
| `evals/unit-tests.xml` | Local executable positive/negative controls, actual raster/OCR, labelled provider doubles, atomic obligation consumption/replay, authority drift, current file limits, accounting, final reporting and configuration semantics |
| `evals/linux-unit-tests.xml` | Same committed suite in a restricted Linux runtime with isolated disposable state |
| `evals/results.json`, `evals/linux-evidence.json` | Actual 21-PDF raster/OCR/text/EPC corpus, with no AI dispatch; hidden-text evidence expectations differ explicitly from full-workflow expectations |
| `evals/live-pipeline.json` | Actual hosted isolated-worker/model/approval/sandbox-release pipeline for every declared case; per-case stage latency and exact source hash |
| `evals/live-semantic.json` | Twenty stated prompts against the actual local model, ten benign and ten behavioral overrides, including Czech/Polish and indirect role instructions |
| `evals/live-sdk.json` | Actual bank-handle evidence/proposal restrictions and independent reviewer release |
| `evals/browser.json` | Real desktop/mobile browser/API/model flows, complete/current evaluation banner, exports, final reporting and live feed allow/block/allow; bound source/release hashes |
| `evals/performance.json`, `evals/linux-performance.json` | Measured sequential deterministic gateway latency with catalog/privacy/permission/audit processing; no AI/OCR/network dispatch and no production-throughput claim |
| `evals/deployment.json` | Actual public HTTPS/source release, model availability and retained signed session/data across project-container recreation |

The 21-case manifest includes nine legitimate variants, eleven blocked cases and one review hold. The unreadable-document expectation is a block because mandatory purchase-order/amount authority is absent; it is not a semantic classification. New positives include a genuinely reordered layout and a benign raster/text-layer hybrid. The hidden-prose case holds for representation review, rather than being labelled a known injection.

## Performance interpretation

Deterministic gateway measurements include synchronous central-policy/feed reads, permission/privacy/signature checks and SQLite audit persistence. They exclude document rendering, model queue/inference and payment execution. Host/architecture and sampling scope are recorded. Separately labelled workspace stage percentiles cover gateway, evidence, document, semantic inference, proposal inference, queue and executor wherever measured. Full-workflow percentiles include queue/OCR/AI and allowed approval/release/replay; they must not be described as gate overhead.

Finite synthetic results are not a universal attack-detection guarantee. Tests may reveal false positives or misses; these are reported, not replaced by a test double on the live path. Dispatched unknown usage stays pessimistic, while known no-dispatch cancellation refunds token/financial holds. The optional external adapter is exercised only with in-memory mocked HTTP responses, never billed real calls.

## Provenance

Runtime and evaluator share one digest over `renderguard`, `src`, `policies`, `signatures` and `fixtures`, excluding bytecode. Runtime includes frontend source solely for this proof. The dashboard compares actual current-source digest with the recorded result and checks every fixture ID; a stale/incomplete record is visibly labelled. Reports keep their actual tested release SHA. Documentation and immutable package commits can change Git HEAD without changing the tested application-content digest.

Earlier development reports such as `local-live-pipeline.json` are historical; prefer revised `live-pipeline.json`. Original draft/final snapshots retain their earlier reports. Optional CI is a template, not an active GitHub Actions run. All effects are synthetic sandbox receipts, with no bank connection or competition submission.
