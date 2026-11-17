"""Dataclasses, types and records for the cognitive tier router (`Story 8.2`, `Story 6.2`).

Extracted to enforce strict module size (< 300 lines).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_kernel.secret_ports import SecretRef

InferenceTier = Literal["simple", "medium", "complex", "auto"]
ResolvedInferenceTier = Literal["simple", "medium", "complex"]
InferenceEffort = Literal["default", "fast", "balanced", "deep"]
PinRemovalMode = Literal["reject", "drain", "force"]

EFFORT_TOKEN_MULTIPLIER: dict[InferenceEffort, float] = {
    "fast": 0.6,
    "default": 1.0,
    "balanced": 1.25,
    "deep": 1.75,
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class WorkspaceLlmTierMapping:
    """Mapping between an abstract `(inference_tier, effort)` and a physical model (`Story 8.2`)."""

    id: str
    scope_level: Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
    scope_id: str
    inference_tier: ResolvedInferenceTier
    effort: InferenceEffort
    provider_slug: str
    model_family: str
    model_name: str
    secret_ref: SecretRef | None = None
    max_tokens_budget: int = 8192
    max_cost_usd: float = 10.0
    fallback_order: int = 1
    is_active: bool = True
    draining: bool = False
    updated_at_iso: str = field(default_factory=now_iso)


@dataclass(frozen=True, slots=True)
class InferenceAttemptRecord:
    """Idempotent DBOS sub-step record in `inference_attempts` (`Story 8.2`, `AD-21`)."""

    id: str
    run_id: str
    step_execution_id: str
    attempt_index: int
    requested_tier: InferenceTier
    resolved_tier: ResolvedInferenceTier
    effort: InferenceEffort
    model_family: str
    model_name: str
    deterministic_gate_passed: bool
    failure_reason: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    idempotency_key: str
    response_content: str = ""
    created_at_iso: str = field(default_factory=now_iso)


@dataclass(frozen=True, slots=True)
class CognitiveRoutingOutcome:
    """Outcome of a cognitive tier invocation (single tier or `auto` escalation)."""

    run_id: str
    step_execution_id: str
    requested_tier: InferenceTier
    final_resolved_tier: ResolvedInferenceTier
    effort: InferenceEffort
    response_content: str
    model_family: str
    model_name: str
    attempts: tuple[InferenceAttemptRecord, ...]
    total_cost_usd: float
    paused_budget_exceeded: bool = False
    paused_max_retries: bool = False


@dataclass(frozen=True, slots=True)
class DurableProc01RunState:
    """End-to-end durable run state for `PROC-01` verification (`Story 8.2`)."""

    run_id: str
    workspace_id: str
    status: Literal[
        "RUNNING",
        "WAITING_FOR_HUMAN_ARBITRATION",
        "PAUSED_BUDGET_EXCEEDED",
        "PAUSED_MAX_RETRIES",
        "COMPLETED",
    ]
    step_1_outcome: CognitiveRoutingOutcome
    arbitration_resolution: str | None = None
    final_artifact: dict[str, Any] = field(default_factory=dict)
    replayed_after_restart: bool = False


def build_default_tier_mappings(
    workspace_id: str = "0195f000-0000-7000-8000-000000000301",
) -> tuple[WorkspaceLlmTierMapping, ...]:
    """Return default empty tier mappings for Day-0 state (D4)."""
    _ = workspace_id
    return ()


def make_paused_outcome(
    *,
    run_id: str,
    step_execution_id: str,
    requested_tier: InferenceTier,
    resolved_tier: ResolvedInferenceTier,
    effort: InferenceEffort,
    attempts: list[InferenceAttemptRecord],
    total_cost_usd: float,
    paused_budget_exceeded: bool = False,
    paused_max_retries: bool = False,
) -> CognitiveRoutingOutcome:
    """Build a CognitiveRoutingOutcome paused due to budget or retries limit."""
    return CognitiveRoutingOutcome(
        run_id=run_id,
        step_execution_id=step_execution_id,
        requested_tier=requested_tier,
        final_resolved_tier=resolved_tier,
        effort=effort,
        response_content="",
        model_family="none",
        model_name="none",
        attempts=tuple(attempts),
        total_cost_usd=total_cost_usd,
        paused_budget_exceeded=paused_budget_exceeded,
        paused_max_retries=paused_max_retries,
    )


__all__ = [
    "CognitiveRoutingOutcome",
    "DurableProc01RunState",
    "EFFORT_TOKEN_MULTIPLIER",
    "InferenceAttemptRecord",
    "InferenceEffort",
    "InferenceTier",
    "PinRemovalMode",
    "ResolvedInferenceTier",
    "WorkspaceLlmTierMapping",
    "build_default_tier_mappings",
    "make_paused_outcome",
    "now_iso",
]
