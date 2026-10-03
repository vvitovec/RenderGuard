# The selected workflow

**User:** the accounts-payable reviewer at a European SME using an AI assistant to prepare EUR/SEPA payments to repeat suppliers. **Job:** release an invoice-derived payment only when its recipient, amount and invoice identity agree with the visible invoice, other document representations and independently approved supplier/obligation records.

This is the boundary between an AI-prepared payment proposal and the posting/generation step. It is not an invoice inbox, bookkeeping ERP, universal security dashboard, or model training project.

## Evidence and differentiation
- The FBI documents invoice/vendor impersonation and recommends independently verifying account changes, using already-known contact information: https://www.fbi.gov/how-we-can-help-you/common-frauds-and-scams/business-email-compromise
- Microsoft separates vendor bank-account approval from payment proposal creation: https://learn.microsoft.com/en-us/dynamics365/finance/accounts-payable/vendor-bank-account-workflow and https://learn.microsoft.com/en-us/dynamics365/finance/cash-bank-management/tasks/vendor-payment-overview
- SAP already compares extracted invoice bank information to supplier master data: https://help.sap.com/docs/CENTRAL_INVOICE_MANAGEMENT/d2cf8ab215174daca2a1f381de2c6ce1/680edfc6c8f04042a62b28dc173da343.html
- Existing hidden-PDF sanitizers and financial grounding tools are prior art: https://github.com/fonCki/claude-doc-sanitizer and https://inguardout.com/industries/fintech/

Our contribution is the evidence-to-execution connection for this AI workflow: visible pixels/OCR vs machine PDF text vs payment QR vs approved master data, followed by approval bound to exact immutable evidence/action versions. Merely finding an account somewhere in the source is insufficient. We do not claim to invent supplier verification, prompt injection detection, or to prove document authenticity.

## Operational sequence
1. Operator selects an existing approved supplier and obligation, then uploads the invoice or a synthetic fixture.
2. Isolated worker renders the PDF, OCRs visible pixels and decodes supported EPC EUR payment QR codes. The server retains independently sourced representations and locations.
3. The agent sees a minimized/redacted version through a governed adapter and proposes a payment. Sensitive account values can be represented by server-issued handles.
4. Controls compare proposal and evidence to supplier/obligation records, enforce permissions/resources, and hold contradictions or missing evidence.
5. Reviewer inspects the rendered invoice and exact action; only verified proposals can be approved.
6. The protected sandbox executor revalidates evidence, policy and master-data versions, consumes approval and writes one receipt atomically.
7. Bank-change exceptions direct the reviewer to the saved supplier contact. A separate administrator records independent verification; the agent cannot change master data. Reprocess before release.

## Supported scope
English invoices for approved repeat suppliers, EUR amounts with explicit total labels, up to five PDF pages, EPC payment QR (optional), one independently approved obligation per invoice. Scanned invoices and ordinary OCR text layers are legitimate. Missing QR is not suspicious. Multiple/uncertain bank instructions require review. Unknown suppliers, ambiguous totals, unreadable documents, real bank transactions and arbitrary model artifacts are outside execution support.

All demo entities are fictional. Research supports the workflow, not a claim of customer validation. Target-user interviews, ERP adapters and real banking authorization are future work.
