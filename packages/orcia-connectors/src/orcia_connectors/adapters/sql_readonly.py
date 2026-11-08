"""SQL Read-Only Connector (`sql:readonly`) implementing `OrciaConnectorProtocol`."""

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
from orcia_core.kernel.errors import PolicyDeniedError, ValidationDomainError


class SqlReadonlyConnector(OrciaConnectorProtocol):
    """Read-only SQL connector blocking mutating statements and requiring Broker approval."""

    connector_type: str = "sql:readonly"

    async def healthcheck(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(
            connector_type=self.connector_type,
            ok=True,
            latency_ms=3,
            error_message=None,
        )

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        cleaned = resource_uri.strip()
        if not cleaned:
            raise ValidationDomainError(detail_override="resource_uri is required.")
        sql = str((query or {}).get("sql") or "SELECT 1").strip()
        forbidden = ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE ")
        if any(tok in sql.upper() for tok in forbidden):
            raise PolicyDeniedError(
                detail_override="ERR_SQL_READONLY_VIOLATION: Mutating SQL forbidden in read()."
            )
        return {
            "connector_type": self.connector_type,
            "resource_uri": cleaned,
            "sql": sql,
            "rows": [{"result": 1}],
        }

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        clean_action = action.strip() or "sql_write"
        sha = compute_payload_sha256(clean_action, payload)
        return WritePreviewCard(
            connector_type=self.connector_type,
            target_resource_uri="db://readonly/forbidden",
            action_summary=f"[SQL ReadOnly] {clean_action}",
            diff_or_payload_preview=dict(payload),
            payload_sha256=sha,
        )

    async def execute_write(
        self,
        approval_token: SignedApprovalToken,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        verify_signed_approval_token(approval_token, action=action.strip(), payload=payload)
        raise PolicyDeniedError(
            detail_override="ERR_SQL_READONLY_ENFORCED: sql_readonly connector forbids writes."
        )
