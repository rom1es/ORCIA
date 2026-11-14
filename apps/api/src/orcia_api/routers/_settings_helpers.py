"""Shared serialization and guard helpers for `settings_and_studio.py` (`< 400`-line hygiene)."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Request

from orcia_api.schemas.problem_details import ProblemDetails
from orcia_api.schemas.settings_and_studio import (
    CognitiveRoutingOutcomeResponse,
    InferenceAttemptResponse,
    LlmTierMappingResponse,
    PlatformSettingResponse,
    RolePermissionGrantResponse,
    SecretStatusResponse,
)
from orcia_core.orchestration import CognitiveRoutingOutcome, WorkspaceLlmTierMapping
from orcia_core.permissions import PlatformSettingRecord, RolePermissionGrant
from orcia_core.permissions.errors import ObserverModeReadOnlyError

SETTINGS_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    412: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    428: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}


def is_pg_bootstrap_enabled() -> bool:
    return os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1"


def enforce_not_observer_mode(request: Request) -> None:
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or observer_hdr in ("1", "true", "yes")
        or active_hat == "OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))


def serialize_grant(g: RolePermissionGrant) -> RolePermissionGrantResponse:
    return RolePermissionGrantResponse(
        id=g.id,
        subject_type=g.subject_type,
        subject_id=g.subject_id,
        scope_path=g.scope_path,
        verb=g.verb,
        effect=g.effect,
        inheritance_block=g.inheritance_block,
        resource_kind=g.resource_kind,
        conditions=g.conditions,
        hidden_when_unauthorized=g.hidden_when_unauthorized,
        granted_by_user_id=g.granted_by_user_id,
        created_at_iso=g.created_at_iso,
    )


def to_setting_response(rec: PlatformSettingRecord) -> PlatformSettingResponse:
    return PlatformSettingResponse(
        id=rec.id,
        scope_level=rec.scope_level,
        scope_id=rec.scope_id,
        category=rec.category,
        key=rec.key,
        value_jsonb=rec.value_jsonb,
        secret_status=SecretStatusResponse(
            configured=rec.secret_status.configured,
            fingerprint=rec.secret_status.fingerprint,
            updated_at=rec.secret_status.updated_at,
            updated_by=rec.secret_status.updated_by,
        ),
        version=rec.version,
        etag=rec.etag,
        updated_at=rec.updated_at,
        updated_by=rec.updated_by,
    )


def to_llm_mapping_response(m: WorkspaceLlmTierMapping) -> LlmTierMappingResponse:
    return LlmTierMappingResponse(
        id=m.id,
        scope_level=m.scope_level,
        scope_id=m.scope_id,
        inference_tier=m.inference_tier,
        effort=m.effort,
        provider_slug=m.provider_slug,
        model_family=m.model_family,
        model_name=m.model_name,
        max_tokens_budget=m.max_tokens_budget,
        max_cost_usd=m.max_cost_usd,
        fallback_order=m.fallback_order,
        is_active=m.is_active,
        draining=m.draining,
    )


def to_routing_outcome_response(
    outcome: CognitiveRoutingOutcome,
) -> CognitiveRoutingOutcomeResponse:
    return CognitiveRoutingOutcomeResponse(
        run_id=outcome.run_id,
        step_execution_id=outcome.step_execution_id,
        requested_tier=outcome.requested_tier,
        final_resolved_tier=outcome.final_resolved_tier,
        effort=outcome.effort,
        response_content=outcome.response_content,
        model_family=outcome.model_family,
        model_name=outcome.model_name,
        attempts=[
            InferenceAttemptResponse(
                id=a.id,
                attempt_index=a.attempt_index,
                requested_tier=a.requested_tier,
                resolved_tier=a.resolved_tier,
                effort=a.effort,
                model_family=a.model_family,
                model_name=a.model_name,
                deterministic_gate_passed=a.deterministic_gate_passed,
                failure_reason=a.failure_reason,
                cost_usd=a.cost_usd,
                idempotency_key=a.idempotency_key,
            )
            for a in outcome.attempts
        ],
        total_cost_usd=outcome.total_cost_usd,
        paused_budget_exceeded=outcome.paused_budget_exceeded,
    )
