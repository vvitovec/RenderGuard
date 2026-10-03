# Architecture

## One concrete workflow, reusable controls

The integrated workflow is repeat-supplier EUR payment preparation against an approved obligation. `Gateway` owns authenticated identity checks, model/tool allowlists, outbound and inbound privacy controls, semantic interpretation, literal historical signatures, and transactional resource reservations. `Payments` owns document/action grounding, independent supplier authority, immutable approval and the protected execution effect. These are separate modules with provider injection and API contracts; the React application is an inspection surface, not an enforcement boundary.

## Immutable evidence and execution

Source PDF and each rendered PNG have SHA-256 hashes. The structured evidence is hashed. A proposal binding contains source/evidence/payment hashes, supplier and obligation record hashes, policy version, signature-catalog hash and workspace. The reviewer token is HMAC-signed with an expiry and a separate audience. It refers to an approval row containing those hashes. A session token cannot be used as payment approval.

Execution serializes rereading the proposal/approval, rechecking source/renders/master data/configuration, inserting the immutable receipt and consuming approval inside one SQLite `BEGIN IMMEDIATE` transaction. Database uniqueness prevents two receipts for the same proposal or supplier/invoice/currency. A separate atomic obligation-consumption ledger permits one full release per independently approved obligation, including concurrent differently numbered invoices. Existing receipts are preserved; ambiguous historical consumption is held. Replaying the same valid approval returns the existing receipt. It never accepts replacement action fields. Expired approval is rejected even if a receipt exists; obtain the saved receipt from the register.

## Model and cost limits

Policy validation requires explicit rates for every permitted model. The local model's charge rates are zero, which does not imply hosting has no operating cost. Monetary values are integer micro-USD and payment amounts integer EUR cents. Input byte limits, conservative token reservations, context/output bounds, model and tool attempt counts, per-workspace concurrency and an overall one-call model semaphore prevent uncontrolled dispatch. Timeout includes waiting for the shared model slot. Failed/interrupted dispatched calls with unknown usage consume the full reservation. Known pre-dispatch queue cancellation releases token/financial holds, while retaining an attempt count. Reported usage overruns are fully accounted and the response is held. Frozen reservation rates prevent later policy changes from repricing earlier calls.

Queue wait and provider inference are timed separately. Preparation retains the exact policy and feed authority that was evaluated; changes across an awaited operation hold the action. Both labelled machine and rendered-OCR representations are minimized and inspected, with deterministic hidden-text and narrow literal indicators before the semantic guard. Current page/byte limits are rechecked for previously processed evidence.

The conservative byte/BPE bound is specific to the supplied text adapters and includes chat-frame margins. It is not a generic tokenizer for every possible model/provider. For a different tokenizer/adapter, implement a verified upper bound before claiming hard token safety.

## PDF isolation

Hosted PDF processing runs as UID 10001 in a read-only container, with no network, no Linux capabilities, no privilege escalation, a 768 MB memory limit, CPU/PID limits, bounded tmpfs and a 55-second child-processing timeout. It mounts only the queue directory. PDFium is built without V8. The API verifies worker evidence schema, source hash and rendered-file hashes before accepting it.

This boundary reduces parser access to the model service or approval database. It does not formally prove the rendering/OCR stack safe against every malformed PDF. Worker output is trusted only within this isolated processor boundary; a privileged host or a compromised rendering worker could forge evidence. Production needs hardened disposable workers, stronger input fuzzing, retention controls and operational monitoring.

## Deployment and scale

The current deployment is deliberately bounded: one API process, one PDF worker, one model slot and SQLite WAL. Workspace scope is explicit on every resource lookup and export. No claim of horizontal scalability or load-tested multi-tenant production readiness is made. For scale, move queue claims to an atomic job service, the ledger/approval transaction to PostgreSQL, and budget reservations to a shared transactional store; keep the protected executor invariant and unique invoice/proposal constraints. Model/provider adapters and central validated policies allow controlled extension without giving agents new authority implicitly.
