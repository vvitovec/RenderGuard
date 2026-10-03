"""Network-isolated PDF worker. Shared queue contains no DB or approval secret."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from .documents import write_result


def run_one(folder: Path):
    from .documents import process_pdf

    try:
        request = json.loads((folder / "request.json").read_text())
        limit = request.get("max_pages", 5)
        if not isinstance(limit, int) or not 1 <= limit <= 5:
            raise ValueError("Invalid page bound")
        result = process_pdf(folder, max_pages=limit)
        write_result(folder, {"ok": True, "evidence": result})
    except Exception as exc:
        write_result(folder, {"ok": False, "error": str(exc)[:400]})


def main():
    root = Path(os.environ.get("DOCUMENT_ROOT", "data/documents"))
    root.mkdir(parents=True, exist_ok=True)
    while True:
        for folder in sorted(root.iterdir()):
            if (
                not folder.is_dir()
                or not (folder / "request.json").exists()
                or (folder / "result.json").exists()
            ):
                continue
            try:
                subprocess.run(
                    [sys.executable, "-m", "renderguard.worker", "--one", str(folder)],
                    timeout=55,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                write_result(
                    folder, {"ok": False, "error": "Document processing exceeded the 55-second limit"}
                )
            if not (folder / "result.json").exists():
                write_result(
                    folder, {"ok": False, "error": "Document worker stopped before producing valid evidence"}
                )
        time.sleep(0.3)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--one":
        run_one(Path(sys.argv[2]))
    else:
        main()
