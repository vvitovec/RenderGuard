"""Stable digest shared by runtime inspection and recorded evaluation tooling."""

import hashlib
from pathlib import Path


def source_hash(root: Path | None = None) -> str:
    root = root or Path(__file__).resolve().parents[1]
    paths = [
        path for directory in ("renderguard", "src", "policies", "signatures", "fixtures")
        for path in (root / directory).rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    ]
    return hashlib.sha256(
        b"".join(str(path.relative_to(root)).encode() + path.read_bytes() for path in sorted(paths))
    ).hexdigest()
