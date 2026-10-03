from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .gateway import Denied, Gateway, OllamaProvider, Principal
from .masterdata import seed_workspace
from .payments import Payments, unpack
from .policy import Policy, PolicyCatalog
from .privacy import safe_log
from .store import Store, canonical, now, uid

ROOT = Path(__file__).resolve().parents[1]


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Persona(Body):
    role: Literal["operator", "reviewer", "admin"]


class FixtureImport(Body):
    fixture_id: str = Field(max_length=60)


class Interaction(Body):
    kind: Literal[
        "model.request", "model.response", "tool.call", "resource.read", "mcp.discovery", "model.load"
    ]
    payload: dict
    semantic: bool = False


class ProposalBody(Body):
    document_id: str
    payment: dict


class ExecutionBody(Body):
    approval_token: str = Field(max_length=4000)


class VerifyBank(Body):
    iban: str = Field(max_length=34)
    verification_note: str = Field(min_length=20, max_length=500)


def create_app(
    state_root: Path | None = None,
    document_root: Path | None = None,
    provider=None,
    policy_path: Path | None = None,
    embedded_worker: bool | None = None,
) -> FastAPI:
    state_root = state_root or Path(os.environ.get("STATE_ROOT", "data/state"))
    document_root = document_root or Path(os.environ.get("DOCUMENT_ROOT", "data/documents"))
    document_root.mkdir(parents=True, exist_ok=True)
    store = Store(state_root)
    catalog = PolicyCatalog(
        store, policy_path or ROOT / "policies/default.yaml", ROOT / "signatures/catalog.json"
    )
    provider = provider or OllamaProvider(os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    gateway = Gateway(store, catalog, provider)
    payments = Payments(store, gateway, document_root)
    if embedded_worker is None:
        embedded_worker = os.environ.get("EMBEDDED_WORKER", "false").lower() == "true"
    rate_history: dict[str, list[float]] = {}

    @asynccontextmanager
    async def lifespan(app):
        process = None
        if embedded_worker:
            env = {**os.environ, "DOCUMENT_ROOT": str(document_root.resolve())}
            process = subprocess.Popen([sys.executable, "-m", "renderguard.worker"], env=env)
        yield
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    app = FastAPI(
        title="RenderGuard",
        version="1.0.0",
        description="Release controls for AI-prepared repeat-supplier SEPA payments. All hosted demo payments are sandbox-only.",
        lifespan=lifespan,
    )
    app.state.store, app.state.gateway, app.state.payments = store, gateway, payments

    @app.middleware("http")
    async def security_headers(request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.headers.get("origin"):
            origin = request.headers["origin"].rstrip("/")
            configured = os.environ.get("PUBLIC_ORIGIN", "").rstrip("/")
            host_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
            allowed = {host_origin, configured, "http://127.0.0.1:5173", "http://localhost:5173"}
            if origin not in allowed:
                return JSONResponse(
                    {"error": "origin", "message": "Cross-origin state changes are not allowed"},
                    status_code=403,
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; font-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(Denied)
    async def denied_handler(request, exc):
        return JSONResponse(
            {"error": exc.code, "message": exc.reason, "verdict": exc.verdict},
            status_code=403 if exc.verdict == "block" else 409,
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request, exc):
        return JSONResponse({"error": "invalid_input", "message": str(exc)[:1000]}, status_code=422)

    def capability(workspace, role, demo=False):
        return store.sign(
            {
                "aud": "session",
                "workspace": workspace,
                "role": role,
                "sub": "demo-" + role,
                "demo": demo,
                "exp": now() + 86400,
            }
        )

    def set_cookie(response, token):
        response.set_cookie(
            "rg_session",
            token,
            httponly=True,
            samesite="strict",
            max_age=86400,
            secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        )

    def auth(authorization: str | None = Header(default=None), rg_session: str | None = Cookie(default=None)):
        token = authorization[7:] if authorization and authorization.startswith("Bearer ") else rg_session
        if not token:
            raise HTTPException(401, "Start an isolated demo workspace or supply a signed capability")
        try:
            payload = store.verify(token, "session")
        except ValueError as exc:
            raise HTTPException(401, "Invalid or expired session capability") from exc
        if payload.get("role") not in ("operator", "reviewer", "admin", "agent"):
            raise HTTPException(401, "Invalid role")
        if not store.one("SELECT id FROM workspaces WHERE id=?", (payload["workspace"],)):
            raise HTTPException(401, "Unknown workspace")
        return Principal(payload["workspace"], payload["role"], payload.get("sub", "unknown"))

    def require(p: Principal, roles):
        if p.role not in roles:
            raise Denied("role", f"This action requires {' or '.join(roles)} capability")

    def summary(p: Principal):
        policy, version = catalog.get(p.workspace)
        usage = store.one(
            "SELECT model_calls,tool_calls,tokens,cost,reserved_tokens,reserved_cost,active_calls FROM workspaces WHERE id=?",
            (p.workspace,),
        )
        return {
            "workspace": p.workspace,
            "role": p.role,
            "subject": p.subject,
            "sandbox": True,
            "policy": policy.model_dump(),
            "policy_version": version,
            "policy_error": catalog.last_error,
            "usage": usage,
            "release_sha": os.environ.get("RELEASE_SHA", "development"),
            "demo_personas": os.environ.get("AUTH_MODE", "demo") == "demo",
        }

    @app.get("/api/health")
    async def health():
        return {
            "ok": True,
            "version": "1.0.0",
            "release_sha": os.environ.get("RELEASE_SHA", "development"),
            "bank_connected": False,
            "worker_mode": "subprocess" if embedded_worker else "isolated-container",
        }

    @app.post("/api/demo/start")
    async def start(request: Request, response: Response):
        if os.environ.get("AUTH_MODE", "demo") != "demo":
            raise HTTPException(403, "Public demo provisioning is disabled")
        address = request.headers.get("cf-connecting-ip") or (
            request.client.host if request.client else "local"
        )
        history = [t for t in rate_history.get(address, []) if now() - t < 3600]
        if len(history) >= 30:
            raise HTTPException(429, "Demo workspace limit reached. Reuse the current workspace.")
        history.append(now())
        rate_history[address] = history
        workspace = uid()
        seed_workspace(store, workspace)
        set_cookie(response, capability(workspace, "operator", True))
        store.event(workspace, "workspace.created", "allow", "demo", {"fictional_data": True})
        return summary(Principal(workspace, "operator", "demo-operator"))

    @app.get("/api/session")
    async def session(p=Depends(auth)):
        return summary(p)

    @app.get("/api/session-status")
    async def session_status(request: Request):
        try:
            payload = store.verify(request.cookies.get("rg_session", ""), "session")
            exists = bool(store.one("SELECT id FROM workspaces WHERE id=?", (payload["workspace"],)))
            return {"logged_in": exists}
        except ValueError:
            return {"logged_in": False}

    @app.post("/api/session/persona")
    async def persona(body: Persona, response: Response, request: Request, p=Depends(auth)):
        if os.environ.get("AUTH_MODE", "demo") != "demo":
            raise Denied("demo_disabled", "Demo persona switching is disabled")
        original = store.verify(request.cookies.get("rg_session", ""), "session")
        if not original.get("demo") or p.role == "agent":
            raise Denied("persona", "Agent capabilities cannot switch into human personas")
        set_cookie(response, capability(p.workspace, body.role, True))
        store.event(
            p.workspace,
            "persona.changed",
            "allow",
            "demo",
            {"role": body.role, "scope": "own fictional workspace"},
        )
        return summary(Principal(p.workspace, body.role, "demo-" + body.role))

    @app.get("/api/model-health")
    async def model_health(p=Depends(auth)):
        return (
            await provider.health()
            if hasattr(provider, "health")
            else {"available": True, "models": ["test-provider"]}
        )

    @app.get("/api/suppliers")
    async def suppliers(p=Depends(auth)):
        return [
            json.loads(row["data"])
            for row in store.all("SELECT data FROM suppliers WHERE workspace=?", (p.workspace,))
        ]

    @app.get("/api/obligations")
    async def obligations(p=Depends(auth)):
        return [
            json.loads(row["data"])
            for row in store.all("SELECT data FROM obligations WHERE workspace=?", (p.workspace,))
        ]

    @app.post("/api/suppliers/{supplier_id}/verify-bank")
    async def verify_bank(supplier_id: str, body: VerifyBank, p=Depends(auth)):
        from .documents import normalize_iban, valid_iban

        require(p, {"admin"})
        value = normalize_iban(body.iban)
        if not valid_iban(value):
            raise HTTPException(422, "A format-valid supported account is required")
        supplier = payments.supplier(p.workspace, supplier_id)
        supplier.update(
            {
                "iban": value,
                "version": supplier["version"] + 1,
                "verification": body.verification_note,
                "verified_at": now(),
            }
        )
        store.execute(
            "UPDATE suppliers SET data=? WHERE workspace=? AND id=?",
            (canonical(supplier), p.workspace, supplier_id),
        )
        store.event(
            p.workspace,
            "supplier.bank_verified",
            "allow",
            "independent_verification",
            {"supplier_id": supplier_id, "version": supplier["version"], "note": body.verification_note},
        )
        return {
            "supplier": supplier,
            "message": "Demo verification recorded separately. Existing proposals/approvals are stale; prepare again.",
        }

    @app.get("/api/fixtures")
    async def fixtures():
        return json.loads((ROOT / "fixtures/manifest.json").read_text())

    @app.get("/api/fixtures/{fixture_id}/download")
    async def fixture_download(fixture_id: str):
        manifest = json.loads((ROOT / "fixtures/manifest.json").read_text())
        item = next((x for x in manifest if x["id"] == fixture_id), None)
        if not item:
            raise HTTPException(404, "Unknown synthetic fixture")
        return FileResponse(
            ROOT / "fixtures" / item["filename"], media_type="application/pdf", filename=item["filename"]
        )

    def enqueue(p, content, filename, supplier_id, obligation_id):
        require(p, {"operator", "admin"})
        policy, _ = catalog.get(p.workspace)
        if not content.startswith(b"%PDF-"):
            raise HTTPException(422, "Only PDF invoices are accepted")
        if len(content) > policy.document.max_bytes:
            raise HTTPException(413, "Invoice exceeds the configured file-size limit")
        count = store.one("SELECT COUNT(*) AS n FROM documents WHERE workspace=?", (p.workspace,))["n"]
        if count >= 30:
            raise HTTPException(429, "This demo workspace has reached its 30-document processing limit")
        payments.supplier(p.workspace, supplier_id)
        obligation = payments.obligation(p.workspace, obligation_id)
        if obligation["supplier_id"] != supplier_id:
            raise HTTPException(422, "Obligation belongs to another supplier")
        doc_id = uid()
        folder = document_root / doc_id
        folder.mkdir(mode=0o750)
        (folder / "input.pdf").write_bytes(content)
        filename = re.sub(r"[^A-Za-z0-9._ -]", "_", filename)[:120]
        sha = hashlib.sha256(content).hexdigest()
        store.execute(
            "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)",
            (doc_id, p.workspace, now(), filename, sha, supplier_id, obligation_id, "queued", "{}"),
        )
        (folder / "request.tmp").write_text(
            canonical({"document_id": doc_id, "sha": sha, "max_pages": policy.document.max_pages})
        )
        (folder / "request.tmp").replace(folder / "request.json")
        store.event(
            p.workspace,
            "document.queued",
            "allow",
            "document_input",
            {"document_id": doc_id, "bytes": len(content), "sha": sha},
        )
        return payments.document(p.workspace, doc_id)

    @app.post("/api/documents/import-fixture")
    async def import_fixture(body: FixtureImport, p=Depends(auth)):
        item = next(
            (
                x
                for x in json.loads((ROOT / "fixtures/manifest.json").read_text())
                if x["id"] == body.fixture_id
            ),
            None,
        )
        if not item:
            raise HTTPException(404, "Unknown synthetic fixture")
        return enqueue(
            p,
            (ROOT / "fixtures" / item["filename"]).read_bytes(),
            item["filename"],
            item["supplier_id"],
            item["obligation_id"],
        )

    @app.post("/api/documents/upload")
    async def upload(
        file: UploadFile = File(...),
        supplier_id: str = Form(...),
        obligation_id: str = Form(...),
        p=Depends(auth),
    ):
        policy, _ = catalog.get(p.workspace)
        content = await file.read(policy.document.max_bytes + 1)
        return enqueue(p, content, file.filename or "invoice.pdf", supplier_id, obligation_id)

    @app.get("/api/documents")
    async def documents(p=Depends(auth)):
        rows = store.all(
            "SELECT id,created,filename,sha,supplier_id,obligation_id,status FROM documents WHERE workspace=? ORDER BY created DESC",
            (p.workspace,),
        )
        for row in rows:
            if row["status"] in ("queued", "processing"):
                row["status"] = payments.consume_worker_result(p.workspace, row["id"])["status"]
            latest = store.one(
                "SELECT id,status FROM proposals WHERE workspace=? AND document=? ORDER BY created DESC LIMIT 1",
                (p.workspace, row["id"]),
            )
            row["proposal"] = latest
        return rows

    @app.get("/api/documents/{document_id}")
    async def document(document_id: str, p=Depends(auth)):
        doc = payments.consume_worker_result(p.workspace, document_id)
        doc["evidence_decision"] = payments.evidence_checks(p.workspace, doc)
        latest = store.one(
            "SELECT id FROM proposals WHERE workspace=? AND document=? ORDER BY created DESC LIMIT 1",
            (p.workspace, document_id),
        )
        doc["proposal"] = payments.proposal(p.workspace, latest["id"]) if latest else None
        return doc

    @app.get("/api/documents/{document_id}/pages/{number}")
    async def page(document_id: str, number: int, p=Depends(auth)):
        doc = payments.document(p.workspace, document_id)
        if doc["status"] != "ready" or number not in [x["page"] for x in doc["data"].get("pages", [])]:
            raise HTTPException(404, "Rendered page is not available")
        return FileResponse(document_root / document_id / f"page-{number}.png", media_type="image/png")

    @app.post("/api/documents/{document_id}/prepare")
    async def prepare(document_id: str, p=Depends(auth)):
        require(p, {"operator", "admin"})
        return await payments.prepare(p, document_id)

    @app.post("/api/sdk/propose")
    async def propose(body: ProposalBody, p=Depends(auth)):
        require(p, {"operator", "agent", "admin"})
        return await payments.propose(p, body.document_id, body.payment)

    @app.post("/api/proposals/{proposal_id}/approve")
    async def approve(proposal_id: str, p=Depends(auth)):
        return payments.approve(p, proposal_id)

    @app.post("/api/proposals/{proposal_id}/execute")
    async def execute(proposal_id: str, body: ExecutionBody, p=Depends(auth)):
        try:
            return payments.execute(p, proposal_id, body.approval_token)
        except Denied as exc:
            store.event(
                p.workspace,
                "payment.execution_denied",
                exc.verdict,
                exc.code,
                {"proposal_id": proposal_id, "reason": exc.reason},
            )
            raise

    @app.get("/api/policy")
    async def policy(p=Depends(auth)):
        current, version = catalog.get(p.workspace)
        return {
            "policy": current.model_dump(),
            "version": version,
            "error": catalog.last_error,
            "feed": catalog.feed(p.workspace),
            "scope": "isolated demo workspace",
        }

    @app.put("/api/signatures")
    async def update_feed(body: dict, p=Depends(auth)):
        require(p, {"admin"})
        try:
            return catalog.update_feed(p.workspace, body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.put("/api/policy")
    async def update_policy(body: Policy, p=Depends(auth)):
        require(p, {"admin"})
        version = catalog.update(p.workspace, body.model_dump())
        return {
            "policy": body.model_dump(),
            "version": version,
            "message": "Applied atomically. Earlier proposals/approvals require fresh preparation.",
        }

    @app.post("/api/playground")
    async def playground(body: Interaction, p=Depends(auth)):
        # Identity is derived from the signed capability, never from a claimed payload role.
        if len(canonical(body.payload).encode()) > 30000:
            raise HTTPException(413, "Interaction exceeds playground size bound")
        result = gateway.evaluate(p, body.kind, body.payload)
        if body.semantic and result["verdict"] == "allow":
            guard = await gateway.semantic(p, str(result["payload"].get("text", "")))
            from .gateway import decision

            result = {**result, **decision(result["checks"] + [guard], result["policy_version"])}
        return result

    @app.get("/api/events")
    async def events(p=Depends(auth)):
        return [
            unpack(row)
            for row in store.all(
                "SELECT * FROM events WHERE workspace=? ORDER BY created DESC LIMIT 200", (p.workspace,)
            )
        ]

    @app.get("/api/audit/export")
    async def export(p=Depends(auth)):
        require(p, {"reviewer", "admin"})
        rows = [
            unpack(row)
            for row in store.all("SELECT * FROM events WHERE workspace=? ORDER BY created", (p.workspace,))
        ]
        text = "\n".join(canonical(safe_log(row)) for row in rows) + "\n"
        return PlainTextResponse(
            text, headers={"Content-Disposition": 'attachment; filename="renderguard-audit.jsonl"'}
        )

    @app.get("/api/receipts")
    async def receipts(p=Depends(auth)):
        require(p, {"operator", "reviewer", "admin"})
        return [
            json.loads(row["data"])
            for row in store.all(
                "SELECT data FROM receipts WHERE workspace=? ORDER BY created DESC", (p.workspace,)
            )
        ]

    @app.get("/api/receipts/export")
    async def receipt_export(p=Depends(auth)):
        require(p, {"reviewer", "admin"})
        rows = [
            json.loads(row["data"])
            for row in store.all(
                "SELECT data FROM receipts WHERE workspace=? ORDER BY created", (p.workspace,)
            )
        ]
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "sandbox_only",
                "receipt",
                "supplier",
                "invoice",
                "iban",
                "amount_minor",
                "currency",
                "proposal_hash",
            ]
        )
        for row in rows:
            payment = row["payment"]
            writer.writerow(
                [
                    "TRUE",
                    row["id"],
                    payment["supplier_id"],
                    payment["invoice_number"],
                    payment["iban"],
                    payment["amount_minor"],
                    payment["currency"],
                    row["binding"]["payment_hash"],
                ]
            )
        return PlainTextResponse(
            buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="sandbox-release-register.csv"'},
        )

    @app.get("/api/metrics")
    async def metrics(p=Depends(auth)):
        rows = [
            unpack(row)
            for row in store.all("SELECT * FROM events WHERE workspace=? ORDER BY created", (p.workspace,))
        ]
        latency = sorted(
            [
                x["data"]["latency_ms"]
                for x in rows
                if x["kind"] in ("model.complete", "document.ready")
                and isinstance(x["data"].get("latency_ms"), (int, float))
            ]
        )
        totals = {
            verdict: sum(x["verdict"] == verdict for x in rows) for verdict in ("allow", "block", "review")
        }
        controls = {}
        for row in rows:
            for c in row["data"].get("checks", []):
                if c["verdict"] in ("block", "review"):
                    controls[c["control"]] = controls.get(c["control"], 0) + 1
        return {
            "events": len(rows),
            "decisions": totals,
            "held_controls": controls,
            "model_calls": summary(p)["usage"],
            "p50_processing_ms": latency[len(latency) // 2] if latency else None,
            "p95_processing_ms": latency[min(len(latency) - 1, int(len(latency) * 0.95))]
            if latency
            else None,
            "latency_scope": "model/document stages, not total end-to-end time",
            "receipts": store.one("SELECT COUNT(*) AS n FROM receipts WHERE workspace=?", (p.workspace,))[
                "n"
            ],
        }

    @app.get("/api/evaluation")
    async def evaluation(p=Depends(auth)):
        target = ROOT / "evals/results.json"
        return (
            json.loads(target.read_text())
            if target.exists()
            else {
                "status": "not_run",
                "message": "Run the executable suite to generate an evidence-backed report.",
            }
        )

    dist = ROOT / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}")
        async def frontend(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "Unknown API route")
            candidate = (dist / path).resolve()
            if candidate.is_relative_to(dist.resolve()) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


app = create_app()
