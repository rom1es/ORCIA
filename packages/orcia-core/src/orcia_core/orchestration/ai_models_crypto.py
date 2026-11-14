"""AI Models SSRF Validation and Secret Encryption Helpers (`Story 17.5`, `AD-21`)."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from orcia_core.observability.logging import register_sensitive_secret_value
from orcia_core.orchestration.ai_models_errors import UnsafeLlmEndpointUrlError
from orcia_core.orchestration.errors import ValidationDomainError
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.platform_settings import compute_salted_secret_fingerprint
from orcia_core.permissions.secret_hint import (
    SecretInputSpec,
    SecretStatusView,
    compute_secret_masked_hint,
)

_BLOCKED_HOSTS: frozenset[str] = frozenset(
    {"169.254.169.254", "metadata.google.internal", "100.100.100.200"}
)
_LINK_LOCAL_NETWORK = ipaddress.ip_network("169.254.0.0/16")


def validate_safe_llm_endpoint_url(url: str, *, instance: str | None = None) -> str:
    """Validate `url` against Cloud Metadata SSRF while permitting `.local`/`.internal`."""
    raw = (url or "").strip()
    if not raw:
        raise UnsafeLlmEndpointUrlError(
            detail_override="LLM endpoint URL cannot be empty.", instance=instance
        )
    try:
        parsed = urlparse(raw)
    except ValueError as exc:
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Malformed endpoint URL: {raw}", instance=instance
        ) from exc
    if parsed.scheme not in ("http", "https"):
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Invalid endpoint scheme '{parsed.scheme}'. Must be http or https.",
            instance=instance,
        )
    if parsed.username or parsed.password:
        raise UnsafeLlmEndpointUrlError(
            detail_override="Credentials embedded in endpoint authority are forbidden.",
            instance=instance,
        )
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host in _BLOCKED_HOSTS or host.endswith((".example.com", ".google.internal")):
        raise UnsafeLlmEndpointUrlError(
            detail_override=f"Target host '{host}' is prohibited by SSRF policy.",
            instance=instance,
        )
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_link_local or ip.is_unspecified or ip.is_multicast or ip in _LINK_LOCAL_NETWORK:
            raise UnsafeLlmEndpointUrlError(
                detail_override=f"Target IP '{ip}' is blocked by link-local SSRF policy.",
                instance=instance,
            )
    except ValueError:
        pass
    return raw


def pack_encrypted_api_key(
    cipher: PassthroughVaultCipher,
    *,
    mapping_id: str,
    plaintext_key: str,
    target_host: str = "default",
) -> str:
    """Encrypt `plaintext_key` with `AES-256-GCM` and return `ct_b64:nonce_b64`."""
    ct_b64, nonce_b64 = cipher.encrypt(
        mapping_id,
        plaintext_key,
        connector_scheme="llm",
        target_host=target_host.lower() or "default",
    )
    return f"{ct_b64}:{nonce_b64}"


def unpack_encrypted_api_key(
    cipher: PassthroughVaultCipher,
    *,
    mapping_id: str,
    packed: str,
    target_host: str = "default",
) -> str:
    """Decrypt `AES-256-GCM` packed key and register it for redaction (`DEC-SEC-01`)."""
    parts = packed.split(":", 1)
    if len(parts) != 2:
        raise ValidationDomainError(detail_override="Malformed encrypted api_key envelope.")
    plaintext = cipher.decrypt(
        mapping_id,
        parts[0],
        parts[1],
        connector_scheme="llm",
        target_host=target_host.lower() or "default",
    )
    register_sensitive_secret_value(plaintext)
    return plaintext


def apply_ai_model_secret_input(
    cipher: PassthroughVaultCipher,
    *,
    mapping_id: str,
    target_host: str,
    current_status: SecretStatusView,
    current_encrypted_key: str | None,
    secret_input: SecretInputSpec | None,
    now_iso: str,
    actor_id: str = "system",
) -> tuple[SecretStatusView, str | None]:
    """Apply write-only secret mutation (keep | set | clear) with AES-256-GCM encryption."""
    if secret_input is None or secret_input.action == "keep":
        return current_status, current_encrypted_key
    if secret_input.action == "clear":
        cleared_status = SecretStatusView(
            configured=False,
            fingerprint=None,
            masked_hint=None,
            updated_at=now_iso,
            updated_by=actor_id,
        )
        return cleared_status, None
    raw_key = secret_input.plaintext_value or ""
    encrypted_key = pack_encrypted_api_key(
        cipher, mapping_id=mapping_id, plaintext_key=raw_key, target_host=target_host
    )
    fp = compute_salted_secret_fingerprint(mapping_id, raw_key)
    hint = compute_secret_masked_hint(raw_key)
    new_status = SecretStatusView(
        configured=True,
        fingerprint=fp,
        masked_hint=hint,
        updated_at=now_iso,
        updated_by=actor_id,
    )
    return new_status, encrypted_key


__all__ = [
    "apply_ai_model_secret_input",
    "pack_encrypted_api_key",
    "unpack_encrypted_api_key",
    "validate_safe_llm_endpoint_url",
]
