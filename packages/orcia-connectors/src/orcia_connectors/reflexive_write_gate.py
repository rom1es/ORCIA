"""Governed `WritePreviewCard` & `SignedApprovalToken` Gate Adapter (`Story 16.2`, `CAP-160`).

Implements `ReflexiveWriteGatePort` in `packages/orcia-connectors` so `orcia_core` stays 100%
isolated from concrete connectors (`AD-20`). Enforces cryptographic `SignedApprovalToken`
verification (`HMAC-SHA256` + `payload_sha256`) before any external mutation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from orcia_connectors.protocol import (
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_core.kernel.errors import PolicyDeniedError
from orcia_core.ports.reflexive_runtime_ports import (
    PendingWritePreviewSpec,
    ReflexiveWriteApprovalInput,
    ReflexiveWriteGatePort,
)


class ConnectorReflexiveWriteGateAdapter(ReflexiveWriteGatePort):
    """Bridges `ReflexiveWriteGatePort` to `OrciaConnectorProtocol` + `SignedApprovalToken`."""

    def __init__(
        self,
        *,
        connectors: Mapping[str, OrciaConnectorProtocol] | None = None,
    ) -> None:
        self._connectors: dict[str, OrciaConnectorProtocol] = dict(connectors or {})
        self._audit_executed_writes: list[dict[str, Any]] = []

    @property
    def executed_writes(self) -> tuple[dict[str, Any], ...]:
        """Return immutable audit log of cryptographically approved writes."""
        return tuple(self._audit_executed_writes)

    async def prepare_write_preview(
        self,
        *,
        connector_type: str,
        action: str,
        target_resource_uri: str,
        action_summary: str,
        payload: dict[str, Any],
    ) -> PendingWritePreviewSpec:
        """Prepare a `WritePreviewCard` without mutating any external system."""
        normalized_payload = dict(payload)
        normalized_payload.setdefault("target_uri", target_resource_uri)
        connector = self._connectors.get(connector_type)
        if connector is not None:
            card = await connector.preview_write(action, normalized_payload)
            return PendingWritePreviewSpec(
                preview_id=card.preview_id,
                connector_type=card.connector_type,
                action=action,
                target_resource_uri=card.target_resource_uri or target_resource_uri,
                action_summary=action_summary or card.action_summary,
                diff_or_payload_preview=dict(card.diff_or_payload_preview),
                payload=normalized_payload,
                payload_sha256=compute_payload_sha256(action, normalized_payload),
            )

        sha = compute_payload_sha256(action, normalized_payload)
        card = WritePreviewCard(
            connector_type=connector_type,
            target_resource_uri=target_resource_uri,
            action_summary=action_summary,
            diff_or_payload_preview={
                "action": action,
                "target_resource_uri": target_resource_uri,
                "payload": normalized_payload,
            },
            payload_sha256=sha,
        )
        return PendingWritePreviewSpec(
            preview_id=card.preview_id,
            connector_type=card.connector_type,
            action=action,
            target_resource_uri=card.target_resource_uri,
            action_summary=card.action_summary,
            diff_or_payload_preview=card.diff_or_payload_preview,
            payload=normalized_payload,
            payload_sha256=card.payload_sha256,
        )

    async def execute_approved_write(
        self,
        *,
        preview: PendingWritePreviewSpec,
        approval: ReflexiveWriteApprovalInput,
    ) -> dict[str, Any]:
        """Verify `SignedApprovalToken` HMAC-SHA256 + `payload_sha256` and execute write."""
        if approval.preview_id != preview.preview_id:
            raise PolicyDeniedError(
                detail_override=(
                    "ERR_WRITE_PREVIEW_ID_MISMATCH: Approval token preview_id does not match "
                    "the pending WritePreviewCard."
                )
            )
        token = SignedApprovalToken(
            preview_id=approval.preview_id,
            approver_user_id=approval.approver_user_id,
            approved_at_utc=approval.approved_at_utc,
            payload_sha256=approval.payload_sha256,
            broker_signature=approval.broker_signature,
        )
        verify_signed_approval_token(token, action=preview.action, payload=preview.payload)

        connector = self._connectors.get(preview.connector_type)
        if connector is not None:
            result = await connector.execute_write(token, preview.action, preview.payload)
        else:
            result = {
                "status": "APPLIED",
                "connector_type": preview.connector_type,
                "target_resource_uri": preview.target_resource_uri,
                "action": preview.action,
                "approver_user_id": token.approver_user_id,
                "preview_id": token.preview_id,
            }

        self._audit_executed_writes.append(dict(result))
        return result


def issue_broker_write_approval(
    *,
    preview: PendingWritePreviewSpec,
    approver_user_id: str,
) -> ReflexiveWriteApprovalInput:
    """Issue a Permission Broker `SignedApprovalToken` after authenticated human validation."""
    card = WritePreviewCard(
        preview_id=preview.preview_id,
        connector_type=preview.connector_type,
        target_resource_uri=preview.target_resource_uri,
        action_summary=preview.action_summary,
        diff_or_payload_preview=preview.diff_or_payload_preview,
        payload_sha256=preview.payload_sha256,
    )
    signed = SignedApprovalToken.issue(preview_card=card, approver_user_id=approver_user_id)
    return ReflexiveWriteApprovalInput(
        preview_id=signed.preview_id,
        approver_user_id=signed.approver_user_id,
        approved_at_utc=signed.approved_at_utc,
        payload_sha256=signed.payload_sha256,
        broker_signature=signed.broker_signature,
    )


__all__ = [
    "ConnectorReflexiveWriteGateAdapter",
    "issue_broker_write_approval",
]
