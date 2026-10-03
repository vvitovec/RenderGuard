# Third-party runtime attribution

Generated from installed Python runtime dependencies and the locked production npm packages; full notices are preserved under `docs/third-party/notices`. This records package metadata, not a legal clearance certificate. Dev tooling is excluded. Original RenderGuard authors retain their rights; this inventory does not change the project code license.

| Ecosystem | Package | Locked/installed version | License metadata |
|---|---|---|---|
| npm | @fontsource/literata | 5.3.0 | OFL-1.1 |
| npm | @fontsource/public-sans | 5.3.0 | OFL-1.1 |
| npm | @scarf/scarf | 1.4.0 | Apache-2.0 |
| npm | lucide-react | 0.577.0 | ISC |
| npm | react | 19.3.0 | MIT |
| npm | react-dom | 19.3.0 | MIT |
| npm | scheduler | 0.28.0 | MIT |
| npm | swagger-ui-dist | 5.33.1 | Apache-2.0 |
| python | annotated-doc | 0.0.5 | MIT |
| python | annotated-types | 0.8.0 | MIT |
| python | anyio | 4.15.1 | MIT |
| python | certifi | 2026.7.22 | MPL-2.0 |
| python | charset-normalizer | 3.5.2 | MIT |
| python | click | 8.5.0 | BSD-3-Clause |
| python | fastapi | 0.142.2 | MIT |
| python | h11 | 0.16.0 | MIT |
| python | httpcore | 1.0.9 | BSD-3-Clause |
| python | httpx | 0.28.1 | BSD-3-Clause |
| python | idna | 3.20 | BSD-3-Clause |
| python | opentelemetry-api | 1.45.0 | Apache-2.0 |
| python | packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| python | pillow | 12.3.0 | MIT-CMU |
| python | pydantic | 2.13.5 | MIT |
| python | pydantic_core | 2.46.5 | MIT |
| python | pypdf | 6.19.0 | BSD-3-Clause |
| python | pypdfium2 | 5.13.0 | BSD-3-Clause, Apache-2.0, dependency licenses |
| python | pytesseract | 0.3.13 | Apache License 2.0 |
| python | python-multipart | 0.0.32 | Apache-2.0 |
| python | PyYAML | 6.0.3 | MIT |
| python | qrcode | 8.2 | BSD |
| python | reportlab | 4.5.1 | BSD license (see license.txt for details), Copyright (c) 2000-2025, ReportLab Inc. |
| python | starlette | 1.7.0 | BSD-3-Clause |
| python | typing-inspection | 0.4.4 | MIT |
| python | typing_extensions | 4.16.0 | PSF-2.0 |
| python | uvicorn | 0.54.0 | BSD-3-Clause |
| python | zxing-cpp | 3.1.1 | Apache-2.0 |

Additional runtime components: Tesseract (Apache-2.0), PDFium and its bundled dependency notices (preserved with pypdfium2), Ollama (MIT), uv (Apache-2.0/MIT), Cloudflared (Apache-2.0). System/container base libraries retain their upstream licenses. Fonts Literata/Public Sans retain their included OFL notices.

The actual `qwen2.5:3b` model is Qwen2.5-3B-Instruct under the **Qwen Research License**, not Apache-2.0. This is a research/evaluation hackathon prototype; commercial deployment needs a separately suitable/licensed model. Weights are not redistributed in the submission source archive. The model license and attribution are preserved alongside the runtime model and in this package. [Official model license](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE).

Runtime upstream sources: [Tesseract](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE), [Ollama](https://github.com/ollama/ollama/blob/main/LICENSE), [uv](https://github.com/astral-sh/uv), [Cloudflared](https://github.com/cloudflare/cloudflared/blob/master/LICENSE).
