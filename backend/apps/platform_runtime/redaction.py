import re
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEY_PARTS = frozenset(
    {
        "access",
        "api",
        "authorization",
        "credential",
        "key",
        "password",
        "private",
        "refresh",
        "secret",
        "signature",
        "token",
    }
)


def is_sensitive_key(key: str) -> bool:
    parts = {part for part in re.split(r"[^a-z0-9]+", key.lower()) if part}
    return bool(parts & SENSITIVE_KEY_PARTS)


def redact_value(value: Any) -> Any:
    """Return a JSON-safe copy with credential-like values removed."""
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]"
            if is_sensitive_key(str(key))
            else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value
