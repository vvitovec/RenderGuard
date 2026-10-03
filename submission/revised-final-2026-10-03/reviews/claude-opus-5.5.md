# Claude critique provenance

Model confirmed by CLI: `claude-opus-5-5`. One successful `claude -p` read-only pass at baseline `b5d21c556e288c1bb6216cfacf8defda1e98a345`; browser integration/MCP disabled, Read/Glob/Grep only. Findings are advisory, not jury scores or independent test results. Claude did not run tests.

# RenderGuard: adversarial review for the Goldman Sachs AI Control Layer track

**Changed files: none.** I didn't run any tests, builds, evaluators or browser checks, and I didn't contact the live site.

**What I read:** AGENTS.md, README, the five docs, `payments.py`, `gateway.py`, `policy.py`, `store.py`, `privacy.py`, the routes in `api.py` (lines 200–733), `policies/default.yaml`, `signatures/catalog.json`, the start of `evals/live-pipeline.json`, the latency fields in `evals/`, the test function names, slides 1–10 in `scripts/presentation.py`, targeted searches of `main.tsx`, and the screenshot `output/playwright/control-probe.png`.

**What I couldn't check:** the final PDF wouldn't render (pdftoppm isn't installed), so I reviewed the deck through its generator script instead. I didn't open the two rules/criteria PDFs or `documents.py` beyond a search, and I didn't read `style.css`. The pass/fail counts below are what the recorded files say; I didn't re-run them.

## Strengths
- **Execution is solid.** Approval, revalidation, receipt insert and consume all happen in one `BEGIN IMMEDIATE` transaction (`payments.py:732-815`), with unique proposal and invoice-key constraints (`store.py:60-61`). The approval token is signed and bound to the payment and binding hashes (`payments.py:693-703`). A changed policy, supplier, feed or file makes the approval stale (`payments.py:366-383`). Replaying the same approval returns the original receipt.
- **The AI is tightly boxed in.** It only sees opaque account handles, and generation is limited to fixed values (`payments.py:529-536`). Budgets are reserved before the model is called and charged pessimistically if a call is interrupted (`gateway.py:325-399`). Rates are frozen at dispatch.
- **Failures hold the payment.** A missing worker result, bad model output, model outage, or a policy change during preparation all end in review or block.
- **Claims are honest.** Scope and limits are stated clearly, the test double is labelled, and the docs separate evidence-only, full-workflow and semantic scopes.
- **There's a real negative and positive corpus.** It includes no-QR, spaced-IBAN, scanned and OCR-text-layer cases that should pass.

## Estimated formal score (30/20/20/20/10)
| Criterion | Estimate | Main drag |
|---|---|---|
| Robustness (30) | 22–26 | Prompt injection in invoices is caught only by the 3B model |
| Architecture/performance (20) | 13–16 | No diagram in the deck; overhead added by the controls isn't measured |
| Reporting (20) | 11–15 | Payment-control outcomes are missing from the events and metrics |
| Tests (20) | 15–17 | Only 6 semantic prompts; reporting isn't tested |
| Practical/scalability (10) | 5–7 | Model budget is a lifetime cap per workspace; deliberately single-host |
| **Total** | **~66–81** | Judges vary a lot; on the 15/15 brief weighting it shifts by about ±2 |

Fixing findings 1–4 below could plausibly add 6–10 points. None of this guarantees a placing.

## Ranked findings

### 1. HIGH (robustness, hybrid controls): invoice prompt injection is caught only by the semantic model; no rule-based check exists for text that isn't rendered
**Evidence:**
- Comparing the PDF text layer with what's visible covers only five payment fields (`payments.py:222-243`).
- Any other text that exists only in the PDF text layer goes straight to the AI (`payments.py:517`), and the only thing checking it is `gateway.semantic` (`payments.py:518`).
- The attack-signature catalog only has `mcp.discovery` and `model.load` entries (`signatures/catalog.json:4-5`). Matching is prefix or exact-value only (`gateway.py:279-281`), so no signature can apply to invoice text.
- In the strict profile, an administrator can set `semantic: false` (`policy.py:69-74` only enforces approval and evidence consistency). With that setting, both injection fixtures would reach approval.

**Problem:** for a project called RenderGuard, text that's in the PDF but not rendered on the page isn't treated as a signal in itself. The "hybrid" claim also doesn't apply to the main threat, and the separate rule-based layer the brief asks for is missing on the payment path.

**Smallest worthwhile fix:**
- Add a `hidden_text` control in `evidence_checks`. Normalise the text-layer lines, and if a line's tokens are mostly absent from the OCR text (with tolerance for OCR noise), flag `review`.
- Make the threshold and action configurable in policy, e.g. `controls.hidden_text_min_tokens`. This also gives judges a real sensitivity setting to adjust live.
- Add a `document.text` signature kind with a literal `forbidden_substrings` list. Validate it as data in `validate_feed` and evaluate it on the redacted text in `prepare` and `propose`. It's already part of the approval binding through `signature_hash`.
- Use specific phrases and default them to `review`, so wording like "ignore the previous invoice" doesn't cause false blocks.

**Acceptance checks:**
- Using a test model that always returns risk 0: the "invisible approval-bypass" fixture is held by `hidden_text`, and the "visible role override" fixture is held by a literal signature.
- All 7 positive cases still pass, including "Legitimate OCR text layer" and the scanned invoice.
- Removing the signature entry live changes the verdict and makes an existing approval stale.

**Impact:** robustness +2–3, tests +1. The "historical exploits / feed edits" requirement becomes relevant to payments rather than only to the MCP/pickle probes.

### 2. HIGH (reporting): payment-control outcomes are missing from the audit trail and metrics
**Evidence:**
- The `payment.proposed` event stores only `summary`, not `checks` (`payments.py:453-465`).
- `/api/metrics` `held_controls` counts only checks that appear inside events (`api.py:683-687`), which means gateway checks only. QR, supplier-account, PDF-vs-visible mismatch, purchase-order and semantic holds are never counted.
- `model.complete` is logged as `allow` before the semantic risk is compared to the threshold (`gateway.py:472-478`).
- An exported audit file for a semantically blocked invoice shows model allow → allow → proposal block, with only a text summary.

**Problem:** security reporting can't answer "which control stopped what, how often". Management reporting has no figures for value released vs held (EUR, count) or for denial reasons.

**Fix:**
- Store a compact list of checks in the event: `control`, `verdict`, a truncated reason, and risk/threshold where present.
- Have metrics count by control and add: released/held/blocked counts and EUR totals, approvals issued vs consumed vs expired, and a distribution of semantic risk scores.
- Show these in the Release register view, next to the existing figures.

**Acceptance checks:**
- After a QR-swap case, metrics show `qr: 1` and that invoice's amount under held EUR.
- After a semantic-injection case, `semantic: 1` with its risk score.
- The JSONL export contains the per-check verdicts and still leaks no approval token or full IBAN (extend `test_audit_export_redacts_...`).

**Impact:** reporting +3–4.

### 3. HIGH (performance telemetry): the overhead added by the controls themselves is never measured
**Evidence:**
- `gateway.evaluate` records `latency_ms` (`gateway.py:308,319`), but metrics only aggregate `model.complete` and `document.ready` (`api.py:672-697`).
- `evidence_checks`, `proposal_checks` and the executor transaction aren't timed at all.
- `evals/results.json` has `p95_end_to_end_ms: null`.
- The live run reports only a 27,473 ms end-to-end p95.
- The deck mentions "stage latency" (slide 8) but gives no numbers.

**Problem:** the judges' obvious question, "how much latency does your control layer add?", has no answer. The 27 s figure is mostly OCR and model time, and it makes the gate look slow.

**Fix:**
- Time each stage with `time.monotonic()`: rule-based gateway checks, evidence controls, semantic guard, proposal model, worker, and the executor transaction.
- Store `stage` and `latency_ms` on events and return per-stage p50/p95 from metrics.
- Have the live evaluator write these into `live-pipeline.json` and quote the measured values on the slide.

**Acceptance checks:** metrics return separate figures for each stage; a unit test asserts the stages are present; the evaluator JSON contains them.

**Impact:** architecture/performance +2, reporting +1.

### 4. HIGH (presentation/architecture): the deck has no architecture diagram and no screenshot of the controls UI
**Evidence:**
- The slides in `presentation.py:100-399` are: title, problem, a 5-step process strip (slide 3), positive path, QR attack, hybrid controls (text only), execution, reporting, evidence, summary.
- Only `release.png`, `qr-swap.png` and `register.png` are used as screenshots.
- The required "simple architecture diagram" exists only as the README mermaid chart.
- The editable controls (thresholds, budgets, signature catalog) appear only as text on slide 6.

**Fix:**
- Turn slide 3 into a boxes-and-arrows diagram with trust boundaries: operator/agent → API gateway → no-network PDF worker → evidence controls → semantic guard (Mac mini Qwen over the private forward) → proposal tool → reviewer → protected executor → SQLite ledger, with audit and budgets alongside. Keep the 01–05 step labels on the arrows.
- Put a fresh screenshot of the Controls editor on slide 6.
- Add the per-stage latency from finding 3 to slide 9. The deck stays at 10 slides.

**Acceptance checks:** the PDF has ≤10 pages, every architecture component from the README appears on one slide, and all numbers come from `evals/*.json`.

**Impact:** architecture +1–2; a diagram is something judges explicitly check for.

### 5. MEDIUM-HIGH (judge experience, practicality): the model budget is a lifetime cap of 8 calls per workspace
**Evidence:**
- The counter only ever increases and has no time window or reset (`gateway.py:347`, `default.yaml:14`).
- Each preparation uses 2 calls (`payments.py:518,537`), and Test lab semantic probes use more.
- Following `judge-walkthrough.md` (clean prepare, semantic probe ×2, re-prepare after a policy edit, stale-approval retry) uses about 8 calls. The next preparation then fails with "Model-call budget exhausted".
- Raising the limit is a policy edit, which makes approvals stale. That's correct behaviour, but confusing in the middle of a demo.

**Fix:**
- Add `budgets.window_seconds` (e.g. 3600) and reset the call, token and cost counters when the window rolls over. Pending and unknown reservations keep their pessimistic accounting.
- Show the remaining budget and the reset time in the UI.
- Default to about 24 calls per hour.

**Acceptance checks:** exhaust the budget → denied; advance a fake clock → allowed; concurrent reservations still don't overspend (extend `test_parallel_budget_reservations_do_not_overspend`).

**Impact:** practicality +1. Mainly it removes a likely failure in the live demo.

### 6. MEDIUM (stale evidence judges may see): the Test-lab screenshot shows 14/14 and "Not recorded"
**Evidence:**
- `output/playwright/control-probe.png` shows "Recorded evidence suite: 14/14 … b09f9c589d5a", with both injection fixtures marked **"Not recorded"**.
- `evals/live-pipeline.json:5-7` says 16/16 with source `9eaf8897…`.
- The hosted app serves `evals` from a read-only mount (`compose.production.yaml:26`, `api.py:703-715`), so what judges see depends on the host folder having been synced.

**What I couldn't verify:** whether the hosted Test lab now shows 16/16.

**Fix:**
- Check the live `/api/evaluation`.
- Regenerate the screenshot.
- Add a browser assertion that the banner total equals the manifest length and that "Not recorded" doesn't appear.

**Impact:** protects credibility. A visible 14 vs 16 contradiction would undermine the claims on the testing slides.

### 7. MEDIUM (central controls): workspace overrides snapshot the whole policy, release-capable profiles can be weakened silently, and `balanced` does nothing
**Evidence:**
- `catalog.update` stores the full `model_dump` (`policy.py:111-113`). After any edit, later changes to `policies/default.yaml` (e.g. a lower payment ceiling) never reach that workspace, and nothing records which baseline it diverged from.
- `profile: balanced` exists only in the `Literal` type (`policy.py:57`); no code reads it.
- In the strict profile, `semantic: false`, `signatures: false` or `semantic_threshold: 1.0` are accepted, and the receipt doesn't record that controls were weakened.

**Fix:**
- Store only the override delta and report the baseline version plus the overridden keys.
- Either remove `balanced`, or define it as a review band (risk between threshold−0.2 and threshold → `review`). The review band is a real sensitivity control.
- Add a `disabled_controls` list to the approval binding and the receipt.

**Acceptance checks:** after a workspace edit, a baseline edit still takes effect; a receipt from a weakened policy lists the disabled controls; a test covers a `balanced` review-band result.

**Impact:** architecture/robustness +1.

### 8. LOW-MEDIUM (SDK integration): account handles are derived three times, and the SDK hardcodes `account_1`
**Evidence:**
- Handles are built in `payments.py:515-516` and again in `api.py:517-518`.
- `api.py:482` maps only `"account_1"`. Any other handle becomes `"UNRECOGNIZED"` instead of the account it actually refers to.
- This is safe today only because `visible_fields` requires exactly one visible IBAN, which is always handle 1.

**Fix:** add a single `Payments.handles(doc)` helper, resolve handles through the reverse map, and reuse the helper in all three places.

**Acceptance checks:** on the hidden-account fixture, an agent choosing `account_2` resolves to the hidden IBAN and is blocked by the PDF recipient-agreement check (`representation_ibans`), with the reason given.

**Impact:** small, but it makes the "external agent via SDK" integration story hold up in practice.

## Fastest changes with the biggest payoff (≈1 working session)
1. **Finding 1**: the rule-based `hidden_text` control plus the literal `document.text` feed. This gives the biggest robustness gain and directly fits the niche.
2. **Findings 2 and 3**: add the per-check list to events, per-control and EUR metrics, and per-stage latency. Re-run the live evaluator so the numbers are real.
3. **Finding 4**: architecture diagram and controls screenshot in the deck.
4. **Finding 5**: windowed budgets, plus the **finding 6** check of the hosted evaluation banner.
5. Grow `live-semantic` from 6 to about 20 prompts, including benign wording that is likely to cause false positives (e.g. "ignore the previous invoice; this one replaces it") and non-English overrides. Report false positives and misses honestly.

## Deliberately not recommended (enterprise scope creep)
SSO/IdP, Postgres or horizontal scaling, a real bank API, hash-chained or WORM audit storage, enforcing that the proposer and approver are different people in the demo (the personas are honestly documented), commercial model fallbacks, general-purpose PII detection, and badge-style "compliance" claims. The current limitations doc already covers these honestly.

## Still open
- I haven't verified whether the hosted evaluation banner is current (finding 6).
- I didn't render the final PDF.
- I didn't read the rules/criteria PDFs, so the weights above are taken from your summary.
- I haven't run any checks for finding 1 against the OCR-noise tolerance on the scanned and OCR-text-layer fixtures. That needs real tests before relying on it.
