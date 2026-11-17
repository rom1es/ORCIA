"""Shared constant-time HMAC-SHA256 webhook verification (`Story 18.2` + `Story 7.2`).

Extracted to `orcia_core.permissions` (Layer 4 `lint-imports`) so both
`datasource_webhooks.py` and `workflow_triggers.py` reuse the exact same
timing-safe signature verification primitive with zero duplication.
"""

from __future__ import annotations

import hashlib
import hmac


def compute_webhook_hmac_sha256(raw_body: bytes, secret: str) -> str:
    """Compute canonical `sha256=<hex>` HMAC signature over `raw_body`."""
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_webhook_hmac_sha256(
    raw_body: bytes,
    secret: str,
    signature_header: str | None,
) -> bool:
    """Verify `X-Orcia-Webhook-Signature` or `X-Hub-Signature-256` in constant time."""
    if not secret or not signature_header:
        return False
    clean = signature_header.strip()
    if not clean:
        return False
    if clean.lower().startswith("sha256="):
        clean = clean[7:].strip()
    if len(clean) != 64:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.lower(), clean.lower())


__all__ = [
    "compute_webhook_hmac_sha256",
    "verify_webhook_hmac_sha256",
]
