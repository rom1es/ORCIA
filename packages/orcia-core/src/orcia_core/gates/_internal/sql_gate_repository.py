"""PostgreSQL 18 Repository for Deterministic, Agentic & Human Gates (`0017`, `0018`, `REM-11`)."""

from __future__ import annotations

import json
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.gates._internal._sql_gate_human_queries import (
    list_human_evaluations_sql,
    save_human_evaluation_sql,
)
from orcia_core.gates._internal._sql_gate_mappers import (
    enqueue_gate_outbox_event_in_conn,
    row_to_gate_entity,
    row_to_human_record,
)
from orcia_core.gates._internal._sql_gate_parents import coerce_gate_uuid, ensure_gate_parents
from orcia_core.gates.human import HumanGateEvaluationRecord
from orcia_core.gates.models import GateEvaluationEntity, GateType


class SqlGateEvaluationRepository:
    """Async SQLAlchemy 2.1 (`asyncpg`) repository for `gate_evaluations` & `chunk_approvals`."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save_gate_evaluation(self, entity: GateEvaluationEntity) -> None:
        """Persist or update a Deterministic or Agentic `GateEvaluationEntity` in PG18."""
        eval_uuid = str(coerce_gate_uuid(entity.id))
        briefing_payload = dict(entity.briefing_4blocks)
        if (
            entity.missing_sections
            or entity.violated_axioms
            or entity.sandbox_exit_code != 0
            or entity.sandbox_stderr
        ):
            briefing_payload["_det_meta"] = {
                "missing_sections": list(entity.missing_sections),
                "violated_axioms": [dict(a) for a in entity.violated_axioms],
                "sandbox_exit_code": entity.sandbox_exit_code,
                "sandbox_stderr": entity.sandbox_stderr,
            }

        async with self._engine.begin() as conn:
            ws_id, run_id, step_id = await ensure_gate_parents(
                conn,
                workspace_id=entity.workspace_id,
                run_id=entity.run_id,
                step_execution_id=entity.step_execution_id,
                step_key=entity.step_key,
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
                        CAST(:step_id AS uuid), :step_key, :gate_type, :sandbox_tier,
                        :status, :score, :schema_ok, :axioms_ok, :drift_ok,
                        CAST(:drift_json AS jsonb), CAST(:lens_json AS jsonb),
                        CAST(:briefing_json AS jsonb), :evaluator_model_id,
                        :duration_ms, :review_duration_ms, :fast_warning,
                        CAST(:outbox_id AS uuid), NOW()
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        score = EXCLUDED.score,
                        briefing_4blocks_jsonb = EXCLUDED.briefing_4blocks_jsonb,
                        lens_findings_jsonb = EXCLUDED.lens_findings_jsonb,
                        review_duration_ms = EXCLUDED.review_duration_ms,
                        fast_approval_warning = EXCLUDED.fast_approval_warning,
                        outbox_event_id = EXCLUDED.outbox_event_id,
                        evaluated_at = NOW();
                    """
                ),
                {
                    "id": eval_uuid,
                    "ws_id": ws_id,
                    "run_id": run_id,
                    "step_id": step_id,
                    "step_key": entity.step_key[:128],
                    "gate_type": entity.gate_type,
                    "sandbox_tier": entity.sandbox_tier,
                    "status": entity.status,
                    "score": float(entity.score),
                    "schema_ok": bool(entity.schema_validation_passed),
                    "axioms_ok": bool(entity.ontology_axioms_passed),
                    "drift_ok": bool(entity.pattern_drift_passed),
                    "drift_json": json.dumps(
                        [
                            {
                                "rule_id": f.rule_id,
                                "forbidden_symbol": f.forbidden_symbol,
                                "severity": f.severity,
                                "message": f.message,
                            }
                            for f in entity.pattern_drift_findings
                        ]
                    ),
                    "lens_json": json.dumps(list(entity.lens_findings)),
                    "briefing_json": json.dumps(briefing_payload),
                    "evaluator_model_id": entity.evaluator_model_id,
                    "duration_ms": max(0, int(entity.duration_ms)),
                    "review_duration_ms": max(0, int(entity.review_duration_ms)),
                    "fast_warning": bool(entity.fast_approval_warning),
                    "outbox_id": (
                        str(coerce_gate_uuid(entity.outbox_event_id))
                        if entity.outbox_event_id
                        else None
                    ),
                },
            )
            await enqueue_gate_outbox_event_in_conn(
                conn,
                outbox_event_id=entity.outbox_event_id,
                gate_eval_id=eval_uuid,
                run_id=run_id,
                workspace_id=ws_id,
                gate_type=entity.gate_type,
                passed=(entity.status == "PASS"),
                score=entity.score,
            )

    async def list_gate_evaluations(
        self,
        *,
        run_id: str | None = None,
        gate_type: GateType | None = None,
    ) -> list[GateEvaluationEntity]:
        """List Deterministic / Agentic / Human evaluations from PostgreSQL 18."""
        clauses: list[str] = []
        params: dict[str, Any] = {}
        if run_id is not None:
            clauses.append("run_id = CAST(:run_id AS uuid)")
            params["run_id"] = str(coerce_gate_uuid(run_id))
        if gate_type is not None:
            clauses.append("gate_type = :gate_type")
            params["gate_type"] = gate_type
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        async with self._engine.connect() as conn:
            rows = (
                (
                    await conn.execute(
                        sa.text(
                            f"""
                            SELECT
                                id::text, workspace_id::text, run_id::text,
                                step_execution_id::text, step_key, gate_type,
                                sandbox_tier, status, score::float8,
                                schema_validation_passed, ontology_axioms_passed,
                                pattern_drift_passed, pattern_drift_findings_jsonb,
                                lens_findings_jsonb, briefing_4blocks_jsonb,
                                evaluator_model_id, duration_ms, review_duration_ms,
                                fast_approval_warning, outbox_event_id::text, evaluated_at
                            FROM gate_evaluations
                            {where_sql}
                            ORDER BY evaluated_at ASC, id ASC;
                            """
                        ),
                        params,
                    )
                )
                .mappings()
                .all()
            )
            return [row_to_gate_entity(dict(r)) for r in rows]

    async def save_human_evaluation(self, record: HumanGateEvaluationRecord) -> None:
        """Persist or update a `HUMAN` gate evaluation + `chunk_approvals` in PG18."""
        await save_human_evaluation_sql(self._engine, record)

    async def get_human_evaluation(
        self, gate_evaluation_id: str
    ) -> HumanGateEvaluationRecord | None:
        """Read one `HUMAN` evaluation and its `chunk_approvals` from PostgreSQL 18."""
        eval_uuid = str(coerce_gate_uuid(gate_evaluation_id))
        async with self._engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT
                                id::text, workspace_id::text, run_id::text,
                                step_execution_id::text, step_key, status,
                                score::float8, schema_validation_passed,
                                ontology_axioms_passed, briefing_4blocks_jsonb,
                                review_duration_ms, fast_approval_warning,
                                outbox_event_id::text, evaluated_at
                            FROM gate_evaluations
                            WHERE id = CAST(:id AS uuid) AND gate_type = 'HUMAN'
                            LIMIT 1;
                            """
                        ),
                        {"id": eval_uuid},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
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
                            WHERE gate_evaluation_id = CAST(:id AS uuid)
                            ORDER BY section_index ASC, id ASC;
                            """
                        ),
                        {"id": eval_uuid},
                    )
                )
                .mappings()
                .all()
            )
            return row_to_human_record(dict(row), [dict(c) for c in chunk_rows])

    async def list_human_evaluations(
        self, *, workspace_id: str | None = None
    ) -> list[HumanGateEvaluationRecord]:
        """List `HUMAN` evaluations and batch-fetch `chunk_approvals` from PostgreSQL 18."""
        return await list_human_evaluations_sql(self._engine, workspace_id=workspace_id)
