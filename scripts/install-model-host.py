"""Install only project-owned LaunchAgents on the durable Mac mini model host."""

import os
import plistlib
import subprocess
from pathlib import Path

root = Path.home() / "Projects/renderguard-runtime"
root.mkdir(parents=True, exist_ok=True)
agents = Path.home() / "Library/LaunchAgents"
agents.mkdir(parents=True, exist_ok=True)
jobs = {
    "com.renderguard.ollama": {
        "ProgramArguments": ["/opt/homebrew/bin/ollama", "serve"],
        "EnvironmentVariables": {
            "OLLAMA_HOST": "127.0.0.1:11444",
            "OLLAMA_MODELS": str(root / "models"),
            "OLLAMA_KEEP_ALIVE": "24h",
            "OLLAMA_NUM_PARALLEL": "1",
            "OLLAMA_MAX_LOADED_MODELS": "1",
            "OLLAMA_FLASH_ATTENTION": "1",
            "OLLAMA_KV_CACHE_TYPE": "q8_0",
        },
    },
    "com.renderguard.model-forward": {
        "ProgramArguments": [
            "/usr/bin/ssh",
            "-NT",
            "-o",
            "ControlMaster=no",
            "-o",
            "ControlPath=none",
            "-o",
            "ControlPersist=no",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "BatchMode=yes",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-o",
            "ServerAliveCountMax=3",
            "-R",
            "127.0.0.1:11444:127.0.0.1:11444",
            "baller",
        ],
    },
}
for name, config in jobs.items():
    target = agents / (name + ".plist")
    payload = {
        **config,
        "Label": name,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "WorkingDirectory": str(root),
        "StandardOutPath": str(root / (name + ".log")),
        "StandardErrorPath": str(root / (name + ".err.log")),
    }
    target.write_bytes(plistlib.dumps(payload))
    domain = "gui/" + str(os.getuid())
    subprocess.run(["launchctl", "bootout", domain, str(target)], capture_output=True)
    result = subprocess.run(["launchctl", "bootstrap", domain, str(target)], capture_output=True, text=True)
    print(name, "loaded" if result.returncode == 0 else result.stderr.strip())
