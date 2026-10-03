from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .store import Store, canonical, digest


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Controls(StrictModel):
    semantic: bool = True
    semantic_threshold: float = Field(default=0.75, ge=0, le=1)
    pii_action: Literal["redact", "block"] = "redact"
    signatures: bool = True
    require_approval: bool = True
    evidence_consistency: bool = True


class Budgets(StrictModel):
    max_model_calls: int = Field(default=8, ge=0, le=100)
    max_tool_calls: int = Field(default=12, ge=0, le=200)
    max_input_bytes: int = Field(default=24000, ge=1, le=100000)
    max_output_tokens: int = Field(default=700, ge=1, le=4096)
    max_tokens: int = Field(default=80000, ge=0, le=1000000)
    max_cost_microusd: int = Field(default=1000000, ge=0, le=100000000)
    timeout_seconds: int = Field(default=45, ge=1, le=120)
    max_concurrent: int = Field(default=1, ge=1, le=2)


class DocumentPolicy(StrictModel):
    max_bytes: int = Field(default=8388608, ge=1024, le=8388608)
    max_pages: int = Field(default=5, ge=1, le=5)
    ocr_min_confidence: int = Field(default=55, ge=0, le=100)
    currency: Literal["EUR"] = "EUR"


class PaymentPolicy(StrictModel):
    max_amount_minor: int = Field(default=500000, ge=1, le=100000000)
    approval_ttl_seconds: int = Field(default=900, ge=1, le=3600)


class Rate(StrictModel):
    input_microusd_per_token: int = Field(default=0, ge=0, le=10000)
    output_microusd_per_token: int = Field(default=0, ge=0, le=10000)


class Policy(StrictModel):
    name: str = Field(max_length=100)
    profile: Literal["strict", "balanced", "observe"] = "strict"
    allowed_models: list[str] = Field(max_length=10)
    allowed_tools: list[str] = Field(max_length=10)
    allowed_hosts: list[str] = Field(max_length=10)
    controls: Controls
    budgets: Budgets
    document: DocumentPolicy
    payment: PaymentPolicy
    rates: dict[str, Rate]

    @model_validator(mode="after")
    def protected_execution(self):
        if self.profile != "observe" and (
            not self.controls.require_approval or not self.controls.evidence_consistency
        ):
            raise ValueError(
                "Payment-capable profiles require approval and evidence consistency. Use observe for disabled controls."
            )
        if any(x not in self.rates for x in self.allowed_models):
            raise ValueError(
                "Every allowed model needs an explicit rate entry, including zero-fee local models."
            )
        return self


def merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


class PolicyCatalog:
    def __init__(self, store: Store, path: Path, signatures: Path):
        self.store, self.path, self.signature_path = store, path, signatures
        self.last_good = Policy.model_validate(yaml.safe_load(path.read_text())).model_dump()
        self.last_error = None

    def get(self, workspace: str) -> tuple[Policy, str]:
        try:
            base = Policy.model_validate(yaml.safe_load(self.path.read_text())).model_dump()
            self.last_good, self.last_error = base, None
        except Exception as exc:
            base = self.last_good
            self.last_error = str(exc)[:500]
        row = self.store.one("SELECT policy FROM workspaces WHERE id=?", (workspace,))
        override = json.loads(row["policy"] or "{}") if row else {}
        policy = Policy.model_validate(merge(base, override))
        return policy, digest(policy.model_dump())[:20]

    def update(self, workspace: str, value: dict) -> str:
        policy = Policy.model_validate(value)
        self.store.execute(
            "UPDATE workspaces SET policy=? WHERE id=?", (canonical(policy.model_dump()), workspace)
        )
        version = digest(policy.model_dump())[:20]
        self.store.event(
            workspace,
            "policy.update",
            "allow",
            "configuration",
            {"version": version, "profile": policy.profile},
        )
        return version

    def feed(self, workspace: str | None = None) -> dict:
        row = self.store.one("SELECT feed FROM workspaces WHERE id=?", (workspace,)) if workspace else None
        data = json.loads(row["feed"]) if row and row["feed"] else json.loads(self.signature_path.read_text())
        return self.validate_feed(data)

    @staticmethod
    def validate_feed(data: dict) -> dict:
        if not isinstance(data, dict) or set(data) != {"version", "entries"}:
            raise ValueError("Feed requires only version and entries")
        if not isinstance(data.get("version"), str) or not isinstance(data.get("entries"), list):
            raise ValueError("Malformed signature catalog")
        if not 1 <= len(data["version"]) <= 80:
            raise ValueError("Invalid signature version")
        if len(data["entries"]) > 100:
            raise ValueError("Signature feed too large")
        for item in data["entries"]:
            if (
                not isinstance(item, dict)
                or not {"id", "kind", "field"} <= set(item)
                or set(item)
                - {
                    "id",
                    "kind",
                    "field",
                    "forbidden_prefixes",
                    "forbidden_values",
                    "reference",
                    "description",
                }
            ):
                raise ValueError(
                    "Entries use id, kind, field, literal forbidden lists and optional reference only"
                )
            if not all(
                isinstance(item.get(key), str) and 1 <= len(item[key]) <= 250
                for key in ("id", "kind", "field")
            ):
                raise ValueError("Malformed signature entry")
            for key in ("forbidden_prefixes", "forbidden_values"):
                if key in item and (
                    not isinstance(item[key], list)
                    or len(item[key]) > 30
                    or any(not isinstance(x, str) or len(x) > 500 for x in item[key])
                ):
                    raise ValueError(
                        "Signatures contain only literal data; executable expressions are forbidden"
                    )
        return data

    def update_feed(self, workspace: str, value: dict):
        data = self.validate_feed(value)
        self.store.execute("UPDATE workspaces SET feed=? WHERE id=?", (canonical(data), workspace))
        self.store.event(
            workspace,
            "signatures.update",
            "allow",
            "configuration",
            {"version": data["version"], "entries": len(data["entries"])},
        )
        return data
