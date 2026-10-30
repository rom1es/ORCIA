"""Envelope DEK/KEK Secret Manager (`SecretProviderPort`) & Canary Leak Verifier (`DEC-SEC-01`).

Implements:
- `EnvelopeVaultSecretProvider` (`SecretProviderPort`):
  - Per-Workspace Data Encryption Key (DEK) wrapped by a Vault/KMS Key Encryption Key (KEK)
    using authenticated AES-256-GCM (`PassthroughVaultCipher`).
  - Resolution of opaque `SecretRef` (`secret://<scope>/<key>`) at outbound call time without
    ever serializing raw secret values into step inputs/outputs (`NFR-SEC-4`).
  - Automatic registration of resolved secret values in `orcia_core.observability.logging`
    so `structlog` and connector scrubbers redact them (`DEC-SEC-01`).
  - Immutable audit log of DEK and secret rotations (`SecretRotationAuditEntry`, `SEC-03`).
- `verify_canary_secret_absence`:
  - Verifies that a canary secret (`CANARY_SECRET_*` or custom token) never appears in
    `dbos.*`, `audit_ledger`, `domain_events_outbox`, `step_executions`, or `structlog` output.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from orcia_core.observability.logging import register_sensitive_secret_value
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_kernel.errors import ResourceNotFoundError
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.secret_ports import (
    SecretProviderPort,
    SecretRef,
    SecretRotationAuditEntry,
    WorkspaceEnvelopeKeyRecord,
)


@dataclass(frozen=True, slots=True)
class CanaryLeakAuditReport:
    """Result of `DEC-SEC-01` canary secret leak verification across all persistence & log sinks."""

    canary_fingerprint_sha256: str
    leaked_in_dbos: bool
    leaked_in_audit_ledger: bool
    leaked_in_domain_events_outbox: bool
    leaked_in_step_executions: bool
    leaked_in_structlog: bool

    @property
    def passed(self) -> bool:
        """Return True iff the canary secret was not found in any sink (`0` leaks)."""
        return not (
            self.leaked_in_dbos
            or self.leaked_in_audit_ledger
            or self.leaked_in_domain_events_outbox
            or self.leaked_in_step_executions
            or self.leaked_in_structlog
        )


class EnvelopeVaultSecretProvider(SecretProviderPort):
    """KMS/Vault Envelope Encryption Secret Provider (`DEC-SEC-01`, `SEC-03`, `AD-6`)."""

    def __init__(
        self,
        *,
        kek_key_id: str = "vault://kms/kek/orcia-root-v1",
        kek_cipher: PassthroughVaultCipher | None = None,
        initial_secrets: dict[str, str] | None = None,
    ) -> None:
        self.kek_key_id = kek_key_id
        self._kek_cipher = kek_cipher or PassthroughVaultCipher(master_key=os.urandom(32))
        self._workspace_deks: dict[
            str, tuple[WorkspaceEnvelopeKeyRecord, PassthroughVaultCipher]
        ] = {}
        self._encrypted_secrets: dict[str, tuple[str, str, str, str | None]] = {}
        self._rotation_audit_log: list[SecretRotationAuditEntry] = []

        if initial_secrets:
            for uri, val in initial_secrets.items():
                self.store_secret(SecretRef(uri=uri), val, actor_id="bootstrap")

    def list_rotation_audit_entries(self) -> tuple[SecretRotationAuditEntry, ...]:
        """Return immutable history of all secret and Workspace DEK rotations (`SEC-03`)."""
        return tuple(self._rotation_audit_log)

    def get_or_create_workspace_dek(
        self, workspace_id: str, *, actor_id: str = "system"
    ) -> WorkspaceEnvelopeKeyRecord:
        """Return active Workspace DEK record or generate and wrap a new 256-bit DEK with KEK."""
        existing = self._workspace_deks.get(workspace_id)
        if existing is not None:
            return existing[0]
        return self.rotate_workspace_dek(workspace_id, actor_id=actor_id)

    def rotate_workspace_dek(
        self, workspace_id: str, *, actor_id: str
    ) -> WorkspaceEnvelopeKeyRecord:
        """Generate a new 256-bit DEK for `workspace_id`, wrap with KEK, and re-wrap secrets."""
        prev = self._workspace_deks.get(workspace_id)
        prev_version = prev[0].dek_version if prev is not None else "none"
        next_num = int(prev_version.lstrip("v")) + 1 if prev_version.startswith("v") else 1
        new_version = f"v{next_num}"

        raw_dek = os.urandom(32)
        dek_b64 = base64.urlsafe_b64encode(raw_dek).decode("ascii")
        ct_b64, nonce_b64 = self._kek_cipher.encrypt(
            workspace_id,
            dek_b64,
            connector_scheme="kms_dek",
            target_host=new_version,
        )
        wrapped_b64 = f"{nonce_b64}:{ct_b64}"
        now_iso = datetime.now(UTC).isoformat()

        record = WorkspaceEnvelopeKeyRecord(
            workspace_id=workspace_id,
            kek_key_id=self.kek_key_id,
            dek_version=new_version,
            wrapped_dek_b64=wrapped_b64,
            created_at_iso=now_iso,
        )
        new_dek_cipher = PassthroughVaultCipher(master_key=raw_dek)

        # Re-encrypt any secrets scoped to this workspace under the new DEK
        if prev is not None:
            old_dek_cipher = prev[1]
            for uri, (ver, old_ct, old_nonce, ws_id) in list(self._encrypted_secrets.items()):
                if ws_id == workspace_id:
                    plaintext = old_dek_cipher.decrypt(
                        ws_id,
                        old_ct,
                        old_nonce,
                        connector_scheme="vault",
                        target_host=uri,
                    )
                    new_ct, new_nonce = new_dek_cipher.encrypt(
                        ws_id,
                        plaintext,
                        connector_scheme="vault",
                        target_host=uri,
                    )
                    self._encrypted_secrets[uri] = (ver, new_ct, new_nonce, ws_id)

        self._workspace_deks[workspace_id] = (record, new_dek_cipher)
        self._rotation_audit_log.append(
            SecretRotationAuditEntry(
                id=new_uuid7_str(),
                workspace_id=workspace_id,
                secret_uri=f"secret://workspace/{workspace_id}/dek",
                previous_version=prev_version,
                new_version=new_version,
                rotated_by_actor_id=actor_id,
                rotated_at_iso=now_iso,
                kek_key_id=self.kek_key_id,
            )
        )
        return record

    def store_secret(
        self, ref: SecretRef, plaintext_value: str, *, actor_id: str = "system"
    ) -> SecretRef:
        """Encrypt `plaintext_value` using Workspace DEK (or KEK) and register for redaction."""
        register_sensitive_secret_value(plaintext_value)
        ws_id = ref.workspace_id
        prev_entry = self._encrypted_secrets.get(ref.uri)
        prev_ver = prev_entry[0] if prev_entry is not None else "none"
        new_ver = (
            f"v{int(prev_ver.lstrip('v')) + 1}"
            if prev_entry is not None and prev_ver.startswith("v")
            else ref.version
        )

        if ws_id is not None:
            self.get_or_create_workspace_dek(ws_id, actor_id=actor_id)
            _, cipher = self._workspace_deks[ws_id]
            scope_key = ws_id
        else:
            cipher = self._kek_cipher
            scope_key = "GLOBAL"

        ct_b64, nonce_b64 = cipher.encrypt(
            scope_key,
            plaintext_value,
            connector_scheme="vault",
            target_host=ref.uri,
        )
        self._encrypted_secrets[ref.uri] = (new_ver, ct_b64, nonce_b64, ws_id)

        if prev_entry is not None:
            self._rotation_audit_log.append(
                SecretRotationAuditEntry(
                    id=new_uuid7_str(),
                    workspace_id=ws_id or "GLOBAL",
                    secret_uri=ref.uri,
                    previous_version=prev_ver,
                    new_version=new_ver,
                    rotated_by_actor_id=actor_id,
                    rotated_at_iso=datetime.now(UTC).isoformat(),
                    kek_key_id=self.kek_key_id,
                )
            )
        return SecretRef(uri=ref.uri, workspace_id=ws_id, version=new_ver)

    def resolve_secret(self, ref: SecretRef) -> str:
        """Decrypt and return the secret value for `ref`, registering it in the log scrubber."""
        entry = self._encrypted_secrets.get(ref.uri)
        if entry is None:
            raise ResourceNotFoundError(
                detail_override=f"Secret '{ref.uri}' introuvable dans SecretProviderPort."
            )
        _ver, ct_b64, nonce_b64, ws_id = entry
        if ws_id is not None and ws_id in self._workspace_deks:
            _, cipher = self._workspace_deks[ws_id]
            scope_key = ws_id
        else:
            cipher = self._kek_cipher
            scope_key = "GLOBAL"
        plaintext = cipher.decrypt(
            scope_key,
            ct_b64,
            nonce_b64,
            connector_scheme="vault",
            target_host=ref.uri,
        )
        register_sensitive_secret_value(plaintext)
        return plaintext


def _contains_secret(sink_items: tuple[Any, ...] | list[Any], canary_secret: str) -> bool:
    for item in sink_items:
        serialized = item if isinstance(item, str) else json.dumps(item, default=str)
        if canary_secret in serialized:
            return True
    return False


def verify_canary_secret_absence(
    canary_secret: str,
    *,
    dbos_payloads: tuple[Any, ...] | list[Any] = (),
    audit_entries: tuple[Any, ...] | list[Any] = (),
    outbox_events: tuple[Any, ...] | list[Any] = (),
    step_executions: tuple[Any, ...] | list[Any] = (),
    log_lines: tuple[str, ...] | list[str] = (),
) -> CanaryLeakAuditReport:
    """Verify `canary_secret` never leaked into DBOS, Audit, Outbox, Steps, or Structlog."""
    fp = f"sha256:{hashlib.sha256(canary_secret.encode('utf-8')).hexdigest()}"
    return CanaryLeakAuditReport(
        canary_fingerprint_sha256=fp,
        leaked_in_dbos=_contains_secret(dbos_payloads, canary_secret),
        leaked_in_audit_ledger=_contains_secret(audit_entries, canary_secret),
        leaked_in_domain_events_outbox=_contains_secret(outbox_events, canary_secret),
        leaked_in_step_executions=_contains_secret(step_executions, canary_secret),
        leaked_in_structlog=_contains_secret(log_lines, canary_secret),
    )


__all__ = [
    "CanaryLeakAuditReport",
    "EnvelopeVaultSecretProvider",
    "verify_canary_secret_absence",
]
