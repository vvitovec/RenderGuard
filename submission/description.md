# RenderGuard

**Team:** Blue Bands Collectors  
**Members:** Viktor Vitovec, Jan Sebastian Rosicky, Krystof Bigas  
**Challenge:** Goldman Sachs — AI Control Layer  
**Language:** English

RenderGuard is an evidence-bound release control layer for an AI accounts-payable assistant preparing repeat-supplier EUR payments. The operator selects an independently approved supplier and purchase order before uploading an invoice. A network-isolated worker renders the actual PDF, OCRs visible pixels, extracts machine text and decodes its EPC payment QR. The gate compares those representations with independently approved supplier and obligation data; discrepancy, ambiguity or poor evidence holds the action.

A real local semantic guard checks untrusted behavioral instructions. A real local proposal model receives minimized evidence and opaque account handles, with evidence-grounded structured generation. Signed identities, explicit model/tool permissions, privacy boundaries, historical attack indicators and atomic resource reservations constrain the agent. The agent cannot update supplier authority, approve itself or execute payments.

A separate reviewer approves the exact action, bound to source/render/evidence/payment hashes, supplier/obligation records, policy and signature catalog. The protected executor revalidates those bindings, consumes approval and persists a single immutable sandbox receipt in one transaction. Concurrent retries return the same receipt. A changed account, policy or approved intent requires fresh preparation and approval.

The English workbench includes direct evidence comparison, policy and literal signature editing, spontaneous interaction probes, a real event trail, usage/latency reporting, redacted JSONL export and sandbox release CSV. The repository packages executable positive/negative tests, actual raster/OCR fixtures, separate real-model evaluations, and headless desktop/mobile browser checks. Results state their finite-corpus scope; no universal fraud-detection claim is made.

**Demo:** https://renderguard.vvitovec.com  
**Repository:** https://github.com/vvitovec/RenderGuard

All suppliers and accounts are synthetic. The executor writes sandbox ledger receipts only; no bank is connected and no money moves. Demo persona switching is explicitly labelled and scoped to each fictional workspace. Production requires external identity and independently managed ERP authority.

**Status:** Prepared for team review. Not submitted to HackYeah.
