from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def uid() -> str:
    return secrets.token_hex(16)


def now() -> float:
    return time.time()


class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        secret_path = root / "signing.key"
        if not secret_path.exists():
            try:
                fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(secrets.token_bytes(48))
            except FileExistsError:
                pass
        self.secret = secret_path.read_bytes()
        self.path = root / "ledger.sqlite"
        with closing(self.connect()) as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS workspaces(id TEXT PRIMARY KEY, created REAL, policy TEXT,
                  model_calls INTEGER DEFAULT 0, tool_calls INTEGER DEFAULT 0, tokens INTEGER DEFAULT 0,
                  cost INTEGER DEFAULT 0, reserved_tokens INTEGER DEFAULT 0, reserved_cost INTEGER DEFAULT 0,
                  active_calls INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS suppliers(workspace TEXT, id TEXT, data TEXT, PRIMARY KEY(workspace,id));
                CREATE TABLE IF NOT EXISTS obligations(workspace TEXT, id TEXT, data TEXT, PRIMARY KEY(workspace,id));
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, workspace TEXT, created REAL,
                  filename TEXT, sha TEXT, supplier_id TEXT, obligation_id TEXT, status TEXT, data TEXT);
                CREATE TABLE IF NOT EXISTS proposals(id TEXT PRIMARY KEY, workspace TEXT, document TEXT,
                  created REAL, status TEXT, payment TEXT, binding TEXT, decision TEXT, agent TEXT);
                CREATE TABLE IF NOT EXISTS approvals(id TEXT PRIMARY KEY, workspace TEXT, proposal TEXT,
                  hash TEXT, binding_hash TEXT, expires REAL, consumed REAL, approver TEXT);
                CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, workspace TEXT, proposal TEXT UNIQUE,
                  invoice_key TEXT, created REAL, data TEXT, UNIQUE(workspace,invoice_key));
                CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, workspace TEXT, created REAL,
                  kind TEXT, verdict TEXT, control TEXT, data TEXT);
                CREATE TABLE IF NOT EXISTS reservations(id TEXT PRIMARY KEY, workspace TEXT, tokens INTEGER,
                  cost INTEGER, status TEXT, created REAL, rates TEXT DEFAULT '{}');
                CREATE INDEX IF NOT EXISTS events_workspace ON events(workspace,created);
                CREATE INDEX IF NOT EXISTS documents_workspace ON documents(workspace,created);
            """)
            if "rates" not in [row["name"] for row in db.execute("PRAGMA table_info(reservations)")]:
                db.execute("ALTER TABLE reservations ADD COLUMN rates TEXT DEFAULT '{}'")
            if "feed" not in [row["name"] for row in db.execute("PRAGMA table_info(workspaces)")]:
                db.execute("ALTER TABLE workspaces ADD COLUMN feed TEXT")

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=15000")
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    def one(self, sql: str, params=()) -> dict | None:
        with closing(self.connect()) as db:
            row = db.execute(sql, params).fetchone()
        return dict(row) if row else None

    def all(self, sql: str, params=()) -> list[dict]:
        with closing(self.connect()) as db:
            return [dict(x) for x in db.execute(sql, params).fetchall()]

    def execute(self, sql: str, params=()):
        with closing(self.connect()) as db:
            db.execute(sql, params)

    def event(self, workspace: str, kind: str, verdict: str, control: str, data: dict):
        from .privacy import safe_log

        self.execute(
            "INSERT INTO events VALUES(?,?,?,?,?,?,?)",
            (uid(), workspace, now(), kind, verdict, control, canonical(safe_log(data))),
        )

    def sign(self, payload: dict) -> str:
        import base64

        body = base64.urlsafe_b64encode(canonical(payload).encode()).decode().rstrip("=")
        sig = hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{sig}"

    def verify(self, token: str, audience: str) -> dict:
        import base64

        try:
            body, sig = token.split(".")
            expected = hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                raise ValueError("Invalid signature")
            payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
            if payload.get("aud") != audience or payload.get("exp", 0) <= now():
                raise ValueError("Expired or wrong audience")
            if not isinstance(payload.get("workspace"), str):
                raise ValueError("Missing workspace")
            return payload
        except (ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid or expired capability") from exc
