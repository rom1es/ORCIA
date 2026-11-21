"""AI Models Hub Router (`/api/v1/settings/ai-models/*`, `Story 17.5`, `AD-21`).

Enforces:
- 6-verb RBAC & observer rejection (`403 ERR_OBSERVER_MODE_READ_ONLY`)
- Anti-SSRF guard (`422 ERR_UNSAFE_LLM_ENDPOINT_URL`)
- Write-only secret encryption with AES-256-GCM (`SecretStatus` + `masked_hint`)
- Pre-deletion impact analysis and drainage mode (`409`)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_ai_models_hub_service,
    get_auth_service,
)
from orcia_api.routers._ai_models_helpers import (
    compute_tiers_coverage,
    execute_models_discovery,
    require_ai_models_platform_admin,
    resolve_mapping_decrypted_key,
    to_item_response,
)
from orcia_api.routers._ai_models_reindex_helpers import (
    trigger_global_reindexing_job,
)
from orcia_api.routers._ai_models_test_and_reindex_routes import (
    router as test_and_reindex_router,
)
from orcia_api.routers._ai_models_test_and_reindex_routes import (
    test_ai_model_connection as test_ai_model_connection,
)
from orcia_api.schemas.ai_models_hub import (
    AiModelCreateRequest,
    AiModelDiscoverRequest,
    AiModelDiscoveryResponse,
    AiModelMappingItemResponse,
    AiModelMappingsListResponse,
    AiModelPatchRequest,
    InferenceTierLiteral,
    LlmModelUsageLiteral,
    LlmProtocolModeLiteral,
    ScopeLevelLiteral,
)
from orcia_core.orchestration import (
    AiModelsHubService,
)
from orcia_core.orchestration._internal.sql_ai_model_mappings import (
    create_ai_model_mapping_pg18,
    ensure_ai_model_mappings_schema_on_postgres18,
    list_ai_model_mappings_pg18,
    update_ai_model_mapping_pg18,
)
from orcia_core.permissions import AuthAndOrganizationService, SecretInputSpec, UserIdentity

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
    user: Annotated[UserIdentity, Depends(require_ai_models_platform_admin)],
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
) -> AiModelMappingItemResponse:
    """Connect a new AI model mapping with AES-256-GCM encrypted API key."""
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
                actor_id=user.id,
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
            actor_id=user.id,
            instance=str(request.url.path),
        )

    if rec.usage == "embedding" and rec.scope_level == "GLOBAL" and rec.is_active:
        await trigger_global_reindexing_job(
            request,
            rec,
            actor_id=user.id,
        )
    return to_item_response(rec)


@router.patch("/mappings/{mapping_id}", response_model=AiModelMappingItemResponse)
async def update_ai_model_mapping(
    mapping_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: AiModelPatchRequest,
    request: Request,
    user: Annotated[UserIdentity, Depends(require_ai_models_platform_admin)],
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
) -> AiModelMappingItemResponse:
    """Update model settings or rotate/clear its API key."""
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
                actor_id=user.id,
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
            actor_id=user.id,
            instance=str(request.url.path),
        )

    if rec.usage == "embedding" and rec.scope_level == "GLOBAL" and rec.is_active:
        await trigger_global_reindexing_job(
            request,
            rec,
            actor_id=user.id,
        )
    return to_item_response(rec)


@router.post("/discover", response_model=AiModelDiscoveryResponse)
async def discover_ai_models_post(
    payload: AiModelDiscoverRequest,
    request: Request,
    _user: Annotated[UserIdentity, Depends(require_ai_models_platform_admin)],
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
) -> AiModelDiscoveryResponse:
    """Discover available models on provider endpoint without consuming inference tokens (`0 $`)."""
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
    _user: Annotated[UserIdentity, Depends(require_ai_models_platform_admin)],
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[AiModelsHubService, Depends(get_ai_models_hub_service)],
    base_url: Annotated[str, Query(alias="base_url", min_length=1, max_length=1024)],
    provider: Annotated[str | None, Query(alias="provider", max_length=64)] = None,
    protocol_mode: Annotated[LlmProtocolModeLiteral, Query()] = "openai_compatible",
    mapping_id: Annotated[str | None, Query(max_length=128)] = None,
) -> AiModelDiscoveryResponse:
    """GET discovery endpoint for local or existing models without sending secrets in URL."""
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


router.include_router(test_and_reindex_router)

__all__ = ["router", "test_ai_model_connection"]
