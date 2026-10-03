# Judge walkthrough (English)

## A three-minute live demo

**0:00–0:30: the actual problem.** An AI accounts-payable assistant can read a PDF's text or QR while a reviewer sees different pixels. Independent supplier-bank checks alone do not expose all representation discrepancies. RenderGuard puts the check at the release boundary.

**0:30–1:15: legitimate completion.** New workspace → Clean invoice → prepare. Show one outgoing minimized model message: the actual assistant sees `account_1`, not the full bank account. Switch to reviewer → approve the exact action → release. Show the immutable sandbox receipt; no money moved.

**1:15–2:00: attack and safe recovery.** New workspace → QR account swap → Payment fields. The page says one account, the QR another. Preparation is blocked before model dispatch. Then show Unverified bank change: all representations agree, but independent master data still stops it. Bank verification belongs in a separate administrator workflow using a saved contact.

**2:00–2:40: change the controls live.** Switch Administrator → Test lab. Probe a supported credential and inspect the redacted boundary output. In Controls set `pii_action` to `block`, apply, and repeat. Show a forbidden `execute_payment` request with `role: reviewer` in its JSON: it cannot grant a capability. Show semantic injection versus ordinary payment terms.

**2:40–3:00: evidence.** Show recorded finite-corpus results, executable tests, exports and exact approval binding. Explain that source, policy, supplier or action changes invalidate approval and concurrent retries produce one receipt.

## Spontaneous adversarial cases

- Approve a clean invoice, edit the policy as Administrator, return to Reviewer and attempt release: stale approval is rejected. Re-prepare under the changed configuration.
- Use the SDK to propose a different amount/recipient: action grounding blocks it. SDK proposals also run semantic controls.
- In Test lab use the feed canary: an otherwise permitted read_evidence probe allows; adding a literal tool signature blocks; removing it allows again. Export the responsible feed version. An unsafe non-HTTPS endpoint remains blocked by independent permissions even with an empty feed.
- Set `max_model_calls` to zero and prepare: provider dispatch is denied. Explicit positive/negative cost reservation tests use configured rates, not real charges.
- Set `profile: observe` to explore skipped controls; observe mode cannot approve/release.
- Give a differently numbered invoice the same approved obligation: it cannot create a second receipt. This is one full release per obligation, not partial-invoice reconciliation.
- Retry execution concurrently with the same capability: same receipt, one persisted effect. The automated suite runs eight parallel attempts.
- Inspect audit export: no approval token, model credential or supported private-data patterns leak through the reporting surface.

## If the model is unavailable

The UI indicates it and preparation is held. Show a deterministic representation attack and the packaged tests; do not describe a recorded model result as a current live call. Restart only the project-owned model service/tunnel using the operations guide. No paid fallback or fake proposal exists.

## Differentiation and honest claims

Supplier-account validation is prior art. The useful differentiator is a single evidence-bound authorization chain: pixels/text/QR, independent supplier/PO, minimized AI proposal, exact human approval, and protected one-effect execution. Claims concern implemented boundaries and the recorded finite corpus, not universal fraud prevention.

## Explaining the control layer quickly

Payments are the specialized adapter. The reusable gateway intercepts model requests/responses, registered tools and resource discovery under one validated policy/feed, with capability-derived identity, privacy, reservations and reporting. The guarded effect is independent of model confidence. Use the architecture diagram to show which process holds each authority.

Show deterministic gateway p95 separately from OCR, queue and inference latency. These are actual scoped measurements, not claimed production throughput. Read the release register as unique current invoice outcomes; raw stage events have a separate count. Budget remaining is visible, and a new synthetic workspace starts with fresh capped resources.
