"""Install the project-owned, resource-bounded Baller model service. Run on Baller."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path('/srv/projects/renderguard')
MODELS = ROOT / 'models'
SOURCE = Path('/usr/share/ollama/.ollama/models')
relative = Path('manifests/registry.ollama.ai/library/qwen2.5/7b')


def main():
    if not Path('/usr/local/bin/ollama').is_file():
        raise SystemExit('Install Ollama before running this Baller-only installer')
    subprocess.run(['systemctl', '--user', 'stop', 'renderguard-model-probe'], check=False)
    prototype = ROOT / 'model-probe/models'
    if prototype.exists() and not MODELS.exists():
        shutil.move(str(prototype), MODELS)
    if not (MODELS / relative).exists():
        manifest = json.loads((SOURCE / relative).read_text())
        for entry in [manifest['config'], *manifest['layers']]:
            name = entry['digest'].replace(':', '-')
            target = MODELS / 'blobs' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['cp', '--reflink=auto', str(SOURCE / 'blobs' / name), str(target)], check=True)
            with target.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != entry['digest'].split(':')[1]:
                    raise SystemExit('Model digest verification failed')
        target = MODELS / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((SOURCE / relative).read_bytes())
    folder = Path.home() / '.config/systemd/user'
    folder.mkdir(parents=True, exist_ok=True)
    unit = '''[Unit]
Description=RenderGuard private local model
After=network.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Environment=OLLAMA_HOST=127.0.0.1:11445
Environment=OLLAMA_MODELS=/srv/projects/renderguard/models
Environment=OLLAMA_NUM_PARALLEL=1
Environment=OLLAMA_MAX_LOADED_MODELS=1
Environment=OLLAMA_KEEP_ALIVE=24h
Restart=always
RestartSec=5
MemoryMax=7G
CPUQuota=300%
NoNewPrivileges=true

[Install]
WantedBy=default.target
'''
    (folder / 'renderguard-model.service').write_text(unit)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', '--now', 'renderguard-model'], check=True)
    print('Installed private model on loopback 11445; shared Ollama untouched')


if __name__ == '__main__':
    main()
