"""Test connection, delete-impact, routing, and reindexing routes for AI Models Hub (`MINOR-01`)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_ai_models_hub_service,
    get_audit_ledger_service,
    get_auth_service,
    get_cognitive_router_service,
)
from orcia_api.routers._ai_models_helpers import (
    execute_model_connection_test,
    require_ai_models_platform_admin,
    resolve_mapping_decrypted_key,
)
from orcia_api.routers._ai_models_reindex_helpers import (
    fetch_reindex_status_response,
    trigger_manual_reindex_embeddings,
)
from orcia_api.routers._settings_helpers import to_routing_outcome_response
from orcia_api.schemas.ai_models_hub import (
    AiModelDeleteImpactResponse,
    AiModelDeleteResponse,
    AiModelTestResponse,
    PinRemovalModeLiteral,
    RagReindexStatusResponse,
    RagReindexTriggerResponse,
)
from orcia_api.schemas.settings_and_studio import (
    CognitiveRoutingOutcomeResponse,
    ExecuteTierRoutingRequest,
)
from orcia_core.audit_finops import (
    SqlAuditLedgerService,
    map_domain_event_to_ledger_entry,
)
from orcia_core.kernel.events import AdminConnectionTested
from orcia_core.orchestration import (
    AiModelsHubService,
    CognitiveModelRouterService,
    ResolvedInferenceTier,
    delete_or_drain_ai_model_mapping_pg18,
    ensure_ai_model_mappings_schema_on_postgres18,
    evaluate_ai_model_delete_impact_pg18,
    record_ai_model_test_result_pg18,
)
from orcia_core.permissions import AuthAndOrganizationService, UserIdentity
from orcia_kernel.errors import OrciaDomainError

router = APIRouter()


@router.post("/mappings/{mapping_id}/test", response_model=AiModelTestResponse)
async def test_ai_model_connection(
    mapping_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    user: Annotated[UserIdentity, Depends(require_ai_models_platform_admin)],
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    audit_svc: Annotated[SqlAuditLedgerService, Depends(get_audit_ledger_service)],
) -> AiModelTestResponse:
    """Execute on-demand non-blocking connectivity test against model endpoint."""
    path = str(request.url.path)
    engine = getattr(request.app.state, "db_engine", None)
    rec, decrypted_key = await resolve_mapping_decrypted_key(request, mapping_id, auth_svc, hub_svc)

    try:
        health, resp = await execute_model_connection_test(rec, decrypted_key, request)
        if engine is not None:
            async with engine.begin() as conn:
                await record_ai_model_test_result_pg18(
                    conn,
                    mapping_id,
                    health_status=health,
                    latency_ms=resp.latency_ms,
                    instance=path,
                )
        else:
            hub_svc.record_test_result(
                mapping_id, health_status=health, latency_ms=resp.latency_ms, instance=path
            )
        evt = AdminConnectionTested.create(
            actor_id=user.id,
            target_type="AI_MODEL",
            target_id=mapping_id,
            protocol="HTTP_INFERENCE",
            test_status=health,
            latency_ms=resp.latency_ms,
            detail=f"Test de connexion modèle IA {mapping_id}: {health}",
            metadata={
                "actor_type": "ADMIN_CONNECTION_TEST",
                "actor_display_name": getattr(user, "display_name", None),
                "actor_email": getattr(user, "email", None),
                "model_id": rec.model_name if rec else mapping_id,
                "provider": rec.provider_slug if rec else None,
                "health_status": health,
            },
        )
        entry = map_domain_event_to_ledger_entry(evt)
        await audit_svc.record_entry(entry)
        return resp
    except OrciaDomainError as exc:
        lat_val = getattr(exc, "latency_ms", None)
        lat_ms: int = int(lat_val) if isinstance(lat_val, (int, float)) else 0
        if engine is not None:
            async with engine.begin() as conn:
                await record_ai_model_test_result_pg18(
                    conn, mapping_id, health_status="ERROR", latency_ms=lat_ms, instance=path
                )
        else:
            hub_svc.record_test_result(
                mapping_id, health_status="ERROR", latency_ms=lat_ms, instance=path
            )
        evt_err = AdminConnectionTested.create(
            actor_id=user.id,
            target_type="AI_MODEL",
            target_id=mapping_id,
            protocol="HTTP_INFERENCE",
            test_status="ERROR",
            latency_ms=lat_ms,
            detail=f"Test de connexion modèle IA {mapping_id}: ERROR ({type(exc).__name__})",
            metadata={
                "actor_type": "ADMIN_CONNECTION_TEST",
                "actor_display_name": getattr(user, "display_name", None),
                "actor_email": getattr(user, "email", None),
                "model_id": rec.model_name if rec else mapping_id,
                "provider": rec.provider_slug if rec else None,
                "health_status": "ERROR",
                "error_type": type(exc).__name__,
            },
        )
        entry_err = map_domain_event_to_ledger_entry(evt_err)
        await audit_svc.record_entry(entry_err)
        raise exc


@router.get("/mappings/{mapping_id}/delete-impact", response_model=AiModelDeleteImpactResponse)
async def get_ai_model_delete_impact(
    mapping_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
) -> AiModelDeleteImpactResponse:
    """Analyze workflow and active run dependencies before deleting a model."""
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
            impact = await evaluate_ai_model_delete_impact_pg18(
                conn, mapping_id, instance=str(request.url.path)
            )
    else:
        impact = hub_svc.evaluate_delete_impact(mapping_id, instance=str(request.url.path))

    return AiModelDeleteImpactResponse(
        mapping_id=impact.mapping_id,
        inference_tier=impact.inference_tier,
        model_name=impact.model_name,
        remaining_active_for_tier=impact.remaining_active_for_tier,
        dependent_workflows_count=impact.dependent_workflows_count,
        dependent_workflow_ids=list(impact.dependent_workflow_ids),
        pinned_active_runs_count=impact.pinned_active_runs_count,
        pinned_run_ids=list(impact.pinned_run_ids),
        is_last_active_for_tier=impact.is_last_active_for_tier,
    )


@router.delete("/mappings/{mapping_id}", response_model=AiModelDeleteResponse)
async def delete_ai_model_mapping(
    mapping_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    _user: Annotated[UserIdentity, Depends(require_ai_models_platform_admin)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    mode: Annotated[PinRemovalModeLiteral, Query()] = "reject",
) -> AiModelDeleteResponse:
    """Delete or drain a mapping enforcing dependency & active run guards."""
    server_actor_role = "PLATFORM_ADMIN"
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
            res = await delete_or_drain_ai_model_mapping_pg18(
                conn,
                mapping_id,
                mode=mode,
                actor_role=server_actor_role,
                instance=str(request.url.path),
            )
    else:
        res = hub_svc.delete_or_drain_mapping(
            mapping_id,
            mode=mode,
            actor_role=server_actor_role,
            instance=str(request.url.path),
        )
    st: Literal["DELETED", "DRAINING"] = "DRAINING" if res and res.draining else "DELETED"
    return AiModelDeleteResponse(mapping_id=mapping_id, status=st)


@router.post("/route", response_model=CognitiveRoutingOutcomeResponse)
async def execute_cognitive_tier_route(
    payload: ExecuteTierRoutingRequest,
    router_svc: Annotated[CognitiveModelRouterService, Depends(get_cognitive_router_service)],
) -> CognitiveRoutingOutcomeResponse:
    """Execute cognitive tier routing and auto escalation (`Story 8.2`, `AD-21.4`)."""

    def _gate_fn(_content: str, tier: ResolvedInferenceTier) -> tuple[bool, str]:
        if payload.fail_simple_tier_gate and tier == "simple":
            return False, "Simple tier deterministic schema gate failed"
        return True, ""

    outcome = await router_svc.execute_with_tier_routing(
        run_id=payload.run_id,
        step_execution_id=payload.step_execution_id,
        scope_id=payload.scope_id,
        system_prompt=payload.system_prompt,
        user_prompt=payload.user_prompt,
        inference_tier=payload.inference_tier,
        effort=payload.effort,
        evaluator_model_family=payload.evaluator_model_family,
        deterministic_gate_fn=_gate_fn,
    )
    return to_routing_outcome_response(outcome)


@router.get("/reindex-status", response_model=RagReindexStatusResponse)
async def get_reindex_status(request: Request) -> RagReindexStatusResponse:
    """Get current status of vector corpus reindexing (`Story 19.7`, `AD-24.7`)."""
    return await fetch_reindex_status_response(request)


@router.post("/reindex-embeddings", response_model=RagReindexTriggerResponse)
async def trigger_reindex_embeddings(
    request: Request,
    user: Annotated[UserIdentity, Depends(require_ai_models_platform_admin)],
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
) -> RagReindexTriggerResponse:
    """Trigger a global reindexing of all document chunks on active embedding model."""
    return await trigger_manual_reindex_embeddings(request, auth_svc, hub_svc, actor_id=user.id)


__all__ = ["router", "test_ai_model_connection"]
