FROM node:22-bookworm-slim AS web
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src ./src
COPY index.html tsconfig.json vite.config.ts ./
COPY scripts/copy-swagger.mjs ./scripts/copy-swagger.mjs
COPY docs/third-party ./docs/third-party
COPY docs/third-party-licenses.md ./docs/third-party-licenses.md
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.10.0 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY renderguard ./renderguard
COPY src ./src
COPY policies ./policies
COPY signatures ./signatures
COPY fixtures ./fixtures
COPY scripts ./scripts
COPY --from=web /app/dist ./dist
RUN groupadd -g 10001 renderguard && useradd -u 10001 -g 10001 -M renderguard
ENV PATH="/app/.venv/bin:$PATH" STATE_ROOT=/data/state DOCUMENT_ROOT=/data/documents
USER 10001:10001
CMD ["uvicorn","renderguard.api:app","--host","127.0.0.1","--port","18341","--proxy-headers","--forwarded-allow-ips","127.0.0.1"]
