"""Synchronous chunk and evaluation helpers for `AdaptiveHumanGateService` (`Story 4.3`)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any, Literal

from orcia_core.gates._gate_locales import get_gate_locale_bundle
from orcia_core.gates._human_models import (
    AUTO_PASS_MIN_AGENTIC_SCORE,
    RUBBER_STAMPING_MIN_DURATION_MS,
    RUBBER_STAMPING_WORD_THRESHOLD,
    SAMPLING_RATE_PERCENT,
    ChunkApprovalRecord,
    ChunkDecisionAction,
    HumanGateEvaluationRecord,
    HumanGatePolicy,
    build_default_human_briefing,
    compute_sampling_bucket,
    count_words,
    extract_chunks_from_payload,
)
from orcia_core.gates.errors import (
    HumanGateNotFoundError,
    RubberStampingGuardTriggeredError,
    UnapprovedChunksRemainingError,
)
from orcia_kernel.enums import DEFAULT_LOCALE
from orcia_kernel.events import GateEvaluated
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import OutboxRelayPort


def apply_chunk_decision(
    record: HumanGateEvaluationRecord,
    chunk_key: str,
    *,
    action: ChunkDecisionAction,
    reviewer_user_id: str,
    co_edited_content: str | None = None,
    challenge_reason: str | None = None,
    locale: str = DEFAULT_LOCALE,
) -> ChunkApprovalRecord:
    """Apply `APPROVE`, `CO_EDIT`, or `CHALLENGE` to a target Human Gate chunk."""
    target = next((c for c in record.chunks if c.chunk_key == chunk_key), None)
    if target is None:
        raise HumanGateNotFoundError(
            detail_override=f"Chunk '{chunk_key}' not found in Human Gate '{record.id}'."
        )
    target.reviewer_user_id = reviewer_user_id
    target.reviewed_at = datetime.now(UTC)
    if action == "APPROVE":
        target.status = "APPROVED"
    elif action == "CO_EDIT":
        updated_text = (
            co_edited_content if co_edited_content is not None else target.content_markdown
        )
        target.content_markdown = updated_text
        target.word_count = count_words(updated_text)
        target.status = "CO_EDITED"
        target.human_anchor_signature_id = new_uuid7_str()
        target.human_anchor_sha256 = hashlib.sha256(updated_text.encode("utf-8")).hexdigest()
        record.total_word_count = sum(c.word_count for c in record.chunks)
    elif action == "CHALLENGE":
        target.status = "CHALLENGED"
        target.challenge_reason = (
            challenge_reason or get_gate_locale_bundle(locale).human_default_challenge_reason
        )
        record.status = "FAIL"
    return target


def validate_and_finalize_record(
    record: HumanGateEvaluationRecord,
    *,
    reviewer_user_id: str,
    review_duration_ms: int,
    explicit_hypotheses_confirmation: bool = False,
) -> None:
    """Validate chunk completion and `<15s` rubber-stamping guard before finalizing."""
    if explicit_hypotheses_confirmation:
        record.hypotheses_block_inspected = True
    unapproved = [c.chunk_key for c in record.chunks if c.status not in ("APPROVED", "CO_EDITED")]
    if unapproved or not record.hypotheses_block_inspected:
        raise UnapprovedChunksRemainingError(
            detail_override=(
                f"Cannot finalize Human Gate '{record.id}': "
                f"unapproved chunks={unapproved}, "
                f"hypotheses_inspected={record.hypotheses_block_inspected}."
            )
        )
    record.review_duration_ms = max(0, review_duration_ms)
    record.reviewer_user_id = reviewer_user_id
    if (
        record.total_word_count > RUBBER_STAMPING_WORD_THRESHOLD
        and record.review_duration_ms < RUBBER_STAMPING_MIN_DURATION_MS
    ):
        record.fast_approval_warning = True
        if not explicit_hypotheses_confirmation:
            raise RubberStampingGuardTriggeredError(
                detail_override=(
                    f"Fast approval detected ({record.review_duration_ms} ms < "
                    f"{RUBBER_STAMPING_MIN_DURATION_MS} ms on "
                    f"{record.total_word_count} words). "
                    "Explicit confirmation of retained hypotheses is required."
                )
            )
    record.status = "PASS"
    record.evaluated_at = datetime.now(UTC)


def enqueue_human_gate_event(
    *,
    outbox_events: list[GateEvaluated],
    outbox_relay: OutboxRelayPort | None,
    gate_evaluation_id: str,
    workspace_id: str,
    run_id: str,
    passed: bool,
    score: float,
) -> str:
    """Build and enqueue a `GateEvaluated` event for a Human Gate."""
    outbox_evt = GateEvaluated.create(
        gate_evaluation_id=gate_evaluation_id,
        run_id=run_id,
        workspace_id=workspace_id,
        gate_type="HUMAN",
        passed=passed,
        score=score,
    )
    outbox_events.append(outbox_evt)
    if outbox_relay is not None:
        outbox_relay.enqueue_in_transaction(outbox_evt)
    return outbox_evt.event_id


def mark_hypotheses_inspected(
    record: HumanGateEvaluationRecord, *, reviewer_user_id: str
) -> HumanGateEvaluationRecord:
    """Mark Block 4 (`Retained Hypotheses`) as inspected on the briefing."""
    record.hypotheses_block_inspected = True
    record.reviewer_user_id = reviewer_user_id
    block4: Any = record.briefing_4blocks_jsonb.get("block_4_retained_hypotheses")
    if isinstance(block4, dict):
        block4["requires_human_inspection"] = False
        block4["inspected_by"] = reviewer_user_id
    return record


def build_human_gate_evaluation_record(
    *,
    outbox_events: list[GateEvaluated],
    outbox_relay: OutboxRelayPort | None,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
    step_key: str,
    policy: HumanGatePolicy,
    artifact_payload: dict[str, Any],
    deterministic_status: str,
    agentic_score: float,
    ontology_conflicts: int,
    stale_warnings: int,
    briefing_4blocks_jsonb: dict[str, Any] | None,
    sampling_override: bool | None,
    locale: str,
) -> HumanGateEvaluationRecord:
    """Create and evaluate a `HumanGateEvaluationRecord` with auto-pass/sampling rules."""
    eval_id = new_uuid7_str()
    chunks = extract_chunks_from_payload(
        gate_evaluation_id=eval_id,
        workspace_id=workspace_id,
        run_id=run_id,
        step_execution_id=step_execution_id,
        artifact_payload=artifact_payload,
        locale=locale,
    )
    total_words = sum(c.word_count for c in chunks)
    has_human_anchor = any(c.human_authored_required for c in chunks) or bool(
        artifact_payload.get("human_authored_required", False)
    )
    eligible = (
        deterministic_status == "PASS"
        and agentic_score >= AUTO_PASS_MIN_AGENTIC_SCORE
        and ontology_conflicts == 0
        and stale_warnings == 0
        and not has_human_anchor
    )
    requires_human = True
    if policy == "risk_or_exception_based":
        requires_human = not eligible
    elif policy == "sampling":
        if not eligible:
            requires_human = True
        elif sampling_override is not None:
            requires_human = sampling_override
        else:
            requires_human = (
                compute_sampling_bucket(run_id, step_execution_id) < SAMPLING_RATE_PERCENT
            )

    default_briefing = briefing_4blocks_jsonb or build_default_human_briefing(
        step_key=step_key,
        chunk_count=len(chunks),
        ontology_conflicts=ontology_conflicts,
        stale_warnings=stale_warnings,
        artifact_payload=artifact_payload,
        locale=locale,
    )
    status: Literal["PASS", "FAIL", "PENDING_HUMAN_REVIEW"] = (
        "PENDING_HUMAN_REVIEW" if requires_human else "PASS"
    )
    outbox_event_id: str | None = None
    if status == "PASS":
        for chunk in chunks:
            chunk.status = "APPROVED"
            chunk.reviewed_at = datetime.now(UTC)
        outbox_event_id = enqueue_human_gate_event(
            outbox_events=outbox_events,
            outbox_relay=outbox_relay,
            gate_evaluation_id=eval_id,
            workspace_id=workspace_id,
            run_id=run_id,
            passed=True,
            score=agentic_score,
        )
    return HumanGateEvaluationRecord(
        id=eval_id,
        workspace_id=workspace_id,
        run_id=run_id,
        step_execution_id=step_execution_id,
        step_key=step_key,
        policy=policy,
        status=status,
        auto_passed=not requires_human,
        deterministic_status=deterministic_status,
        agentic_score=agentic_score,
        ontology_conflicts=ontology_conflicts,
        stale_warnings=stale_warnings,
        total_word_count=total_words,
        briefing_4blocks_jsonb=default_briefing,
        hypotheses_block_inspected=not requires_human,
        chunks=chunks,
        outbox_event_id=outbox_event_id,
    )
