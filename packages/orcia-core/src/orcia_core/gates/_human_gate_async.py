"""Async PostgreSQL 18 helpers for `AdaptiveHumanGateService` (`Story 4.3`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orcia_core.gates._human_models import (
    ChunkApprovalRecord,
    ChunkDecisionAction,
    HumanGateEvaluationRecord,
    HumanGatePolicy,
)
from orcia_core.gates.errors import HumanGateNotFoundError, RubberStampingGuardTriggeredError
from orcia_kernel.enums import DEFAULT_LOCALE

if TYPE_CHECKING:
    from orcia_core.gates.human import AdaptiveHumanGateService


async def get_evaluation_async_op(
    service: AdaptiveHumanGateService, gate_evaluation_id: str
) -> HumanGateEvaluationRecord:
    record = service._evaluations.get(gate_evaluation_id)
    if record is not None:
        return record
    if service._repository is not None:
        loaded = await service._repository.get_human_evaluation(gate_evaluation_id)
        if loaded is not None:
            service._evaluations[loaded.id] = loaded
            return loaded
    raise HumanGateNotFoundError(
        detail_override=f"Human Gate evaluation '{gate_evaluation_id}' not found."
    )


async def list_evaluations_async_op(
    service: AdaptiveHumanGateService, *, workspace_id: str | None = None
) -> list[HumanGateEvaluationRecord]:
    if service._repository is not None:
        rows = await service._repository.list_human_evaluations(workspace_id=workspace_id)
        for row in rows:
            service._evaluations[row.id] = row
        return rows
    return service.list_evaluations(workspace_id=workspace_id)


async def evaluate_human_gate_async_op(
    service: AdaptiveHumanGateService,
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
    record = service.evaluate_human_gate(
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
    if service._repository is not None:
        await service._repository.save_human_evaluation(record)
    return record


async def decide_chunk_async_op(
    service: AdaptiveHumanGateService,
    gate_evaluation_id: str,
    chunk_key: str,
    *,
    action: ChunkDecisionAction,
    reviewer_user_id: str,
    co_edited_content: str | None = None,
    challenge_reason: str | None = None,
    locale: str = DEFAULT_LOCALE,
) -> tuple[ChunkApprovalRecord, HumanGateEvaluationRecord]:
    record = await get_evaluation_async_op(service, gate_evaluation_id)
    chunk = service.decide_chunk(
        gate_evaluation_id,
        chunk_key,
        action=action,
        reviewer_user_id=reviewer_user_id,
        co_edited_content=co_edited_content,
        challenge_reason=challenge_reason,
        locale=locale,
    )
    if service._repository is not None:
        await service._repository.save_human_evaluation(record)
    return chunk, record


async def finalize_human_gate_async_op(
    service: AdaptiveHumanGateService,
    gate_evaluation_id: str,
    *,
    reviewer_user_id: str,
    review_duration_ms: int,
    explicit_hypotheses_confirmation: bool = False,
    trace_id: str | None = None,
) -> HumanGateEvaluationRecord:
    record = await get_evaluation_async_op(service, gate_evaluation_id)
    try:
        finalized = service.finalize_human_gate(
            gate_evaluation_id,
            reviewer_user_id=reviewer_user_id,
            review_duration_ms=review_duration_ms,
            explicit_hypotheses_confirmation=explicit_hypotheses_confirmation,
            trace_id=trace_id,
        )
    except RubberStampingGuardTriggeredError:
        if service._repository is not None:
            await service._repository.save_human_evaluation(record)
        raise
    if service._repository is not None:
        await service._repository.save_human_evaluation(finalized)
    return finalized
