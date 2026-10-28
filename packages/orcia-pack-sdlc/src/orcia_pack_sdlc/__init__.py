"""ORCIA SDLC Vertical Pack (`orcia_pack_sdlc`, `AD-20`, `Story 3.2e`).

Registers SDLC connectors (`git://`, `jira://`, `confluence://`, `nexus://`), rule `FR-13`
(`Intention -> Code` & `brownfield_bootstrap`), SDLC memlog markers (`sdlc.*`), `BMAD_PACK`
format adapter, and SDLC indexers via `importlib.metadata.entry_points` without polluting
`orcia_kernel` or `orcia_core`.
"""

from __future__ import annotations

from orcia_pack_sdlc.connectors import (
    SdlcConnectorAdapter,
    create_confluence_connector,
    create_git_connector,
    create_jira_connector,
    create_nexus_connector,
    register_all_sdlc_connectors,
)
from orcia_pack_sdlc.formats_and_indexers import (
    SdlcDocVsCodeAuditAssistantTemplate,
    create_sdlc_assistant_template_plugin,
    get_bmad_pack_format_adapter,
    get_git_code_ast_indexer,
    get_jira_hybrid_indexer,
    get_tripartite_graph_indexer,
)
from orcia_pack_sdlc.markers import (
    SDLC_BUG_CODE_MARKER,
    SDLC_DOC_OBSOLETE_MARKER,
    SdlcMemlogMarkerPlugin,
    create_sdlc_memlog_marker_plugin,
)
from orcia_pack_sdlc.policies import (
    SdlcFr13WorkflowPolicyPlugin,
    create_sdlc_fr13_policy_plugin,
)

__version__: str = "0.1.0"


def activate_sdlc_pack() -> None:
    """Idempotently register all SDLC connectors, policies, markers, indexers & templates."""
    register_all_sdlc_connectors()
    create_sdlc_fr13_policy_plugin()
    create_sdlc_memlog_marker_plugin()
    get_git_code_ast_indexer()
    get_jira_hybrid_indexer()
    get_tripartite_graph_indexer()
    create_sdlc_assistant_template_plugin()


# Activate when imported in composition root or tests
activate_sdlc_pack()

__all__ = [
    "SDLC_BUG_CODE_MARKER",
    "SDLC_DOC_OBSOLETE_MARKER",
    "SdlcConnectorAdapter",
    "SdlcDocVsCodeAuditAssistantTemplate",
    "SdlcFr13WorkflowPolicyPlugin",
    "SdlcMemlogMarkerPlugin",
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
]
