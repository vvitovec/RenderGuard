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
- Actual model: Mac mini, dedicated Ollama on loopback 11444, `qwen2.5:3b`; persistent private reverse forward exposes only Baller loopback `http://127.0.0.1:11444`. Do not change or restart the shared Baller Ollama service on 11434.
- Mac mini model runtime: `/Users/viktorvitovec/Projects/renderguard-runtime`; project-owned LaunchAgents `com.renderguard.ollama` and `com.renderguard.model-forward`, Homebrew Ollama, project model folder. Install/restart instructions are in `docs/operations.md` and `scripts/install-model-host.py`.
- Document worker is a separate container with no network, capped CPU/memory, and access only to the document queue/output volume, never the ledger or signing secret.
- Deploy: `./scripts/deploy.sh`. Persistent API state: `/srv/projects/renderguard/data/state`; document jobs: `/srv/projects/renderguard/data/documents`.
- Public URL verified: `https://renderguard.vvitovec.com`. Dedicated Cloudflare tunnel `renderguard-hackyeah-2026` / `48c29292-0517-4dab-bcfd-90ac7ec553c6`; container `renderguard-tunnel`; token `.secrets/tunnel-token` never committed. Preserve existing DNS, tunnels and unrelated projects.

## Completion
Preserve an immutable first-draft Git tag and submission package, then continue final work. Run the meaningful control suite, document/OCR integration tests, headless end-to-end flows, real local-model checks, and verify the live service. Commit/push current branch. Submission PDF has at most 10 slides and all materials are English. Save ready-to-upload packages; Viktor handles HackTribe/Discord/Drive. Do not submit any entry before Viktor reviews it. Team: Blue Bands Collectors; Viktor Vitovec, Jan Sebastian Rosicky, Krystof Bigas.
