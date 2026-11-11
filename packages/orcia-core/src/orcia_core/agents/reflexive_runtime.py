"""Pure `asyncio` Non-Deterministic Reflexive Runtime (`Story 16.2`, `CAP-160`).

Executes `Mon Assistant`, `Mes Agents`, and Goal-Driven Processes via a `Think -> Act -> Observe`
loop with real-time SSE streaming, strict separation between `cancel_execution` (`■ Arrêter`) and
`request_synthesize_now` (`Synthétiser maintenant`), bounded sub-agent delegation (`depth <= 1`),
stateless Suspend/Resume on `WritePreviewCard` (`F5` survival, 24h TTL), and `ClaimCheckPointer`
archival — with ZERO DBOS workflow or step overhead.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

from orcia_core.agents._runtime_helpers import (
    build_child_delegation_config,
    build_initial_reflexive_snapshot,
    build_turn_input,
)
from orcia_core.agents._runtime_turn_actions import (
    apply_write_gate_decision,
    emit_thought_and_answer_deltas,
    execute_surgical_turn,
    finalize_completed_snapshot,
    mark_snapshot_cancelled,
    suspend_for_write_preview,
)
from orcia_core.agents.errors import ResourceNotFoundError
from orcia_core.agents.reflexive_schemas import (
    MAX_DELEGATION_DEPTH_CAP,
    AgentTraceEvent,
    ReflexiveRuntimeConfig,
    ReflexiveScratchpadEntry,
    ReflexiveSessionSnapshot,
    ReflexiveTurnDecision,
    ReflexiveWriteApprovalInput,
    TraceEventKind,
)
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.ports.reflexive_runtime_ports import (
    ReflexiveEventStreamPort,
    ReflexiveLlmPort,
    ReflexiveSessionStorePort,
    ReflexiveWriteGatePort,
)
from orcia_core.ports.surgical_explorer_port import SurgicalExplorerPort
from orcia_core.storage.claim_check import ClaimCheckStorageService, get_claim_check_storage


class NonDeterministicReflexiveRuntime:
    """100% pure `asyncio` reflexive orchestrator (zero DBOS tables or decorators)."""

    def __init__(
        self,
        *,
        llm_port: ReflexiveLlmPort,
        surgical_explorer: SurgicalExplorerPort,
        session_store: ReflexiveSessionStorePort,
        event_stream: ReflexiveEventStreamPort,
        write_gate: ReflexiveWriteGatePort | None = None,
        claim_check_storage: ClaimCheckStorageService | None = None,
    ) -> None:
        self._llm = llm_port
        self._explorer = surgical_explorer
        self._session_store = session_store
        self._event_stream = event_stream
        self._write_gate = write_gate
        self._claim_check = claim_check_storage or get_claim_check_storage()
        self._cancel_flags: set[str] = set()
        self._force_final_flags: set[str] = set()
        self._active_snapshots: dict[str, ReflexiveSessionSnapshot] = {}
        self._running_tasks: dict[str, asyncio.Task[ReflexiveSessionSnapshot]] = {}

    @property
    def active_task_count(self) -> int:
        """Return count of currently active in-flight coroutines (`0` while paused on write)."""
        return len(self._running_tasks)

    async def get_session_snapshot(self, execution_id: str) -> ReflexiveSessionSnapshot | None:
        """Load `ReflexiveSessionSnapshot` from active flight or persistent store (`F5`)."""
        in_flight = self._active_snapshots.get(execution_id)
        if in_flight is not None:
            return in_flight
        raw = await self._session_store.load_session_record(execution_id)
        return None if raw is None else ReflexiveSessionSnapshot.model_validate(raw)

    def start_background_execution(
        self,
        *,
        actor_slug: str,
        objective: str,
        config: ReflexiveRuntimeConfig,
        execution_id: str | None = None,
    ) -> tuple[str, asyncio.Task[ReflexiveSessionSnapshot]]:
        """Launch `run_execution` as a tracked background `asyncio.Task` for live SSE streaming."""
        exec_id = execution_id or new_uuid7_str()
        task = asyncio.create_task(
            self.run_execution(
                execution_id=exec_id, actor_slug=actor_slug, objective=objective, config=config
            )
        )
        self._running_tasks[exec_id] = task
        return exec_id, task

    async def run_execution(
        self,
        *,
        actor_slug: str,
        objective: str,
        config: ReflexiveRuntimeConfig,
        execution_id: str | None = None,
    ) -> ReflexiveSessionSnapshot:
        """Run the reflexive `Think -> Act -> Observe` loop until completion, cancel, or pause."""
        snapshot = build_initial_reflexive_snapshot(
            execution_id=execution_id or new_uuid7_str(),
            actor_slug=actor_slug,
            objective=objective,
            config=config,
        )
        await self._persist_snapshot(snapshot)
        return await self._execute_loop(snapshot, step_delay_ms=config.step_delay_ms)

    async def cancel_execution(self, execution_id: str) -> ReflexiveSessionSnapshot:
        """Immediately cancel `execution_id` (`■ Arrêter` — `0` extra LLM turns)."""
        self._cancel_flags.add(execution_id)
        snapshot = await self.get_session_snapshot(execution_id)
        if snapshot is None:
            raise ResourceNotFoundError(detail_override=f"Execution '{execution_id}' introuvable.")
        if snapshot.status in ("COMPLETED", "CANCELLED"):
            return snapshot
        return await mark_snapshot_cancelled(
            snapshot=snapshot,
            publish_fn=self._append_and_publish,
            persist_fn=self._persist_snapshot,
        )

    async def request_synthesize_now(
        self,
        execution_id: str,
        *,
        resume_if_idle: bool = False,
    ) -> ReflexiveSessionSnapshot:
        """Raise `force_final = True` (`Synthétiser maintenant`) for immediate synthesis."""
        self._force_final_flags.add(execution_id)
        snapshot = await self.get_session_snapshot(execution_id)
        if snapshot is None:
            raise ResourceNotFoundError(detail_override=f"Execution '{execution_id}' introuvable.")
        snapshot.force_final = True
        snapshot.updated_at_utc = datetime.now(UTC).isoformat()
        await self._persist_snapshot(snapshot)
        if (
            resume_if_idle
            and execution_id not in self._running_tasks
            and snapshot.status == "RUNNING"
        ):
            return await self._execute_loop(snapshot)
        return snapshot

    async def resume_after_write_decision(
        self,
        execution_id: str,
        *,
        approved: bool,
        approval: ReflexiveWriteApprovalInput | None = None,
        rejection_reason: str = "",
    ) -> ReflexiveSessionSnapshot:
        """Statelessly reload `WAITING_WRITE_PREVIEW` snapshot, handle write gate, and resume."""
        snapshot = await self.get_session_snapshot(execution_id)
        if snapshot is None:
            raise ResourceNotFoundError(detail_override=f"Execution '{execution_id}' introuvable.")
        await apply_write_gate_decision(
            write_gate=self._write_gate,
            snapshot=snapshot,
            approved=approved,
            approval=approval,
            rejection_reason=rejection_reason,
            persist_fn=self._persist_snapshot,
        )
        return await self._execute_loop(snapshot)

    async def _execute_loop(
        self,
        snapshot: ReflexiveSessionSnapshot,
        *,
        step_delay_ms: int = 0,
    ) -> ReflexiveSessionSnapshot:
        exec_id = snapshot.execution_id
        current_task = asyncio.current_task()
        if current_task is not None:
            self._running_tasks[exec_id] = current_task
        self._active_snapshots[exec_id] = snapshot
        try:
            while snapshot.turns_used < snapshot.max_turns:
                if self._is_cancelled(exec_id, snapshot):
                    return await mark_snapshot_cancelled(
                        snapshot=snapshot,
                        publish_fn=self._append_and_publish,
                        persist_fn=self._persist_snapshot,
                    )
                turn_idx = snapshot.turns_used
                at_budget_limit = (
                    turn_idx >= snapshot.max_turns - 1
                    or snapshot.tokens_used >= snapshot.max_budget_tokens
                )
                snapshot.force_final = (
                    snapshot.force_final or (exec_id in self._force_final_flags) or at_budget_limit
                )
                turn_input = build_turn_input(snapshot, turn_idx)
                t0 = time.perf_counter()
                decision = await self._llm.decide_next_turn(turn_input)
                if step_delay_ms > 0:
                    await asyncio.sleep(step_delay_ms / 1000.0)
                if self._is_cancelled(exec_id, snapshot):
                    return await mark_snapshot_cancelled(
                        snapshot=snapshot,
                        publish_fn=self._append_and_publish,
                        persist_fn=self._persist_snapshot,
                    )
                snapshot.tokens_used += decision.tokens_used
                await emit_thought_and_answer_deltas(
                    llm=self._llm,
                    snapshot=snapshot,
                    turn_input=turn_input,
                    decision=decision,
                    turn_idx=turn_idx,
                    started_perf=t0,
                    publish_fn=self._append_and_publish,
                )
                if decision.action_kind == "final_answer":
                    snapshot.turns_used = turn_idx + 1
                    return await finalize_completed_snapshot(
                        claim_check=self._claim_check,
                        snapshot=snapshot,
                        final_markdown=decision.final_markdown,
                        publish_fn=self._append_and_publish,
                        persist_fn=self._persist_snapshot,
                    )
                if decision.action_kind == "propose_external_write_preview":
                    return await suspend_for_write_preview(
                        write_gate=self._write_gate,
                        snapshot=snapshot,
                        decision=decision,
                        turn_idx=turn_idx,
                        publish_fn=self._append_and_publish,
                        persist_fn=self._persist_snapshot,
                    )
                if decision.action_kind == "delegate_sub_agent":
                    await self._handle_delegation_turn(snapshot, decision, turn_idx)
                else:
                    await execute_surgical_turn(
                        explorer=self._explorer,
                        snapshot=snapshot,
                        decision=decision,
                        turn_idx=turn_idx,
                        publish_fn=self._append_and_publish,
                    )
                snapshot.turns_used = turn_idx + 1
                snapshot.updated_at_utc = datetime.now(UTC).isoformat()
                await self._persist_snapshot(snapshot)
            return await finalize_completed_snapshot(
                claim_check=self._claim_check,
                snapshot=snapshot,
                final_markdown=snapshot.final_markdown or "# Synthèse consolidée\n",
                publish_fn=self._append_and_publish,
                persist_fn=self._persist_snapshot,
            )
        finally:
            self._active_snapshots.pop(exec_id, None)
            self._running_tasks.pop(exec_id, None)
            self._cancel_flags.discard(exec_id)
            self._force_final_flags.discard(exec_id)

    async def _handle_delegation_turn(
        self,
        snapshot: ReflexiveSessionSnapshot,
        decision: ReflexiveTurnDecision,
        turn_idx: int,
    ) -> None:
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
                    summary="Délégation imbriquée ou non autorisée ignorée (profondeur max = 1).",
                )
            )
            return
        await self._append_and_publish(
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
        child_snap = await self.run_execution(
            actor_slug=target_slug,
            objective=decision.delegate_sub_objective or snapshot.objective,
            config=build_child_delegation_config(snapshot),
        )
        snapshot.tokens_used += child_snap.tokens_used
        snapshot.scratchpad.append(
            ReflexiveScratchpadEntry(
                turn_index=turn_idx,
                action_kind="sub_agent_result",
                summary=f"Retour de @{target_slug}",
                excerpt=child_snap.final_markdown,
                metadata={"child_execution_id": child_snap.execution_id},
            )
        )

    def _is_cancelled(self, exec_id: str, snapshot: ReflexiveSessionSnapshot) -> bool:
        return exec_id in self._cancel_flags or str(snapshot.status) == "CANCELLED"

    async def _append_and_publish(
        self, snapshot: ReflexiveSessionSnapshot, event: AgentTraceEvent
    ) -> None:
        snapshot.trace_events.append(event)
        await self._event_stream.publish_event(snapshot.execution_id, event.model_dump(mode="json"))

    async def _persist_snapshot(self, snapshot: ReflexiveSessionSnapshot) -> None:
        await self._session_store.save_session_record(
            snapshot.execution_id,
            workspace_id=snapshot.workspace_id,
            actor_slug=snapshot.actor_slug,
            orchestration_mode=snapshot.orchestration_type.value,
            effort_level=snapshot.effort_level.value,
            status=snapshot.status,
            snapshot_payload=snapshot.model_dump(mode="json"),
            expires_at_utc=snapshot.expires_at_utc,
        )
