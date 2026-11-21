"""AI Models SSRF Validation and Secret Encryption Helpers (`Story 17.5`, `AD-21`)."""

from __future__ import annotations

from orcia_core.observability.logging import register_sensitive_secret_value
from orcia_core.orchestration.errors import ValidationDomainError
from orcia_core.orchestration.ssrf_guard import validate_safe_llm_endpoint_url
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.platform_settings import compute_salted_secret_fingerprint
from orcia_core.permissions.secret_hint import (
    SecretInputSpec,
    SecretStatusView,
    compute_secret_masked_hint,
)


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
