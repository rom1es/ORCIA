"""Masked secret hint extraction, secret specs and settings helpers (`AD-21.3`, `Story 17.5`).

Preserves zero-leak invariant:
- Secrets < 12 characters receive NO hint (`None`).
- Secrets 12..15 characters receive `••••••••<last-3-chars>`.
- Secrets >= 16 characters receive `••••••••<last-4-chars>`.
- Pure placeholder strings (dots/stars) receive `None`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError
from orcia_kernel.secret_ports import SecretProviderPort, SecretRef

SecretAction = Literal["keep", "set", "clear"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def compute_secret_masked_hint(plaintext: str) -> str | None:
    """Compute safe masked hint (`••••••••<last3-4>`) or `None` if too short (`AD-21.3`)."""
    trimmed = (plaintext or "").strip()
    if not trimmed:
        return None
    if set(trimmed) <= {"•", "*"}:
        return None
    if len(trimmed) >= 16:
        return f"••••••••{trimmed[-4:]}"
    if len(trimmed) >= 12:
        return f"••••••••{trimmed[-3:]}"
    return None


def compute_value_sha256(value_jsonb: dict[str, Any], secret_fingerprint: str | None) -> str:
    """Compute canonical sha256 checksum over setting values and secret fingerprint."""
    canonical = json.dumps(
        {"value": value_jsonb, "secret_fp": secret_fingerprint or ""},
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def compute_etag(setting_id: str, version: int, value_sha256: str) -> str:
    """Compute ETag header value for optimistic concurrency control (`Story 8.3`)."""
    raw = f"{setting_id}:v{version}:{value_sha256}".encode()
    return f'W/"{version}-{hashlib.sha256(raw).hexdigest()[:12]}"'


@dataclass(frozen=True, slots=True)
class SecretInputSpec:
    """Write-only secret mutation command (`keep | set | clear`, `Story 8.3`, `AD-21`)."""

    action: SecretAction = "keep"  # pragma: allowlist secret
    plaintext_value: str | None = None

    def __post_init__(self) -> None:
        if self.action == "set":
            val = (self.plaintext_value or "").strip()
            if not val:
                raise ValidationDomainError(
                    detail_override="SecretInput with action='set' requires a non-empty value."
                )
            if set(val) <= {"•", "*"}:
                raise ValidationDomainError(
                    detail_override="Masked placeholder strings cannot be saved as secrets."
                )

    def __repr__(self) -> str:
        return f"SecretInputSpec(action={self.action!r}, value='[REDACTED]')"


@dataclass(frozen=True, slots=True)
class SecretStatusView:
    """Read-only secret metadata returned by the API (`Story 8.3`, `AD-21.3`)."""

    configured: bool
    fingerprint: str | None = None
    masked_hint: str | None = None
    updated_at: str = field(default_factory=_now_iso)
    updated_by: str = "system"


@dataclass(frozen=True, slots=True)
class OutboxReplayOutcome:
    """Result of an Outbox event replay operation (`Story 8.3`)."""

    consumer_name: str
    dry_run: bool
    scanned_count: int
    replayed_count: int
    event_ids: tuple[str, ...]


class DefaultMemorySecretProvider(SecretProviderPort):
    """In-memory fallback secret provider for unit testing without Vault/PostgreSQL."""

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def resolve_secret(self, ref: SecretRef) -> str:
        if ref.uri not in self._secrets:
            raise ResourceNotFoundError(detail_override=f"SecretRef not found: {ref.uri}")
        return self._secrets[ref.uri]

    def store_secret(
        self, ref: SecretRef, plaintext_value: str, *, actor_id: str = "system"
    ) -> SecretRef:
        _ = actor_id
        self._secrets[ref.uri] = plaintext_value
        return ref

    def delete_secret(self, ref: SecretRef) -> None:
        self._secrets.pop(ref.uri, None)

    def rotate_workspace_dek(self, workspace_id: str, *, actor_id: str) -> Any:
        _ = (workspace_id, actor_id)
        return None


__all__ = [
    "DefaultMemorySecretProvider",
    "OutboxReplayOutcome",
    "SecretAction",
    "SecretInputSpec",
    "SecretStatusView",
    "compute_etag",
    "compute_secret_masked_hint",
    "compute_value_sha256",
]
