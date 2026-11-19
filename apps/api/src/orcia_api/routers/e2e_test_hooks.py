"""Isolated E2E test hook router (`/api/v1/_e2e/*`, active only when `ORCIA_ENV == 'e2e'`)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.schemas.e2e_test_hooks import EvictMemoryCachesResponse
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions.errors import ResourceNotFoundError

logger = get_logger("orcia.api.e2e_hooks")

router = APIRouter(prefix="/api/v1/_e2e", tags=["_e2e"])

_E2E_EVICTABLE_STATE_ATTRS: tuple[str, ...] = (
    "auth_service",
    "auth_policy_store",
    "catalog_service",
    "contextual_help_service",
    "permission_broker_service",
    "bootstrap_service",
    "orchestration_service",
    "notification_service",
    "resource_lease_service",
    "control_center_service",
    "hierarchical_rbac_service",
    "iam_accounts_service",
    "platform_settings_service",
    "cognitive_router_service",
    "connector_hub_service",
    "studio_and_pack_service",
    "durable_wizard_service",
    "audit_ledger_service",
    "finops_accounting_service",
    "cognitive_impact_service",
    "post_hoc_audit_service",
    "autonomous_supervision_service",
    "autonomy_contract_service",
    "trigger_dispatcher_service",
    "ai_models_hub_service",
    "accostage_service",
    "two_speed_search_service",
    "user_preferences_and_mcp_token_service",
    "assistant_governance_service",
    "assistant_three_speed_router_service",
    "assistant_citation_and_v5_guard_service",
    "assistant_folders_and_sharing_service",
    "assistant_service",
    "workspace_governance_and_rebaser_service",
    "dna_starlark_and_glossary_service",
    "remote_test_bench_and_mcp_service",
    "pack_builder_system_service",
    "help_generation_and_attachment_service",
    "agents_and_skills_service",
    "surgical_explorer_service",
    "reflexive_runtime_service",
    "reflexive_event_stream_broker",
    "reflexive_write_gate_service",
    "workflows_v2_sql_store",
    "process_execution_dispatcher",
    "platform_setup_snapshot",
    "declarative_pack_bundles",
    "auth_policy_explicitly_set",
    "enterprise_connectors_service",
    "jira_staged_action_service",
    "mcp_server_service",
    "workflows_v2_store",
    "vsm_v2_store",
    "workflow_v2_runs_store",
    "ontology_rag_seeded_bundle",
    "ontology_rag_runtime_bundle",
    "gate_repository",
    "connector_quota_guard_service",
    "finops_sanitizer",
    "connector_invoker",
)


@router.post(
    "/evict-memory-caches",
    response_model=EvictMemoryCachesResponse,
    summary="Evict all in-memory application caches for cold PG18 reload (E2E only)",
    responses={
        404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    },
)
async def evict_memory_caches(request: Request) -> EvictMemoryCachesResponse:
    """Clear all RAM caches/mirrors on `app.state` without touching PostgreSQL 18.

    Returns HTTP 404 (RFC 9457) whenever `ORCIA_ENV != "e2e"`.
    """
    if os.environ.get("ORCIA_ENV", "").strip().lower() != "e2e":
        raise ResourceNotFoundError(
            detail_override="Endpoint disponible uniquement en environnement E2E.",
            instance=str(request.url.path),
        )

    cleared: list[str] = []
    for attr in _E2E_EVICTABLE_STATE_ATTRS:
        if getattr(request.app.state, attr, None) is not None:
            setattr(request.app.state, attr, None)
            cleared.append(attr)

    initialize_app_services(request.app)

    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    logger.info("e2e_memory_caches_evicted", cleared_count=len(cleared), trace_id=trace_id)
    return EvictMemoryCachesResponse(
        evicted=True,
        cleared_caches=cleared,
        trace_id=trace_id,
    )
