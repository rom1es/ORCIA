"""Cognitive Impact and Human Reversibility domain service (`Story 6.3`, `FR-27`).

Calculates human mastery counter-metrics, evaluates warning thresholds,
and generates actionable gate policy adjustment recommendations.

Strict Hexagonal Boundary (`AD-19 Contract 2`):
- ZERO import of `orcia_core.gates`. Queries via `_internal/sql_cognitive_impact.py`.
- Strict typing, zero raw hex colors, zero unhandled errors.
"""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

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
from orcia_core.audit_finops.finops_models import ScopeType
from orcia_core.audit_finops.post_hoc_audit import PostHocAuditService
from orcia_core.observability.logging import get_logger
from orcia_kernel.errors import ResourceNotFoundError

logger = get_logger("orcia.core.audit_finops.cognitive")

# Re-export models for backward compatibility
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

        # 1. Ratio Cadrage Actif (SM-C2): Target >= 40%
        if total_human_ms > 0:
            active_framing_ratio = round(active_framing_ms / total_human_ms, 4)
        else:
            active_framing_ratio = 1.0
        active_framing_alert = total_human_ms > 0 and active_framing_ratio < 0.40

        # 2. Taux de Validations Expéditives (SM-C1): Threshold < 5%
        human_approvals = ov["human_approvals_count"]
        quick_pass_count = ov["quick_pass_approvals_count"]
        if human_approvals > 0:
            quick_pass_rate = round(quick_pass_count / human_approvals, 4)
        else:
            quick_pass_rate = 0.0
        quick_pass_alert = human_approvals > 0 and quick_pass_rate >= 0.05

        # 3. Indice de Dérive d'Architecture (SM-C3): Absolute Target 0%
        total_arch_evals = ov["total_arch_evaluations_count"]
        uncovered_deviations = ov["uncovered_deviations_count"]
        if total_arch_evals > 0:
            architecture_deviation_index = round(uncovered_deviations / total_arch_evals, 4)
        else:
            architecture_deviation_index = 0.0
        architecture_deviation_alert = uncovered_deviations > 0

        # Workflow breakdowns and recommendation engine
        breakdowns: list[WorkflowCognitiveMetrics] = []
        recommendations: list[GatePolicyRecommendation] = []

        for r in wf_rows:
            h_gates = r["human_gates_count"]
            h_passes = r["human_passes_count"]
            q_passes = r["quick_passes_count"]
            median_ms = r["median_review_duration_ms"]
            comments = r["findings_or_comments_count"]
            uncovered_drift = r["uncovered_drift_count"]
            criticality = r["criticality"]
            wf_id = r["workflow_id"]
            wf_title = r["workflow_title"]

            wf_quick_rate = round(q_passes / h_passes, 4) if h_passes > 0 else 0.0
            wf_has_alert = wf_quick_rate >= 0.05 or uncovered_drift > 0

            breakdowns.append(
                WorkflowCognitiveMetrics(
                    workflow_id=wf_id,
                    workflow_title=wf_title,
                    criticality=criticality,
                    human_gates_count=h_gates,
                    human_passes_count=h_passes,
                    quick_passes_count=q_passes,
                    quick_pass_rate=wf_quick_rate,
                    median_review_duration_ms=median_ms,
                    uncovered_drift_count=uncovered_drift,
                    has_alert=wf_has_alert,
                )
            )

            # Governance Analyzer Rule:
            # If >= 5 human reviews, pass rate > 98%, median review < 15s, and 0 comments/challenges
            pass_rate = (h_passes / h_gates) if h_gates > 0 else 0.0
            if h_gates >= 5 and pass_rate > 0.98 and median_ms < 15000 and comments == 0:
                rec_id = f"rec-{wf_id}"
                is_applied = rec_id in applied_map
                app_info = applied_map.get(rec_id)
                rec_status: RecommendationStatus = "APPLIED" if is_applied else "PROPOSED"
                applied_at_dt = (
                    datetime.fromisoformat(app_info["applied_at"])
                    if app_info and isinstance(app_info["applied_at"], str)
                    else (app_info["applied_at"] if app_info else None)
                )
                applied_by_val = app_info["applied_by"] if app_info else None

                if criticality == "HIGH_CRITICAL":
                    recommendations.append(
                        GatePolicyRecommendation(
                            id=rec_id,
                            workflow_id=wf_id,
                            workflow_title=wf_title,
                            recommendation_type="STRENGTHEN_HUMAN_ANCHORS",
                            title="Renforcement des saisies expertes préalables",
                            description=(
                                f"Le processus '{wf_title}' hautement critique est validé à 100 % "
                                "sans observation. Pour garantir une maîtrise active, renforcez "
                                "les ancrages humains obligatoires en amont de l'étape."
                            ),
                            action_label="Renforcer les saisies expertes",
                            suggested_policy="STRENGTHEN_ANCHORS",
                            status=rec_status,
                            applied_at=applied_at_dt,
                            applied_by=applied_by_val,
                        )
                    )
                else:
                    recommendations.append(
                        GatePolicyRecommendation(
                            id=rec_id,
                            workflow_id=wf_id,
                            workflow_title=wf_title,
                            recommendation_type="SWITCH_TO_RISK_OR_SAMPLING",
                            title="Politique ciblée par risque ou par échantillonnage",
                            description=(
                                f"Le processus '{wf_title}' présente un taux de validation unanime "
                                "avec des délais de lecture courts. Basculez la vérification en "
                                "échantillonnage (20 %) pour préserver l'attention critique."
                            ),
                            action_label="Passer en échantillonnage (20 %)",
                            suggested_policy="SAMPLING_20_PCT",
                            status=rec_status,
                            applied_at=applied_at_dt,
                            applied_by=applied_by_val,
                        )
                    )

        # Append any previously applied recommendations not in the current active window
        seen_rec_ids = {r.id for r in recommendations}
        for app_rec_id, app_info in applied_map.items():
            if app_rec_id not in seen_rec_ids:
                applied_at_dt = (
                    datetime.fromisoformat(app_info["applied_at"])
                    if isinstance(app_info["applied_at"], str)
                    else app_info["applied_at"]
                )
                recommendations.append(
                    GatePolicyRecommendation(
                        id=app_rec_id,
                        workflow_id=app_info["workflow_id"],
                        workflow_title=app_info["workflow_title"] or "Processus appliqué",
                        recommendation_type=app_info["recommendation_type"],
                        title="Politique de validation ajustée",
                        description="Politique ajustée avec succès.",
                        action_label="Appliquée",
                        suggested_policy=app_info["suggested_policy"],
                        status="APPLIED",
                        applied_at=applied_at_dt,
                        applied_by=app_info["applied_by"],
                    )
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
        candidate_wf = recommendation_id.removeprefix("rec-")
        wf_uuid = safe_uuid(candidate_wf)
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
    ) -> GatePolicyRecommendation:
        """Apply an actionable gate policy recommendation and persist into audit_ledger."""
        dashboard = await self.get_dashboard(allowed_workspace_ids=allowed_workspace_ids)
        target_rec: GatePolicyRecommendation | None = None
        for rec in dashboard.recommendations:
            if rec.id == recommendation_id:
                target_rec = rec
                break

        if target_rec is None:
            raise ResourceNotFoundError(
                detail_override=f"Gate policy recommendation '{recommendation_id}' not found."
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
