# RenderGuard

Build a specialised release gate for AI-prepared repeat-supplier SEPA payments. This is a HackYeah 2026 Goldman Sachs AI Control Layer entry. Preserve unrelated work. Never connect the executor to a real bank or send real money; all fixtures, suppliers, approvals and receipts are synthetic.

## Development
- Python 3.12, FastAPI, SQLite, React/TypeScript/Vite. Use `uv sync --extra dev`, `npm ci`, `npm run build`, `uv run pytest`.
- Policy and signature catalogs are data, never executable code. Never deserialize model artifacts or execute model output.
- The agent may propose; only an authenticated human reviewer may approve. The executor validates immutable proposal/evidence/policy/supplier versions and consumes approval atomically.
- Keep credentials, runtime state, original private documents and authentication tokens out of Git, exports, reports and submission bundles.
- Do not automate Viktor's Google Drive, Discord or other interactive apps. Headless verification of RenderGuard itself is allowed.

## Deployment
- Host: Baller (`ssh baller`), isolated folder `/srv/projects/renderguard`.
- Compose project `renderguard`; gateway listens on host loopback `127.0.0.1:18341`.
- Actual model: Baller, private `renderguard-model.service` user unit on loopback11445, Qwen2.5:7b, `/srv/projects/renderguard/models`, Ollama0.20.5, MemoryMax7G/CPUQuota300%, one loaded model/request, automatic restart and enabled user lingering. Installer: `scripts/install-baller-model.py`; restart/inspect with `systemctl --user restart/status renderguard-model`. Do not change or restart shared Baller Ollama11434.
- Historical Mac mini 3B runtime: `/Users/viktorvitovec/Projects/renderguard-runtime`; project-owned LaunchAgents `com.renderguard.ollama` and `com.renderguard.model-forward`, Homebrew Ollama, project model folder. Install/restart instructions are in `docs/operations.md` and `scripts/install-model-host.py`.
- Document worker is a separate container with no network, capped CPU/memory, and access only to the document queue/output volume, never the ledger or signing secret.
- Deploy: `./scripts/deploy.sh`. Persistent API state: `/srv/projects/renderguard/data/state`; document jobs: `/srv/projects/renderguard/data/documents`.
- Public URL verified: `https://renderguard.vvitovec.com`. Dedicated Cloudflare tunnel `renderguard-hackyeah-2026` / `48c29292-0517-4dab-bcfd-90ac7ec553c6`; container `renderguard-tunnel`; token `.secrets/tunnel-token` never committed. Preserve existing DNS, tunnels and unrelated projects.

## Completion
Preserve an immutable first-draft Git tag and submission package, then continue final work. Run the meaningful control suite, document/OCR integration tests, headless end-to-end flows, real local-model checks, and verify the live service. Commit/push current branch. Submission PDF has at most 10 slides and all materials are English. Save ready-to-upload packages; Viktor handles HackTribe/Discord/Drive. Do not submit any entry before Viktor reviews it. Team: Blue Bands Collectors; Viktor Vitovec, Jan Sebastian Rosicky, Krystof Bigas.

## Revised review snapshots
Preserve both `submission/draft-2026-10-03` and `submission/final` unchanged. Critique-driven revised packages use a distinct name such as `submission/revised-final-2026-10-03`; all remain prepared for review. The user requested a19:20Oct3 draft task; submission still requires the user to review and approve the exact package first. Current policy is a durable per-workspace cap, not a rolling hourly budget. Model attribution is retained at Mac mini runtime `models/notices/qwen2.5-3b` and `docs/third-party`; the historical 3B weights use the Qwen Research License; current7B uses Apache-2.0 and its runtime notices are at `/srv/projects/renderguard/models/notices/qwen2.5-7b`. Original notices are also shipped at `/third-party-licenses.txt` and `/licenses/` assets.

## Revision model probe

A temporary isolated 7B comparison runs on Baller at `/srv/projects/renderguard/model-probe/models`, loopback `127.0.0.1:11445`, user systemd unit `renderguard-model-probe.service` (`MemoryMax=7G`, `CPUQuota=300%`, one loaded model/call). It uses `/usr/local/bin/ollama` 0.20.5 and SHA-verified copied Qwen2.5:7b cache; the shared Ollama on 11434 is untouched. The five-case real-model comparison passed and this cache has been promoted to `/srv/projects/renderguard/models` under the persistent `renderguard-model.service`; the transient probe unit is stopped. Inspect with `systemctl --user status renderguard-model-probe`; stop with `systemctl --user stop renderguard-model-probe`. Logs are in the user journal; probe outputs remain under the project.
