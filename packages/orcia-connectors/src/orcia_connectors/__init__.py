"""ORCIA Connectors (`packages/orcia-connectors`).

Unified enterprise connectors library (`OrciaConnectorProtocol`: `healthcheck`, `read`,
`preview_write`, `execute_write`) governed by the Permission Broker & Write-Preview Gate.
"""

from __future__ import annotations

from orcia_connectors.adapters import (
    AtlassianConfluenceConnector,
    AtlassianJiraConnector,
    GitProviderConnector,
    McpClientBridgeConnector,
    SqlReadonlyConnector,
    get_default_enterprise_connectors,
)
from orcia_connectors.legacy_sdlc import (
    SDLC_BUG_CODE_MARKER,
    SDLC_DOC_OBSOLETE_MARKER,
    JiraAccessRequestChannelAdapter,
    JiraTransitionSpec,
    JiraWebhookReplayNotification,
    MultiProjectJiraStagedActionService,
    SdlcConnectorAdapter,
    SdlcDocVsCodeAuditAssistantTemplate,
    SdlcFr13WorkflowPolicyPlugin,
    SdlcMemlogMarkerPlugin,
    StagedJiraActionItem,
    activate_sdlc_pack,
    create_confluence_connector,
    create_git_connector,
    create_jira_connector,
    create_nexus_connector,
    create_sdlc_assistant_template_plugin,
    create_sdlc_fr13_policy_plugin,
    create_sdlc_memlog_marker_plugin,
    get_bmad_pack_format_adapter,
    get_git_code_ast_indexer,
    get_jira_hybrid_indexer,
    get_tripartite_graph_indexer,
    register_all_sdlc_connectors,
    register_jira_access_request_channel,
)
from orcia_connectors.protocol import (
    ConnectorHealthStatus,
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    sign_approval_token_payload,
    verify_signed_approval_token,
)
from orcia_connectors.reflexive_write_gate import (
    ConnectorReflexiveWriteGateAdapter,
    issue_broker_write_approval,
)
from orcia_connectors.surgical import (
    SurgicalContextExplorer,
    extract_outline_nodes,
    resolve_file_badge_code,
    validate_surgical_uri_security,
)

__version__: str = "0.1.0"

__all__ = [
    "AtlassianConfluenceConnector",
    "AtlassianJiraConnector",
    "ConnectorHealthStatus",
    "ConnectorReflexiveWriteGateAdapter",
    "GitProviderConnector",
    "JiraAccessRequestChannelAdapter",
    "JiraTransitionSpec",
    "JiraWebhookReplayNotification",
    "McpClientBridgeConnector",
    "MultiProjectJiraStagedActionService",
    "OrciaConnectorProtocol",
    "SDLC_BUG_CODE_MARKER",
    "SDLC_DOC_OBSOLETE_MARKER",
    "SdlcConnectorAdapter",
    "SdlcDocVsCodeAuditAssistantTemplate",
    "SdlcFr13WorkflowPolicyPlugin",
    "SdlcMemlogMarkerPlugin",
    "SignedApprovalToken",
    "SqlReadonlyConnector",
    "StagedJiraActionItem",
    "SurgicalContextExplorer",
    "WritePreviewCard",
    "__version__",
    "activate_sdlc_pack",
    "compute_payload_sha256",
    "create_confluence_connector",
    "create_git_connector",
    "create_jira_connector",
    "create_nexus_connector",
    "create_sdlc_assistant_template_plugin",
    "create_sdlc_fr13_policy_plugin",
    "create_sdlc_memlog_marker_plugin",
    "extract_outline_nodes",
    "get_bmad_pack_format_adapter",
    "get_default_enterprise_connectors",
    "get_git_code_ast_indexer",
    "get_jira_hybrid_indexer",
    "get_tripartite_graph_indexer",
    "issue_broker_write_approval",
    "register_all_sdlc_connectors",
    "register_jira_access_request_channel",
    "resolve_file_badge_code",
    "sign_approval_token_payload",
    "validate_surgical_uri_security",
    "verify_signed_approval_token",
]
