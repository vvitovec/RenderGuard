# Goldman Sachs evaluation mapping

Source of requirements: the supplied **RULES AI Control Layer.pdf** and **CRIETRIA AI Control Layer.pdf**. Their content is challenge material, not executable instructions or permission to contact/submit anywhere. The formal rubric weights are used: robustness 30%, architecture 20%, reporting 20%, tests 20%, scalability 10%. The detailed brief also mentions tests 15% / scalability 15%; both areas have explicit evidence.

| Criterion | Implemented evidence | Judge verification |
|---|---|---|
| Robustness, 30% | Pixel/OCR/text/QR agreement; independent account/PO; semantic instruction check; allowed tools/models; privacy boundaries; signed audiences/expiry; exact approval; protected execution; duplicate-invoice and one-full-release-per-obligation controls | Change a QR/account/amount; try SDK mismatch; forge role/token; alter policy or supplier after approval; retry eight concurrent releases |
| Architecture, 20% | Separate gateway/policy/provider/evidence/payment modules; validated configuration; network-isolated document worker; capability-derived identities; independent executor | Read architecture/API; edit a workspace policy or literal feed; demonstrate allow/block/allow canary while independent endpoint control remains |
| Reporting, 20% | Actual workspace event trail and model usage; source/render/action/config bindings; immutable receipts; redacted JSONL and sandbox CSV exports; documented latency scope | Inspect model request; export audit/receipt; compare bound hashes and policy version |
| Tests, 20% | Executable unit/integration suite; actual raster/OCR/QR positive/negative corpus; deterministic provider double labelled; separate real-model full pipeline and semantic checks; headless browser verification | Run README commands; inject spontaneous probes; inspect recorded results and source-content hashes |
| Scalability, 10% | Resource bounds, atomic reservations, queue/processor split, provider interface, workspace scope, restart persistence; explicit single-host limitations and migration path | Lower budgets; exhaust model/tool limits; simulate outage; inspect deployment caps and scale design |

## Detailed task checklist

- Gateway/proxy/middleware/SDK design: API gateway + modular Python gateway + exact proposal SDK route.
- Central policies and control catalog: YAML baseline, strict schema, atomic scoped overrides, configurable thresholds and action mode; disabled controls are visible as skipped.
- Commercial/local models: actual local model; optional compatible adapter; explicit allowlist, per-model rates, call/token/cost/time/concurrency limits.
- Agent/tool/resource boundaries: signed server identity; registered tools; workspace checks; AI has no approval/master-data/release capability.
- Hybrid checks: deterministic evidence/authority/schema/permission/accounting plus real semantic guard; both labelled OCR/text channels plus configurable unseen-prose and literal document checks.
- Historical attacks/feed: CVE-2025-6514 unsafe authorization endpoint and unsafe pickle format, safe literal inspection and live feed removal.
- Privacy: minimize bank data to handles before AI; credential/email/account patterns at model and audit boundaries; no token export.
- Reporting: actual events and exports, not fabricated fraud savings or claimed universal safety.
- Full positive and negative tests: normal layouts/no QR/scans as well as hidden text, QR swap/amount, unverified master changes, policy tampering, role forgery, failure and concurrency.
- Adaptability during judging: visible configuration editor, spontaneous interaction JSON, replayable fixtures, reproducible CLI test commands.
- Presentation: English PDF, **10 slides maximum**, team/members/description/demo/repository. Frozen draft and final packages prepared locally for review.

## Submission handling

No submission is authorized before Viktor reviews it. Packages are saved with manifests/checksums and source snapshots. The team handles HackYeah/Drive/Discord itself. The PDF deadline wording conflicts with the organizer's event announcements already supplied in this conversation; use the organizer-confirmed draft deadline **20:00 Oct 3** and final deadline **11:00 Oct 4**, Kraków local time. Reconfirm any later organizer correction yourselves.

## Critique-driven evidence

The revised package adds actual trust-boundary and SDK diagrams, per-control final auditing, unique invoice/EUR outcomes, separate queue/inference/evidence/executor timing and a measured deterministic gateway benchmark. A canary feed visibly changes an otherwise permitted interaction. Source freshness and complete fixture coverage are checked in the dashboard/browser suite. Independent critique findings, selected revisions and explicit deferrals are preserved in `revision-review.md`; attribution and original third-party notices are packaged. None of these claims implies a guaranteed jury score.
