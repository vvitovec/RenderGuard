import re
from typing import Any

from .documents import find_ibans

SECRET = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0-9]{16}|ghp_[A-Za-z0-9]{20,})\b")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
ACCOUNT = re.compile(r"\b(?:DE\d{20}|NL\d{2}[A-Z]{4}\d{10}|CZ\d{22}|AT\d{18}|PL\d{26})\b")
REDACTION_PATTERNS = frozenset({"secret", "api_key", "email", "bank_account", "account_handle"})


def redact_text(value: str, accounts: dict[str, str] | None = None) -> tuple[str, list[str]]:
    kinds = []
    if accounts:
        for account, handle in accounts.items():
            pattern = r"\b" + r"\s*".join(re.escape(c) for c in account) + r"\b"
            value, count = re.subn(pattern, handle, value, flags=re.I)
            if count:
                kinds.extend(["account_handle"] * count)
    for account in find_ibans(value):
        pattern = r"\b" + r"\s*".join(re.escape(c) for c in account) + r"\b"
        value, count = re.subn(pattern, "[REDACTED_ACCOUNT]", value, flags=re.IGNORECASE)
        if count:
            kinds.extend(["bank_account"] * count)
    for regex, replacement, label in [
        (SECRET, "[REDACTED_SECRET]", "secret"),
        (EMAIL, "[REDACTED_EMAIL]", "email"),
        (ACCOUNT, "[REDACTED_ACCOUNT]", "bank_account"),
    ]:
        value, count = regex.subn(replacement, value)
        if count:
            kinds.extend([label] * count)
    return value, kinds


def safe_log(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if re.sub(r"[^a-z0-9]", "", key.lower()) in (
                "token",
                "approvaltoken",
                "agenttoken",
                "authorization",
                "password",
                "secret",
                "apikey",
                "accesstoken",
                "refreshtoken",
                "signingkey",
            ):
                result[key] = "[REDACTED]"
            elif key.lower() == "iban" and isinstance(item, str):
                result[key] = "•••• " + item[-4:]
            else:
                result[key] = safe_log(item)
        return result
    if isinstance(value, list):
        return [safe_log(x) for x in value[:100]]
    if isinstance(value, str):
        return redact_text(value)[0][:3000]
    return value
