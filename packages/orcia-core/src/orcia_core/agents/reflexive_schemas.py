"""Domain schemas for `NonDeterministicReflexiveRuntime` (`Story 16.2`, `CAP-160`).

Enforces:
- Strict 2-mode cognitive effort mapping (`Standard` -> `(4 turns, 8_000 tokens)` vs
  `Approfondi` -> `(25 turns, 48_000 tokens)`) aligned with `EffortLevel`.
- Serializable `ReflexiveSessionSnapshot` (`24h` TTL) enabling stateless Suspend/Resume on
  `WritePreviewCard` (`WAITING_WRITE_PREVIEW`) with zero blocked coroutine in memory.
- Zero vendor or methodology terms inside `orcia_core`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.ports.reflexive_runtime_ports import (
    AgentTraceEvent,
    PendingWritePreviewSpec,
    ReflexiveActionKind,
    ReflexiveTurnDecision,
    ReflexiveTurnInput,
    ReflexiveWriteApprovalInput,
    TraceEventKind,
)
from orcia_core.storage.claim_check import ClaimCheckPointer
from orcia_core.workflows.schemas_v2 import (
    EffortLevel,
)
from orcia_core.workflows.schemas_v2 import (
    ProcessOrchestrationType as ProcessOrchestrationType,
)

STANDARD_MAX_TURNS: Final[int] = 4
STANDARD_MAX_TOKENS: Final[int] = 8_000
APPROFONDI_MAX_TURNS: Final[int] = 25
APPROFONDI_MAX_TOKENS: Final[int] = 48_000
SESSION_SNAPSHOT_TTL_HOURS: Final[int] = 24
MAX_DELEGATION_DEPTH_CAP: Final[int] = 1

ReflexiveEffortMode = Literal["standard", "approfondi"]
ReflexiveExecutionStatus = Literal[
    "RUNNING",
    "WAITING_WRITE_PREVIEW",
    "COMPLETED",
    "CANCELLED",
    "FAILED",
]


def resolve_effort_budget(effort: EffortLevel) -> tuple[ReflexiveEffortMode, int, int]:
    """Map `EffortLevel` onto the 2 locked cognitive modes (`Standard` vs `Approfondi`)."""
    if effort == EffortLevel.HIGH:
        return ("approfondi", APPROFONDI_MAX_TURNS, APPROFONDI_MAX_TOKENS)
    return ("standard", STANDARD_MAX_TURNS, STANDARD_MAX_TOKENS)


class ReflexiveRuntimeConfig(BaseModel):
    """Immutable runtime configuration governing a single reflexive execution."""

    model_config = ConfigDict(extra="forbid")

    effort_level: EffortLevel = EffortLevel.DEFAULT
    effort_mode: ReflexiveEffortMode = "standard"
    max_turns: int = Field(default=STANDARD_MAX_TURNS, ge=1, le=APPROFONDI_MAX_TURNS)
    max_budget_tokens: int = Field(default=STANDARD_MAX_TOKENS, ge=256, le=APPROFONDI_MAX_TOKENS)
    allow_sub_agent_delegation: bool = False
    delegation_depth: int = Field(default=0, ge=0, le=MAX_DELEGATION_DEPTH_CAP)
    max_delegation_depth: int = Field(
        default=MAX_DELEGATION_DEPTH_CAP,
        ge=0,
        le=MAX_DELEGATION_DEPTH_CAP,
    )
    available_delegate_agents: tuple[str, ...] = ()
    workspace_id: str | None = None
    actor_user_id: str | None = None
    has_read_source: bool = True
    locale: str = "fr"
    initial_resources: tuple[str, ...] = ()
    requested_write_preview: dict[str, Any] | None = None
    step_delay_ms: int = Field(default=0, ge=0, le=500)

    @model_validator(mode="before")
    @classmethod
    def _align_effort_mode_defaults(cls, raw: Any) -> Any:
        if not isinstance(raw, dict):
            return raw
        data = dict(raw)
        explicit_mode = data.get("effort_mode")
        if explicit_mode == "approfondi" and "effort_level" not in data:
            data["effort_level"] = EffortLevel.HIGH
        raw_effort = data.get("effort_level", EffortLevel.DEFAULT)
        effort = raw_effort if isinstance(raw_effort, EffortLevel) else EffortLevel(str(raw_effort))
        if explicit_mode == "approfondi":
            effort = EffortLevel.HIGH
            data["effort_level"] = EffortLevel.HIGH
        mode, turns, tokens = resolve_effort_budget(effort)
        data.setdefault("effort_mode", mode)
        if "max_turns" not in data:
            data["max_turns"] = turns
        if "max_budget_tokens" not in data:
            data["max_budget_tokens"] = tokens
        return data

    @classmethod
    def from_effort_level(
        cls,
        effort: EffortLevel,
        *,
        allow_sub_agent_delegation: bool = False,
        available_delegate_agents: tuple[str, ...] = (),
        workspace_id: str | None = None,
        actor_user_id: str | None = None,
        has_read_source: bool = True,
        locale: str = "fr",
        initial_resources: tuple[str, ...] = (),
        requested_write_preview: dict[str, Any] | None = None,
        step_delay_ms: int = 0,
    ) -> ReflexiveRuntimeConfig:
        """Construct a `ReflexiveRuntimeConfig` strictly aligned on `Standard` or `Approfondi`."""
        mode, turns, tokens = resolve_effort_budget(effort)
        return cls(
            effort_level=effort,
            effort_mode=mode,
            max_turns=turns,
            max_budget_tokens=tokens,
            allow_sub_agent_delegation=allow_sub_agent_delegation,
            available_delegate_agents=available_delegate_agents,
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            has_read_source=has_read_source,
            locale=locale,
            initial_resources=initial_resources,
            requested_write_preview=requested_write_preview,
            step_delay_ms=step_delay_ms,
        )


class ReflexiveScratchpadEntry(BaseModel):
    """Structured observation recorded in the session `scratchpad` after each turn."""

    model_config = ConfigDict(extra="forbid")

    turn_index: int = Field(ge=0)
    action_kind: str
    resource_uri: str = ""
    line_anchor: str = ""
    formatted_badge: str = ""
    summary: str
    excerpt: str = ""
    redacted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


def compute_default_session_expiry_utc(now: datetime | None = None) -> str:
    """Compute ISO-8601 UTC timestamp `+24h` for `ReflexiveSessionSnapshot.expires_at_utc`."""
    base = now or datetime.now(UTC)
    return (base + timedelta(hours=SESSION_SNAPSHOT_TTL_HOURS)).isoformat()


class ReflexiveSessionSnapshot(BaseModel):
    """Lightweight serializable snapshot persisted across `F5` reloads and `WritePreviewCard`."""

    model_config = ConfigDict(extra="forbid")

    execution_id: str = Field(default_factory=new_uuid7_str)
    workspace_id: str | None = None
    actor_slug: str
    actor_user_id: str | None = None
    objective: str
    orchestration_type: ProcessOrchestrationType = ProcessOrchestrationType.NON_DETERMINISTIC
    effort_level: EffortLevel = EffortLevel.DEFAULT
    effort_mode: ReflexiveEffortMode = "standard"
    status: ReflexiveExecutionStatus = "RUNNING"
    allow_sub_agent_delegation: bool = False
    delegation_depth: int = Field(default=0, ge=0, le=MAX_DELEGATION_DEPTH_CAP)
    available_delegate_agents: list[str] = Field(default_factory=list)
    has_read_source: bool = True
    locale: str = "fr"
    initial_resources: list[str] = Field(default_factory=list)
    requested_write_preview: dict[str, Any] | None = None
    force_final: bool = False
    turns_used: int = Field(default=0, ge=0)
    max_turns: int = Field(default=STANDARD_MAX_TURNS, ge=1)
    tokens_used: int = Field(default=0, ge=0)
    max_budget_tokens: int = Field(default=STANDARD_MAX_TOKENS, ge=1)
    final_markdown: str = ""
    scratchpad: list[ReflexiveScratchpadEntry] = Field(default_factory=list)
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)
    pending_write_preview: PendingWritePreviewSpec | None = None
    artifact_pointer: ClaimCheckPointer | None = None
    created_at_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at_utc: str = Field(default_factory=compute_default_session_expiry_utc)


__all__ = [
    "APPROFONDI_MAX_TOKENS",
    "APPROFONDI_MAX_TURNS",
    "AgentTraceEvent",
    "MAX_DELEGATION_DEPTH_CAP",
    "PendingWritePreviewSpec",
    "ProcessOrchestrationType",
    "ReflexiveActionKind",
    "ReflexiveEffortMode",
    "ReflexiveExecutionStatus",
    "ReflexiveRuntimeConfig",
    "ReflexiveScratchpadEntry",
    "ReflexiveSessionSnapshot",
    "ReflexiveTurnDecision",
    "ReflexiveTurnInput",
    "ReflexiveWriteApprovalInput",
    "SESSION_SNAPSHOT_TTL_HOURS",
    "STANDARD_MAX_TOKENS",
    "STANDARD_MAX_TURNS",
    "TraceEventKind",
    "compute_default_session_expiry_utc",
    "resolve_effort_budget",
]
