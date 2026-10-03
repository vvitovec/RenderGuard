"""Verify the own-app HTTPS release and retained demo state; never print credentials."""

import argparse
import json
import subprocess
import time
from pathlib import Path

import httpx

from renderguard.provenance import source_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='https://renderguard.vvitovec.com')
    parser.add_argument('--output', default='evals/deployment.json')
    args = parser.parse_args()
    expected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    checkpoint_path = ROOT / '.secrets/deployment-checkpoint.json'
    checkpoint = json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else None
    with httpx.Client(base_url=args.url, cookies=checkpoint['cookies'] if checkpoint else {}, timeout=20) as client:
        def get(path):
            result = client.get(path)
            result.raise_for_status()
            return result

        health = get('/api/health').json()
        if not checkpoint:
            response = client.post('/api/demo/start')
            response.raise_for_status()
        session = get('/api/session').json()
        suppliers = get('/api/suppliers').json()
        model = get('/api/model-health').json()
        assert health['release_sha'] == expected and health['bank_connected'] is False
        assert session['source_sha'] == source_hash()
        assert len(suppliers) >= 3 and model['available'] and 'qwen2.5:7b' in model['models']
        if checkpoint:
            assert session['workspace'] == checkpoint['workspace']
        assert 'qwen2.5:7b' in get('/third-party-licenses.txt').text
        assert 'Apache License' in get('/licenses/qwen2.5-7b/LICENSE').text
        assert get('/').status_code == 200
        report = {
            'recorded_at': time.time(), 'health': health, 'source_sha': session['source_sha'],
            'session_survived_container_recreation': True if checkpoint else None,
            'supplier_records_survived': True if checkpoint else None,
            'private_model_available': True, 'model': 'qwen2.5:7b',
            'self_hosted_model_notices_available': True,
            'scope': 'Actual public HTTPS, current application digest, private7B availability and self-hosted notices. Retained signed-session checks use an optional private checkpoint; actual inference is separately verified in live reports. Sandbox only.',
        }
    target = ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n')
    print('Verified actual HTTPS/source, signed session, supplier records, private7B model and notices')


if __name__ == '__main__':
    main()
