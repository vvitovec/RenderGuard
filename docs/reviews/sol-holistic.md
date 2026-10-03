# GPT-6.1 Sol holistic critique

Read-only baseline b5d21c556e288c1bb6216cfacf8defda1e98a345. Reviewer read both supplied PDFs, final presentation and scoped actual reports, rendered slides and freshly ran 83/83 baseline tests. Application-content hash matched baseline reports. No source edits/live writes.

Advisory estimate 78/100, plausible72–85, not a jury result: robustness24/30, architecture16/20, reporting14/20, tests17/20, practical7/10. Specialized workflow, independent supplier authority, account handles, exact approval, isolated worker and honest limits were strengths; broad MCP expansion was discouraged.

Reproduced defects:
- Two distinct invoice numbers each for EUR1240 against one EUR1240 PO both approved/released, creating EUR2480 receipts. Invoice uniqueness does not consume the approved obligation.
- A semantic playground block returned block but metrics had zero blocked events and no held controls. Final semantic verdict was not logged.
- A one-second global-semaphore timeout called the provider zero times but charged537 tokens/microUSD from an unknown reservation. Pre-dispatch cancellation must be distinguished from unknown dispatched usage.

Recommended improvements: correlated final/control reporting; separately measured middleware and queue/inference latency; held-out multilingual/indirect and legitimate-layout cases; actual trust-boundary/SDK diagram; readable settled screenshots (baseline QR shot still showed Checking local AI); live allow/block/allow canary feed; verified model/runtime license attribution. Preserve exact constrained action generation and avoid enterprise scope bloat.
