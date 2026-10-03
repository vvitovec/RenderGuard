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
python3 - "$renderguard_sha" <<'PY'
import json, sys, time, urllib.request
expected=sys.argv[1]
for attempt in range(30):
    try:
        with urllib.request.urlopen('https://renderguard.vvitovec.com/api/health',timeout=5) as response:
            result=json.load(response)
        if result.get('release_sha')==expected and result.get('bank_connected') is False:
            print('Verified deployed SHA',expected)
            break
    except Exception:
        pass
    time.sleep(2)
else:
    raise SystemExit('Deployment did not verify the expected SHA')
PY
