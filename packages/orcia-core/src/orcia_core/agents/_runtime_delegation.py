"""Sub-agent delegation & session snapshot helpers for `NonDeterministicReflexiveRuntime`."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from orcia_core.agents._runtime_helpers import build_child_delegation_config
from orcia_core.agents.reflexive_schemas import (
    MAX_DELEGATION_DEPTH_CAP,
    AgentTraceEvent,
    ReflexiveRuntimeConfig,
    ReflexiveScratchpadEntry,
    ReflexiveSessionSnapshot,
    ReflexiveTurnDecision,
    TraceEventKind,
)
from orcia_core.ports.reflexive_runtime_ports import ReflexiveSessionStorePort


async def persist_reflexive_snapshot(
    session_store: ReflexiveSessionStorePort,
    snapshot: ReflexiveSessionSnapshot,
) -> None:
    """Persist `ReflexiveSessionSnapshot` into `ReflexiveSessionStorePort`."""
    await session_store.save_session_record(
        snapshot.execution_id,
        workspace_id=snapshot.workspace_id,
        actor_slug=snapshot.actor_slug,
        orchestration_mode=snapshot.orchestration_type.value,
        effort_level=snapshot.effort_level.value,
        status=snapshot.status,
        snapshot_payload=snapshot.model_dump(mode="json"),
        expires_at_utc=snapshot.expires_at_utc,
    )


async def execute_delegation_turn(
    *,
    snapshot: ReflexiveSessionSnapshot,
    decision: ReflexiveTurnDecision,
    turn_idx: int,
    publish_fn: Callable[[ReflexiveSessionSnapshot, AgentTraceEvent], Awaitable[None]],
    run_child_fn: Callable[..., Awaitable[ReflexiveSessionSnapshot]],
) -> None:
    """Delegate a bounded (`depth <= 1`) sub-agent turn and append its result to scratchpad."""
    target_slug = (decision.delegate_agent_slug or "").strip()
    allowed_set = set(snapshot.available_delegate_agents)
    can_delegate = (
        bool(target_slug)
        and snapshot.allow_sub_agent_delegation
        and snapshot.delegation_depth < MAX_DELEGATION_DEPTH_CAP
        and (not allowed_set or target_slug in allowed_set)
    )
    if not can_delegate:
        snapshot.scratchpad.append(
            ReflexiveScratchpadEntry(
                turn_index=turn_idx,
                action_kind="delegation_blocked",
                summary="Nested or unauthorized sub-agent delegation ignored (max depth = 1).",
            )
        )
        return
    await publish_fn(
        snapshot,
        AgentTraceEvent(
            execution_id=snapshot.execution_id,
            sequence_index=len(snapshot.trace_events),
            turn_index=turn_idx,
            kind=TraceEventKind.AGENT_DELEGATED,
            delegate_agent_slug=target_slug,
            status_label=decision.delegate_sub_objective or snapshot.objective,
        ),
    )
    child_config: ReflexiveRuntimeConfig = build_child_delegation_config(snapshot)
    child_snap = await run_child_fn(
        actor_slug=target_slug,
        objective=decision.delegate_sub_objective or snapshot.objective,
        config=child_config,
    )
    snapshot.tokens_used += child_snap.tokens_used
    snapshot.scratchpad.append(
        ReflexiveScratchpadEntry(
            turn_index=turn_idx,
            action_kind="sub_agent_result",
            summary=f"Returned from @{target_slug}",
            excerpt=child_snap.final_markdown,
            metadata={"child_execution_id": child_snap.execution_id},
        )
    )


async def mark_snapshot_cancelled(
    *,
    snapshot: ReflexiveSessionSnapshot,
    publish_fn: Callable[[ReflexiveSessionSnapshot, AgentTraceEvent], Awaitable[None]],
    persist_fn: Callable[[ReflexiveSessionSnapshot], Awaitable[None]],
) -> ReflexiveSessionSnapshot:
    """Transition snapshot to `CANCELLED` (`0` extra LLM turns) and emit `loop_cancelled`."""
    snapshot.status = "CANCELLED"
    snapshot.updated_at_utc = datetime.now(UTC).isoformat()
    if not snapshot.trace_events or snapshot.trace_events[-1].kind != TraceEventKind.LOOP_CANCELLED:
        await publish_fn(
            snapshot,
            AgentTraceEvent(
                execution_id=snapshot.execution_id,
                sequence_index=len(snapshot.trace_events),
                turn_index=snapshot.turns_used,
                kind=TraceEventKind.LOOP_CANCELLED,
            ),
        )
    await persist_fn(snapshot)
    return snapshot


def resolve_fallback_final_markdown(snapshot: ReflexiveSessionSnapshot) -> str:
    """Resolve fallback final markdown when the turn loop exits without `final_answer`."""
    from orcia_core.agents._agents_locales import get_agent_runtime_copy

    return snapshot.final_markdown or get_agent_runtime_copy().fallback_synthesis_heading


async def dispatch_non_terminal_turn(
    *,
    explorer: Any,
    snapshot: ReflexiveSessionSnapshot,
    decision: Any,
    turn_idx: int,
    publish_fn: Any,
    run_child_fn: Any,
    persist_fn: Any,
) -> None:
    """Execute delegation or surgical exploration turn and update snapshot turn counter."""
    if decision.action_kind == "delegate_sub_agent":
        await execute_delegation_turn(
            snapshot=snapshot,
            decision=decision,
            turn_idx=turn_idx,
            publish_fn=publish_fn,
            run_child_fn=run_child_fn,
        )
    else:
        from orcia_core.agents._runtime_turn_actions import execute_surgical_turn

        await execute_surgical_turn(
            explorer=explorer,
            snapshot=snapshot,
            decision=decision,
            turn_idx=turn_idx,
            publish_fn=publish_fn,
        )
    snapshot.turns_used = turn_idx + 1
    snapshot.updated_at_utc = datetime.now(UTC).isoformat()
    await persist_fn(snapshot)


__all__: list[str] = [
    "dispatch_non_terminal_turn",
    "execute_delegation_turn",
    "mark_snapshot_cancelled",
    "persist_reflexive_snapshot",
    "resolve_fallback_final_markdown",
]
