"""Cognitive Impact and Human Reversibility domain service (`Story 6.3`, `FR-27`)."""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._cognitive_impact_recs import build_gate_policy_recommendations
from orcia_core.audit_finops._internal._sql_scope_filter import safe_uuid
from orcia_core.audit_finops._internal.sql_cognitive_impact import (
    fetch_cognitive_mastery_overview_sql,
    fetch_workflow_cognitive_breakdown_sql,
)
from orcia_core.audit_finops._internal.sql_cognitive_recommendations import (
    fetch_applied_recommendations_sql,
    record_applied_policy_recommendation_sql,
)
from orcia_core.audit_finops.cognitive_impact_models import (
    CognitiveMasteryDashboard,
    GatePolicyRecommendation,
    PolicyRecommendationType,
    RecommendationStatus,
    WorkflowCognitiveMetrics,
)
from orcia_core.audit_finops.errors import ResourceNotFoundError
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.audit_finops.post_hoc_audit import PostHocAuditService
from orcia_core.observability.logging import get_logger
from orcia_kernel.enums import DEFAULT_LOCALE

logger = get_logger("orcia.core.audit_finops.cognitive")

__all__ = [
    "CognitiveImpactService",
    "CognitiveMasteryDashboard",
    "GatePolicyRecommendation",
    "PolicyRecommendationType",
    "RecommendationStatus",
    "WorkflowCognitiveMetrics",
]


class CognitiveImpactService:
    """Domain service orchestrating cognitive governance and gate policy recommendations."""

    def __init__(
        self,
        engine: AsyncEngine | None = None,
        post_hoc_service: PostHocAuditService | None = None,
    ) -> None:
        self._engine = engine
        self._post_hoc = post_hoc_service or PostHocAuditService(engine=engine)
        self._fallback_applied: dict[str, GatePolicyRecommendation] = {}

    async def get_dashboard(
        self,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str | None = None,
        time_window: str = "30D",
        allowed_workspace_ids: tuple[str, ...] | None = None,
        locale: str = DEFAULT_LOCALE,
    ) -> CognitiveMasteryDashboard:
        """Calculate the 3 counter-metrics and generate gate recommendations."""
        ov = await fetch_cognitive_mastery_overview_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            time_window=time_window,
            allowed_workspace_ids=allowed_workspace_ids,
        )
        wf_rows = await fetch_workflow_cognitive_breakdown_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            time_window=time_window,
            allowed_workspace_ids=allowed_workspace_ids,
        )
        applied_map = await fetch_applied_recommendations_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            allowed_workspace_ids=allowed_workspace_ids,
        )
        if self._engine is None:
            for k, v in self._fallback_applied.items():
                if k not in applied_map:
                    applied_map[k] = {
                        "recommendation_id": v.id,
                        "workflow_id": v.workflow_id,
                        "workflow_title": v.workflow_title,
                        "recommendation_type": v.recommendation_type,
                        "suggested_policy": v.suggested_policy,
                        "applied_by": v.applied_by or "system",
                        "applied_at": (
                            v.applied_at.isoformat()
                            if v.applied_at
                            else datetime.now(UTC).isoformat()
                        ),
                    }

        total_human_ms = ov["total_human_ms"]
        active_framing_ms = ov["active_framing_ms"]
        review_ms = ov["review_ms"]
        active_framing_ratio = (
            round(active_framing_ms / total_human_ms, 4) if total_human_ms > 0 else 1.0
        )
        active_framing_alert = total_human_ms > 0 and active_framing_ratio < 0.40

        human_approvals = ov["human_approvals_count"]
        quick_pass_count = ov["quick_pass_approvals_count"]
        quick_pass_rate = (
            round(quick_pass_count / human_approvals, 4) if human_approvals > 0 else 0.0
        )
        quick_pass_alert = human_approvals > 0 and quick_pass_rate >= 0.05

        total_arch_evals = ov["total_arch_evaluations_count"]
        uncovered_deviations = ov["uncovered_deviations_count"]
        architecture_deviation_index = (
            round(uncovered_deviations / total_arch_evals, 4) if total_arch_evals > 0 else 0.0
        )
        architecture_deviation_alert = uncovered_deviations > 0

        breakdowns = [
            WorkflowCognitiveMetrics(
                workflow_id=r["workflow_id"],
                workflow_title=r["workflow_title"],
                criticality=r["criticality"],
                human_gates_count=r["human_gates_count"],
                human_passes_count=r["human_passes_count"],
                quick_passes_count=r["quick_passes_count"],
                quick_pass_rate=(
                    round(r["quick_passes_count"] / r["human_passes_count"], 4)
                    if r["human_passes_count"] > 0
                    else 0.0
                ),
                median_review_duration_ms=r["median_review_duration_ms"],
                uncovered_drift_count=r["uncovered_drift_count"],
                has_alert=(
                    (
                        round(r["quick_passes_count"] / r["human_passes_count"], 4)
                        if r["human_passes_count"] > 0
                        else 0.0
                    )
                    >= 0.05
                    or r["uncovered_drift_count"] > 0
                ),
            )
            for r in wf_rows
        ]
        recommendations = build_gate_policy_recommendations(
            wf_rows=wf_rows, applied_map=applied_map, locale=locale
        )
        if self._engine is not None and self._post_hoc._engine is None:
            self._post_hoc._engine = self._engine
        auto_metrics = await self._post_hoc.get_autonomous_governance_metrics(
            scope_type=scope_type,
            scope_id=scope_id,
            time_window=time_window,
            allowed_workspace_ids=allowed_workspace_ids,
        )
        return CognitiveMasteryDashboard(
            active_framing_ratio=active_framing_ratio,
            active_framing_target=0.40,
            active_framing_alert=active_framing_alert,
            quick_pass_rate=quick_pass_rate,
            quick_pass_threshold=0.05,
            quick_pass_alert=quick_pass_alert,
            architecture_deviation_index=architecture_deviation_index,
            architecture_deviation_target=0.00,
            architecture_deviation_alert=architecture_deviation_alert,
            total_human_hours=round(total_human_ms / 3_600_000, 2),
            active_framing_hours=round(active_framing_ms / 3_600_000, 2),
            review_hours=round(review_ms / 3_600_000, 2),
            uncovered_deviations_count=uncovered_deviations,
            workflow_breakdowns=breakdowns,
            recommendations=recommendations,
            autonomous_governance=auto_metrics,
        )

    async def resolve_recommendation_workspace_id(self, recommendation_id: str) -> str | None:
        """Resolve the workspace UUID owning the workflow referenced by `recommendation_id`."""
        if self._engine is None:
            return None
        wf_uuid = safe_uuid(recommendation_id.removeprefix("rec-"))
        if wf_uuid is None:
            return None
        async with self._engine.connect() as conn:
            ws_id = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT COALESCE(
                            wd.workspace_id::text,
                            (SELECT wr.workspace_id::text FROM workflow_runs wr
                             WHERE wr.workflow_def_id = wd.id
                             ORDER BY wr.created_at DESC LIMIT 1)
                        )
                        FROM workflow_definitions wd
                        WHERE wd.id = :wf_id;
                        """
                    ),
                    {"wf_id": wf_uuid},
                )
            ).scalar()
            return str(ws_id) if ws_id else None

    async def apply_policy_recommendation(
        self,
        recommendation_id: str,
        *,
        applied_by: str,
        allowed_workspace_ids: tuple[str, ...] | None = None,
        locale: str = DEFAULT_LOCALE,
    ) -> GatePolicyRecommendation:
        """Apply an actionable gate policy recommendation and persist into audit_ledger."""
        dashboard = await self.get_dashboard(
            allowed_workspace_ids=allowed_workspace_ids, locale=locale
        )
        target_rec = next((r for r in dashboard.recommendations if r.id == recommendation_id), None)
        if target_rec is None:
            raise ResourceNotFoundError(
                detail_code="ERR_COGNITIVE_REC_NOT_FOUND_DETAIL",
                detail_params={"recommendation_id": recommendation_id},
            )
        now = datetime.now(UTC)
        updated = GatePolicyRecommendation(
            id=target_rec.id,
            workflow_id=target_rec.workflow_id,
            workflow_title=target_rec.workflow_title,
            recommendation_type=target_rec.recommendation_type,
            title=target_rec.title,
            description=target_rec.description,
            action_label=target_rec.action_label,
            suggested_policy=target_rec.suggested_policy,
            status="APPLIED",
            applied_at=now,
            applied_by=applied_by,
        )
        if self._engine is not None:
            await record_applied_policy_recommendation_sql(
                self._engine,
                rec_id=updated.id,
                workflow_id=updated.workflow_id,
                workflow_title=updated.workflow_title,
                rec_type=updated.recommendation_type,
                title=updated.title,
                suggested_policy=updated.suggested_policy,
                applied_by=applied_by,
                applied_at=now,
            )
        else:
            self._fallback_applied[recommendation_id] = updated

        logger.info(
            "finops_gate_recommendation_applied",
            recommendation_id=recommendation_id,
            applied_by=applied_by,
            workflow_id=target_rec.workflow_id,
        )
        return updated
