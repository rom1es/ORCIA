"""MCP Client Bridge Connector (`mcp:client-bridge`) implementing `OrciaConnectorProtocol`."""

from __future__ import annotations

from typing import Any

from orcia_connectors.protocol import (
    ConnectorHealthStatus,
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_core.kernel.errors import ValidationDomainError
from orcia_core.kernel.ids import new_uuid7_str


class McpClientBridgeConnector(OrciaConnectorProtocol):
    """Generic MCP client bridge routing tool calls through the Permission Broker."""

    def __init__(self, *, connector_type: str = "mcp:client-bridge") -> None:
        self.connector_type = connector_type

    async def healthcheck(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(
            connector_type=self.connector_type,
            ok=True,
            latency_ms=5,
            error_message=None,
        )

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        cleaned = resource_uri.strip()
        if not cleaned:
            raise ValidationDomainError(detail_override="resource_uri is required.")
        return {
            "connector_type": self.connector_type,
            "resource_uri": cleaned,
            "query": dict(query or {}),
            "tools": [
                {"name": "SearchTool", "mode": "read"},
                {"name": "ContentReadTool", "mode": "read"},
                {"name": "IssueSearchTool", "mode": "read"},
                {"name": "CreateWorkItem", "mode": "write_preview_required"},
            ],
        }

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        clean_action = action.strip()
        if not clean_action:
            raise ValidationDomainError(detail_override="action is required for preview_write.")
        sha = compute_payload_sha256(clean_action, payload)
        target_uri = str(payload.get("target_uri") or f"mcp://{self.connector_type}/{clean_action}")
        return WritePreviewCard(
            preview_id=new_uuid7_str(),
            connector_type=self.connector_type,
            target_resource_uri=target_uri,
            action_summary=f"[MCP {clean_action}] {target_uri}",
            diff_or_payload_preview=dict(payload),
            payload_sha256=sha,
        )

    async def execute_write(
        self,
        approval_token: SignedApprovalToken,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        clean_action = action.strip()
        verify_signed_approval_token(approval_token, action=clean_action, payload=payload)
        return {
            "connector_type": self.connector_type,
            "action": clean_action,
            "approved_by": approval_token.approver_user_id,
            "preview_id": approval_token.preview_id,
            "payload_sha256": approval_token.payload_sha256,
            "status": "COMMITTED",
            "result": dict(payload),
        }
