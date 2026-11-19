"""Row mappers & Outbox persistence helpers for `SqlGateEvaluationRepository` (`REM-11`)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.gates._internal._sql_gate_parents import coerce_gate_uuid
from orcia_core.gates.human import (
    ChunkApprovalRecord,
    ChunkApprovalStatus,
    HumanGateEvaluationRecord,
    HumanGatePolicy,
)
from orcia_core.gates.models import (
    GateEvaluationEntity,
    GateStatus,
    GateType,
    PatternDriftFinding,
    SandboxTierLiteral,
)
from orcia_kernel.events import GateEvaluated


def parse_json_field(raw: Any, fallback: Any) -> Any:
    """Decode JSONB string or return pre-decoded Python collection."""
    if raw is None:
        return fallback
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


async def enqueue_gate_outbox_event_in_conn(
    conn: AsyncConnection,
    *,
    outbox_event_id: str | None,
    gate_eval_id: str,
    run_id: str,
    workspace_id: str,
    gate_type: GateType,
    passed: bool,
    score: float,
) -> None:
    """Persist `GateEvaluated` in `domain_events_outbox` inside the same ACID transaction."""
    if not outbox_event_id:
        return
    evt = GateEvaluated.create(
        gate_evaluation_id=gate_eval_id,
        run_id=run_id,
        workspace_id=workspace_id,
        gate_type=gate_type,
        passed=passed,
        score=score,
    )
    await conn.execute(
        sa.text(
            """
            INSERT INTO domain_events_outbox (
                event_id, event_type, aggregate_type, aggregate_id,
                run_id, workspace_id, payload_jsonb, trace_id, status, attempts
            ) VALUES (
                CAST(:event_id AS uuid), :event_type, :aggregate_type, :aggregate_id,
                CAST(:run_id AS uuid), CAST(:workspace_id AS uuid),
                CAST(:payload_jsonb AS jsonb), :trace_id, 'PENDING', 0
            )
            ON CONFLICT (event_id) DO NOTHING;
            """
        ),
        {
            "event_id": str(coerce_gate_uuid(outbox_event_id)),
            "event_type": evt.event_type,
            "aggregate_type": evt.aggregate_type,
            "aggregate_id": gate_eval_id,
            "run_id": run_id,
            "workspace_id": workspace_id,
            "payload_jsonb": json.dumps(evt.payload, sort_keys=True),
            "trace_id": evt.trace_id,
        },
    )


def row_to_gate_entity(row: dict[str, Any]) -> GateEvaluationEntity:
    """Map a PG18 `gate_evaluations` row onto `GateEvaluationEntity`."""
    drift_raw = parse_json_field(row["pattern_drift_findings_jsonb"], [])
    lens_raw = parse_json_field(row["lens_findings_jsonb"], [])
    briefing_raw = dict(parse_json_field(row["briefing_4blocks_jsonb"], {}))
    det_meta = briefing_raw.pop("_det_meta", {})
    briefing_raw.pop("_human_gate_meta", None)
    ev_at = row["evaluated_at"]
    ev_iso = ev_at.isoformat() if isinstance(ev_at, datetime) else str(ev_at or "")
    return GateEvaluationEntity(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        run_id=str(row["run_id"]),
        step_execution_id=str(row["step_execution_id"]),
        step_key=str(row["step_key"]),
        gate_type=cast(GateType, str(row["gate_type"])),
        sandbox_tier=cast(SandboxTierLiteral, str(row["sandbox_tier"])),
        status=cast(GateStatus, str(row["status"])),
        score=float(row["score"]),
        schema_validation_passed=bool(row["schema_validation_passed"]),
        ontology_axioms_passed=bool(row["ontology_axioms_passed"]),
        pattern_drift_passed=bool(row["pattern_drift_passed"]),
        pattern_drift_findings=tuple(
            PatternDriftFinding(
                rule_id=str(d.get("rule_id", "")),
                forbidden_symbol=str(d.get("forbidden_symbol", "")),
                severity=str(d.get("severity", "HIGH")),
                message=str(d.get("message", "")),
            )
            for d in drift_raw
            if isinstance(d, dict)
        ),
        missing_sections=tuple(str(s) for s in (det_meta.get("missing_sections") or [])),
        violated_axioms=tuple(dict(a) for a in (det_meta.get("violated_axioms") or [])),
        lens_findings=tuple(dict(f) for f in lens_raw if isinstance(f, dict)),
        briefing_4blocks=briefing_raw,
        evaluator_model_id=(str(row["evaluator_model_id"]) if row["evaluator_model_id"] else None),
        duration_ms=int(row["duration_ms"]),
        review_duration_ms=int(row["review_duration_ms"]),
        fast_approval_warning=bool(row["fast_approval_warning"]),
        outbox_event_id=str(row["outbox_event_id"]) if row["outbox_event_id"] else None,
        evaluated_at=ev_iso,
        sandbox_exit_code=int(det_meta.get("sandbox_exit_code", 0)),
        sandbox_stderr=str(det_meta.get("sandbox_stderr", "")),
    )


def row_to_human_record(
    row: dict[str, Any], chunk_rows: list[dict[str, Any]]
) -> HumanGateEvaluationRecord:
    """Map PG18 `gate_evaluations` + `chunk_approvals` rows onto `HumanGateEvaluationRecord`."""
    briefing_raw = dict(parse_json_field(row["briefing_4blocks_jsonb"], {}))
    meta = dict(briefing_raw.pop("_human_gate_meta", {}) or {})
    sha_map: dict[str, str] = dict(meta.get("chunk_sha256_map") or {})
    chunks = [
        ChunkApprovalRecord(
            id=str(c["id"]),
            gate_evaluation_id=str(c["gate_evaluation_id"]),
            workspace_id=str(c["workspace_id"]),
            run_id=str(c["run_id"]),
            step_execution_id=str(c["step_execution_id"]),
            chunk_key=str(c["chunk_key"]),
            section_title=str(c["section_title"]),
            section_index=int(c["section_index"]),
            content_markdown=str(c["content_markdown"]),
            word_count=int(c["word_count"]),
            human_authored_required=bool(c["human_authored_required"]),
            status=cast(ChunkApprovalStatus, str(c["status"])),
            reviewer_user_id=str(c["reviewer_user_id"]) if c["reviewer_user_id"] else None,
            human_anchor_signature_id=(
                str(c["human_anchor_signature_id"]) if c["human_anchor_signature_id"] else None
            ),
            human_anchor_sha256=sha_map.get(str(c["chunk_key"])),
            challenge_reason=str(c["challenge_reason"]) if c["challenge_reason"] else None,
            reviewed_at=c["reviewed_at"],
        )
        for c in chunk_rows
    ]
    block4 = briefing_raw.get("block_4_retained_hypotheses")
    block4_inspected = isinstance(block4, dict) and block4.get("requires_human_inspection") is False
    ev_at = row["evaluated_at"]
    evaluated_dt = ev_at if isinstance(ev_at, datetime) else datetime.now(UTC)
    status_raw = str(row["status"])
    status_typed: Any = (
        status_raw
        if status_raw in ("PASS", "FAIL", "PENDING_HUMAN_REVIEW")
        else "PENDING_HUMAN_REVIEW"
    )
    return HumanGateEvaluationRecord(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        run_id=str(row["run_id"]),
        step_execution_id=str(row["step_execution_id"]),
        step_key=str(row["step_key"]),
        policy=cast(HumanGatePolicy, str(meta.get("policy", "mandatory_full"))),
        status=status_typed,
        auto_passed=bool(meta.get("auto_passed", False)),
        deterministic_status=str(
            meta.get(
                "deterministic_status",
                "PASS" if row["schema_validation_passed"] else "FAIL",
            )
        ),
        agentic_score=float(meta.get("agentic_score", row["score"])),
        ontology_conflicts=int(
            meta.get("ontology_conflicts", 0 if row["ontology_axioms_passed"] else 1)
        ),
        stale_warnings=int(meta.get("stale_warnings", 0)),
        total_word_count=int(meta.get("total_word_count", sum(c.word_count for c in chunks))),
        briefing_4blocks_jsonb=briefing_raw,
        hypotheses_block_inspected=bool(meta.get("hypotheses_block_inspected", block4_inspected)),
        chunks=chunks,
        review_duration_ms=int(row["review_duration_ms"]),
        fast_approval_warning=bool(row["fast_approval_warning"]),
        reviewer_user_id=(str(meta["reviewer_user_id"]) if meta.get("reviewer_user_id") else None),
        outbox_event_id=str(row["outbox_event_id"]) if row["outbox_event_id"] else None,
        evaluated_at=evaluated_dt,
    )
