"""Recommendation builders for `CognitiveImpactService` (`Story 6.3`)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from orcia_core.audit_finops._audit_finops_locales import get_audit_finops_locale_bundle
from orcia_core.audit_finops.cognitive_impact_models import (
    GatePolicyRecommendation,
    RecommendationStatus,
)
from orcia_kernel.enums import DEFAULT_LOCALE


def build_gate_policy_recommendations(
    *,
    wf_rows: list[dict[str, Any]],
    applied_map: dict[str, dict[str, Any]],
    locale: str = DEFAULT_LOCALE,
) -> list[GatePolicyRecommendation]:
    """Build proposed and applied gate policy adjustment recommendations."""
    bundle = get_audit_finops_locale_bundle(locale)
    recommendations: list[GatePolicyRecommendation] = []
    for r in wf_rows:
        h_gates = r["human_gates_count"]
        h_passes = r["human_passes_count"]
        median_ms = r["median_review_duration_ms"]
        comments = r["findings_or_comments_count"]
        criticality = r["criticality"]
        wf_id = r["workflow_id"]
        wf_title = r["workflow_title"]
        pass_rate = (h_passes / h_gates) if h_gates > 0 else 0.0
        if not (h_gates >= 5 and pass_rate > 0.98 and median_ms < 15000 and comments == 0):
            continue
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
                    title=bundle.rec_strengthen_title,
                    description=bundle.rec_strengthen_desc_tpl.format(wf_title=wf_title),
                    action_label=bundle.rec_strengthen_action,
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
                    title=bundle.rec_sampling_title,
                    description=bundle.rec_sampling_desc_tpl.format(wf_title=wf_title),
                    action_label=bundle.rec_sampling_action,
                    suggested_policy="SAMPLING_20_PCT",
                    status=rec_status,
                    applied_at=applied_at_dt,
                    applied_by=applied_by_val,
                )
            )

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
                    workflow_title=app_info["workflow_title"] or bundle.rec_applied_wf_fallback,
                    recommendation_type=app_info["recommendation_type"],
                    title=bundle.rec_applied_title,
                    description=bundle.rec_applied_desc,
                    action_label=bundle.rec_applied_action,
                    suggested_policy=app_info["suggested_policy"],
                    status="APPLIED",
                    applied_at=applied_at_dt,
                    applied_by=app_info["applied_by"],
                )
            )
    return recommendations
