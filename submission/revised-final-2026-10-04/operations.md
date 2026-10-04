# Deployment operations

The MacBook is the interactive development machine. The app, ledger and current 7B local-model service live on always-on **Baller**. The earlier Mac mini 3B evaluation runtime remains a documented standby, with its original notices preserved.

## Baller resources

- Project: `/srv/projects/renderguard`.
- App: `renderguard-gateway`, loopback `127.0.0.1:18341`; not publicly bound.
- PDF processor: `renderguard-pdf-worker`, network mode **none**; only document queue mounted.
- Public ingress: `renderguard-tunnel`, dedicated Cloudflare tunnel `renderguard-hackyeah-2026` / `48c29292-0517-4dab-bcfd-90ac7ec553c6`.
- Public URL: `https://renderguard.vvitovec.com`; dedicated CNAME record, no unrelated DNS changes.
- Current model: private user systemd service `renderguard-model.service`, loopback `127.0.0.1:11445`, `/srv/projects/renderguard/models`, Qwen2.5:7b Q4_K_M (~4.7 GB). Ollama `/usr/local/bin/ollama` 0.20.5; one parallel request/model, 7 GiB memory cap, 300% CPU quota, automatic restart, enabled with user lingering. Existing Baller Ollama on 11434 was not reconfigured or restarted.
- Install the project model with `python3 scripts/install-baller-model.py` on Baller. Restart only `systemctl --user restart renderguard-model`; inspect `journalctl --user -u renderguard-model` and `curl http://127.0.0.1:11445/api/tags`. Model files were copied from the existing cache with each blob SHA-256 checked. The model license/notice is retained under `models/notices/qwen2.5-7b`.
- Persistent state: `data/state/ledger.sqlite` + `data/state/signing.key` (private), and `data/documents/<id>` (PDF, renders, evidence). App/worker UID 10001. Back up state/queue together for recovery; do not delete customer databases or unrelated resources.
- Tunnel token: `.secrets/tunnel-token`, UID 10001, mode 600, never committed. It is mounted only into cloudflared.
- Deployment: `RELEASE_SHA=<committed SHA> docker compose -f compose.production.yaml up -d --build`. Verify `/api/health` reports that exact SHA, worker mode, and bank disconnected; then verify the actual workflow.
- Inspect: `docker compose -f compose.production.yaml ps`, `docker logs --tail 80 renderguard-gateway`, `docker logs --tail 80 renderguard-pdf-worker`, `docker logs --tail 40 renderguard-tunnel`.
- Resource limits/read-only filesystems/capability drops are in Compose. No production bank integration or paid model fallback is configured.

## Historical Mac mini 3B runtime

- Project model runtime: `/Users/viktorvitovec/Projects/renderguard-runtime`.
- Model files: `models`, `qwen2.5:3b` Q4_K_M (~1.9 GB), copied from the verified existing local model cache.
- Model service: `com.renderguard.ollama` LaunchAgent. `OLLAMA_HOST=127.0.0.1:11444`, one loaded model, one parallel request, private project model folder. Ollama installed through Homebrew.
- Private reverse forward: `com.renderguard.model-forward` LaunchAgent, `ssh -N -R 127.0.0.1:11444:127.0.0.1:11444 baller`, keepalive / automatic restart. The forward uses `ControlMaster=no`, `ControlPath=none`, `ControlPersist=no` so LaunchAgent supervises its dedicated SSH process. Uses the existing authenticated host connection; no public model port.
- Both definitions: `~/Library/LaunchAgents/com.renderguard.*.plist`. Logs: project runtime `com.renderguard.*.log` / `.err.log`.
- Recreate project-owned jobs only: `/opt/homebrew/bin/python3 /Users/viktorvitovec/Projects/renderguard-runtime/install-model-host.py` (source: `scripts/install-model-host.py`).
- Verify: `curl http://127.0.0.1:11444/api/tags` on Mac mini and Baller. Restart only `launchctl kickstart -k gui/$(id -u)/com.renderguard.ollama` or the project forward when needed.

## Local deployment script

`scripts/deploy.sh` checks for a clean committed tree, transfers the committed snapshot to the isolated Baller directory, builds/starts the three project containers, and verifies the public health SHA. It leaves unrelated projects and services alone. Follow this with the full live evaluator / browser flow when application behavior changes.

## First draft and final review packages

`scripts/package_submission.py --stage draft` creates a frozen draft folder / ZIP with its presentation, description, demo guide, source snapshot and evidence reports. It records a manifest and SHA-256 checksums. The final stage similarly produces a separate final review package. No script contacts the submission portal, sends a message, or uploads a competition entry.
