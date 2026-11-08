"""Unit tests for `OrciaConnectorProtocol` & `SignedApprovalToken` (`TASK-01`)."""

from __future__ import annotations

import pytest

from orcia_connectors.adapters.atlassian_confluence import AtlassianConfluenceConnector
from orcia_connectors.adapters.atlassian_jira import AtlassianJiraConnector
from orcia_connectors.adapters.git_provider import GitProviderConnector
from orcia_connectors.adapters.mcp_client_bridge import McpClientBridgeConnector
from orcia_connectors.adapters.sql_readonly import SqlReadonlyConnector
from orcia_connectors.protocol import (
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
)
from orcia_core.kernel.errors import PolicyDeniedError


@pytest.mark.asyncio
async def test_all_enterprise_connectors_implement_orcia_connector_protocol() -> None:
    """Verify Jira, Confluence, Git, SQL and MCP Bridge implement `OrciaConnectorProtocol`."""
    connectors: list[OrciaConnectorProtocol] = [
        AtlassianJiraConnector(),
        AtlassianConfluenceConnector(),
        GitProviderConnector(),
        SqlReadonlyConnector(),
        McpClientBridgeConnector(),
    ]
    for conn in connectors:
        assert isinstance(conn, OrciaConnectorProtocol)
        health = await conn.healthcheck()
        assert health.ok is True
        assert health.connector_type == conn.connector_type


@pytest.mark.asyncio
async def test_execute_write_rejects_missing_or_tampered_signed_approval_token() -> None:
    """Verify no `execute_write()` call succeeds without a valid Permission Broker token."""
    jira = AtlassianJiraConnector()
    payload = {
        "project_key": "MCIA",
        "issue_type": "Feature",
        "summary": "Refonte parcours Mon Compte",
    }

    preview: WritePreviewCard = await jira.preview_write("create_item", payload)
    assert len(preview.payload_sha256) == 64

    # 1. Missing token -> PolicyDeniedError
    with pytest.raises(PolicyDeniedError, match="ERR_WRITE_PREVIEW_APPROVAL_REQUIRED"):
        await jira.execute_write(None, "create_item", payload)  # type: ignore[arg-type]

    # 2. Tampered signature -> PolicyDeniedError
    valid_token = SignedApprovalToken.issue(
        preview_card=preview,
        approver_user_id="romain.po",
    )
    forged_token = valid_token.model_copy(update={"broker_signature": "0" * 64})
    with pytest.raises(PolicyDeniedError, match="ERR_WRITE_PREVIEW_INVALID_SIGNATURE"):
        await jira.execute_write(forged_token, "create_item", payload)

    # 3. Tampered payload after preview approval -> PolicyDeniedError (SHA-256 mismatch)
    tampered_payload = {**payload, "summary": "Payload modifié après validation humaine"}
    with pytest.raises(PolicyDeniedError, match="ERR_WRITE_PREVIEW_SHA256_MISMATCH"):
        await jira.execute_write(valid_token, "create_item", tampered_payload)

    # 4. Valid SignedApprovalToken -> COMMITTED
    result = await jira.execute_write(valid_token, "create_item", payload)
    assert result["status"] == "COMMITTED"
    assert result["approved_by"] == "romain.po"
    assert result["payload_sha256"] == preview.payload_sha256


@pytest.mark.asyncio
async def test_confluence_git_mcp_and_sql_readonly_write_preview_enforcement() -> None:
    """Verify Write-Preview Gate across Confluence, Git, MCP Bridge and SQL Readonly."""
    confluence = AtlassianConfluenceConnector()
    conf_payload = {"space_key": "ARCHI", "title": "DE CRL v1", "markdown": "# DE"}
    conf_preview = await confluence.preview_write("update_document", conf_payload)
    conf_token = SignedApprovalToken.issue(preview_card=conf_preview, approver_user_id="archi.crl")
    conf_res = await confluence.execute_write(conf_token, "update_document", conf_payload)
    assert conf_res["status"] == "COMMITTED"

    git = GitProviderConnector()
    git_payload = {"repo": "mon-compte/crl-back", "branch": "feat/crl", "title": "feat: crl"}
    git_preview = await git.preview_write("open_pr", git_payload)
    git_token = SignedApprovalToken.issue(preview_card=git_preview, approver_user_id="dev.lead")
    git_res = await git.execute_write(git_token, "open_pr", git_payload)
    assert git_res["status"] == "COMMITTED"

    mcp = McpClientBridgeConnector()
    mcp_payload = {"target_uri": "mcp://atlassian/work_item", "title": "Epic US"}
    mcp_preview = await mcp.preview_write("create_work_item", mcp_payload)
    mcp_token = SignedApprovalToken.issue(preview_card=mcp_preview, approver_user_id="po.mc")
    mcp_res = await mcp.execute_write(mcp_token, "create_work_item", mcp_payload)
    assert mcp_res["status"] == "COMMITTED"

    sql = SqlReadonlyConnector()
    read_res = await sql.read("db://analytics/metrics", {"sql": "SELECT 1"})
    assert read_res["rows"] == [{"result": 1}]
    with pytest.raises(PolicyDeniedError, match="ERR_SQL_READONLY_VIOLATION"):
        await sql.read("db://analytics/metrics", {"sql": "DROP TABLE users"})
