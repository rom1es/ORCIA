"""Helper functions and response mappers for AI Models Hub router (`Story 17.5`)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Literal

from fastapi import Request

from orcia_api.routers.assistant_llm_gemini_adapter import evaluate_welcome_llm_connection_test
from orcia_api.schemas.ai_models_hub import AiModelMappingItemResponse, AiModelTestResponse
from orcia_api.schemas.bootstrap import LlmConnectionTestRequest
from orcia_api.schemas.settings_and_studio import SecretStatusResponse
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration import AiModelMappingRecord, validate_safe_llm_endpoint_url
from orcia_core.permissions.errors import ObserverModeReadOnlyError


def assert_ai_models_write_allowed(request: Request, persona_key: str | None = None) -> None:
    """Enforce read-only observer protection on AI models mutations."""
    path = str(request.url.path)
    if (
        request.headers.get("x-orcia-access-mode", "").strip().upper() == "READ_ONLY_OBSERVER"
        or request.headers.get("x-orcia-observer", "").strip().lower() in ("1", "true", "yes")
        or request.headers.get("x-orcia-active-hat", "").strip().upper() == "OBSERVER"
        or persona_key == "observer"
    ):
        raise ObserverModeReadOnlyError(instance=path)


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


def execute_model_connection_test(
    rec: AiModelMappingRecord,
    decrypted_key: str | None,
    request: Request,
) -> tuple[Literal["OPERATIONAL", "DEGRADED", "ERROR", "UNTESTED"], AiModelTestResponse]:
    """Execute connectivity test with SSRF validation and return health status and response."""
    path = str(request.url.path)
    validate_safe_llm_endpoint_url(rec.endpoint_uri, instance=path)

    effective_key = decrypted_key
    if rec.auth_mode == "env_var" and rec.env_var_name:
        effective_key = os.environ.get(rec.env_var_name)

    test_req = LlmConnectionTestRequest(
        provider_slug=rec.provider_slug,
        model_name=rec.model_name,
        endpoint_uri=rec.endpoint_uri,
        auth_mode=rec.auth_mode,
        api_key=effective_key,
        api_key_configured=bool(effective_key or rec.auth_mode == "none_local"),
    )
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    outcome = evaluate_welcome_llm_connection_test(test_req, trace_id=trace_id)
    health: Literal["OPERATIONAL", "DEGRADED", "ERROR", "UNTESTED"] = (
        "OPERATIONAL" if outcome.ok else "ERROR"
    )
    is_fr = "fr" in request.headers.get("accept-language", "").lower()
    msg = outcome.message_fr if is_fr else outcome.message_en
    resp = AiModelTestResponse(
        mapping_id=rec.id,
        health_status=health,
        latency_ms=outcome.latency_ms,
        tested_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        message=msg,
    )
    return health, resp


def compute_tiers_coverage(records: list[AiModelMappingRecord]) -> dict[str, bool]:
    """Compute 4-tier active coverage dictionary (`simple`, `medium`, `complex`, `auto`)."""
    return {
        tier: any(r.inference_tier == tier and r.is_active and not r.draining for r in records)
        for tier in ("simple", "medium", "complex", "auto")
    }


__all__ = [
    "assert_ai_models_write_allowed",
    "compute_tiers_coverage",
    "execute_model_connection_test",
    "to_item_response",
]
