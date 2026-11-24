"""Story 4.3: Adaptive Human Gates, 4-Block Review Briefing, Chunked Validation & <15s Guard."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orcia_core.gates._human_gate_async import (
    decide_chunk_async_op,
    evaluate_human_gate_async_op,
    finalize_human_gate_async_op,
    get_evaluation_async_op,
    list_evaluations_async_op,
)
from orcia_core.gates._human_gate_ops import (
    apply_chunk_decision,
    build_human_gate_evaluation_record,
    enqueue_human_gate_event,
    mark_hypotheses_inspected,
    validate_and_finalize_record,
)
from orcia_core.gates._human_models import (
    AUTO_PASS_MIN_AGENTIC_SCORE,
    RUBBER_STAMPING_MIN_DURATION_MS,
    RUBBER_STAMPING_WORD_THRESHOLD,
    SAMPLING_RATE_PERCENT,
    ChunkApprovalRecord,
    ChunkApprovalStatus,
    ChunkDecisionAction,
    HumanGateEvaluationRecord,
    HumanGatePolicy,
    compute_sampling_bucket,
    count_words,
)
from orcia_core.gates.errors import HumanGateNotFoundError
from orcia_kernel.enums import DEFAULT_LOCALE
from orcia_kernel.events import GateEvaluated
from orcia_kernel.ports import OutboxRelayPort

if TYPE_CHECKING:
    from orcia_core.gates._internal.sql_gate_repository import SqlGateEvaluationRepository

__all__ = [
    "AUTO_PASS_MIN_AGENTIC_SCORE",
    "RUBBER_STAMPING_MIN_DURATION_MS",
    "RUBBER_STAMPING_WORD_THRESHOLD",
    "SAMPLING_RATE_PERCENT",
    "AdaptiveHumanGateService",
    "ChunkApprovalRecord",
    "ChunkApprovalStatus",
    "ChunkDecisionAction",
    "HumanGateEvaluationRecord",
    "HumanGatePolicy",
    "compute_sampling_bucket",
    "count_words",
]


class AdaptiveHumanGateService:
    """Service orchestrating Adaptive Human Gates, Chunked Approvals & Anti-Rubber-Stamping."""

    def __init__(
        self,
        *,
        outbox_relay: OutboxRelayPort | None = None,
        repository: SqlGateEvaluationRepository | None = None,
    ) -> None:
        self._outbox_relay = outbox_relay
        self._repository = repository
        self._outbox_events: list[GateEvaluated] = []
        self._evaluations: dict[str, HumanGateEvaluationRecord] = {}

    def set_repository(self, repository: SqlGateEvaluationRepository | None) -> None:
        """Attach PostgreSQL 18 repository (`SqlGateEvaluationRepository`) in Composition Root."""
        self._repository = repository

    def list_outbox_events(self) -> list[GateEvaluated]:
        return list(self._outbox_events)

    def get_evaluation(self, gate_evaluation_id: str) -> HumanGateEvaluationRecord:
        record = self._evaluations.get(gate_evaluation_id)
        if record is None:
            raise HumanGateNotFoundError(
                detail_override=f"Human Gate evaluation '{gate_evaluation_id}' not found."
            )
        return record

    def list_evaluations(
        self, *, workspace_id: str | None = None
    ) -> list[HumanGateEvaluationRecord]:
        items = list(self._evaluations.values())
        if workspace_id is not None:
            items = [e for e in items if e.workspace_id == workspace_id]
        return items

    def evaluate_human_gate(
        self,
        *,
        workspace_id: str,
        run_id: str,
        step_execution_id: str,
        step_key: str,
        policy: HumanGatePolicy,
        artifact_payload: dict[str, Any],
        deterministic_status: str = "PASS",
        agentic_score: float = 0.92,
        ontology_conflicts: int = 0,
        stale_warnings: int = 0,
        briefing_4blocks_jsonb: dict[str, Any] | None = None,
        sampling_override: bool | None = None,
        trace_id: str | None = None,
        locale: str = DEFAULT_LOCALE,
    ) -> HumanGateEvaluationRecord:
        """Evaluate whether a Human Gate auto-passes or requires chunked human review (`AD-11`)."""
        _ = trace_id
        record = build_human_gate_evaluation_record(
            outbox_events=self._outbox_events,
            outbox_relay=self._outbox_relay,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            policy=policy,
            artifact_payload=artifact_payload,
            deterministic_status=deterministic_status,
            agentic_score=agentic_score,
            ontology_conflicts=ontology_conflicts,
            stale_warnings=stale_warnings,
            briefing_4blocks_jsonb=briefing_4blocks_jsonb,
            sampling_override=sampling_override,
            locale=locale,
        )
        self._evaluations[record.id] = record
        return record

    def inspect_briefing_hypotheses(
        self, gate_evaluation_id: str, *, reviewer_user_id: str
    ) -> HumanGateEvaluationRecord:
        return mark_hypotheses_inspected(
            self.get_evaluation(gate_evaluation_id), reviewer_user_id=reviewer_user_id
        )

    def decide_chunk(
        self,
        gate_evaluation_id: str,
        chunk_key: str,
        *,
        action: ChunkDecisionAction,
        reviewer_user_id: str,
        co_edited_content: str | None = None,
        challenge_reason: str | None = None,
        locale: str = DEFAULT_LOCALE,
    ) -> ChunkApprovalRecord:
        return apply_chunk_decision(
            self.get_evaluation(gate_evaluation_id),
            chunk_key,
            action=action,
            reviewer_user_id=reviewer_user_id,
            co_edited_content=co_edited_content,
            challenge_reason=challenge_reason,
            locale=locale,
        )

    def finalize_human_gate(
        self,
        gate_evaluation_id: str,
        *,
        reviewer_user_id: str,
        review_duration_ms: int,
        explicit_hypotheses_confirmation: bool = False,
        trace_id: str | None = None,
    ) -> HumanGateEvaluationRecord:
        _ = trace_id
        record = self.get_evaluation(gate_evaluation_id)
        validate_and_finalize_record(
            record,
            reviewer_user_id=reviewer_user_id,
            review_duration_ms=review_duration_ms,
            explicit_hypotheses_confirmation=explicit_hypotheses_confirmation,
        )
        record.outbox_event_id = enqueue_human_gate_event(
            outbox_events=self._outbox_events,
            outbox_relay=self._outbox_relay,
            gate_evaluation_id=record.id,
            workspace_id=record.workspace_id,
            run_id=record.run_id,
            passed=True,
            score=1.0,
        )
        return record

    async def get_evaluation_async(self, gate_evaluation_id: str) -> HumanGateEvaluationRecord:
        return await get_evaluation_async_op(self, gate_evaluation_id)

    async def list_evaluations_async(
        self, *, workspace_id: str | None = None
    ) -> list[HumanGateEvaluationRecord]:
        return await list_evaluations_async_op(self, workspace_id=workspace_id)

    async def evaluate_human_gate_async(
        self,
        *,
        workspace_id: str,
        run_id: str,
        step_execution_id: str,
        step_key: str,
        policy: HumanGatePolicy,
        artifact_payload: dict[str, Any],
        deterministic_status: str = "PASS",
        agentic_score: float = 0.92,
        ontology_conflicts: int = 0,
        stale_warnings: int = 0,
        briefing_4blocks_jsonb: dict[str, Any] | None = None,
        sampling_override: bool | None = None,
        trace_id: str | None = None,
        locale: str = DEFAULT_LOCALE,
    ) -> HumanGateEvaluationRecord:
        return await evaluate_human_gate_async_op(
            self,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            step_key=step_key,
            policy=policy,
            artifact_payload=artifact_payload,
            deterministic_status=deterministic_status,
            agentic_score=agentic_score,
            ontology_conflicts=ontology_conflicts,
            stale_warnings=stale_warnings,
            briefing_4blocks_jsonb=briefing_4blocks_jsonb,
            sampling_override=sampling_override,
            trace_id=trace_id,
            locale=locale,
        )

    async def inspect_briefing_hypotheses_async(
        self, gate_evaluation_id: str, *, reviewer_user_id: str
    ) -> HumanGateEvaluationRecord:
        await get_evaluation_async_op(self, gate_evaluation_id)
        updated = self.inspect_briefing_hypotheses(
            gate_evaluation_id, reviewer_user_id=reviewer_user_id
        )
        if self._repository is not None:
            await self._repository.save_human_evaluation(updated)
        return updated

    async def decide_chunk_async(
        self,
        gate_evaluation_id: str,
        chunk_key: str,
        *,
        action: ChunkDecisionAction,
        reviewer_user_id: str,
        co_edited_content: str | None = None,
        challenge_reason: str | None = None,
        locale: str = DEFAULT_LOCALE,
    ) -> tuple[ChunkApprovalRecord, HumanGateEvaluationRecord]:
        return await decide_chunk_async_op(
            self,
            gate_evaluation_id,
            chunk_key,
            action=action,
            reviewer_user_id=reviewer_user_id,
            co_edited_content=co_edited_content,
            challenge_reason=challenge_reason,
            locale=locale,
        )

    async def finalize_human_gate_async(
        self,
        gate_evaluation_id: str,
        *,
        reviewer_user_id: str,
        review_duration_ms: int,
        explicit_hypotheses_confirmation: bool = False,
        trace_id: str | None = None,
    ) -> HumanGateEvaluationRecord:
        return await finalize_human_gate_async_op(
            self,
            gate_evaluation_id,
            reviewer_user_id=reviewer_user_id,
            review_duration_ms=review_duration_ms,
            explicit_hypotheses_confirmation=explicit_hypotheses_confirmation,
            trace_id=trace_id,
        )
