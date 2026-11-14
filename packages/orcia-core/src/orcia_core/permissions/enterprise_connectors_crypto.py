"""Story 17.4 & 18.1 — Enterprise Connectors Cryptography & URL Safety Helpers.

Zero SQL / FastAPI / external library imports:
- Anti-SSRF URL validation (`validate_safe_connector_base_url`)
- URL hostname extraction (`extract_url_host`)
- Salted Write-Only fingerprint generation (`compute_secret_fingerprint`)
- AES-256-GCM packing and unpacking (`pack_encrypted_secret`, `unpack_encrypted_secret`)
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
from urllib.parse import urlparse

from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.errors import (
    UnsafeConnectorEndpointUrlError,
    ValidationDomainError,
)

_BLOCKED_METADATA_HOSTS: frozenset[str] = frozenset(
    {
        "169.254.169.254",
        "metadata.google.internal",
        "metadata",
        "100.100.100.200",
        "instance-data",
    }
)


def validate_safe_connector_base_url(base_url: str, *, instance: str | None = None) -> str:
    """Validate `base_url` against SSRF while allowing `.local` and `.internal`."""
    raw = (base_url or "").strip()
    if not raw:
        raise UnsafeConnectorEndpointUrlError(instance=instance)
    try:
        parsed = urlparse(raw)
    except ValueError as exc:
        raise UnsafeConnectorEndpointUrlError(instance=instance) from exc
    if parsed.scheme not in ("http", "https"):
        raise UnsafeConnectorEndpointUrlError(instance=instance)
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host in _BLOCKED_METADATA_HOSTS or host.endswith(".google.internal"):
        raise UnsafeConnectorEndpointUrlError(instance=instance)
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_link_local or ip.is_unspecified or ip.is_multicast:
            raise UnsafeConnectorEndpointUrlError(instance=instance)
    except ValueError:
        pass
    return raw.rstrip("/")


def extract_url_host(url: str) -> str:
    """Extract lowercase hostname from `url` for `AES-256-GCM` AAD binding."""
    parsed = urlparse((url or "").strip())
    return (parsed.hostname or "default").strip().lower() or "default"


def compute_secret_fingerprint(entity_id: str, plaintext_secret: str) -> str:
    """Compute a deterministic salted Write-Only fingerprint (`sha256:<8-hex>`, `AD-21`)."""
    digest = hmac.new(
        f"orcia:secret-fp:{entity_id}".encode(),
        plaintext_secret.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"sha256:{digest[:8]}"


def pack_encrypted_secret(
    cipher: PassthroughVaultCipher,
    *,
    owner_id: str,
    plaintext: str,
    scheme: str,
    host: str,
) -> str:
    """Encrypt `plaintext` with `AES-256-GCM` and pack as `ciphertext_b64:nonce_b64`."""
    ct_b64, nonce_b64 = cipher.encrypt(
        owner_id,
        plaintext,
        connector_scheme=scheme.lower(),
        target_host=host.lower(),
    )
    return f"{ct_b64}:{nonce_b64}"


def unpack_encrypted_secret(
    cipher: PassthroughVaultCipher,
    *,
    owner_id: str,
    packed: str,
    scheme: str,
    host: str,
) -> str:
    """Verify `AES-256-GCM` tag and return plaintext for internal connector execution only."""
    parts = packed.split(":", 1)
    if len(parts) != 2:
        raise ValidationDomainError(detail_override="Malformed encrypted secret envelope.")
    return cipher.decrypt(
        owner_id,
        parts[0],
        parts[1],
        connector_scheme=scheme.lower(),
        target_host=host.lower(),
    )
