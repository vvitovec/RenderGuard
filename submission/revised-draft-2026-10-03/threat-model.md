# Threat boundary review

| Attacker input / capability | Protected asset | Implemented control | Residual limit |
|---|---|---|---|
| White / hidden PDF account or total | Exact proposed payment | Independent rendered OCR versus extracted text | Malformed/ambiguous layouts held; OCR is not authenticity proof |
| Different EPC QR recipient / amount | Recipient and amount | Decode raster QR and compare with visible/approved fields | Only EPC SCT recognized; unsupported payment QR held |
| All invoice layers agree on a new account | Supplier authority | Independently selected approved master, separate admin verification | Synthetic demo verification is a recorded demonstration, not a real callback |
| Invoice instruction to override AI | Agent behavior | Real semantic classifier, minimized data, fixed tool catalog | Probabilistic classifier can miss novel instructions; executor authority remains deterministic |
| Agent claims reviewer/admin role | Approval and master data | Server-signed identity; separate role/audience checks | Demo visitor can select human personas only in own fictional workspace |
| Edited action/source/master/policy after approval | Approved intent | HMAC capability + hashes/versions + execution revalidation | Trusted administrator/host remains privileged; no protection from host-root compromise |
| Replay / concurrent release | Single ledger effect | Serialized transaction, consumed approval, unique proposal/invoice constraints | Sandbox ledger only; real bank integration needs equivalent external idempotency |
| Excess model/tool requests | Resource/financial budget | Pre-dispatch atomic holds, explicit rates, counters, time/concurrency limits | Hosting infrastructure costs are not model-token charges |
| Secrets in prompt/output/log | Credentials / personal data | Supported pattern redaction/block, account handles, safe audit fields | Not comprehensive PII / obfuscation detection |
| Crafted PDF parser exploit | Database / signing key / model service | Worker no-network, separate mount, no secrets/DB, read-only and resource bounds | Processor compromise can forge queue evidence; production needs disposable workers/fuzzing |
| Unsafe MCP discovery URL / pickle metadata | Host execution | Literal historical signatures + independent HTTPS allowlist; arbitrary artifact loading denied | Inspection harness, not a general arbitrary MCP client |
| Other demo visitor's document/token | Workspace evidence / receipts | Workspace ownership on routes; signed scope; isolated sessions | Demo provisioning throttle is per process; no enterprise identity claims |

No real bank actions, customer invoices, external messages, portal submissions or paid requests are part of verification.
