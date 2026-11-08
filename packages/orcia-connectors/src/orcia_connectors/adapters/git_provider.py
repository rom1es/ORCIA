"""Git Provider Connector (`mcp:git-provider`) implementing `OrciaConnectorProtocol`."""

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


class GitProviderConnector(OrciaConnectorProtocol):
    """Governed Git/GitLab/GitHub connector enforcing Write-Preview Gate before PR/commit."""

    connector_type: str = "mcp:git-provider"

    def __init__(self, *, default_repo: str = "mon-compte/crl-back") -> None:
        self._default_repo = default_repo
        self._pull_requests: dict[str, dict[str, Any]] = {}

    async def healthcheck(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(
            connector_type=self.connector_type,
            ok=True,
            latency_ms=6,
            error_message=None,
        )

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        cleaned = resource_uri.strip()
        if not cleaned:
            raise ValidationDomainError(detail_override="resource_uri is required.")
        if "404" in cleaned or "not-found" in cleaned:
            raise ResourceNotFoundError(detail_override=f"Git resource not found: {cleaned}")
        ref = (query or {}).get("ref", "main")
        return {
            "connector_type": self.connector_type,
            "resource_uri": cleaned,
            "ref": str(ref),
            "repo": self._default_repo,
            "content": f"// Contenu vérifié depuis {cleaned}@{ref}",
        }

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        clean_action = action.strip()
        if not clean_action:
            raise ValidationDomainError(detail_override="action is required for preview_write.")
        sha = compute_payload_sha256(clean_action, payload)
        repo = str(payload.get("repo") or self._default_repo)
        branch = str(payload.get("branch") or "feat/orcia-change")
        title = str(payload.get("title") or clean_action)
        return WritePreviewCard(
            preview_id=new_uuid7_str(),
            connector_type=self.connector_type,
            target_resource_uri=f"git://{repo}/pulls/{branch}",
            action_summary=f"[Git {clean_action}] {title} ({branch})",
            diff_or_payload_preview={
                "action": clean_action,
                "repo": repo,
                "branch": branch,
                "title": title,
                "diff": str(payload.get("diff") or ""),
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
        repo = str(payload.get("repo") or self._default_repo)
        pr_id = f"PR-{len(self._pull_requests) + 1}"
        record = {
            "connector_type": self.connector_type,
            "action": clean_action,
            "repo": repo,
            "pr_id": pr_id,
            "approved_by": approval_token.approver_user_id,
            "preview_id": approval_token.preview_id,
            "payload_sha256": approval_token.payload_sha256,
            "status": "COMMITTED",
        }
        self._pull_requests[pr_id] = record
        return record
