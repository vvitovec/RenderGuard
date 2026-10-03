# Scope and limitations

Supported use case: independently approved repeat supplier, approved EUR obligation, labelled invoice number / PO / total / IBAN, supported IBAN-country lengths, up to five PDF pages, optional EPC SCT QR. Positive cases include no QR, spaced IBAN, scanned pages and a matching OCR text layer.

The prototype does not prove invoice authenticity, bank-account ownership, contractual delivery or supplier legal identity. It does not reconcile tax/accounting, support arbitrary national payment QR formats, provide a real SEPA bank integration or guarantee complete prompt-injection detection. Confidence and ambiguity cause holds rather than silent OCR correction. A generated receipt is a sandbox ledger effect only.

The OCR extractor intentionally uses constrained labelled fields. An unusual legitimate layout may need manual evidence resolution. PDF text and OCR are not independent proofs of truth; agreement is necessary, and the independently approved supplier/obligation remains the payment authority.

Semantic classification is probabilistic. Results report the exact finite synthetic cases and stated prompts. The deterministic executor does not rely on the model to authorize identity, recipient, amount, approval or idempotency. Novel attacks and obfuscated secrets can evade pattern detectors or the semantic model. Email, supported IBAN and common credential patterns are implemented; this is not comprehensive PII detection or a regulatory compliance certification.

Demo personas are selectable within each visitor's synthetic workspace. This makes judge testing accessible but is not independent enterprise separation of duties. Production must disable public provisioning/persona switching, integrate external identity, restrict capability issuance, connect independently managed master data and add retention/delete/audit-access controls. Do not upload real customer invoices to the public demo.

The current single-process API, one-worker queue, SQLite WAL and one model slot prioritize repeatability. They are bounded rather than horizontally scalable. API process restart loses only in-memory demo-creation throttling; persistent sessions, evidence, proposals, approvals, budgets and receipts remain on disk. A model outage holds actions instead of switching to a fake or paid model.

Historical examples are safe inspections of endpoint/artifact metadata. The project never executes an RCE payload, opens a supplied MCP endpoint, deserializes pickle, or downloads an arbitrary model.

External model adapter code is supplied for architecture extensibility but is not selected by the hosted demo or claimed as live-tested. The name RenderGuard is a hackathon working title; we do not claim trademark exclusivity or a globally first-ever invoice security product.
