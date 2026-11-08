"""Atlassian Jira Connector (`mcp:atlassian-jira`) implementing `OrciaConnectorProtocol`."""

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
from orcia_core.kernel.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.kernel.ids import new_uuid7_str


class AtlassianJiraConnector(OrciaConnectorProtocol):
    """Governed Jira connector enforcing Write-Preview Gate and Permission Broker approval."""

    connector_type: str = "mcp:atlassian-jira"

    def __init__(self, *, base_url: str = "https://jira.enterprise.internal") -> None:
        self._base_url = base_url
        self._executed_writes: list[dict[str, Any]] = []
        self._issues: dict[str, dict[str, Any]] = {
            "MCIA-101": {
                "key": "MCIA-101",
                "project": "MCIA",
                "type": "Feature",
                "summary": "Mon Compte — Refonte parcours authentification & PRD Light",
                "status": "EN_REVUE",
            },
            "PAYBUILD-101": {
                "key": "PAYBUILD-101",
                "project": "PAYBUILD",
                "type": "Story",
                "summary": "Implémenter le connecteur checkout idempotent",
                "status": "IN_PROGRESS",
            },
        }

    async def healthcheck(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(
            connector_type=self.connector_type,
            ok=True,
            latency_ms=8,
            error_message=None,
        )

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        cleaned = resource_uri.strip()
        if not cleaned:
            raise ValidationDomainError(detail_override="resource_uri is required.")
        if "404" in cleaned or "not-found" in cleaned:
            raise ResourceNotFoundError(detail_override=f"Jira resource not found: {cleaned}")
        jql = (query or {}).get("jql")
        if jql:
            return {
                "connector_type": self.connector_type,
                "resource_uri": cleaned,
                "jql": str(jql),
                "issues": list(self._issues.values()),
            }
        key = cleaned.rsplit("/", 1)[-1].split("@", 1)[0].upper()
        issue = self._issues.get(
            key,
            {
                "key": key or "MCIA-101",
                "project": (key.split("-")[0] if "-" in key else "MCIA"),
                "type": "Feature",
                "summary": f"Ticket {key}",
                "status": "OPEN",
            },
        )
        return {
            "connector_type": self.connector_type,
            "resource_uri": cleaned,
            "issue": issue,
        }

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        clean_action = action.strip()
        if not clean_action:
            raise ValidationDomainError(detail_override="action is required for preview_write.")
        sha = compute_payload_sha256(clean_action, payload)
        project = str(payload.get("project_key") or payload.get("project") or "MCIA")
        issue_key = str(payload.get("issue_key") or f"{project}-PREVIEW")
        summary = str(payload.get("summary") or payload.get("title") or clean_action)
        return WritePreviewCard(
            preview_id=new_uuid7_str(),
            connector_type=self.connector_type,
            target_resource_uri=f"jira://{project}/{issue_key}",
            action_summary=f"[Jira {clean_action}] {summary}",
            diff_or_payload_preview={
                "action": clean_action,
                "project_key": project,
                "issue_key": issue_key,
                "fields": dict(payload),
            },
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
        project = str(payload.get("project_key") or payload.get("project") or "MCIA")
        created_key = str(payload.get("issue_key") or f"{project}-{100 + len(self._issues) + 1}")
        record = {
            "connector_type": self.connector_type,
            "action": clean_action,
            "issue_key": created_key,
            "project_key": project,
            "approved_by": approval_token.approver_user_id,
            "preview_id": approval_token.preview_id,
            "payload_sha256": approval_token.payload_sha256,
            "status": "COMMITTED",
        }
        self._issues[created_key] = {
            "key": created_key,
            "project": project,
            "type": str(payload.get("issue_type") or "Feature"),
            "summary": str(payload.get("summary") or clean_action),
            "status": "CREATED",
        }
        self._executed_writes.append(record)
        return record
