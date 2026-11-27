"""Lazy submodule export mapping for `orcia_api.dependencies` (PEP 562)."""

from __future__ import annotations

SUBMODULE_EXPORTS: dict[str, tuple[str, ...]] = {
    "orcia_api.dependencies.assistant_tools": (
        "build_assistant_tool_catalog_context_async",
        "get_governed_assistant_tool_router",
    ),
    "orcia_api.dependencies.autonomous_supervision": (
        "get_autonomous_supervision_service",
        "get_post_hoc_audit_service",
    ),
    "orcia_api.dependencies.core_and_lifespan": (
        "app_lifespan",
        "get_auth_service",
        "get_bootstrap_service",
        "get_catalog_service",
        "get_ontology_and_rag_services",
        "get_or_create_shared_db_engine",
        "get_permission_broker_service",
        "initialize_app_services",
    ),
    "orcia_api.dependencies.jira_and_mcp": (
        "get_jira_staged_action_service",
        "get_mcp_server_service",
    ),
    "orcia_api.dependencies.orchestration_and_settings": (
        "get_ai_models_hub_service",
        "get_assistant_process_launcher_service",
        "get_audit_ledger_service",
        "get_autonomy_contract_service",
        "get_cognitive_impact_service",
        "get_cognitive_router_service",
        "get_connector_hub_service",
        "get_connector_quota_guard_service",
        "get_control_center_service",
        "get_durable_wizard_service",
        "get_finops_accounting_service",
        "get_hierarchical_rbac_service",
        "get_iam_accounts_service",
        "get_log_sink_port",
        "get_notification_service",
        "get_orchestration_service",
        "get_platform_settings_service",
        "get_provenance_exporter_service",
        "get_remote_usage_sanitizer",
        "get_resource_lease_service",
        "get_studio_and_pack_service",
        "get_trigger_dispatcher_service",
    ),
    "orcia_api.dependencies.pack_import_deps": (
        "get_pack_bundle_v2_repository",
        "get_pack_cas_storage",
        "get_pack_composer_service",
        "get_pack_import_service",
        "get_workspace_packs_service",
    ),
    "orcia_api.dependencies.portal_and_assistant": (
        "get_accostage_service",
        "get_assistant_citation_and_v5_guard_service",
        "get_assistant_feedback_repository",
        "get_assistant_folders_and_sharing_service",
        "get_assistant_governance_service",
        "get_assistant_service",
        "get_assistant_thread_messages_repository",
        "get_assistant_turn_engine",
        "get_contextual_help_service",
        "get_embedding_port",
        "get_llm_streaming_port",
        "get_optional_embedding_port",
        "get_or_create_async_http_client",
        "get_two_speed_search_service",
        "get_user_preferences_and_mcp_token_service",
        "require_rag_available",
    ),
    "orcia_api.dependencies.reflexive_execution": (
        "get_assistant_reflexive_runtime_service",
        "get_process_execution_dispatcher",
        "get_reflexive_event_stream_broker",
        "get_reflexive_runtime_service",
        "get_reflexive_write_gate_service",
        "get_vsm_v2_sql_store",
        "get_workflow_v2_runs_store",
        "get_workflows_v2_runs_sql_store",
        "get_workflows_v2_sql_store",
    ),
    "orcia_api.dependencies.workspace_and_packs": (
        "get_agents_and_skills_service",
        "get_dna_starlark_and_glossary_service",
        "get_help_generation_and_attachment_service",
        "get_pack_builder_system_service",
        "get_remote_test_bench_and_mcp_service",
        "get_surgical_explorer_service",
        "get_workspace_governance_and_rebaser_service",
    ),
}

SYMBOL_TO_MODULE: dict[str, str] = {
    sym: mod for mod, symbols in SUBMODULE_EXPORTS.items() for sym in symbols
}

ALL_EXPORTS: tuple[str, ...] = tuple(SYMBOL_TO_MODULE.keys())
