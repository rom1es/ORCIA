"""Single Composition Root & FastAPI `Depends` providers for `apps/api` (`AD-19`).

Sharded by bounded domain into `< 300`-line modules (`core_and_lifespan`,
`orchestration_and_settings`, `portal_and_assistant`, `workspace_and_packs`) and re-exported
from `orcia_api.dependencies` as the unified public façade.
"""

from __future__ import annotations

from orcia_api.dependencies.core_and_lifespan import (
    app_lifespan,
    get_auth_service,
    get_bootstrap_service,
    get_catalog_service,
    get_ontology_and_rag_services,
    get_permission_broker_service,
    initialize_app_services,
)
from orcia_api.dependencies.orchestration_and_settings import (
    get_cognitive_router_service,
    get_connector_hub_service,
    get_control_center_service,
    get_durable_wizard_service,
    get_hierarchical_rbac_service,
    get_notification_service,
    get_orchestration_service,
    get_platform_settings_service,
    get_resource_lease_service,
    get_studio_and_pack_service,
)
from orcia_api.dependencies.portal_and_assistant import (
    get_accostage_service,
    get_assistant_citation_and_v5_guard_service,
    get_assistant_folders_and_sharing_service,
    get_assistant_governance_service,
    get_assistant_service,
    get_assistant_three_speed_router_service,
    get_contextual_help_service,
    get_two_speed_search_service,
    get_user_preferences_and_mcp_token_service,
)
from orcia_api.dependencies.workspace_and_packs import (
    get_agents_and_skills_service,
    get_dna_starlark_and_glossary_service,
    get_help_generation_and_attachment_service,
    get_pack_builder_system_service,
    get_remote_test_bench_and_mcp_service,
    get_workspace_governance_and_rebaser_service,
)

__all__ = [
    "app_lifespan",
    "get_accostage_service",
    "get_agents_and_skills_service",
    "get_assistant_citation_and_v5_guard_service",
    "get_assistant_folders_and_sharing_service",
    "get_assistant_governance_service",
    "get_assistant_service",
    "get_assistant_three_speed_router_service",
    "get_auth_service",
    "get_bootstrap_service",
    "get_catalog_service",
    "get_cognitive_router_service",
    "get_connector_hub_service",
    "get_contextual_help_service",
    "get_control_center_service",
    "get_dna_starlark_and_glossary_service",
    "get_durable_wizard_service",
    "get_help_generation_and_attachment_service",
    "get_hierarchical_rbac_service",
    "get_notification_service",
    "get_ontology_and_rag_services",
    "get_orchestration_service",
    "get_pack_builder_system_service",
    "get_permission_broker_service",
    "get_platform_settings_service",
    "get_remote_test_bench_and_mcp_service",
    "get_resource_lease_service",
    "get_studio_and_pack_service",
    "get_two_speed_search_service",
    "get_user_preferences_and_mcp_token_service",
    "get_workspace_governance_and_rebaser_service",
    "initialize_app_services",
]
