"""Credential Sanitizer for Platform Setup Snapshots (`Story 26.1`, `H-17`)."""

from __future__ import annotations

from typing import Any

_CREDENTIAL_KEY_TOKENS: frozenset[str] = frozenset(
    {
        "apikey",
        "secret",
        "secretkey",
        "plaintextvalue",
        "password",
        "passwd",
        "token",
        "authtoken",
        "bearertoken",
        "clientsecret",
        "encryptedapikey",
    }
)


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested in value.items():
            norm = str(key).strip().lower().replace("_", "").replace("-", "")
            if norm in _CREDENTIAL_KEY_TOKENS:
                continue
            sanitized[key] = _sanitize_value(nested)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item) for item in value)
    return value


def strip_snapshot_credentials(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return deep-copied collection items with raw credential keys stripped recursively."""
    cleaned: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cleaned_item = _sanitize_value(item)
        if isinstance(cleaned_item, dict):
            cleaned.append(cleaned_item)
    return cleaned


__all__ = ["strip_snapshot_credentials"]
