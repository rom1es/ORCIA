"""Async SQL aggregation queries for Cognitive Impact and Human Reversibility (`Story 6.3`).

Calculates the 3 human mastery counter-metrics (`FR-27`, `SM-C1`, `SM-C2`, `SM-C3`):
1. Active Framing Ratio (SM-C2)
2. Quick-Pass Approvals Rate (SM-C1)
3. Architecture Deviation & Reversibility Index (SM-C3)

Strict Hexagonal Boundary (`AD-19 Contract 2`):
- ZERO import of `orcia_core.gates`. Queries `gate_evaluations`, `human_anchor_signatures`,
  `human_arbitration_requests`, and `workspace_exception_waivers` via pure SQL.
- File size < 350 lines.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import (
    build_cognitive_scope_clause,
    build_time_interval_clause,
    is_missing_table_error,
    safe_uuid,
)
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.audit_finops.cognitive")


async def fetch_cognitive_mastery_overview_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    time_window: str = "30D",
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Aggregate top-level cognitive mastery and human reversibility metrics."""
    default_overview: dict[str, Any] = {
        "active_framing_ms": 0,
        "review_ms": 0,
        "total_human_ms": 0,
        "human_approvals_count": 0,
        "quick_pass_approvals_count": 0,
        "total_arch_evaluations_count": 0,
        "uncovered_deviations_count": 0,
    }
    if engine is None:
        return default_overview
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return default_overview

    uuid_val = safe_uuid(scope_id)
    scope_clause_ge, params_ge = build_cognitive_scope_clause(
        scope_type, uuid_val, "ge.workspace_id", allowed_workspace_ids
    )
    scope_clause_has, params_has = build_cognitive_scope_clause(
        scope_type, uuid_val, "has.workspace_id", allowed_workspace_ids
    )
    scope_clause_har, params_har = build_cognitive_scope_clause(
        scope_type, uuid_val, "har.workspace_id", allowed_workspace_ids
    )

    tw_ge = build_time_interval_clause(time_window, "ge.evaluated_at")
    tw_has = build_time_interval_clause(time_window, "has.signed_at")
    tw_har = build_time_interval_clause(time_window, "har.created_at")

    # 1. Active framing from human anchor signatures (~200ms per char, min 30s)
    anchors_sql = sa.text(
        f"""
        SELECT COALESCE(SUM(GREATEST(has.char_length * 200, 30000)), 0) AS anchors_ms
        FROM human_anchor_signatures has
        WHERE 1=1 {scope_clause_has} {tw_has};
        """
    )

    # 2. Active framing from human arbitration requests (resolved by human)
    arbitrations_sql = sa.text(
        f"""
        SELECT COALESCE(SUM(
            CASE
                WHEN har.resolved_at IS NOT NULL AND har.resolved_at >= har.created_at
                THEN LEAST(
                    GREATEST(EXTRACT(EPOCH FROM (har.resolved_at - har.created_at)) * 1000, 15000),
                    1800000
                )
                ELSE 60000
            END
        ), 0) AS arbitrations_ms
        FROM human_arbitration_requests har
        WHERE har.status = 'RESOLVED_BY_HUMAN' {scope_clause_har} {tw_har};
        """
    )

    # 3. Gate evaluations: review durations, quick-passes, and architecture deviations
    # A quick-pass is an approval where fast_approval_warning is true, or review < 15s on text,
    # or briefing was never inspected (opened = false).
    gates_sql = sa.text(
        f"""
        SELECT
            COALESCE(
                SUM(CASE WHEN ge.gate_type = 'HUMAN' THEN ge.review_duration_ms ELSE 0 END), 0
            ) AS review_ms,
            COALESCE(SUM(
                CASE WHEN ge.gate_type = 'HUMAN' AND (
                    ge.status = 'FAIL' OR jsonb_array_length(ge.lens_findings_jsonb) > 0
                ) THEN ge.review_duration_ms ELSE 0 END
            ), 0) AS challenge_ms,
            COALESCE(SUM(
                CASE WHEN ge.gate_type = 'HUMAN' AND ge.status = 'PASS' THEN 1 ELSE 0 END
            ), 0) AS human_approvals_count,
            COALESCE(SUM(
                CASE
                    WHEN ge.gate_type = 'HUMAN' AND ge.status = 'PASS' AND (
                        ge.fast_approval_warning = TRUE
                        OR ge.review_duration_ms < 15000
                        OR (
                            ge.briefing_4blocks_jsonb->>'opened' IS NOT NULL
                            AND ge.briefing_4blocks_jsonb->>'opened' = 'false'
                        )
                    ) THEN 1
                    ELSE 0
                END
            ), 0) AS quick_pass_approvals_count,
            COUNT(*) AS total_arch_evaluations_count,
            COALESCE(SUM(
                CASE
                    WHEN ge.pattern_drift_passed = FALSE
                         AND NOT EXISTS (
                             SELECT 1 FROM workspace_exception_waivers w
                             WHERE w.workspace_id = ge.workspace_id
                               AND w.status = 'ACTIVE'
                         )
                    THEN 1
                    ELSE 0
                END
            ), 0) AS uncovered_deviations_count
        FROM gate_evaluations ge
        WHERE 1=1 {scope_clause_ge} {tw_ge};
        """
    )

    merged_params: dict[str, Any] = {**params_ge, **params_has, **params_har}

    try:
        async with engine.connect() as conn:
            anchors_res = (await conn.execute(anchors_sql, merged_params)).mappings().one()
            arbitrations_res = (
                (await conn.execute(arbitrations_sql, merged_params)).mappings().one()
            )
            gates_res = (await conn.execute(gates_sql, merged_params)).mappings().one()

            anchors_ms = int(anchors_res["anchors_ms"])
            arbitrations_ms = int(arbitrations_res["arbitrations_ms"])
            challenge_ms = int(gates_res["challenge_ms"])
            review_ms = int(gates_res["review_ms"])

            active_framing_ms = anchors_ms + arbitrations_ms + challenge_ms
            total_human_ms = active_framing_ms + review_ms

            return {
                "active_framing_ms": active_framing_ms,
                "review_ms": review_ms,
                "total_human_ms": total_human_ms,
                "human_approvals_count": int(gates_res["human_approvals_count"]),
                "quick_pass_approvals_count": int(gates_res["quick_pass_approvals_count"]),
                "total_arch_evaluations_count": int(gates_res["total_arch_evaluations_count"]),
                "uncovered_deviations_count": int(gates_res["uncovered_deviations_count"]),
            }
    except Exception as exc:  # pragma: no cover
        if is_missing_table_error(exc):
            logger.warning(
                "fetch_cognitive_mastery_overview_sql_skipped",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return default_overview
        logger.error(
            "fetch_cognitive_mastery_overview_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise


async def fetch_workflow_cognitive_breakdown_sql(
    engine: AsyncEngine | None,
    *,
    scope_type: ScopeType = "GLOBAL",
    scope_id: str | None = None,
    time_window: str = "30D",
    allowed_workspace_ids: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate per-workflow cognitive metrics and gate behavior for recommendation engine."""
    if engine is None:
        return []
    if allowed_workspace_ids is not None and len(allowed_workspace_ids) == 0:
        return []

    uuid_val = safe_uuid(scope_id)
    scope_clause, params = build_cognitive_scope_clause(
        scope_type, uuid_val, "wr.workspace_id", allowed_workspace_ids
    )
    tw_clause = build_time_interval_clause(time_window, "ge.evaluated_at")

    stmt = sa.text(
        f"""
        SELECT
            wd.id::text AS workflow_id,
            wd.uri AS workflow_uri,
            COALESCE(wr.criticality, 'STANDARD') AS criticality,
            COUNT(ge.id) AS total_gates_evaluated,
            COALESCE(
                SUM(CASE WHEN ge.gate_type = 'HUMAN' THEN 1 ELSE 0 END), 0
            ) AS human_gates_count,
            COALESCE(
                SUM(CASE WHEN ge.gate_type = 'HUMAN' AND ge.status = 'PASS' THEN 1 ELSE 0 END), 0
            ) AS human_passes_count,
            COALESCE(
                SUM(
                    CASE
                        WHEN ge.gate_type = 'HUMAN' AND ge.status = 'PASS' AND (
                            ge.fast_approval_warning = TRUE OR ge.review_duration_ms < 15000
                        ) THEN 1
                        ELSE 0
                    END
                ), 0
            ) AS quick_passes_count,
            COALESCE(
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ge.review_duration_ms)
                FILTER (WHERE ge.gate_type = 'HUMAN'),
                0
            )::int AS median_review_duration_ms,
            COALESCE(SUM(
                CASE
                    WHEN ge.gate_type = 'HUMAN'
                    THEN jsonb_array_length(ge.lens_findings_jsonb)
                    ELSE 0
                END
            ), 0) AS findings_or_comments_count,
            COALESCE(SUM(
                CASE
                    WHEN ge.pattern_drift_passed = FALSE
                         AND NOT EXISTS (
                             SELECT 1 FROM workspace_exception_waivers w
                             WHERE w.workspace_id = ge.workspace_id
                               AND w.status = 'ACTIVE'
                         )
                    THEN 1
                    ELSE 0
                END
            ), 0) AS uncovered_drift_count,
            COALESCE(
                SUM(CASE WHEN ge.gate_type = 'HUMAN' THEN ge.review_duration_ms ELSE 0 END), 0
            ) AS review_ms,
            COALESCE(SUM(
                CASE WHEN ge.gate_type = 'HUMAN' AND (
                    ge.status = 'FAIL' OR jsonb_array_length(ge.lens_findings_jsonb) > 0
                ) THEN ge.review_duration_ms ELSE 0 END
            ), 0) AS challenge_ms
        FROM workflow_definitions wd
        JOIN workflow_runs wr ON wr.workflow_def_id = wd.id
        LEFT JOIN gate_evaluations ge ON ge.run_id = wr.id
        WHERE 1=1 {scope_clause} {tw_clause}
        GROUP BY wd.id, wd.uri, wr.criticality
        ORDER BY wd.uri ASC;
        """
    )

    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(stmt, params)).mappings().all()
            results: list[dict[str, Any]] = []
            for r in rows:
                results.append(
                    {
                        "workflow_id": str(r["workflow_id"]),
                        "workflow_title": str(r["workflow_uri"]).split("/")[-1]
                        or str(r["workflow_uri"]),
                        "workflow_uri": str(r["workflow_uri"]),
                        "criticality": str(r["criticality"]),
                        "total_gates_evaluated": int(r["total_gates_evaluated"]),
                        "human_gates_count": int(r["human_gates_count"]),
                        "human_passes_count": int(r["human_passes_count"]),
                        "quick_passes_count": int(r["quick_passes_count"]),
                        "median_review_duration_ms": int(r["median_review_duration_ms"]),
                        "findings_or_comments_count": int(r["findings_or_comments_count"]),
                        "uncovered_drift_count": int(r["uncovered_drift_count"]),
                        "review_ms": int(r["review_ms"]),
                        "challenge_ms": int(r["challenge_ms"]),
                    }
                )
            return results
    except Exception as exc:  # pragma: no cover
        if is_missing_table_error(exc):
            logger.warning(
                "fetch_workflow_cognitive_breakdown_sql_skipped",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return []
        logger.error(
            "fetch_workflow_cognitive_breakdown_sql_error",
            error_type=type(exc).__name__,
            detail=str(exc),
        )
        raise
