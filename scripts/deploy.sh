#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Commit project changes before deployment."
  exit 1
fi
renderguard_sha=$(git rev-parse HEAD)
git archive HEAD | ssh baller 'tar -xf - -C /srv/projects/renderguard'
ssh baller "cd /srv/projects/renderguard && RELEASE_SHA=$renderguard_sha docker compose -f compose.production.yaml up --build -d"
uv run python - "$renderguard_sha" <<'PY'
import sys, time
import httpx
expected=sys.argv[1]
for attempt in range(30):
    try:
        response=httpx.get('https://renderguard.vvitovec.com/api/health',timeout=5)
        response.raise_for_status()
        result=response.json()
        if result.get('release_sha')==expected and result.get('bank_connected') is False:
            print('Verified deployed SHA',expected)
            break
    except Exception:
        pass
    time.sleep(2)
else:
    raise SystemExit('Deployment did not verify the expected SHA')
PY
