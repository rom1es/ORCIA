"""Single Composition Root & FastAPI `Depends` providers for `apps/api` (`AD-19`).

Sharded by bounded domain into `< 300`-line modules and lazily re-exported via PEP 562
from `orcia_api.dependencies` as the unified public facade.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from orcia_api.dependencies._lazy_exports import ALL_EXPORTS, SYMBOL_TO_MODULE

if TYPE_CHECKING:
    from orcia_api.dependencies.assistant_tools import (
        build_assistant_tool_catalog_context_async as build_assistant_tool_catalog_context_async,
    )
    from orcia_api.dependencies.assistant_tools import (
        get_governed_assistant_tool_router as get_governed_assistant_tool_router,
    )
    from orcia_api.dependencies.autonomous_supervision import (
        get_autonomous_supervision_service as get_autonomous_supervision_service,
    )
    from orcia_api.dependencies.autonomous_supervision import (
        get_post_hoc_audit_service as get_post_hoc_audit_service,
    )
    from orcia_api.dependencies.core_and_lifespan import (
        app_lifespan as app_lifespan,
    )
    from orcia_api.dependencies.core_and_lifespan import (
        get_auth_service as get_auth_service,
    )
    from orcia_api.dependencies.core_and_lifespan import (
        get_bootstrap_service as get_bootstrap_service,
    )
    from orcia_api.dependencies.core_and_lifespan import (
        get_catalog_service as get_catalog_service,
    )
    from orcia_api.dependencies.core_and_lifespan import (
        get_ontology_and_rag_services as get_ontology_and_rag_services,
    )
    from orcia_api.dependencies.core_and_lifespan import (
        get_or_create_shared_db_engine as get_or_create_shared_db_engine,
    )
    from orcia_api.dependencies.core_and_lifespan import (
        get_permission_broker_service as get_permission_broker_service,
    )
    from orcia_api.dependencies.core_and_lifespan import (
        initialize_app_services as initialize_app_services,
    )
    from orcia_api.dependencies.jira_and_mcp import (
        get_jira_staged_action_service as get_jira_staged_action_service,
    )
    from orcia_api.dependencies.jira_and_mcp import (
        get_mcp_server_service as get_mcp_server_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_ai_models_hub_service as get_ai_models_hub_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_assistant_process_launcher_service as get_assistant_process_launcher_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_audit_ledger_service as get_audit_ledger_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_autonomy_contract_service as get_autonomy_contract_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_cognitive_impact_service as get_cognitive_impact_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_cognitive_router_service as get_cognitive_router_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_connector_hub_service as get_connector_hub_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_connector_quota_guard_service as get_connector_quota_guard_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_control_center_service as get_control_center_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_durable_wizard_service as get_durable_wizard_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_finops_accounting_service as get_finops_accounting_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_hierarchical_rbac_service as get_hierarchical_rbac_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_iam_accounts_service as get_iam_accounts_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_log_sink_port as get_log_sink_port,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_notification_service as get_notification_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_orchestration_service as get_orchestration_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_platform_settings_service as get_platform_settings_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_provenance_exporter_service as get_provenance_exporter_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_remote_usage_sanitizer as get_remote_usage_sanitizer,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_resource_lease_service as get_resource_lease_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_studio_and_pack_service as get_studio_and_pack_service,
    )
    from orcia_api.dependencies.orchestration_and_settings import (
        get_trigger_dispatcher_service as get_trigger_dispatcher_service,
    )
    from orcia_api.dependencies.pack_import_deps import (
        get_pack_bundle_v2_repository as get_pack_bundle_v2_repository,
    )
    from orcia_api.dependencies.pack_import_deps import (
        get_pack_cas_storage as get_pack_cas_storage,
    )
    from orcia_api.dependencies.pack_import_deps import (
        get_pack_composer_service as get_pack_composer_service,
    )
    from orcia_api.dependencies.pack_import_deps import (
        get_pack_import_service as get_pack_import_service,
    )
    from orcia_api.dependencies.pack_import_deps import (
        get_workspace_packs_service as get_workspace_packs_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_accostage_service as get_accostage_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_assistant_citation_and_v5_guard_service as get_assistant_citation_and_v5_guard_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_assistant_feedback_repository as get_assistant_feedback_repository,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_assistant_folders_and_sharing_service as get_assistant_folders_and_sharing_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_assistant_governance_service as get_assistant_governance_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_assistant_service as get_assistant_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_assistant_thread_messages_repository as get_assistant_thread_messages_repository,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_assistant_turn_engine as get_assistant_turn_engine,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_contextual_help_service as get_contextual_help_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_embedding_port as get_embedding_port,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_llm_streaming_port as get_llm_streaming_port,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_optional_embedding_port as get_optional_embedding_port,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_or_create_async_http_client as get_or_create_async_http_client,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_two_speed_search_service as get_two_speed_search_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        get_user_preferences_and_mcp_token_service as get_user_preferences_and_mcp_token_service,
    )
    from orcia_api.dependencies.portal_and_assistant import (
        require_rag_available as require_rag_available,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_assistant_reflexive_runtime_service as get_assistant_reflexive_runtime_service,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_process_execution_dispatcher as get_process_execution_dispatcher,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_reflexive_event_stream_broker as get_reflexive_event_stream_broker,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_reflexive_runtime_service as get_reflexive_runtime_service,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_reflexive_write_gate_service as get_reflexive_write_gate_service,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_vsm_v2_sql_store as get_vsm_v2_sql_store,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_workflow_v2_runs_store as get_workflow_v2_runs_store,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_workflows_v2_runs_sql_store as get_workflows_v2_runs_sql_store,
    )
    from orcia_api.dependencies.reflexive_execution import (
        get_workflows_v2_sql_store as get_workflows_v2_sql_store,
    )
    from orcia_api.dependencies.workspace_and_packs import (
        get_agents_and_skills_service as get_agents_and_skills_service,
    )
    from orcia_api.dependencies.workspace_and_packs import (
        get_dna_starlark_and_glossary_service as get_dna_starlark_and_glossary_service,
    )
    from orcia_api.dependencies.workspace_and_packs import (
        get_help_generation_and_attachment_service as get_help_generation_and_attachment_service,
    )
    from orcia_api.dependencies.workspace_and_packs import (
        get_pack_builder_system_service as get_pack_builder_system_service,
    )
    from orcia_api.dependencies.workspace_and_packs import (
        get_remote_test_bench_and_mcp_service as get_remote_test_bench_and_mcp_service,
    )
    from orcia_api.dependencies.workspace_and_packs import (
        get_surgical_explorer_service as get_surgical_explorer_service,
    )
    from orcia_api.dependencies.workspace_and_packs import (
        get_workspace_governance_and_rebaser_service as get_workspace_governance_and_rebaser_service,  # noqa: E501
    )


def __getattr__(name: str) -> Any:
    module_path = SYMBOL_TO_MODULE.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module_path), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(ALL_EXPORTS))


__all__ = list(ALL_EXPORTS)
