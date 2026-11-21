"""Sub-agent delegation & session snapshot helpers for `NonDeterministicReflexiveRuntime`."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

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


__all__: list[str] = ["execute_delegation_turn", "persist_reflexive_snapshot"]
