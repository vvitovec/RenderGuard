"""Prepare a frozen, reviewable package only. Never sends or submits anything."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from scripts.presentation import build

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["draft", "final"], required=True)
    parser.add_argument(
        "--name", help="Distinct immutable review snapshot name, e.g. revised-final-2026-10-03"
    )
    args = parser.parse_args()
    if args.name and not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,60}", args.name):
        raise SystemExit("Use a simple lowercase snapshot name")
    target = ROOT / "submission" / (args.name or ("draft-2026-10-03" if args.stage == "draft" else "final"))
    if target.exists():
        raise SystemExit("The frozen package already exists; preserve it rather than replacing it.")
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip():
        raise SystemExit("Commit the source and evidence reports before freezing a submission package.")
    target.mkdir(parents=True)
    pdf = build(target / "RenderGuard-Blue-Bands-Collectors.pdf", args.stage)
    assert len(PdfReader(pdf).pages) == 10
    for name in (
        "submission/team.json",
        "submission/description.md",
        "docs/judge-walkthrough.md",
        "docs/criteria-matrix.md",
        "docs/limitations.md",
        "docs/verification.md",
        "docs/architecture.md",
        "docs/operations.md",
        "docs/workflow-research.md",
        "docs/threat-model.md",
        "docs/revision-review.md",
        "docs/third-party-licenses.md",
    ):
        shutil.copy(ROOT / name, target / Path(name).name)
    shutil.copytree(ROOT / "evals", target / "verification")
    shutil.copytree(ROOT / "docs/third-party", target / "third-party")
    shutil.copytree(ROOT / "docs/reviews", target / "reviews")
    images = target / "screenshots"
    images.mkdir()
    for name in (
        "release.png",
        "qr-swap.png",
        "register.png",
        "control-probe.png",
        "mobile-workbench.png",
        "controls.png",
        "release-detail.png",
        "qr-detail.png",
        "model-input.png",
        "audit-detail.png",
    ):
        if (ROOT / "output/playwright" / name).exists():
            shutil.copy(ROOT / "output/playwright" / name, images / name)
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", sha], cwd=ROOT, text=True
    ).splitlines()
    with zipfile.ZipFile(target / "source.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for path in paths:
            if path.startswith(("submission/draft-", "submission/final", "submission/revised-", "output/")):
                continue
            content = subprocess.check_output(["git", "show", sha + ":" + path], cwd=ROOT)
            z.writestr("RenderGuard/" + path, content)
    (target / "START-HERE.md").write_text(
        "# RenderGuard — "
        + args.stage
        + " review package\n\nPrepared for Viktor to review and upload. This revision does not modify the existing HackTribe entry.\n\nPresentation: `RenderGuard-Blue-Bands-Collectors.pdf` (10 English slides). `description.md` contains entry text; `team.json` contains exact team/member metadata. `source.zip` is the frozen committed implementation. `verification` contains scoped actual test reports.\n\nDemo: https://renderguard.vvitovec.com\nRepository: https://github.com/vvitovec/RenderGuard\nSource commit: "
        + sha
        + "\n\nRead the judge walkthrough before presenting. All payment effects are sandbox-only.\n"
    )
    manifest = {
        "project": "RenderGuard",
        "stage": args.stage,
        "snapshot_name": target.name,
        "created_at": datetime.now().astimezone().isoformat(),
        "source_commit": sha,
        "slides": 10,
        "submission_status": "Prepared revision for review; this snapshot has not been uploaded by the packager",
        "demo_url": "https://renderguard.vvitovec.com",
        "repository_url": "https://github.com/vvitovec/RenderGuard",
        "files": {
            str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(target.rglob("*"))
            if p.is_file()
        },
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    archive = target.with_suffix(".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(target.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(target.parent))
    print("Saved review package", target, "and", archive)
    print("Source commit", sha, "· PDF pages", len(PdfReader(pdf).pages), "· not submitted")


if __name__ == "__main__":
    main()
