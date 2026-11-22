"""Helper functions and response mappers for AI Models Hub router (`Story 17.5`)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Annotated, Literal
from urllib.parse import urlparse

from fastapi import Query, Request

from orcia_api.dependencies._llm_streaming_providers import get_or_create_async_http_client
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.ai_models_hub import (
    AiModelDiscoveryResponse,
    AiModelMappingItemResponse,
    AiModelTestResponse,
    DiscoveredModelItem,
    LlmProtocolModeLiteral,
)
from orcia_api.schemas.settings_and_studio import SecretStatusResponse
from orcia_core.orchestration import (
    AiModelMappingRecord,
    AiModelsHubService,
    discover_models_from_provider,
    get_ai_model_mapping_pg18,
    test_ai_model_endpoint_connection,
    validate_safe_llm_endpoint_url,
)
from orcia_core.permissions import AuthAndOrganizationService, UserIdentity
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError


def assert_ai_models_write_allowed(request: Request, persona_key: str | None = None) -> None:
    """Enforce read-only observer protection on AI models mutations."""
    path = str(request.url.path)
    if (
        request.headers.get("x-orcia-access-mode", "").strip().upper() == "READ_ONLY_OBSERVER"
        or request.headers.get("x-orcia-observer", "").strip().lower() in ("1", "true", "yes")
        or request.headers.get("x-orcia-observer-mode", "").strip().lower() in ("1", "true", "yes")
        or request.headers.get("x-orcia-active-hat", "").strip().upper()
        in ("OBSERVER", "READ_ONLY_OBSERVER")
        or persona_key == "observer"
    ):
        raise ObserverModeReadOnlyError(instance=path)


def require_ai_models_platform_admin(
    request: Request,
    actor_persona: Annotated[str | None, Query()] = None,
    persona_key: Annotated[str | None, Query()] = None,
) -> UserIdentity:
    """Resolve authenticated identity via `resolve_request_user` and enforce `PLATFORM_ADMIN`."""
    path = str(request.url.path)
    assert_ai_models_write_allowed(request, actor_persona or persona_key)
    has_bearer = bool(request.headers.get("Authorization"))
    effective_persona = (
        None
        if has_bearer
        else (
            actor_persona
            or persona_key
            or request.headers.get("x-orcia-persona", "").strip()
            or None
        )
    )
    user = resolve_request_user(request, persona_key=effective_persona)
    if user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER"):
        raise ObserverModeReadOnlyError(instance=path)
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    is_platform_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    if not is_platform_admin or (active_hat and active_hat != "PLATFORM_ADMIN"):
        raise ScopeAccessDeniedError(instance=path)
    return user


def to_item_response(m: AiModelMappingRecord) -> AiModelMappingItemResponse:
    """Serialize domain model mapping record to OpenAPI response with zero secret leakage."""
    return AiModelMappingItemResponse(
        id=m.id,
        scope_level=m.scope_level,
        scope_id=m.scope_id,
        display_name=m.display_name,
        inference_tier=m.inference_tier,
        effort=m.effort,
        provider_slug=m.provider_slug,
        model_family=m.model_family,
        model_name=m.model_name,
        fallback_model_name=m.fallback_model_name,
        endpoint_uri=m.endpoint_uri,
        auth_mode=m.auth_mode,
        protocol_mode=m.protocol_mode,
        usage=m.usage,
        env_var_name=m.env_var_name,
        fallback_order=m.fallback_order,
        max_tokens_budget=m.max_tokens_budget,
        max_cost_usd=m.max_cost_usd,
        is_active=m.is_active,
        draining=m.draining,
        health_status=m.health_status,
        last_tested_at=m.last_tested_at,
        last_latency_ms=m.last_latency_ms,
        created_at=m.created_at,
        updated_at=m.updated_at,
        secret_status=SecretStatusResponse(
            configured=m.secret_status.configured,
            fingerprint=m.secret_status.fingerprint,
            masked_hint=m.secret_status.masked_hint,
            updated_at=m.secret_status.updated_at,
            updated_by=m.secret_status.updated_by,
        ),
    )


async def execute_model_connection_test(
    rec: AiModelMappingRecord,
    decrypted_key: str | None,
    request: Request,
) -> tuple[Literal["OPERATIONAL", "DEGRADED", "ERROR", "UNTESTED"], AiModelTestResponse]:
    """Execute real non-blocking connectivity test for chat or embedding model."""
    path = str(request.url.path)
    validate_safe_llm_endpoint_url(rec.endpoint_uri, instance=path)

    effective_key = decrypted_key
    if rec.auth_mode == "env_var" and rec.env_var_name:
        effective_key = os.environ.get(rec.env_var_name)

    http_client = get_or_create_async_http_client(request)
    outcome = await test_ai_model_endpoint_connection(
        http_client=http_client,
        endpoint_uri=rec.endpoint_uri,
        protocol_mode=rec.protocol_mode,
        model_name=rec.model_name,
        usage=rec.usage,
        api_key=effective_key,
        provider_slug=rec.provider_slug,
        instance=path,
    )

    is_fr = "fr" in request.headers.get("accept-language", "").lower()
    msg = outcome.message_fr if is_fr else outcome.message_en
    resp = AiModelTestResponse(
        mapping_id=rec.id,
        health_status="OPERATIONAL",
        latency_ms=outcome.latency_ms,
        tested_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        message=msg,
    )
    return "OPERATIONAL", resp


def compute_tiers_coverage(records: list[AiModelMappingRecord]) -> dict[str, bool]:
    """Compute 4-tier active coverage dictionary (`simple`, `medium`, `complex`, `auto`)."""
    return {
        tier: any(r.inference_tier == tier and r.is_active and not r.draining for r in records)
        for tier in ("simple", "medium", "complex", "auto")
    }


async def resolve_mapping_decrypted_key(
    request: Request,
    mapping_id: str,
    auth_svc: AuthAndOrganizationService,
    hub_svc: AiModelsHubService,
) -> tuple[AiModelMappingRecord, str | None]:
    """Resolve model mapping record and decrypt its API key if configured."""
    path = str(request.url.path)
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        async with engine.begin() as conn:
            rec = await get_ai_model_mapping_pg18(conn, mapping_id, instance=path)
            decrypted_key: str | None = None
            if rec.encrypted_api_key:
                host = urlparse(rec.endpoint_uri).netloc or "default"
                parts = rec.encrypted_api_key.split(":", 1)
                decrypted_key = auth_svc.vault_cipher.decrypt(
                    rec.id, parts[0], parts[1], connector_scheme="llm", target_host=host
                )
            elif rec.auth_mode == "env_var" and rec.env_var_name:
                decrypted_key = os.environ.get(rec.env_var_name)
            return rec, decrypted_key

    rec = hub_svc.get_mapping(mapping_id, instance=path)
    decrypted_key = hub_svc.resolve_decrypted_api_key(mapping_id, instance=path)
    if not decrypted_key and rec.auth_mode == "env_var" and rec.env_var_name:
        decrypted_key = os.environ.get(rec.env_var_name)
    return rec, decrypted_key


async def execute_models_discovery(
    request: Request,
    *,
    endpoint_uri: str,
    protocol_mode: LlmProtocolModeLiteral,
    provider_slug: str | None,
    api_key: str | None,
) -> AiModelDiscoveryResponse:
    """Execute dynamic model discovery over shared httpx client with 0 tokens consumed."""
    client = get_or_create_async_http_client(request)
    path = str(request.url.path)
    raw_models = await discover_models_from_provider(
        http_client=client,
        endpoint_uri=endpoint_uri,
        protocol_mode=protocol_mode,
        provider_slug=provider_slug,
        api_key=api_key,
        instance=path,
    )

    items = [
        DiscoveredModelItem(
            id=m.id,
            display_name=m.display_name,
            description=m.description,
            usage_hint=m.usage_hint,
            owned_by=m.owned_by,
        )
        for m in raw_models
    ]
    return AiModelDiscoveryResponse(
        endpoint_uri=endpoint_uri,
        protocol_mode=protocol_mode,
        provider_slug=provider_slug,
        models=items,
        total_count=len(items),
    )


__all__ = [
    "assert_ai_models_write_allowed",
    "compute_tiers_coverage",
    "execute_model_connection_test",
    "execute_models_discovery",
    "require_ai_models_platform_admin",
    "resolve_mapping_decrypted_key",
    "to_item_response",
]
