"""Enterprise Connector Adapters (`OrciaConnectorProtocol`)."""

from __future__ import annotations

from orcia_connectors.adapters.atlassian_confluence import AtlassianConfluenceConnector
from orcia_connectors.adapters.atlassian_jira import AtlassianJiraConnector
from orcia_connectors.adapters.git_provider import GitProviderConnector
from orcia_connectors.adapters.mcp_client_bridge import McpClientBridgeConnector
from orcia_connectors.adapters.sql_readonly import SqlReadonlyConnector
from orcia_connectors.protocol import OrciaConnectorProtocol


def get_default_enterprise_connectors() -> dict[str, OrciaConnectorProtocol]:
    """Return all built-in enterprise connectors keyed by `connector_type`."""
    jira = AtlassianJiraConnector()
    confluence = AtlassianConfluenceConnector()
    git = GitProviderConnector()
    sql = SqlReadonlyConnector()
    mcp = McpClientBridgeConnector()
    return {
        jira.connector_type: jira,
        confluence.connector_type: confluence,
        git.connector_type: git,
        sql.connector_type: sql,
        mcp.connector_type: mcp,
    }


__all__ = [
    "AtlassianConfluenceConnector",
    "AtlassianJiraConnector",
    "GitProviderConnector",
    "McpClientBridgeConnector",
    "SqlReadonlyConnector",
    "get_default_enterprise_connectors",
]
