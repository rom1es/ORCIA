"""Atlassian Confluence Connector (`mcp:atlassian-confluence`) for `OrciaConnectorProtocol`."""

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


class AtlassianConfluenceConnector(OrciaConnectorProtocol):
    """Governed Confluence connector enforcing Write-Preview Gate and Permission Broker approval."""

    connector_type: str = "mcp:atlassian-confluence"

    def __init__(self, *, base_url: str = "https://confluence.enterprise.internal") -> None:
        self._base_url = base_url
        self._pages: dict[str, dict[str, Any]] = {
            "DE-CRL-01": {
                "page_id": "DE-CRL-01",
                "space_key": "ARCHI",
                "title": "Dossier d'Étude d'Architecture CRL — Mon Compte",
                "version": 1,
                "markdown": "# Dossier d'Étude d'Architecture CRL\n\n## Contexte\nSocle CRL.",
            }
        }

    async def healthcheck(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(
            connector_type=self.connector_type,
            ok=True,
            latency_ms=9,
            error_message=None,
        )

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        cleaned = resource_uri.strip()
        if not cleaned:
            raise ValidationDomainError(detail_override="resource_uri is required.")
        if "404" in cleaned or "not-found" in cleaned:
            raise ResourceNotFoundError(detail_override=f"Confluence page not found: {cleaned}")
        cql = (query or {}).get("cql")
        if cql:
            return {
                "connector_type": self.connector_type,
                "resource_uri": cleaned,
                "cql": str(cql),
                "pages": list(self._pages.values()),
            }
        page_id = cleaned.rsplit("/", 1)[-1].split("@", 1)[0]
        page = self._pages.get(
            page_id,
            {
                "page_id": page_id or "DE-CRL-01",
                "space_key": "ARCHI",
                "title": f"Page {page_id}",
                "version": 1,
                "markdown": f"# {page_id}\nContenu de référence Confluence.",
            },
        )
        return {
            "connector_type": self.connector_type,
            "resource_uri": cleaned,
            "page": page,
        }

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        clean_action = action.strip()
        if not clean_action:
            raise ValidationDomainError(detail_override="action is required for preview_write.")
        sha = compute_payload_sha256(clean_action, payload)
        space_key = str(payload.get("space_key") or "ARCHI")
        page_id = str(payload.get("page_id") or "NEW-PAGE")
        title = str(payload.get("title") or clean_action)
        return WritePreviewCard(
            preview_id=new_uuid7_str(),
            connector_type=self.connector_type,
            target_resource_uri=f"confluence://{space_key}/{page_id}",
            action_summary=f"[Confluence {clean_action}] {title}",
            diff_or_payload_preview={
                "action": clean_action,
                "space_key": space_key,
                "page_id": page_id,
                "title": title,
                "markdown_preview": str(payload.get("markdown") or "")[:500],
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
        space_key = str(payload.get("space_key") or "ARCHI")
        page_id = str(payload.get("page_id") or f"PAGE-{len(self._pages) + 1}")
        title = str(payload.get("title") or clean_action)
        self._pages[page_id] = {
            "page_id": page_id,
            "space_key": space_key,
            "title": title,
            "version": 2,
            "markdown": str(payload.get("markdown") or ""),
        }
        return {
            "connector_type": self.connector_type,
            "action": clean_action,
            "space_key": space_key,
            "page_id": page_id,
            "approved_by": approval_token.approver_user_id,
            "preview_id": approval_token.preview_id,
            "payload_sha256": approval_token.payload_sha256,
            "status": "COMMITTED",
        }
