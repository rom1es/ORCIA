"""Structural `ExecutionProfile` isolation helpers (`Story 26.6b`, `AD-25`, `H-29`).

Ensures `ReflexiveWriteGatePort` / `ConnectorReflexiveWriteGateAdapter` cannot be bound,
reached, or invoked under `execution_profile == 'ASSISTANT'`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.agents.errors import PolicyDeniedError
from orcia_core.agents.reflexive_schemas import (
    APPROFONDI_MAX_TOKENS,
    APPROFONDI_MAX_TURNS,
    STANDARD_MAX_TOKENS,
    STANDARD_MAX_TURNS,
    AgentTraceEvent,
    ExecutionProfile,
    ReflexiveScratchpadEntry,
    ReflexiveSessionSnapshot,
    TraceEventKind,
)
from orcia_core.ports.reflexive_runtime_ports import (
    ReflexiveSessionStorePort,
    ReflexiveWriteGatePort,
)
from orcia_core.workflows.schemas_v2 import EffortLevel


def assert_assistant_profile_write_gate_unreachable(
    execution_profile: ExecutionProfile,
    write_gate: ReflexiveWriteGatePort | None,
) -> None:
    """Reject binding a write gate when runtime profile is `ASSISTANT`."""
    if execution_profile == "ASSISTANT" and write_gate is not None:
        raise PolicyDeniedError(
            detail_override=(
                "ERR_ASSISTANT_WRITE_GATE_FORBIDDEN: Write gate adapter cannot be bound under "
                "execution_profile='ASSISTANT'."
            )
        )


def assert_profile_allows_write_action(execution_profile: ExecutionProfile) -> None:
    """Reject direct write preview/resume transitions when profile is `ASSISTANT`."""
    if execution_profile == "ASSISTANT":
        raise PolicyDeniedError(
            detail_override=(
                "ERR_ASSISTANT_WRITE_GATE_FORBIDDEN: External write previews are structurally "
                "forbidden under execution_profile='ASSISTANT'. Use CONTINUE_IN_PROCESS."
            )
        )


def resolve_effective_write_gate(
    runtime_profile: ExecutionProfile,
    snapshot: ReflexiveSessionSnapshot,
    write_gate: ReflexiveWriteGatePort | None,
) -> ReflexiveWriteGatePort | None:
    """Return `None` and reject write gate access whenever profile is `ASSISTANT`."""
    assert_profile_allows_write_action(runtime_profile)
    assert_profile_allows_write_action(snapshot.execution_profile)
    return write_gate


async def ensure_assistant_reflexive_session(
    *,
    session_store: ReflexiveSessionStorePort,
    active_snapshots: dict[str, ReflexiveSessionSnapshot],
    execution_id: str,
    workspace_id: str,
    user_id: str,
    objective: str,
    effort_mode: Literal["standard", "approfondi"],
    locale: str = "fr",
) -> ReflexiveSessionSnapshot:
    """Create and persist an `ASSISTANT` profile session in `reflexive_execution_sessions`."""
    is_deep = effort_mode == "approfondi"
    snap = ReflexiveSessionSnapshot(
        execution_id=execution_id,
        workspace_id=workspace_id,
        actor_slug="assistant",
        actor_user_id=user_id,
        objective=objective,
        effort_level=EffortLevel.HIGH if is_deep else EffortLevel.DEFAULT,
        effort_mode=effort_mode,
        execution_profile="ASSISTANT",
        status="RUNNING",
        locale=locale,
        max_turns=APPROFONDI_MAX_TURNS if is_deep else STANDARD_MAX_TURNS,
        max_budget_tokens=APPROFONDI_MAX_TOKENS if is_deep else STANDARD_MAX_TOKENS,
    )
    active_snapshots[execution_id] = snap
    await _save_assistant_snapshot(session_store, snap)
    return snap


async def record_assistant_reflexive_step(
    *,
    session_store: ReflexiveSessionStorePort,
    active_snapshots: dict[str, ReflexiveSessionSnapshot],
    execution_id: str,
    turn_index: int,
    action_kind: str,
    summary: str,
    tool_name: str = "",
    tokens_used: int = 0,
) -> None:
    """Append a governed step observation and persist the updated `ASSISTANT` snapshot."""
    snap = await _load_or_cache_snapshot(session_store, active_snapshots, execution_id)
    if snap is None:
        return
    if action_kind == "write_preview":
        assert_profile_allows_write_action(snap.execution_profile)
    snap.turns_used = max(snap.turns_used, turn_index + 1)
    snap.tokens_used += max(0, int(tokens_used))
    snap.scratchpad.append(
        ReflexiveScratchpadEntry(
            turn_index=max(0, turn_index),
            action_kind=action_kind,
            summary=summary,
            metadata={"tool_name": tool_name} if tool_name else {},
        )
    )
    snap.trace_events.append(
        AgentTraceEvent(
            execution_id=execution_id,
            sequence_index=len(snap.trace_events),
            turn_index=max(0, turn_index),
            kind=TraceEventKind.CHECK_EXECUTED,
            check_label=f"{tool_name}: {summary[:120]}" if tool_name else summary[:120],
        )
    )
    snap.updated_at_utc = datetime.now(UTC).isoformat()
    await _save_assistant_snapshot(session_store, snap)


async def complete_assistant_reflexive_session(
    *,
    session_store: ReflexiveSessionStorePort,
    active_snapshots: dict[str, ReflexiveSessionSnapshot],
    execution_id: str,
    status: Literal["COMPLETED", "CANCELLED", "FAILED"],
    final_markdown: str,
    tokens_used: int = 0,
) -> None:
    """Finalize and persist the `ASSISTANT` reflexive session."""
    snap = await _load_or_cache_snapshot(session_store, active_snapshots, execution_id)
    if snap is None:
        return
    snap.status = status
    snap.final_markdown = final_markdown
    if tokens_used > snap.tokens_used:
        snap.tokens_used = tokens_used
    snap.trace_events.append(
        AgentTraceEvent(
            execution_id=execution_id,
            sequence_index=len(snap.trace_events),
            turn_index=snap.turns_used,
            kind=(
                TraceEventKind.LOOP_CANCELLED
                if status == "CANCELLED"
                else TraceEventKind.LOOP_COMPLETED
            ),
            status_label=status,
        )
    )
    snap.updated_at_utc = datetime.now(UTC).isoformat()
    await _save_assistant_snapshot(session_store, snap)
    active_snapshots.pop(execution_id, None)


async def _load_or_cache_snapshot(
    session_store: ReflexiveSessionStorePort,
    active_snapshots: dict[str, ReflexiveSessionSnapshot],
    execution_id: str,
) -> ReflexiveSessionSnapshot | None:
    snap = active_snapshots.get(execution_id)
    if snap is not None:
        return snap
    raw: dict[str, Any] | None = await session_store.load_session_record(execution_id)
    if raw is None:
        return None
    loaded = ReflexiveSessionSnapshot.model_validate(raw)
    active_snapshots[execution_id] = loaded
    return loaded


async def _save_assistant_snapshot(
    session_store: ReflexiveSessionStorePort,
    snap: ReflexiveSessionSnapshot,
) -> None:
    await session_store.save_session_record(
        snap.execution_id,
        workspace_id=snap.workspace_id,
        actor_slug=snap.actor_slug,
        orchestration_mode=snap.orchestration_type.value,
        effort_level=snap.effort_level.value,
        status=snap.status,
        snapshot_payload=snap.model_dump(mode="json"),
        expires_at_utc=snap.expires_at_utc,
    )


class AssistantReflexiveSessionMixin:
    """Mixin implementing `AssistantReflexiveRuntimePort` on `NonDeterministicReflexiveRuntime`."""

    _session_store: ReflexiveSessionStorePort
    _active_snapshots: dict[str, ReflexiveSessionSnapshot]
    _write_gate: ReflexiveWriteGatePort | None
    _force_final_flags: set[str]

    async def ensure_assistant_session(
        self,
        *,
        execution_id: str,
        workspace_id: str,
        user_id: str,
        objective: str,
        effort_mode: Literal["standard", "approfondi"],
        locale: str = "fr",
    ) -> None:
        assert_assistant_profile_write_gate_unreachable("ASSISTANT", self._write_gate)
        await ensure_assistant_reflexive_session(
            session_store=self._session_store,
            active_snapshots=self._active_snapshots,
            execution_id=execution_id,
            workspace_id=workspace_id,
            user_id=user_id,
            objective=objective,
            effort_mode=effort_mode,
            locale=locale,
        )

    async def record_assistant_step(
        self,
        *,
        execution_id: str,
        turn_index: int,
        action_kind: str,
        summary: str,
        tool_name: str = "",
        tokens_used: int = 0,
    ) -> None:
        await record_assistant_reflexive_step(
            session_store=self._session_store,
            active_snapshots=self._active_snapshots,
            execution_id=execution_id,
            turn_index=turn_index,
            action_kind=action_kind,
            summary=summary,
            tool_name=tool_name,
            tokens_used=tokens_used,
        )

    async def complete_assistant_session(
        self,
        *,
        execution_id: str,
        status: Literal["COMPLETED", "CANCELLED", "FAILED"],
        final_markdown: str,
        tokens_used: int = 0,
    ) -> None:
        await complete_assistant_reflexive_session(
            session_store=self._session_store,
            active_snapshots=self._active_snapshots,
            execution_id=execution_id,
            status=status,
            final_markdown=final_markdown,
            tokens_used=tokens_used,
        )
        self._force_final_flags.discard(execution_id)

    async def is_synthesize_now_requested(self, execution_id: str) -> bool:
        if execution_id in self._force_final_flags:
            return True
        raw = await self._session_store.load_session_record(execution_id)
        return bool(raw and raw.get("force_final"))


__all__ = [
    "AssistantReflexiveSessionMixin",
    "assert_assistant_profile_write_gate_unreachable",
    "assert_profile_allows_write_action",
    "complete_assistant_reflexive_session",
    "ensure_assistant_reflexive_session",
    "record_assistant_reflexive_step",
    "resolve_effective_write_gate",
]
