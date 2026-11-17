"""Unit tests for Story 6.3: Cognitive Impact Dashboard, Anti-Rubber-Stamping & Reversibility.

Tests (`FR-27`, `SM-C1`, `SM-C2`, `SM-C3`, `AD-17 Layer 1a`):
- Active Framing Ratio computation and amber alert (< 40%)
- Quick-Pass Approvals Rate computation and red alert (>= 5%)
- Architecture Deviation & Reversibility Index (0% target, waiver exemption)
- Governance analyzer recommendation generation (> 98% pass, < 15s median, 0 comments)
- High critical vs standard workflow recommendations
- Applying a recommendation
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from orcia_core.audit_finops.cognitive_impact_service import (
    CognitiveImpactService,
)
from orcia_kernel.errors import ResourceNotFoundError


@pytest.mark.asyncio
async def test_cognitive_mastery_empty_baseline() -> None:
    """When no executions exist, defaults to 1.0 framing, 0% quick-pass and 0% drift (no alerts)."""
    service = CognitiveImpactService(engine=None)
    dashboard = await service.get_dashboard()

    assert dashboard.active_framing_ratio == 1.0
    assert not dashboard.active_framing_alert
    assert dashboard.quick_pass_rate == 0.0
    assert not dashboard.quick_pass_alert
    assert dashboard.architecture_deviation_index == 0.0
    assert not dashboard.architecture_deviation_alert
    assert dashboard.recommendations == []
    assert dashboard.workflow_breakdowns == []


@pytest.mark.asyncio
async def test_active_framing_ratio_healthy_and_alert() -> None:
    """Active framing ratio triggers amber alert when < 40%."""
    service = CognitiveImpactService(engine=None)

    # 1. Healthy: 60s framing vs 40s review -> 60/100 = 60% (>= 40%)
    with (
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_cognitive_mastery_overview_sql",
            new_callable=AsyncMock,
        ) as mock_ov,
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_workflow_cognitive_breakdown_sql",
            new_callable=AsyncMock,
        ) as mock_wf,
    ):
        mock_ov.return_value = {
            "active_framing_ms": 60_000,
            "review_ms": 40_000,
            "total_human_ms": 100_000,
            "human_approvals_count": 10,
            "quick_pass_approvals_count": 0,
            "total_arch_evaluations_count": 10,
            "uncovered_deviations_count": 0,
        }
        mock_wf.return_value = []

        dash = await service.get_dashboard()
        assert dash.active_framing_ratio == 0.60
        assert not dash.active_framing_alert

    # 2. Alert: 20s framing vs 80s review -> 20/100 = 20% (< 40%)
    with (
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_cognitive_mastery_overview_sql",
            new_callable=AsyncMock,
        ) as mock_ov,
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_workflow_cognitive_breakdown_sql",
            new_callable=AsyncMock,
        ) as mock_wf,
    ):
        mock_ov.return_value = {
            "active_framing_ms": 20_000,
            "review_ms": 80_000,
            "total_human_ms": 100_000,
            "human_approvals_count": 10,
            "quick_pass_approvals_count": 0,
            "total_arch_evaluations_count": 10,
            "uncovered_deviations_count": 0,
        }
        mock_wf.return_value = []

        dash = await service.get_dashboard()
        assert dash.active_framing_ratio == 0.20
        assert dash.active_framing_alert


@pytest.mark.asyncio
async def test_quick_pass_rate_healthy_and_alert() -> None:
    """Quick-pass approval rate triggers red alert when >= 5%."""
    service = CognitiveImpactService(engine=None)

    # 1. Healthy: 1 quick pass out of 100 approvals -> 1% (< 5%)
    with (
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_cognitive_mastery_overview_sql",
            new_callable=AsyncMock,
        ) as mock_ov,
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_workflow_cognitive_breakdown_sql",
            new_callable=AsyncMock,
        ) as mock_wf,
    ):
        mock_ov.return_value = {
            "active_framing_ms": 50_000,
            "review_ms": 50_000,
            "total_human_ms": 100_000,
            "human_approvals_count": 100,
            "quick_pass_approvals_count": 1,
            "total_arch_evaluations_count": 50,
            "uncovered_deviations_count": 0,
        }
        mock_wf.return_value = []

        dash = await service.get_dashboard()
        assert dash.quick_pass_rate == 0.01
        assert not dash.quick_pass_alert

    # 2. Alert: 6 quick passes out of 100 approvals -> 6% (>= 5%)
    with (
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_cognitive_mastery_overview_sql",
            new_callable=AsyncMock,
        ) as mock_ov,
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_workflow_cognitive_breakdown_sql",
            new_callable=AsyncMock,
        ) as mock_wf,
    ):
        mock_ov.return_value = {
            "active_framing_ms": 50_000,
            "review_ms": 50_000,
            "total_human_ms": 100_000,
            "human_approvals_count": 100,
            "quick_pass_approvals_count": 6,
            "total_arch_evaluations_count": 50,
            "uncovered_deviations_count": 0,
        }
        mock_wf.return_value = []

        dash = await service.get_dashboard()
        assert dash.quick_pass_rate == 0.06
        assert dash.quick_pass_alert


@pytest.mark.asyncio
async def test_architecture_deviation_and_reversibility_index() -> None:
    """Architecture deviation index alerts whenever uncovered deviations > 0."""
    service = CognitiveImpactService(engine=None)

    with (
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_cognitive_mastery_overview_sql",
            new_callable=AsyncMock,
        ) as mock_ov,
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_workflow_cognitive_breakdown_sql",
            new_callable=AsyncMock,
        ) as mock_wf,
    ):
        mock_ov.return_value = {
            "active_framing_ms": 50_000,
            "review_ms": 50_000,
            "total_human_ms": 100_000,
            "human_approvals_count": 50,
            "quick_pass_approvals_count": 0,
            "total_arch_evaluations_count": 20,
            "uncovered_deviations_count": 2,
        }
        mock_wf.return_value = []

        dash = await service.get_dashboard()
        assert dash.architecture_deviation_index == 0.10
        assert dash.architecture_deviation_alert
        assert dash.uncovered_deviations_count == 2


@pytest.mark.asyncio
async def test_governance_analyzer_generates_recommendations() -> None:
    """Analyzer recommends sampling for standard workflow and anchor strengthening for critical."""
    service = CognitiveImpactService(engine=None)

    def _make_wf(
        wf_id: str,
        title: str,
        crit: str,
        h_gates: int,
        passes: int,
        quicks: int,
        med_ms: int,
        comm: int,
    ) -> dict[str, Any]:
        return {
            "workflow_id": wf_id,
            "workflow_title": title,
            "workflow_uri": f"orcia://wf/{wf_id}",
            "criticality": crit,
            "total_gates_evaluated": h_gates,
            "human_gates_count": h_gates,
            "human_passes_count": passes,
            "quick_passes_count": quicks,
            "median_review_duration_ms": med_ms,
            "findings_or_comments_count": comm,
            "uncovered_drift_count": 0,
            "review_ms": passes * med_ms,
            "challenge_ms": 0,
        }

    mock_wf_data = [
        _make_wf("wf-std-1", "Contrat Fournisseur", "STANDARD", 10, 10, 8, 4000, 0),
        _make_wf("wf-crit-2", "Paiement Bancaire", "HIGH_CRITICAL", 10, 10, 6, 5000, 0),
        _make_wf("wf-healthy-3", "Analyse Fiscale", "STANDARD", 10, 10, 0, 45000, 5),
    ]

    with (
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_cognitive_mastery_overview_sql",
            new_callable=AsyncMock,
        ) as mock_ov,
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_workflow_cognitive_breakdown_sql",
            new_callable=AsyncMock,
        ) as mock_wf,
    ):
        mock_ov.return_value = {
            "active_framing_ms": 100_000,
            "review_ms": 100_000,
            "total_human_ms": 200_000,
            "human_approvals_count": 30,
            "quick_pass_approvals_count": 14,
            "total_arch_evaluations_count": 30,
            "uncovered_deviations_count": 0,
        }
        mock_wf.return_value = mock_wf_data

        dash = await service.get_dashboard()
        assert len(dash.recommendations) == 2

        # Check rec 1: Standard workflow -> SWITCH_TO_RISK_OR_SAMPLING
        r1 = dash.recommendations[0]
        assert r1.workflow_id == "wf-std-1"
        assert r1.recommendation_type == "SWITCH_TO_RISK_OR_SAMPLING"
        assert r1.suggested_policy == "SAMPLING_20_PCT"
        assert "échantillonnage" in r1.title.lower() or "politique ciblée" in r1.title.lower()
        assert r1.status == "PROPOSED"

        # Check rec 2: High critical workflow -> STRENGTHEN_HUMAN_ANCHORS
        r2 = dash.recommendations[1]
        assert r2.workflow_id == "wf-crit-2"
        assert r2.recommendation_type == "STRENGTHEN_HUMAN_ANCHORS"
        assert r2.suggested_policy == "STRENGTHEN_ANCHORS"
        assert "renforcement" in r2.title.lower()
        assert r2.status == "PROPOSED"


@pytest.mark.asyncio
async def test_apply_policy_recommendation() -> None:
    """Unknown recommendation ID strictly raises 404 ResourceNotFoundError (`MAJOR-01`)."""
    service = CognitiveImpactService(engine=None)

    with pytest.raises(ResourceNotFoundError):
        await service.apply_policy_recommendation(
            "rec-unknown-id",
            applied_by="018f-user-manager",
        )


@pytest.mark.asyncio
async def test_dashboard_properties_aliases_and_apply_existing_rec() -> None:
    """Test backwards-compatible properties aliases and applying a discovered recommendation."""
    service = CognitiveImpactService(engine=None)
    mock_wf = [
        {
            "workflow_id": "wf-1",
            "workflow_title": "Contrat Test",
            "workflow_uri": "orcia://workflows/contrat-test",
            "criticality": "STANDARD",
            "total_gates_evaluated": 6,
            "human_gates_count": 6,
            "human_passes_count": 6,
            "quick_passes_count": 6,
            "median_review_duration_ms": 2000,
            "findings_or_comments_count": 0,
            "uncovered_drift_count": 0,
            "review_ms": 12000,
            "challenge_ms": 0,
        }
    ]

    with (
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_cognitive_mastery_overview_sql",
            new_callable=AsyncMock,
        ) as mock_ov,
        patch(
            "orcia_core.audit_finops.cognitive_impact_service.fetch_workflow_cognitive_breakdown_sql",
            new_callable=AsyncMock,
        ) as mock_breakdown,
    ):
        mock_ov.return_value = {
            "active_framing_ms": 10_000,
            "review_ms": 12_000,
            "total_human_ms": 22_000,
            "human_approvals_count": 6,
            "quick_pass_approvals_count": 6,
            "total_arch_evaluations_count": 6,
            "uncovered_deviations_count": 1,
        }
        mock_breakdown.return_value = mock_wf

        dash = await service.get_dashboard()
        # Test property aliases
        assert dash.rubber_stamping_rate == dash.quick_pass_rate
        assert dash.rubber_stamping_alert == dash.quick_pass_alert
        assert dash.pattern_drift_index == dash.architecture_deviation_index
        assert dash.pattern_drift_alert == dash.architecture_deviation_alert

        assert len(dash.recommendations) == 1
        rec = dash.recommendations[0]
        assert rec.id == "rec-wf-1"

        # Apply the discovered recommendation
        applied = await service.apply_policy_recommendation(rec.id, applied_by="mgr-123")
        assert applied.status == "APPLIED"
        assert applied.applied_by == "mgr-123"

        # Calling get_dashboard again should return the APPLIED recommendation
        dash_after = await service.get_dashboard()
        assert len(dash_after.recommendations) == 1
        assert dash_after.recommendations[0].status == "APPLIED"
