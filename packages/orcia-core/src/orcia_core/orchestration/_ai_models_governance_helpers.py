"""Creation & Update Record Builders for `AiModelsHubService` (`Story 17.5`, `Story 26.6a`)."""

from __future__ import annotations

from dataclasses import replace
from urllib.parse import urlparse

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


def deactivate_other_inmemory_embeddings(
    mappings: dict[str, AiModelMappingRecord],
    *,
    now_iso: str,
    exclude_id: str | None = None,
) -> None:
    """Deactivate existing active GLOBAL embedding mappings in memory."""
    for existing_id, existing_rec in list(mappings.items()):
        if (
            existing_id != exclude_id
            and existing_rec.usage == "embedding"
            and existing_rec.scope_level == "GLOBAL"
            and existing_rec.is_active
        ):
            mappings[existing_id] = replace(existing_rec, is_active=False, updated_at=now_iso)


def build_inmemory_mapping_record(
    *,
    cipher: PassthroughVaultCipher,
    now_iso: str,
    scope_level: ScopeLevel,
    scope_id: str,
    display_name: str,
    inference_tier: InferenceTier,
    effort: InferenceEffort,
    provider_slug: str,
    model_family: str,
    model_name: str,
    fallback_model_name: str | None,
    endpoint_uri: str,
    auth_mode: LlmAuthMode,
    protocol_mode: LlmProtocolMode,
    usage: LlmModelUsage,
    env_var_name: str | None,
    fallback_order: int,
    max_tokens_budget: int,
    max_cost_usd: float,
    secret_input: SecretInputSpec | None,
    supports_tools: bool | None,
    supports_tools_override: bool | None,
    actor_id: str,
    instance: str | None,
) -> AiModelMappingRecord:
    """Validate SSRF/embedding rules and build a new `AiModelMappingRecord`."""
    clean_url = validate_safe_llm_endpoint_url(endpoint_uri, instance=instance)
    if usage == "embedding":
        assert_embedding_usage_supported(provider_slug=provider_slug, protocol_mode=protocol_mode)
    mapping_id = new_uuid7_str()
    host = urlparse(clean_url).netloc or "default"
    init_sec = SecretStatusView(
        configured=False,
        fingerprint=None,
        masked_hint=None,
        updated_at=now_iso,
        updated_by=actor_id,
    )
    sec_status, encrypted_key = apply_ai_model_secret_input(
        cipher,
        mapping_id=mapping_id,
        target_host=host,
        current_status=init_sec,
        current_encrypted_key=None,
        secret_input=secret_input if auth_mode == "api_key" else None,
        now_iso=now_iso,
        actor_id=actor_id,
    )
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
    effective_tools = (
        supports_tools_override if supports_tools_override is not None else detected_tools
    )
    return AiModelMappingRecord(
        id=mapping_id,
        scope_level=scope_level,
        scope_id=scope_id,
        display_name=display_name.strip() or f"{provider_slug} / {model_name}",
        inference_tier=inference_tier,
        effort=effort,
        provider_slug=provider_slug,
        model_family=model_family,
        model_name=model_name,
        fallback_model_name=fallback_model_name,
        endpoint_uri=clean_url,
        auth_mode=auth_mode,
        protocol_mode=protocol_mode,
        usage=usage,
        env_var_name=env_var_name,
        fallback_order=fallback_order,
        max_tokens_budget=max_tokens_budget,
        max_cost_usd=max_cost_usd,
        is_active=True,
        draining=False,
        health_status="UNTESTED",
        created_at=now_iso,
        updated_at=now_iso,
        secret_status=sec_status,
        encrypted_api_key=encrypted_key,
        supports_tools=effective_tools,
        supports_tools_detected=detected_tools,
        supports_tools_override=supports_tools_override,
    )


def apply_inmemory_mapping_update(
    *,
    mappings: dict[str, AiModelMappingRecord] | None = None,
    cipher: PassthroughVaultCipher,
    current: AiModelMappingRecord,
    now_iso: str,
    display_name: str | None,
    fallback_model_name: str | None,
    endpoint_uri: str | None,
    auth_mode: LlmAuthMode | None,
    protocol_mode: LlmProtocolMode | None,
    usage: LlmModelUsage | None,
    env_var_name: str | None,
    is_active: bool | None,
    secret_input: SecretInputSpec | None,
    supports_tools: bool | None,
    supports_tools_override: bool | None,
    clear_supports_tools_override: bool,
    actor_id: str,
    instance: str | None,
) -> AiModelMappingRecord:
    """Apply validated updates (including `supports_tools_override`) onto `current`."""
    effective_usage = usage if usage is not None else current.usage
    effective_protocol = protocol_mode if protocol_mode is not None else current.protocol_mode
    effective_active = is_active if is_active is not None else current.is_active
    if effective_usage == "embedding":
        assert_embedding_usage_supported(
            provider_slug=current.provider_slug, protocol_mode=effective_protocol
        )
        if effective_active and current.scope_level == "GLOBAL" and mappings is not None:
            deactivate_other_inmemory_embeddings(mappings, now_iso=now_iso, exclude_id=current.id)
    clean_url = (
        validate_safe_llm_endpoint_url(endpoint_uri, instance=instance)
        if endpoint_uri is not None
        else current.endpoint_uri
    )
    host = urlparse(clean_url).netloc or "default"
    sec_status, encrypted_key = apply_ai_model_secret_input(
        cipher,
        mapping_id=current.id,
        target_host=host,
        current_status=current.secret_status,
        current_encrypted_key=current.encrypted_api_key,
        secret_input=secret_input,
        now_iso=now_iso,
        actor_id=actor_id,
    )
    new_detected = supports_tools if supports_tools is not None else current.supports_tools_detected
    new_override = (
        None
        if clear_supports_tools_override
        else (
            supports_tools_override
            if supports_tools_override is not None
            else current.supports_tools_override
        )
    )
    new_effective = new_override if new_override is not None else new_detected
    return replace(
        current,
        display_name=display_name.strip() if display_name is not None else current.display_name,
        fallback_model_name=(
            fallback_model_name if fallback_model_name is not None else current.fallback_model_name
        ),
        endpoint_uri=clean_url,
        auth_mode=auth_mode if auth_mode is not None else current.auth_mode,
        protocol_mode=protocol_mode if protocol_mode is not None else current.protocol_mode,
        usage=usage if usage is not None else current.usage,
        env_var_name=env_var_name if env_var_name is not None else current.env_var_name,
        is_active=is_active if is_active is not None else current.is_active,
        updated_at=now_iso,
        secret_status=sec_status,
        encrypted_api_key=encrypted_key,
        supports_tools=new_effective,
        supports_tools_detected=new_detected,
        supports_tools_override=new_override,
    )


def apply_inmemory_test_result(
    current: AiModelMappingRecord,
    *,
    health_status: HealthStatus,
    latency_ms: int,
    supports_tools: bool | None,
    now_iso: str,
) -> AiModelMappingRecord:
    """Apply connection-test health, latency, and detected `supports_tools` onto `current`."""
    new_detected = supports_tools if supports_tools is not None else current.supports_tools_detected
    new_effective = (
        current.supports_tools_override
        if current.supports_tools_override is not None
        else new_detected
    )
    return replace(
        current,
        health_status=health_status,
        last_latency_ms=latency_ms,
        last_tested_at=now_iso,
        updated_at=now_iso,
        supports_tools=new_effective,
        supports_tools_detected=new_detected,
    )
