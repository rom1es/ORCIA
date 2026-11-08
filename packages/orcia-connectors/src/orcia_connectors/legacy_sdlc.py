"""Legacy SDLC connector & plugin registration consolidated into `orcia_connectors`."""

from __future__ import annotations

from orcia_connectors.formats_and_indexers import (
    SdlcDocVsCodeAuditAssistantTemplate,
    create_sdlc_assistant_template_plugin,
    get_bmad_pack_format_adapter,
    get_git_code_ast_indexer,
    get_jira_hybrid_indexer,
    get_tripartite_graph_indexer,
)
from orcia_connectors.jira_actions import (
    JiraAccessRequestChannelAdapter,
    JiraTransitionSpec,
    JiraWebhookReplayNotification,
    MultiProjectJiraStagedActionService,
    StagedJiraActionItem,
    register_jira_access_request_channel,
)
from orcia_connectors.markers import (
    SDLC_BUG_CODE_MARKER,
    SDLC_DOC_OBSOLETE_MARKER,
    SdlcMemlogMarkerPlugin,
    create_sdlc_memlog_marker_plugin,
)
from orcia_connectors.policies import (
    SdlcFr13WorkflowPolicyPlugin,
    create_sdlc_fr13_policy_plugin,
)
from orcia_connectors.sdlc_connectors import (
    SdlcConnectorAdapter,
    create_confluence_connector,
    create_git_connector,
    create_jira_connector,
    create_nexus_connector,
    register_all_sdlc_connectors,
)

__version__: str = "0.1.0"


def activate_sdlc_pack() -> None:
    """Idempotently register all SDLC connectors, policies, markers, indexers & templates."""
    register_all_sdlc_connectors()
    register_jira_access_request_channel()
    create_sdlc_fr13_policy_plugin()
    create_sdlc_memlog_marker_plugin()
    get_git_code_ast_indexer()
    get_jira_hybrid_indexer()
    get_tripartite_graph_indexer()
    create_sdlc_assistant_template_plugin()


activate_sdlc_pack()

__all__ = [
    "JiraAccessRequestChannelAdapter",
    "JiraTransitionSpec",
    "JiraWebhookReplayNotification",
    "MultiProjectJiraStagedActionService",
    "SDLC_BUG_CODE_MARKER",
    "SDLC_DOC_OBSOLETE_MARKER",
    "SdlcConnectorAdapter",
    "SdlcDocVsCodeAuditAssistantTemplate",
    "SdlcFr13WorkflowPolicyPlugin",
    "SdlcMemlogMarkerPlugin",
    "StagedJiraActionItem",
    "__version__",
    "activate_sdlc_pack",
    "create_confluence_connector",
    "create_git_connector",
    "create_jira_connector",
    "create_nexus_connector",
    "create_sdlc_assistant_template_plugin",
    "create_sdlc_fr13_policy_plugin",
    "create_sdlc_memlog_marker_plugin",
    "get_bmad_pack_format_adapter",
    "get_git_code_ast_indexer",
    "get_jira_hybrid_indexer",
    "get_tripartite_graph_indexer",
    "register_all_sdlc_connectors",
    "register_jira_access_request_channel",
]
