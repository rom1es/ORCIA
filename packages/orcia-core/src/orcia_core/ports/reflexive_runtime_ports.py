"""Pure hexagonal ports for the Reflexive Runtime (`AD-19`, `AD-20`, `Story 16.2`).

Defines `ReflexiveLlmPort`, `ReflexiveEventStreamPort`, `ReflexiveSessionStorePort`, and
`ReflexiveWriteGatePort` with zero external framework, database, broker, or connector imports.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.ports.surgical_explorer_port import (
    SurgicalFileBadgeCode,
    SurgicalPrimitiveName,
)


class TraceEventKind(StrEnum):
    """Canonical event kinds streamed over SSE and persisted in `ReflexiveSessionSnapshot`."""

    GROUP_HEADER = "group_header"
    THOUGHT_DELTA = "thought_delta"
    THOUGHT_COMPLETED = "thought_completed"
    CHECK_EXECUTED = "check_executed"
    FILE_ANALYZED = "file_analyzed"
    AGENT_DELEGATED = "agent_delegated"
    WRITE_PREVIEW_REQUESTED = "write_preview_requested"
    ANSWER_TOKEN_DELTA = "answer_token_delta"
    STATUS_WORKING = "status_working"
    LOOP_COMPLETED = "loop_completed"
    LOOP_CANCELLED = "loop_cancelled"


ReflexiveActionKind = Literal[
    "surgical_primitive",
    "delegate_sub_agent",
    "propose_external_write_preview",
    "final_answer",
]


class AgentTraceEvent(BaseModel):
    """Single immutable trace event emitted during a reflexive execution turn."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=new_uuid7_str)
    execution_id: str
    sequence_index: int = Field(ge=0)
    turn_index: int = Field(ge=0)
    kind: TraceEventKind
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    group_title: str | None = None
    delta_text: str | None = None
    thought_duration_ms: int | None = Field(default=None, ge=0)
    resource_uri: str | None = None
    display_filename: str | None = None
    file_badge_code: SurgicalFileBadgeCode | None = None
    formatted_badge: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    check_label: str | None = None
    delegate_agent_slug: str | None = None
    write_preview_id: str | None = None
    status_label: str | None = None
    redacted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingWritePreviewSpec(BaseModel):
    """Serializable governed write preview stored while `status == WAITING_WRITE_PREVIEW`."""

    model_config = ConfigDict(extra="forbid")

    preview_id: str = Field(default_factory=new_uuid7_str)
    connector_type: str = Field(min_length=1, max_length=128)
    action: str = Field(min_length=1, max_length=128)
    target_resource_uri: str = Field(min_length=1, max_length=1024)
    action_summary: str = Field(min_length=1, max_length=512)
    diff_or_payload_preview: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_sha256: str = Field(min_length=64, max_length=64)
    created_at_utc: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ReflexiveWriteApprovalInput(BaseModel):
    """Cryptographic approval credentials verified before executing a pending external write."""

    model_config = ConfigDict(extra="forbid")

    preview_id: str = Field(min_length=1)
    approver_user_id: str = Field(min_length=1)
    approved_at_utc: str = Field(min_length=1)
    payload_sha256: str = Field(min_length=64, max_length=64)
    broker_signature: str = Field(min_length=16)


class ReflexiveLlmChunk(BaseModel):
    """Incremental chunk emitted by `ReflexiveLlmPort.stream_turn_deltas` preserving `\n`."""

    model_config = ConfigDict(extra="forbid")

    thinking_delta: str = ""
    answer_delta: str = ""
    tokens_used: int = Field(default=0, ge=0)


class ReflexiveTurnInput(BaseModel):
    """Context envelope supplied to `ReflexiveLlmPort` at the start of turn `turn_index`."""

    model_config = ConfigDict(extra="forbid")

    execution_id: str
    actor_slug: str
    objective: str
    turn_index: int = Field(ge=0)
    max_turns: int = Field(ge=1)
    force_final: bool = False
    allow_sub_agent_delegation: bool = False
    available_delegate_agents: list[str] = Field(default_factory=list)
    scratchpad: list[dict[str, Any]] = Field(default_factory=list)
    initial_resources: list[str] = Field(default_factory=list)
    requested_write_preview: dict[str, Any] | None = None
    locale: str = "fr"


class ReflexiveTurnDecision(BaseModel):
    """Structured `Think -> Act` decision produced by `ReflexiveLlmPort.decide_next_turn`."""

    model_config = ConfigDict(extra="forbid")

    group_title: str | None = None
    status_label: str | None = None
    thought_text: str = ""
    action_kind: ReflexiveActionKind
    primitive: SurgicalPrimitiveName | None = None
    resource_uri: str = ""
    query: str = ""
    start_line: int = Field(default=1, ge=1)
    end_line: int = Field(default=200, ge=1)
    delegate_agent_slug: str | None = None
    delegate_sub_objective: str = ""
    connector_type: str = ""
    write_action: str = ""
    write_target_uri: str = ""
    write_summary: str = ""
    write_payload: dict[str, Any] = Field(default_factory=dict)
    final_markdown: str = ""
    tokens_used: int = Field(default=128, ge=0)


@runtime_checkable
class ReflexiveLlmPort(Protocol):
    """Hexagonal port driving `Think -> Act` decisions and streaming chunks."""

    async def decide_next_turn(self, turn_input: ReflexiveTurnInput) -> ReflexiveTurnDecision:
        """Compute the next reflexive turn decision."""
        ...

    def stream_turn_deltas(
        self,
        turn_input: ReflexiveTurnInput,
        decision: ReflexiveTurnDecision,
    ) -> AsyncIterator[ReflexiveLlmChunk]:
        """Stream `thinking_delta` and `answer_delta` chunks preserving `\n` and indentation."""
        ...


@runtime_checkable
class ReflexiveEventStreamPort(Protocol):
    """Hexagonal port publishing and subscribing to real-time `AgentTraceEvent` streams."""

    async def publish_event(self, execution_id: str, event_payload: dict[str, Any]) -> None:
        """Broadcast an `AgentTraceEvent` payload to live subscribers."""
        ...

    def subscribe_events(self, execution_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield historical and live `AgentTraceEvent` payloads until terminal or pause state."""
        ...


@runtime_checkable
class ReflexiveSessionStorePort(Protocol):
    """Hexagonal port persisting `ReflexiveSessionSnapshot` records with 24h TTL (`F5` survival)."""

    async def save_session_record(
        self,
        execution_id: str,
        *,
        workspace_id: str | None,
        actor_slug: str,
        orchestration_mode: str,
        effort_level: str,
        status: str,
        snapshot_payload: dict[str, Any],
        expires_at_utc: str,
    ) -> None:
        """Upsert a serialized `ReflexiveSessionSnapshot` record."""
        ...

    async def load_session_record(self, execution_id: str) -> dict[str, Any] | None:
        """Load the serialized `ReflexiveSessionSnapshot` payload or `None` if absent."""
        ...


@runtime_checkable
class ReflexiveWriteGatePort(Protocol):
    """Hexagonal port preparing `WritePreviewCard` previews and executing signed writes."""

    async def prepare_write_preview(
        self,
        *,
        connector_type: str,
        action: str,
        target_resource_uri: str,
        action_summary: str,
        payload: dict[str, Any],
    ) -> PendingWritePreviewSpec:
        """Prepare an unexecuted external write preview with canonical `payload_sha256`."""
        ...

    async def execute_approved_write(
        self,
        *,
        preview: PendingWritePreviewSpec,
        approval: ReflexiveWriteApprovalInput,
    ) -> dict[str, Any]:
        """Verify cryptographic approval signature and execute the external write."""
        ...


__all__ = [
    "AgentTraceEvent",
    "PendingWritePreviewSpec",
    "ReflexiveActionKind",
    "ReflexiveEventStreamPort",
    "ReflexiveLlmChunk",
    "ReflexiveLlmPort",
    "ReflexiveSessionStorePort",
    "ReflexiveTurnDecision",
    "ReflexiveTurnInput",
    "ReflexiveWriteApprovalInput",
    "ReflexiveWriteGatePort",
    "TraceEventKind",
]
