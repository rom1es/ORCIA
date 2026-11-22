"""PostgreSQL 18 mutation adapter for AI Model Mappings (`Story 17.5`, `AD-21`, `Story 26.6a`)."""

from __future__ import annotations

from urllib.parse import urlparse

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.orchestration._internal._sql_ai_model_delete_guards import (
    delete_or_drain_ai_model_mapping_pg18,
    evaluate_ai_model_delete_impact_pg18,
)
from orcia_core.orchestration._internal._sql_ai_model_helpers import (
    deactivate_other_global_embeddings,
    now_iso,
    secret_sql_params,
)
from orcia_core.orchestration._internal._sql_ai_model_helpers import (
    parse_iso_to_dt as _parse_iso_to_dt,
)
from orcia_core.orchestration._internal.sql_ai_model_queries import get_ai_model_mapping_pg18
from orcia_core.orchestration.ai_models_capabilities import infer_default_supports_tools
from orcia_core.orchestration.ai_models_crypto import (
    apply_ai_model_secret_input,
    validate_safe_llm_endpoint_url,
)
from orcia_core.orchestration.ai_models_records import (
    AiModelMappingRecord,
    HealthStatus,
    InferenceEffort,
    InferenceTier,
    LlmAuthMode,
    LlmModelUsage,
    LlmProtocolMode,
    ScopeLevel,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.secret_hint import SecretInputSpec, SecretStatusView
from orcia_core.rag.adapters.embedding_httpx import assert_embedding_usage_supported
from orcia_kernel.ids import new_uuid7_str


async def create_ai_model_mapping_pg18(
    conn: AsyncConnection,
    *,
    cipher: PassthroughVaultCipher,
    scope_level: ScopeLevel = "WORKSPACE",
    scope_id: str,
    display_name: str,
    inference_tier: InferenceTier,
    effort: InferenceEffort = "default",
    provider_slug: str,
    model_family: str,
    model_name: str,
    fallback_model_name: str | None = None,
    endpoint_uri: str,
    auth_mode: LlmAuthMode = "api_key",
    protocol_mode: LlmProtocolMode = "openai_compatible",
    usage: LlmModelUsage = "chat",
    env_var_name: str | None = None,
    fallback_order: int = 1,
    max_tokens_budget: int = 8192,
    max_cost_usd: float = 10.0,
    secret_input: SecretInputSpec | None = None,
    supports_tools: bool | None = None,
    supports_tools_override: bool | None = None,
    actor_id: str = "system",
    instance: str | None = None,
) -> AiModelMappingRecord:
    """Insert mapping with AES-256-GCM encrypted key, SSRF check & `supports_tools`."""
    clean_url = validate_safe_llm_endpoint_url(endpoint_uri, instance=instance)
    if usage == "embedding":
        assert_embedding_usage_supported(provider_slug=provider_slug, protocol_mode=protocol_mode)
        if scope_level == "GLOBAL":
            await deactivate_other_global_embeddings(conn)
    max_order_res = await conn.execute(
        sa.text(
            "SELECT COALESCE(MAX(fallback_order), 0) + 1 FROM workspace_llm_tier_mappings "
            "WHERE scope_id = :scope_id AND inference_tier = :tier AND effort = :effort"
        ),
        {"scope_id": scope_id, "tier": inference_tier, "effort": effort},
    )
    fallback_order = max(fallback_order, max_order_res.scalar() or 1)

    mapping_id, now = new_uuid7_str(), now_iso()
    host = urlparse(clean_url).netloc or "default"
    init_sec = SecretStatusView(configured=False, updated_at=now, updated_by=actor_id)
    sec_status, encrypted_key = apply_ai_model_secret_input(
        cipher,
        mapping_id=mapping_id,
        target_host=host,
        current_status=init_sec,
        current_encrypted_key=None,
        secret_input=secret_input if auth_mode == "api_key" else None,
        now_iso=now,
        actor_id=actor_id,
    )
    disp = display_name.strip() or f"{provider_slug} / {model_name}"
    detected_tools = (
        supports_tools
        if supports_tools is not None
        else infer_default_supports_tools(
            endpoint_uri=clean_url,
            protocol_mode=protocol_mode,
            provider_slug=provider_slug,
            usage=usage,
            model_name=model_name,
        )
    )

    await conn.execute(
        sa.text(
            "INSERT INTO workspace_llm_tier_mappings ("
            "id, scope_level, scope_id, inference_tier, effort, provider_slug, model_family, "
            "model_name, max_tokens_budget, max_cost_usd, fallback_order, is_active, draining, "
            "updated_at, display_name, fallback_model_name, endpoint_uri, auth_mode, "
            "protocol_mode, env_var_name, encrypted_api_key, secret_fingerprint, "
            "secret_masked_hint, secret_updated_at, secret_updated_by, health_status, "
            "created_at, usage, supports_tools, supports_tools_override) VALUES ("
            ":id, :scope_level, :scope_id, :inference_tier, :effort, :provider_slug, "
            ":model_family, :model_name, :max_tokens_budget, :max_cost_usd, :fallback_order, "
            "TRUE, FALSE, NOW(), :display_name, :fallback_model_name, :endpoint_uri, :auth_mode, "
            ":protocol_mode, :env_var_name, :encrypted_api_key, :secret_fingerprint, "
            ":secret_masked_hint, :secret_updated_at, :secret_updated_by, 'UNTESTED', NOW(), "
            ":usage, :supports_tools, :supports_tools_override)"
        ),
        {
            "id": mapping_id,
            "scope_level": scope_level,
            "scope_id": scope_id,
            "inference_tier": inference_tier,
            "effort": effort,
            "provider_slug": provider_slug,
            "model_family": model_family,
            "model_name": model_name,
            "max_tokens_budget": max_tokens_budget,
            "max_cost_usd": max_cost_usd,
            "fallback_order": fallback_order,
            "display_name": disp,
            "fallback_model_name": fallback_model_name,
            "endpoint_uri": clean_url,
            "auth_mode": auth_mode,
            "protocol_mode": protocol_mode,
            "usage": usage,
            "env_var_name": env_var_name,
            "supports_tools": detected_tools,
            "supports_tools_override": supports_tools_override,
            **secret_sql_params(sec_status, encrypted_key),
        },
    )
    return await get_ai_model_mapping_pg18(conn, mapping_id, instance=instance)


async def update_ai_model_mapping_pg18(
    conn: AsyncConnection,
    mapping_id: str,
    *,
    cipher: PassthroughVaultCipher,
    display_name: str | None = None,
    fallback_model_name: str | None = None,
    endpoint_uri: str | None = None,
    auth_mode: LlmAuthMode | None = None,
    protocol_mode: LlmProtocolMode | None = None,
    usage: LlmModelUsage | None = None,
    env_var_name: str | None = None,
    is_active: bool | None = None,
    secret_input: SecretInputSpec | None = None,
    supports_tools: bool | None = None,
    supports_tools_override: bool | None = None,
    clear_supports_tools_override: bool = False,
    actor_id: str = "system",
    instance: str | None = None,
) -> AiModelMappingRecord:
    """Update existing mapping with conditional key rotation, SSRF check & `supports_tools`."""
    current = await get_ai_model_mapping_pg18(conn, mapping_id, instance=instance)
    now = now_iso()
    effective_usage = usage if usage is not None else current.usage
    effective_protocol = protocol_mode if protocol_mode is not None else current.protocol_mode
    effective_active = is_active if is_active is not None else current.is_active

    if effective_usage == "embedding":
        assert_embedding_usage_supported(
            provider_slug=current.provider_slug, protocol_mode=effective_protocol
        )
        if effective_active and current.scope_level == "GLOBAL":
            await deactivate_other_global_embeddings(conn, exclude_id=mapping_id)

    clean_url = (
        validate_safe_llm_endpoint_url(endpoint_uri, instance=instance)
        if endpoint_uri is not None
        else current.endpoint_uri
    )
    host = urlparse(clean_url).netloc or "default"
    sec_status, encrypted_key = apply_ai_model_secret_input(
        cipher,
        mapping_id=mapping_id,
        target_host=host,
        current_status=current.secret_status,
        current_encrypted_key=current.encrypted_api_key,
        secret_input=secret_input,
        now_iso=now,
        actor_id=actor_id,
    )
    override_clause = (
        "supports_tools_override = NULL, "
        if clear_supports_tools_override
        else (
            "supports_tools_override = "
            "COALESCE(:supports_tools_override, supports_tools_override), "
        )
    )
    await conn.execute(
        sa.text(
            "UPDATE workspace_llm_tier_mappings SET "
            "display_name = COALESCE(:display_name, display_name), "
            "fallback_model_name = COALESCE(:fallback_model_name, fallback_model_name), "
            "endpoint_uri = :endpoint_uri, auth_mode = COALESCE(:auth_mode, auth_mode), "
            "protocol_mode = COALESCE(:protocol_mode, protocol_mode), "
            "usage = COALESCE(:usage, usage), "
            "env_var_name = COALESCE(:env_var_name, env_var_name), "
            "is_active = COALESCE(:is_active, is_active), "
            "supports_tools = COALESCE(:supports_tools, supports_tools), "
            f"{override_clause}"
            "encrypted_api_key = :encrypted_api_key, "
            "secret_fingerprint = :secret_fingerprint, "
            "secret_masked_hint = :secret_masked_hint, "
            "secret_updated_at = :secret_updated_at, "
            "secret_updated_by = :secret_updated_by, updated_at = NOW() WHERE id = :id"
        ),
        {
            "id": mapping_id,
            "display_name": display_name.strip() if display_name is not None else None,
            "fallback_model_name": fallback_model_name,
            "endpoint_uri": clean_url,
            "auth_mode": auth_mode,
            "protocol_mode": protocol_mode,
            "usage": usage,
            "env_var_name": env_var_name,
            "is_active": is_active,
            "supports_tools": supports_tools,
            **(
                {}
                if clear_supports_tools_override
                else {"supports_tools_override": supports_tools_override}
            ),
            **secret_sql_params(sec_status, encrypted_key),
        },
    )
    return await get_ai_model_mapping_pg18(conn, mapping_id, instance=instance)


async def record_ai_model_test_result_pg18(
    conn: AsyncConnection,
    mapping_id: str,
    *,
    health_status: HealthStatus,
    latency_ms: int,
    supports_tools: bool | None = None,
    instance: str | None = None,
) -> AiModelMappingRecord:
    """Record async connection test outcome and `supports_tools` probe in PostgreSQL 18."""
    await conn.execute(
        sa.text(
            "UPDATE workspace_llm_tier_mappings SET health_status = :health_status, "
            "last_latency_ms = :latency_ms, last_tested_at = NOW(), updated_at = NOW(), "
            "supports_tools = COALESCE(:supports_tools, supports_tools) "
            "WHERE id = :id"
        ),
        {
            "id": mapping_id,
            "health_status": health_status,
            "latency_ms": latency_ms,
            "supports_tools": supports_tools,
        },
    )
    return await get_ai_model_mapping_pg18(conn, mapping_id, instance=instance)


__all__ = [
    "_parse_iso_to_dt",
    "create_ai_model_mapping_pg18",
    "delete_or_drain_ai_model_mapping_pg18",
    "evaluate_ai_model_delete_impact_pg18",
    "record_ai_model_test_result_pg18",
    "update_ai_model_mapping_pg18",
]
