"""AI Models Hub Domain Records & Value Objects (`Story 17.5`, `AD-21`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from orcia_core.permissions.secret_hint import SecretStatusView

ScopeLevel = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
InferenceTier = Literal["simple", "medium", "complex", "auto"]
InferenceEffort = Literal["default", "fast", "balanced", "deep"]
LlmAuthMode = Literal["api_key", "env_var", "none_local"]
LlmProtocolMode = Literal["openai_compatible", "gemini_native", "anthropic_messages"]
HealthStatus = Literal["OPERATIONAL", "DEGRADED", "ERROR", "UNTESTED"]
PinRemovalMode = Literal["reject", "drain", "force"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class AiModelMappingRecord:
    """Full domain entity for an AI Model mapping (`AD-21`, `Story 17.5`)."""

    id: str
    scope_level: ScopeLevel
    scope_id: str
    display_name: str
    inference_tier: InferenceTier
    effort: InferenceEffort
    provider_slug: str
    model_family: str
    model_name: str
    fallback_model_name: str | None = None
    endpoint_uri: str = ""
    auth_mode: LlmAuthMode = "api_key"
    protocol_mode: LlmProtocolMode = "openai_compatible"
    env_var_name: str | None = None
    fallback_order: int = 1
    max_tokens_budget: int = 8192
    max_cost_usd: float = 10.0
    is_active: bool = True
    draining: bool = False
    health_status: HealthStatus = "UNTESTED"
    last_tested_at: str | None = None
    last_latency_ms: int | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    secret_status: SecretStatusView = field(
        default_factory=lambda: SecretStatusView(configured=False)
    )
    encrypted_api_key: str | None = None


@dataclass(frozen=True, slots=True)
class AiModelDeleteImpact:
    """Pre-deletion impact analysis on published workflows and DBOS runs (`Story 17.5`)."""

    mapping_id: str
    inference_tier: InferenceTier
    model_name: str
    remaining_active_for_tier: int
    dependent_workflows_count: int
    dependent_workflow_ids: tuple[str, ...]
    pinned_active_runs_count: int
    pinned_run_ids: tuple[str, ...]
    is_last_active_for_tier: bool


__all__ = [
    "AiModelDeleteImpact",
    "AiModelMappingRecord",
    "HealthStatus",
    "InferenceEffort",
    "InferenceTier",
    "LlmAuthMode",
    "LlmProtocolMode",
    "PinRemovalMode",
    "ScopeLevel",
]
