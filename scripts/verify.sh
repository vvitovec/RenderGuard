#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
uv sync --extra dev --frozen
npm ci
npm run build
uv run ruff check renderguard tests scripts
uv run python -m pytest -q --junitxml=evals/unit-tests.xml
uv run python -m scripts.evaluate
uv run python -m scripts.performance
