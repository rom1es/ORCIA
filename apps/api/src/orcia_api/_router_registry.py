"""Deferred router imports & registration helper for `orcia_api.main.create_app()`."""

from __future__ import annotations

from fastapi import FastAPI


def register_all_routers(application: FastAPI) -> None:
    """Import and mount all ORCIA FastAPI routers onto `application`."""
    from orcia_api.routers._catalog_delete_routes import router as catalog_delete_router
    from orcia_api.routers.agents_and_skills import router as agents_and_skills_router
    from orcia_api.routers.ai_models_hub import router as ai_models_hub_router
    from orcia_api.routers.assistant_turns import router as assistant_turns_router
    from orcia_api.routers.audit_ledger import router as audit_ledger_router
    from orcia_api.routers.auth import router as auth_router
    from orcia_api.routers.auth_settings import router as auth_settings_router
    from orcia_api.routers.autonomous_supervision import router as autonomous_supervision_router
    from orcia_api.routers.autonomy_contracts import router as autonomy_contracts_router
    from orcia_api.routers.blackboard_and_engine import router as blackboard_and_engine_router
    from orcia_api.routers.bootstrap import router as bootstrap_router
    from orcia_api.routers.catalog import router as catalog_router
    from orcia_api.routers.challenge_and_replay import router as challenge_and_replay_router
    from orcia_api.routers.codegraph_mcp import router as codegraph_mcp_router
    from orcia_api.routers.control_center import router as control_center_router
    from orcia_api.routers.datasource_webhooks import router as datasource_webhooks_router
    from orcia_api.routers.dna_and_glossary import router as dna_and_glossary_router
    from orcia_api.routers.e2e_test_hooks import router as e2e_test_hooks_router
    from orcia_api.routers.enterprise_connectors import router as enterprise_connectors_router
    from orcia_api.routers.executions_trace import router as executions_trace_router
    from orcia_api.routers.finops import router as finops_router
    from orcia_api.routers.gates import router as gates_router
    from orcia_api.routers.health import probe_router as health_probe_router
    from orcia_api.routers.health import router as health_router
    from orcia_api.routers.human_gates import router as human_gates_router
    from orcia_api.routers.iam_accounts import router as iam_accounts_router
    from orcia_api.routers.inbox_and_leases import router as inbox_and_leases_router
    from orcia_api.routers.jira_and_mcp import router as jira_and_mcp_router
    from orcia_api.routers.mcp_and_test_bench import router as mcp_and_test_bench_router
    from orcia_api.routers.ontology_and_rag import router as ontology_and_rag_router
    from orcia_api.routers.ontology_promotions import router as ontology_promotions_router
    from orcia_api.routers.orchestration import router as orchestration_router
    from orcia_api.routers.org_and_workspaces import router as org_and_workspaces_router
    from orcia_api.routers.pack_builder import router as pack_builder_router
    from orcia_api.routers.pack_composer import router as pack_composer_router
    from orcia_api.routers.packs import router as packs_router
    from orcia_api.routers.permission_broker import router as permission_broker_router
    from orcia_api.routers.portal_and_help import router as portal_and_help_router
    from orcia_api.routers.settings_and_studio import router as settings_and_studio_router
    from orcia_api.routers.shell import router as shell_router
    from orcia_api.routers.sources_surgical import router as sources_surgical_router
    from orcia_api.routers.studio_and_wizards import router as studio_and_wizards_router
    from orcia_api.routers.user_account_settings import router as user_account_settings_router
    from orcia_api.routers.user_profile import router as user_profile_router
    from orcia_api.routers.workflow_triggers import router as workflow_triggers_router
    from orcia_api.routers.workflows import router as workflows_v2_router
    from orcia_api.routers.workspace_datasources import router as workspace_datasources_router
    from orcia_api.routers.workspace_governance import router as workspace_governance_router
    from orcia_api.routers.workspace_packs import router as workspace_packs_router
    from orcia_api.routers.workspace_packs import run_lock_router as run_lock_manifest_router

    for rtr in (
        health_router,
        health_probe_router,
        shell_router,
        auth_router,
        org_and_workspaces_router,
        catalog_router,
        catalog_delete_router,
        permission_broker_router,
        gates_router,
        human_gates_router,
        inbox_and_leases_router,
        control_center_router,
        iam_accounts_router,
        auth_settings_router,
        enterprise_connectors_router,
        ai_models_hub_router,
        settings_and_studio_router,
        studio_and_wizards_router,
        jira_and_mcp_router,
        bootstrap_router,
        ontology_and_rag_router,
        ontology_promotions_router,
        orchestration_router,
        blackboard_and_engine_router,
        challenge_and_replay_router,
        portal_and_help_router,
        user_account_settings_router,
        user_profile_router,
        assistant_turns_router,
        workspace_governance_router,
        workspace_datasources_router,
        codegraph_mcp_router,
        datasource_webhooks_router,
        dna_and_glossary_router,
        mcp_and_test_bench_router,
        pack_builder_router,
        agents_and_skills_router,
        pack_composer_router,
        packs_router,
        workspace_packs_router,
        workflows_v2_router,
        run_lock_manifest_router,
        audit_ledger_router,
        finops_router,
        autonomy_contracts_router,
        autonomous_supervision_router,
        workflow_triggers_router,
        sources_surgical_router,
        executions_trace_router,
        e2e_test_hooks_router,
    ):
        application.include_router(rtr)
