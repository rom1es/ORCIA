"""3-Speed Conversational Models (`Story 10.2`, `Story 26.1`, `Story 26.4a`)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from orcia_core.orchestration.assistant_governance_models import AssembledLayerPreviewItem

PROMPT_CACHE_TTL_SECONDS: int = 0
MAX_NODES_1_TO_4_DETERMINISTIC_MS: float = 80.0
SPEED_1_TTFT_SLO_MS: float = 1200.0
SPEED_2_TTFT_SLO_MS: float = 2500.0

AssistantSpeedMode = Literal["SPEED_1_FAST", "SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"]
PromptCacheInvalidationReason = Literal[
    "SETTINGS_CHANGED",
    "OVERRIDE_UPDATED",
    "GLOSSARY_PROMOTED",
]

_AGENT_OR_SKILL_PATTERN = re.compile(r"(?:^|\s)(@[a-zA-Z0-9_-]+|/[a-zA-Z0-9_-]+)")


def build_assistant_prompt_cache_key(workspace_id: str, user_id: str, hat: str) -> str:
    """Build canonical prompt context key `assistant:prompt:<workspace_id>:<user_id>:<hat>`."""
    norm_hat = hat.strip().upper() or "PM"
    return f"assistant:prompt:{workspace_id}:{user_id}:{norm_hat}"


@dataclass(frozen=True, slots=True)
class CachedAssembledPromptResult:
    """5-layer prompt assembled directly without caching under `R6` (`Story 26.4a`)."""

    cache_key: str
    cache_hit: bool
    ttl_seconds: int
    lookup_latency_ms: float
    assembled_prompt_text: str
    layers_sha256: str
    layers: tuple[AssembledLayerPreviewItem, ...]


@dataclass(frozen=True, slots=True)
class PromptCacheInvalidationOutcome:
    """No-op outcome returned by legacy invalidation compatibility path (`R6`)."""

    workspace_id: str
    reason: PromptCacheInvalidationReason
    invalidated_keys_count: int


@dataclass(frozen=True, slots=True)
class ThreeSpeedStepProgressItem:
    """Real-time step progress item streamed in Speeds 1, 2, and 3 (`Story 10.2`)."""

    step_code: str
    label: str
    duration_ms: float
    status: Literal["COMPLETED", "RUNNING"] = "COMPLETED"
    connector_or_lens: str | None = None
    intermediate_output: str | None = None


@dataclass(frozen=True, slots=True)
class ThreeSpeedTurnResult:
    """Complete execution trace and response of a 3-Speed conversational turn (`Story 10.2`)."""

    turn_id: str
    workspace_id: str
    user_id: str
    hat: str
    speed_mode: AssistantSpeedMode
    cache_key: str
    cache_hit: bool
    cache_lookup_ms: float
    nodes_1_to_4_deterministic_ms: float
    ttft_ms: float
    intermediate_llm_calls: int
    invoked_targets: tuple[str, ...]
    step_progress: tuple[ThreeSpeedStepProgressItem, ...]
    response_text: str
    assembled_prompt_sha256: str
    deep_audit_lenses: tuple[str, ...] = field(default_factory=tuple)


def detect_conversational_speed_mode(
    user_prompt: str,
    *,
    requested_speed: AssistantSpeedMode | None = None,
    deep_audit_pill_active: bool = False,
) -> tuple[AssistantSpeedMode, tuple[str, ...]]:
    """Determine conversational speed (`SPEED_1_FAST`, `SPEED_2_AGENT_TOOLS`, `SPEED_3`)."""
    targets = tuple(m.group(1) for m in _AGENT_OR_SKILL_PATTERN.finditer(user_prompt))
    if requested_speed is not None:
        return requested_speed, targets
    if deep_audit_pill_active:
        return "SPEED_3_DEEP_AUDIT", targets
    if targets:
        return "SPEED_2_AGENT_TOOLS", targets
    return "SPEED_1_FAST", ()


__all__ = [
    "AssistantSpeedMode",
    "CachedAssembledPromptResult",
    "MAX_NODES_1_TO_4_DETERMINISTIC_MS",
    "PROMPT_CACHE_TTL_SECONDS",
    "PromptCacheInvalidationOutcome",
    "PromptCacheInvalidationReason",
    "SPEED_1_TTFT_SLO_MS",
    "SPEED_2_TTFT_SLO_MS",
    "ThreeSpeedStepProgressItem",
    "ThreeSpeedTurnResult",
    "build_assistant_prompt_cache_key",
    "detect_conversational_speed_mode",
]
