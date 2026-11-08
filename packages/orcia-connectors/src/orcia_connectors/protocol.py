"""Unified Enterprise Connectors Contract (`OrciaConnectorProtocol`) & Approval Tokens.

Every connector in `packages/orcia-connectors` implements the 4-method `OrciaConnectorProtocol`
(`healthcheck`, `read`, `preview_write`, `execute_write`) and enforces cryptographic signature
verification on `SignedApprovalToken` before any external mutation (`Write-Preview Gate`).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from orcia_core.kernel.errors import PolicyDeniedError, ValidationDomainError
from orcia_core.kernel.ids import new_uuid7_str

_BROKER_HMAC_KEY = b"orcia-permission-broker-v3-signing-key"


def compute_payload_sha256(action: str, payload: dict[str, Any]) -> str:
    """Compute canonical SHA-256 hex digest for `(action, payload)`."""
    canonical = json.dumps({"action": action.strip(), "payload": payload}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sign_approval_token_payload(
    *,
    preview_id: str,
    approver_user_id: str,
    approved_at_utc: str,
    payload_sha256: str,
) -> str:
    """Compute HMAC-SHA256 signature issued by the Permission Broker."""
    msg = f"{preview_id}|{approver_user_id}|{approved_at_utc}|{payload_sha256}".encode()
    return hmac.new(_BROKER_HMAC_KEY, msg, hashlib.sha256).hexdigest()


class ConnectorHealthStatus(BaseModel):
    """Health check status for an enterprise connector (`OrciaConnectorProtocol.healthcheck`)."""

    connector_type: str = Field(..., description="Ex: mcp:atlassian-jira, mcp:git-provider")
    ok: bool
    latency_ms: int = Field(default=1, ge=0)
    error_message: str | None = None


class WritePreviewCard(BaseModel):
    """Preview card returned before any external write (`Write-Preview Gate`, CA-9.5.1)."""

    preview_id: str = Field(default_factory=new_uuid7_str)
    connector_type: str
    target_resource_uri: str
    action_summary: str
    diff_or_payload_preview: dict[str, Any]
    payload_sha256: str = Field(..., min_length=64, max_length=64)


class SignedApprovalToken(BaseModel):
    """Token issued by the Permission Broker after human validation of a `WritePreviewCard`."""

    preview_id: str
    approver_user_id: str
    approved_at_utc: str
    payload_sha256: str = Field(..., min_length=64, max_length=64)
    broker_signature: str = Field(..., min_length=16)

    @classmethod
    def issue(
        cls,
        *,
        preview_card: WritePreviewCard,
        approver_user_id: str,
        approved_at_utc: str | None = None,
    ) -> SignedApprovalToken:
        """Issue a valid Permission Broker signed approval token for `preview_card`."""
        if not approver_user_id.strip():
            raise ValidationDomainError(detail_override="approver_user_id is required.")
        ts = approved_at_utc or datetime.now(UTC).isoformat()
        sig = sign_approval_token_payload(
            preview_id=preview_card.preview_id,
            approver_user_id=approver_user_id.strip(),
            approved_at_utc=ts,
            payload_sha256=preview_card.payload_sha256,
        )
        return cls(
            preview_id=preview_card.preview_id,
            approver_user_id=approver_user_id.strip(),
            approved_at_utc=ts,
            payload_sha256=preview_card.payload_sha256,
            broker_signature=sig,
        )


def verify_signed_approval_token(
    approval_token: SignedApprovalToken | None,
    *,
    action: str,
    payload: dict[str, Any],
) -> None:
    """Verify Permission Broker signature and payload SHA-256 before `execute_write`."""
    if approval_token is None or not isinstance(approval_token, SignedApprovalToken):
        raise PolicyDeniedError(
            detail_override=(
                "ERR_WRITE_PREVIEW_APPROVAL_REQUIRED: External write blocked because "
                "SignedApprovalToken is missing."
            )
        )
    expected_sha = compute_payload_sha256(action, payload)
    if not hmac.compare_digest(approval_token.payload_sha256, expected_sha):
        raise PolicyDeniedError(
            detail_override=(
                "ERR_WRITE_PREVIEW_SHA256_MISMATCH: SignedApprovalToken payload_sha256 does not "
                "match the requested write payload."
            )
        )
    expected_sig = sign_approval_token_payload(
        preview_id=approval_token.preview_id,
        approver_user_id=approval_token.approver_user_id,
        approved_at_utc=approval_token.approved_at_utc,
        payload_sha256=approval_token.payload_sha256,
    )
    if not hmac.compare_digest(approval_token.broker_signature, expected_sig):
        raise PolicyDeniedError(
            detail_override=(
                "ERR_WRITE_PREVIEW_INVALID_SIGNATURE: Invalid Permission Broker signature on "
                "SignedApprovalToken."
            )
        )


@runtime_checkable
class OrciaConnectorProtocol(Protocol):
    """Unified 4-method protocol for all ORCIA enterprise connectors."""

    connector_type: str

    async def healthcheck(self) -> ConnectorHealthStatus:
        """Verify network connectivity, mTLS certificates, and token validity."""
        ...

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read-only operation (issue, wiki page, Git file, JQL/CQL/SQL query)."""
        ...

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        """Simulate and prepare an external write without mutating the external system."""
        ...

    async def execute_write(
        self,
        approval_token: SignedApprovalToken,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute external write ONLY if Permission Broker signature matches SHA-256."""
        ...


__all__ = [
    "ConnectorHealthStatus",
    "OrciaConnectorProtocol",
    "SignedApprovalToken",
    "WritePreviewCard",
    "compute_payload_sha256",
    "sign_approval_token_payload",
    "verify_signed_approval_token",
]
