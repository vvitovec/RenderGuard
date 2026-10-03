# Critique and revision record

Baseline reviewed: `b5d21c556e288c1bb6216cfacf8defda1e98a345`, before any revision. The user explicitly requested GPT-6.1 Sol and Claude Opus-5.5 critiques. Two independent GPT-6.1 Sol passes covered the whole product and control correctness. One terminal `claude -p --model claude-opus-5-5` pass used only Read/Glob/Grep, with browser/MCP disabled. Claude model identity is confirmed by CLI metadata. No reviewer submitted anything or edited the baseline. Claude initially encountered expired OAuth; the human restored login, then its critique completed. No further Claude calls were needed.

Sol reproduced issues using synthetic temporary state and deterministic provider doubles; one Sol pass freshly ran all 83 baseline tests. Claude inspected source, documents and a screenshot but did not run tests or access the hosted app. Its full critique and these limits are preserved in `docs/reviews/claude-opus-5.5.md`. The advisory score estimates are not jury scores or a prediction of placing.

| Finding | Revision acceptance condition |
|---|---|
| Different invoice numbers can reuse one approved full obligation | One atomic persisted effect per obligation; preapproved/concurrent proposals cannot double-pay; valid same-proposal replay remains idempotent; historical receipts preserved |
| Visible-only behavioral text omitted when machine text exists | One minimized, provenance-labelled guard input covers both representations; SDK receives the same consistent evidence |
| Feed changes during an awaited operation become falsely current | Original policy/feed authority retained; drift holds preparation; approval cannot bind old checks to new controls |
| Undispatched queue timeout charged as unknown usage | Known no-dispatch releases token/cost holds; attempts remain counted; unknown dispatched usage stays pessimistic |
| Optional adapter treats absent usage as zero | Missing/invalid counts stay unknown; explicit nonnegative zero is distinguished |
| Tightened page/byte settings ignored for existing evidence | Current constraints apply during preparation, approval and execution |
| Semantic and invoice checks missing in security reporting | Final decisions and compact per-control outcomes exported; invoice/EUR totals separate from stage events |
| OCR/model latency confused with gate overhead | Actual sequential deterministic benchmark plus separately labelled queue/inference/document/executor stage telemetry |
| Render/text mismatch relies entirely on probabilistic interpretation | Configurable hidden-text hold and narrow literal document indicators, with legitimate scan/hybrid/layout positives |
| Live feeds do not visibly change a permitted probe | Allow → canary feed block → removal allow, without executing/opening supplied endpoints |
| Deck omits trust-boundary diagram and captures unsettled states | Ten-slide diagram/controls/SDK narrative; settled readable evidence crops; exact report-backed counts |
| Reports lack freshness attribution | Actual current core hash compared to recorded hash; complete fixture coverage checked; stale reports visibly labelled |
| Policy overrides mask baseline changes; balanced has no semantics | Overrides represented as delta; baseline provenance visible; balanced review band and disabled-control disclosure |
| SDK proposal requested before PDF evidence is ready | Queued/failed evidence returns a controlled review hold, with zero model calls, proposal rows or receipts |
| Dependency/model attribution missing | Locked/installed metadata and original notices packaged; Qwen research license recorded without redistributing weights |

## Hosted validation correction

The first expanded real-model run passed 19/20 probes: a benign Czech payment-reference instruction was falsely classified as an override. The system instruction was refined generally to distinguish multilingual payer/bookkeeping instructions from AI authority circumvention; no phrase allowlist or expected labels were changed. The failed run is preserved in `evals/history/revision-semantic-before-refinement.json`. All live checks are rerun against the refined source.

A concurrently edited local prompt also exposed an evaluator provenance defect: it recomputed the local hash at completion. The historical pipeline record explicitly notes its correction from the recorded immutable hosted release. Revised hosted evaluators record the runtime session source digest directly and reject mixed-source workflow runs.

## Deliberate limits

The project stays a repeat-supplier EUR full-obligation payment release adapter over reusable gateway controls. It does not add a bank connection, enterprise IAM, generalized ERP reconciliation, arbitrary MCP execution or speculative compliance claims. Public demo personas remain honestly labelled synthetic roles.

A complicated rolling financial-budget reset was not added: the workspace budget is a durable session/lifetime cap, with a larger default and visible remaining/reserved limits. Time-window and shared cross-host accounting need a separately specified production design; silently clearing pending or unknown reservations would weaken the tested invariant.

The enlarged live prompt corpus includes benign replacement-invoice terms and Czech/Polish payment instructions as well as role/chat/JSON spoofing and indirect overrides. Results remain finite-corpus measurements; a perfect test run cannot guarantee universal attack detection or a hackathon win. Current recorded results and exact scopes are in `docs/verification.md`.

All earlier draft/final packages remain immutable. Revised materials are a separate review snapshot. **Nothing has been submitted to HackYeah.**
