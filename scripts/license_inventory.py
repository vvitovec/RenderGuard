"""Preserve installed locked-runtime metadata and shipped third-party license notices."""

import importlib.metadata as metadata
import json
import shutil
import tomllib
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs/third-party"


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    pending = [
        Requirement(s).name
        for s in tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    ]
    seen, items = set(), []
    while pending:
        name = pending.pop()
        dist = metadata.distribution(name)
        actual = dist.metadata["Name"]
        if actual.lower() in seen:
            continue
        seen.add(actual.lower())
        for dependency in dist.requires or []:
            r = Requirement(dependency)
            if not r.marker or r.marker.evaluate({"extra": ""}):
                pending.append(r.name)
        license_name = (
            dist.metadata.get("License-Expression")
            or dist.metadata.get("License")
            or "Metadata unspecified; inspect preserved notices"
        )
        notices = []
        for path in dist.files or []:
            if any(part.lower() == "licenses" for part in path.parts) or path.name.lower().startswith(
                ("license", "copying", "notice")
            ):
                source = Path(dist.locate_file(path))
                if source.is_file():
                    target = TARGET / "notices" / actual / Path(str(path))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    notices.append(str(target.relative_to(ROOT)))
        items.append(
            {
                "ecosystem": "python",
                "name": actual,
                "version": dist.version,
                "license_metadata": license_name.splitlines()[0],
                "notices": notices,
            }
        )
    lock = json.loads((ROOT / "package-lock.json").read_text())
    for path, package in lock["packages"].items():
        if not path or package.get("dev"):
            continue
        name = path.split("node_modules/")[-1]
        notices = []
        for source in (ROOT / path).iterdir():
            if source.is_file() and source.name.lower().startswith(("license", "copying", "notice")):
                target = TARGET / "notices/npm" / name / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                notices.append(str(target.relative_to(ROOT)))
        items.append(
            {
                "ecosystem": "npm",
                "name": name,
                "version": package["version"],
                "license_metadata": package.get("license", "unspecified"),
                "notices": notices,
            }
        )
    (TARGET / "inventory.json").write_text(
        json.dumps(sorted(items, key=lambda x: (x["ecosystem"], x["name"].lower())), indent=2) + "\n"
    )
    text = "# Third-party runtime attribution\n\nGenerated from installed Python runtime dependencies and the locked production npm packages; full notices are preserved under `docs/third-party/notices`. This records package metadata, not a legal clearance certificate. Dev tooling is excluded. Original RenderGuard authors retain their rights; this inventory does not change the project code license.\n\n| Ecosystem | Package | Locked/installed version | License metadata |\n|---|---|---|---|\n"
    text += "\n".join(
        f"| {x['ecosystem']} | {x['name']} | {x['version']} | {x['license_metadata']} |"
        for x in sorted(items, key=lambda x: (x["ecosystem"], x["name"].lower()))
    )
    text += "\n\nAdditional runtime components: Tesseract (Apache-2.0), PDFium and its bundled dependency notices (preserved with pypdfium2), Ollama (MIT), uv (Apache-2.0/MIT), Cloudflared (Apache-2.0). System/container base libraries retain their upstream licenses. Fonts Literata/Public Sans retain their included OFL notices.\n\nThe actual `qwen2.5:3b` model is Qwen2.5-3B-Instruct under the **Qwen Research License**, not Apache-2.0. This is a research/evaluation hackathon prototype; commercial deployment needs a separately suitable/licensed model. Weights are not redistributed in the submission source archive. The model license and attribution are preserved alongside the runtime model and in this package. [Official model license](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE).\n\nRuntime upstream sources: [Tesseract](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE), [Ollama](https://github.com/ollama/ollama/blob/main/LICENSE), [uv](https://github.com/astral-sh/uv), [Cloudflared](https://github.com/cloudflare/cloudflared/blob/master/LICENSE).\n"
    (ROOT / "docs/third-party-licenses.md").write_text(text)
    print("Preserved metadata and available original notices for", len(items), "runtime packages")


if __name__ == "__main__":
    main()
