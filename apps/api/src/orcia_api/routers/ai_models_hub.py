"""AI Models Hub Router (`/api/v1/settings/ai-models/*`, `Story 17.5`, `AD-21`).

Enforces:
- 6-verb RBAC & observer rejection (`403 ERR_OBSERVER_MODE_READ_ONLY`)
- Anti-SSRF guard (`422 ERR_UNSAFE_LLM_ENDPOINT_URL`)
- Write-only secret encryption with AES-256-GCM (`SecretStatus` + `masked_hint`)
- Pre-deletion impact analysis and drainage mode (`409`)
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_ai_models_hub_service,
    get_auth_service,
    get_cognitive_router_service,
)
from orcia_api.routers._ai_models_helpers import (
    assert_ai_models_write_allowed,
    compute_tiers_coverage,
    execute_model_connection_test,
    execute_models_discovery,
    resolve_mapping_decrypted_key,
    to_item_response,
)
from orcia_api.routers._settings_helpers import to_routing_outcome_response
from orcia_api.schemas.ai_models_hub import (
    AiModelCreateRequest,
    AiModelDeleteImpactResponse,
    AiModelDeleteResponse,
    AiModelDiscoverRequest,
    AiModelDiscoveryResponse,
    AiModelMappingItemResponse,
    AiModelMappingsListResponse,
    AiModelPatchRequest,
    AiModelTestResponse,
    InferenceTierLiteral,
    LlmModelUsageLiteral,
    LlmProtocolModeLiteral,
    PinRemovalModeLiteral,
    ScopeLevelLiteral,
)
from orcia_api.schemas.settings_and_studio import (
    CognitiveRoutingOutcomeResponse,
    ExecuteTierRoutingRequest,
)
from orcia_core.orchestration import (
    AiModelsHubService,
    CognitiveModelRouterService,
    ResolvedInferenceTier,
)
from orcia_core.orchestration._internal.sql_ai_model_mappings import (
    create_ai_model_mapping_pg18,
    delete_or_drain_ai_model_mapping_pg18,
    ensure_ai_model_mappings_schema_on_postgres18,
    evaluate_ai_model_delete_impact_pg18,
    list_ai_model_mappings_pg18,
    record_ai_model_test_result_pg18,
    update_ai_model_mapping_pg18,
)
from orcia_core.permissions import AuthAndOrganizationService, SecretInputSpec

router = APIRouter(prefix="/api/v1/settings/ai-models", tags=["settings-ai-models"])


@router.get("/mappings", response_model=AiModelMappingsListResponse)
async def list_ai_model_mappings(
    request: Request,
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    scope_level: Annotated[ScopeLevelLiteral | None, Query()] = None,
    scope_id: Annotated[str | None, Query()] = None,
    inference_tier: Annotated[InferenceTierLiteral | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    usage: Annotated[LlmModelUsageLiteral | None, Query()] = None,
) -> AiModelMappingsListResponse:
    """List configured AI model mappings with 4-tier coverage report."""
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
            records = await list_ai_model_mappings_pg18(
                conn,
                scope_level=scope_level,
                scope_id=scope_id,
                inference_tier=inference_tier,
                is_active=is_active,
                usage=usage,
            )
    else:
        records = hub_svc.list_mappings(
            scope_level=scope_level,
            scope_id=scope_id,
            inference_tier=inference_tier,
            is_active=is_active,
            usage=usage,
        )

    return AiModelMappingsListResponse(
        items=[to_item_response(r) for r in records],
        total_count=len(records),
        active_tiers_coverage=compute_tiers_coverage(records),
    )


@router.post("/mappings", response_model=AiModelMappingItemResponse, status_code=201)
async def create_ai_model_mapping(
    payload: AiModelCreateRequest,
    request: Request,
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    actor_persona: Annotated[str | None, Query()] = None,
) -> AiModelMappingItemResponse:
    """Connect a new AI model mapping with AES-256-GCM encrypted API key."""
    assert_ai_models_write_allowed(request, actor_persona)
    sec_input = (
        SecretInputSpec(
            action=payload.secret_input.action,
            plaintext_value=payload.secret_input.plaintext_value,
        )
        if payload.secret_input is not None
        else None
    )
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
            rec = await create_ai_model_mapping_pg18(
                conn,
                cipher=auth_svc.vault_cipher,
                scope_level=payload.scope_level,
                scope_id=payload.scope_id,
                display_name=payload.display_name,
                inference_tier=payload.inference_tier,
                effort=payload.effort,
                provider_slug=payload.provider_slug,
                model_family=payload.model_family,
                model_name=payload.model_name,
                fallback_model_name=payload.fallback_model_name,
                endpoint_uri=payload.endpoint_uri,
                auth_mode=payload.auth_mode,
                protocol_mode=payload.protocol_mode,
                usage=payload.usage,
                env_var_name=payload.env_var_name,
                fallback_order=payload.fallback_order,
                max_tokens_budget=payload.max_tokens_budget,
                max_cost_usd=payload.max_cost_usd,
                secret_input=sec_input,
                actor_id=actor_persona or "system",
                instance=str(request.url.path),
            )
    else:
        rec = hub_svc.create_mapping(
            scope_level=payload.scope_level,
            scope_id=payload.scope_id,
            display_name=payload.display_name,
            inference_tier=payload.inference_tier,
            effort=payload.effort,
            provider_slug=payload.provider_slug,
            model_family=payload.model_family,
            model_name=payload.model_name,
            fallback_model_name=payload.fallback_model_name,
            endpoint_uri=payload.endpoint_uri,
            auth_mode=payload.auth_mode,
            protocol_mode=payload.protocol_mode,
            usage=payload.usage,
            env_var_name=payload.env_var_name,
            fallback_order=payload.fallback_order,
            max_tokens_budget=payload.max_tokens_budget,
            max_cost_usd=payload.max_cost_usd,
            secret_input=sec_input,
            actor_id=actor_persona or "system",
            instance=str(request.url.path),
        )
    return to_item_response(rec)


@router.patch("/mappings/{mapping_id}", response_model=AiModelMappingItemResponse)
async def update_ai_model_mapping(
    mapping_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: AiModelPatchRequest,
    request: Request,
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    actor_persona: Annotated[str | None, Query()] = None,
) -> AiModelMappingItemResponse:
    """Update model settings or rotate/clear its API key."""
    assert_ai_models_write_allowed(request, actor_persona)
    sec_input = (
        SecretInputSpec(
            action=payload.secret_input.action,
            plaintext_value=payload.secret_input.plaintext_value,
        )
        if payload.secret_input is not None
        else None
    )
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
            rec = await update_ai_model_mapping_pg18(
                conn,
                mapping_id,
                cipher=auth_svc.vault_cipher,
                display_name=payload.display_name,
                fallback_model_name=payload.fallback_model_name,
                endpoint_uri=payload.endpoint_uri,
                auth_mode=payload.auth_mode,
                protocol_mode=payload.protocol_mode,
                usage=payload.usage,
                env_var_name=payload.env_var_name,
                is_active=payload.is_active,
                secret_input=sec_input,
                actor_id=actor_persona or "system",
                instance=str(request.url.path),
            )
    else:
        rec = hub_svc.update_mapping(
            mapping_id,
            display_name=payload.display_name,
            fallback_model_name=payload.fallback_model_name,
            endpoint_uri=payload.endpoint_uri,
            auth_mode=payload.auth_mode,
            protocol_mode=payload.protocol_mode,
            usage=payload.usage,
            env_var_name=payload.env_var_name,
            is_active=payload.is_active,
            secret_input=sec_input,
            actor_id=actor_persona or "system",
            instance=str(request.url.path),
        )
    return to_item_response(rec)


@router.post("/discover", response_model=AiModelDiscoveryResponse)
async def discover_ai_models_post(
    payload: AiModelDiscoverRequest,
    request: Request,
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    actor_persona: Annotated[str | None, Query()] = None,
) -> AiModelDiscoveryResponse:
    """Discover available models on provider endpoint without consuming inference tokens (`0 $`)."""
    assert_ai_models_write_allowed(request, actor_persona)
    effective_key = payload.api_key
    endpoint_uri = payload.endpoint_uri
    protocol_mode = payload.protocol_mode
    provider_slug = payload.provider_slug

    if payload.mapping_id and not effective_key:
        rec, decrypted_key = await resolve_mapping_decrypted_key(
            request, payload.mapping_id, auth_svc, hub_svc
        )
        effective_key = decrypted_key
        if not endpoint_uri:
            endpoint_uri = rec.endpoint_uri
        if not protocol_mode:
            protocol_mode = rec.protocol_mode
        if not provider_slug:
            provider_slug = rec.provider_slug

    return await execute_models_discovery(
        request,
        endpoint_uri=endpoint_uri,
        protocol_mode=protocol_mode,
        provider_slug=provider_slug,
        api_key=effective_key,
    )


@router.get("/discover", response_model=AiModelDiscoveryResponse)
async def discover_ai_models_get(
    request: Request,
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    base_url: Annotated[str, Query(alias="base_url", min_length=1, max_length=1024)],
    provider: Annotated[str | None, Query(alias="provider", max_length=64)] = None,
    protocol_mode: Annotated[LlmProtocolModeLiteral, Query()] = "openai_compatible",
    mapping_id: Annotated[str | None, Query(max_length=128)] = None,
    actor_persona: Annotated[str | None, Query()] = None,
) -> AiModelDiscoveryResponse:
    """GET discovery endpoint for local or existing models without sending secrets in URL."""
    assert_ai_models_write_allowed(request, actor_persona)
    effective_key: str | None = None
    if mapping_id:
        rec, decrypted_key = await resolve_mapping_decrypted_key(
            request, mapping_id, auth_svc, hub_svc
        )
        effective_key = decrypted_key
        if not provider:
            provider = rec.provider_slug

    return await execute_models_discovery(
        request,
        endpoint_uri=base_url,
        protocol_mode=protocol_mode,
        provider_slug=provider,
        api_key=effective_key,
    )


@router.post("/mappings/{mapping_id}/test", response_model=AiModelTestResponse)
async def test_ai_model_connection(
    mapping_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
) -> AiModelTestResponse:
    """Execute on-demand non-blocking connectivity test against model endpoint."""
    path = str(request.url.path)
    engine = getattr(request.app.state, "db_engine", None)
    rec, decrypted_key = await resolve_mapping_decrypted_key(request, mapping_id, auth_svc, hub_svc)
    health, resp = execute_model_connection_test(rec, decrypted_key, request)

    if engine is not None:
        async with engine.begin() as conn:
            await record_ai_model_test_result_pg18(
                conn, mapping_id, health_status=health, latency_ms=resp.latency_ms, instance=path
            )
    else:
        hub_svc.record_test_result(
            mapping_id, health_status=health, latency_ms=resp.latency_ms, instance=path
        )

    return resp


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
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    mode: Annotated[PinRemovalModeLiteral, Query()] = "reject",
    actor_role: Annotated[str, Query()] = "PLATFORM_ADMIN",
) -> AiModelDeleteResponse:
    """Delete or drain a mapping enforcing dependency & active run guards."""
    assert_ai_models_write_allowed(request)
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            await ensure_ai_model_mappings_schema_on_postgres18(conn)
            res = await delete_or_drain_ai_model_mapping_pg18(
                conn, mapping_id, mode=mode, actor_role=actor_role, instance=str(request.url.path)
            )
    else:
        res = hub_svc.delete_or_drain_mapping(
            mapping_id, mode=mode, actor_role=actor_role, instance=str(request.url.path)
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


__all__ = ["router"]
