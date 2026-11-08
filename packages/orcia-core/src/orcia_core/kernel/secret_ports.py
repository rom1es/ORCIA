"""Hexagonal Secret Reference & KMS/Vault Envelope Encryption Port (`DEC-SEC-01`, `SEC-03`).

Guarantees that secret references (`SecretRef`) never serialize raw secret values into
DBOS workflow steps, `audit_ledger`, `domain_events_outbox`, `step_executions`, or logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class SecretRef:
    """Non-serializable secret pointer (`secret://<scope>/<key>`, `DEC-SEC-01`, `NFR-SEC-4`).

    Never carries a plaintext secret value. Valid to include in configurations or step
    inputs because `__repr__`, `__str__`, and `to_dict()` only expose the opaque URI.
    """

    uri: str
    workspace_id: str | None = None
    version: str = "v1"

    def __post_init__(self) -> None:
        cleaned = self.uri.strip()
        if not cleaned.startswith("secret://"):
            raise ValueError(f"SecretRef.uri must start with 'secret://', got: {cleaned!r}")
        object.__setattr__(self, "uri", cleaned)

    def __repr__(self) -> str:
        return f"SecretRef(uri={self.uri!r}, version={self.version!r})"

    def __str__(self) -> str:
        return f"[SECRET_REF:{self.uri}@{self.version}]"

    def to_dict(self) -> dict[str, Any]:
        """Return scrubbed dictionary representation containing zero secret material."""
        return {
            "secret_ref_uri": self.uri,
            "workspace_id": self.workspace_id,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceEnvelopeKeyRecord:
    """Workspace Data Encryption Key (DEK) wrapped by a Vault/KMS Key Encryption Key (`SEC-03`)."""

    workspace_id: str
    kek_key_id: str
    dek_version: str
    wrapped_dek_b64: str
    created_at_iso: str


@dataclass(frozen=True, slots=True)
class SecretRotationAuditEntry:
    """Immutable audit record emitted whenever a secret or Workspace DEK is rotated (`SEC-03`)."""

    id: str
    workspace_id: str
    secret_uri: str
    previous_version: str
    new_version: str
    rotated_by_actor_id: str
    rotated_at_iso: str
    kek_key_id: str


@runtime_checkable
class SecretProviderPort(Protocol):
    """Port for resolving `SecretRef` pointers and managing DEK/KEK envelope keys (`DEC-SEC-01`)."""

    def resolve_secret(self, ref: SecretRef) -> str:
        """Resolve `ref` to its plaintext secret value in memory at the point of outbound call."""
        ...

    def store_secret(
        self, ref: SecretRef, plaintext_value: str, *, actor_id: str = "system"
    ) -> SecretRef:
        """Store or rotate a secret under `ref`, wrapping with the Workspace DEK if scoped."""
        ...

    def rotate_workspace_dek(
        self, workspace_id: str, *, actor_id: str
    ) -> WorkspaceEnvelopeKeyRecord:
        """Rotate Data Encryption Key (DEK) for `workspace_id` and record an audit entry."""
        ...


__all__ = [
    "SecretProviderPort",
    "SecretRef",
    "SecretRotationAuditEntry",
    "WorkspaceEnvelopeKeyRecord",
]
