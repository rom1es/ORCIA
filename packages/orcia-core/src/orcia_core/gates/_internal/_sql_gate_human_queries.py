"""Async SQL query helpers for Human Gate & Chunk Approval persistence (`0017`, `0018`)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.gates._internal._sql_gate_mappers import (
    enqueue_gate_outbox_event_in_conn,
    row_to_human_record,
)
from orcia_core.gates._internal._sql_gate_parents import (
    coerce_gate_uuid,
    ensure_chunk_anchor_signature,
    ensure_gate_parents,
)
from orcia_core.gates.human import ChunkApprovalRecord, HumanGateEvaluationRecord


async def upsert_chunk_approval_in_conn(
    conn: AsyncConnection,
    *,
    chunk: ChunkApprovalRecord,
    gate_eval_id: str,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
    step_key: str,
) -> None:
    """Persist or update one `chunk_approvals` row inside an active SQL transaction."""
    sig_uuid = await ensure_chunk_anchor_signature(
        conn,
        signature_id=chunk.human_anchor_signature_id,
        workspace_id=workspace_id,
        run_id=run_id,
        step_execution_id=step_execution_id,
        step_key=step_key,
        chunk_key=chunk.chunk_key,
        content_markdown=chunk.content_markdown,
        content_sha256=chunk.human_anchor_sha256,
        reviewer_user_id=chunk.reviewer_user_id,
    )
    await conn.execute(
        sa.text(
            """
            INSERT INTO chunk_approvals (
                id, gate_evaluation_id, workspace_id, run_id, step_execution_id,
                chunk_key, section_title, section_index, content_markdown,
                word_count, human_authored_required, status, reviewer_user_id,
                human_anchor_signature_id, challenge_reason, reviewed_at
            ) VALUES (
                CAST(:id AS uuid), CAST(:gate_id AS uuid), CAST(:ws_id AS uuid),
                CAST(:run_id AS uuid), CAST(:step_id AS uuid),
                :chunk_key, :section_title, :section_index, :content_markdown,
                :word_count, :human_req, :status, :reviewer_user_id,
                CAST(:sig_id AS uuid), :challenge_reason, :reviewed_at
            )
            ON CONFLICT (gate_evaluation_id, chunk_key) DO UPDATE SET
                content_markdown = EXCLUDED.content_markdown,
                word_count = EXCLUDED.word_count,
                status = EXCLUDED.status,
                reviewer_user_id = EXCLUDED.reviewer_user_id,
                human_anchor_signature_id = EXCLUDED.human_anchor_signature_id,
                challenge_reason = EXCLUDED.challenge_reason,
                reviewed_at = EXCLUDED.reviewed_at;
            """
        ),
        {
            "id": str(coerce_gate_uuid(chunk.id)),
            "gate_id": gate_eval_id,
            "ws_id": workspace_id,
            "run_id": run_id,
            "step_id": step_execution_id,
            "chunk_key": chunk.chunk_key[:128],
            "section_title": chunk.section_title[:255],
            "section_index": max(0, int(chunk.section_index)),
            "content_markdown": chunk.content_markdown,
            "word_count": max(0, int(chunk.word_count)),
            "human_req": bool(chunk.human_authored_required),
            "status": chunk.status,
            "reviewer_user_id": (chunk.reviewer_user_id[:128] if chunk.reviewer_user_id else None),
            "sig_id": sig_uuid,
            "challenge_reason": chunk.challenge_reason,
            "reviewed_at": chunk.reviewed_at,
        },
    )


async def save_human_evaluation_sql(engine: AsyncEngine, record: HumanGateEvaluationRecord) -> None:
    """Persist or update a `HUMAN` gate evaluation + `chunk_approvals` in PG18."""
    eval_uuid = str(coerce_gate_uuid(record.id))
    briefing_copy = dict(record.briefing_4blocks_jsonb)
    briefing_copy["_human_gate_meta"] = {
        "policy": record.policy,
        "auto_passed": record.auto_passed,
        "deterministic_status": record.deterministic_status,
        "agentic_score": record.agentic_score,
        "ontology_conflicts": record.ontology_conflicts,
        "stale_warnings": record.stale_warnings,
        "total_word_count": record.total_word_count,
        "hypotheses_block_inspected": record.hypotheses_block_inspected,
        "reviewer_user_id": record.reviewer_user_id,
        "chunk_sha256_map": {
            c.chunk_key: c.human_anchor_sha256 for c in record.chunks if c.human_anchor_sha256
        },
    }
    async with engine.begin() as conn:
        ws_id, run_id, step_id = await ensure_gate_parents(
            conn,
            workspace_id=record.workspace_id,
            run_id=record.run_id,
            step_execution_id=record.step_execution_id,
            step_key=record.step_key,
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO gate_evaluations (
                    id, workspace_id, run_id, step_execution_id, step_key,
                    gate_type, sandbox_tier, status, score,
                    schema_validation_passed, ontology_axioms_passed,
                    pattern_drift_passed, pattern_drift_findings_jsonb,
                    lens_findings_jsonb, briefing_4blocks_jsonb,
                    evaluator_model_id, duration_ms, review_duration_ms,
                    fast_approval_warning, outbox_event_id, evaluated_at
                ) VALUES (
                    CAST(:id AS uuid), CAST(:ws_id AS uuid), CAST(:run_id AS uuid),
                    CAST(:step_id AS uuid), :step_key, 'HUMAN', 'NONE',
                    :status, :score, :schema_ok, :ontology_ok, TRUE,
                    '[]'::jsonb, '[]'::jsonb, CAST(:briefing_json AS jsonb),
                    NULL, 0, :review_duration_ms, :fast_warning,
                    CAST(:outbox_id AS uuid), :evaluated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    score = EXCLUDED.score,
                    briefing_4blocks_jsonb = EXCLUDED.briefing_4blocks_jsonb,
                    review_duration_ms = EXCLUDED.review_duration_ms,
                    fast_approval_warning = EXCLUDED.fast_approval_warning,
                    outbox_event_id = EXCLUDED.outbox_event_id,
                    evaluated_at = EXCLUDED.evaluated_at;
                """
            ),
            {
                "id": eval_uuid,
                "ws_id": ws_id,
                "run_id": run_id,
                "step_id": step_id,
                "step_key": record.step_key[:128],
                "status": record.status,
                "score": float(max(0.0, min(1.0, record.agentic_score))),
                "schema_ok": record.deterministic_status == "PASS",
                "ontology_ok": record.ontology_conflicts == 0,
                "briefing_json": json.dumps(briefing_copy),
                "review_duration_ms": max(0, int(record.review_duration_ms)),
                "fast_warning": bool(record.fast_approval_warning),
                "outbox_id": (
                    str(coerce_gate_uuid(record.outbox_event_id))
                    if record.outbox_event_id
                    else None
                ),
                "evaluated_at": record.evaluated_at,
            },
        )
        for chunk in record.chunks:
            await upsert_chunk_approval_in_conn(
                conn,
                chunk=chunk,
                gate_eval_id=eval_uuid,
                workspace_id=ws_id,
                run_id=run_id,
                step_execution_id=step_id,
                step_key=record.step_key,
            )
        await enqueue_gate_outbox_event_in_conn(
            conn,
            outbox_event_id=record.outbox_event_id,
            gate_eval_id=eval_uuid,
            run_id=run_id,
            workspace_id=ws_id,
            gate_type="HUMAN",
            passed=(record.status == "PASS"),
            score=record.agentic_score,
        )


async def list_human_evaluations_sql(
    engine: AsyncEngine, *, workspace_id: str | None = None
) -> list[HumanGateEvaluationRecord]:
    """List `HUMAN` evaluations and batch-fetch `chunk_approvals` from PostgreSQL 18."""
    params: dict[str, Any] = {}
    ws_filter = ""
    if workspace_id is not None:
        ws_filter = "AND workspace_id = CAST(:ws_id AS uuid)"
        params["ws_id"] = str(coerce_gate_uuid(workspace_id))
    async with engine.connect() as conn:
        rows = (
            (
                await conn.execute(
                    sa.text(
                        f"""
                        SELECT
                            id::text, workspace_id::text, run_id::text,
                            step_execution_id::text, step_key, status,
                            score::float8, schema_validation_passed,
                            ontology_axioms_passed, briefing_4blocks_jsonb,
                            review_duration_ms, fast_approval_warning,
                            outbox_event_id::text, evaluated_at
                        FROM gate_evaluations
                        WHERE gate_type = 'HUMAN' {ws_filter}
                        ORDER BY evaluated_at ASC, id ASC;
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        if not rows:
            return []
        gate_ids = [str(r["id"]) for r in rows]
        chunk_rows = (
            (
                await conn.execute(
                    sa.text(
                        """
                        SELECT
                            id::text, gate_evaluation_id::text, workspace_id::text,
                            run_id::text, step_execution_id::text, chunk_key,
                            section_title, section_index, content_markdown,
                            word_count, human_authored_required, status,
                            reviewer_user_id, human_anchor_signature_id::text,
                            challenge_reason, reviewed_at
                        FROM chunk_approvals
                        WHERE gate_evaluation_id::text = ANY(:gate_ids)
                        ORDER BY section_index ASC, id ASC;
                        """
                    ),
                    {"gate_ids": gate_ids},
                )
            )
            .mappings()
            .all()
        )
        chunks_by_gate: dict[str, list[dict[str, Any]]] = {}
        for c in chunk_rows:
            chunks_by_gate.setdefault(str(c["gate_evaluation_id"]), []).append(dict(c))
        return [row_to_human_record(dict(r), chunks_by_gate.get(str(r["id"]), [])) for r in rows]
