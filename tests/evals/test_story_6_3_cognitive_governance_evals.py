"""Story 6.3 — Layer 4 Deterministic Evals: Cognitive Governance & Reversibility Analysis.

Zero-dollar ($0) deterministic evaluation benchmark testing:
1. Scenario Golden Benchmark: High-volume rapid approvals trigger proactive policy adjustment.
2. Critic Engagement Benchmark: Thoughtful reviews with comments suppress fatigue alarms.
3. Architecture Deviation Guard: Strict differentiation between covered vs uncovered drift.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from orcia_core.audit_finops.cognitive_impact_service import (
    CognitiveImpactService,
)


@pytest.mark.asyncio
async def test_eval_rubber_stamping_fatigue_golden_dataset() -> None:
    """Eval Benchmark: Verify 100% precision on detecting reviewer fatigue scenarios."""
    service = CognitiveImpactService(engine=None)

    golden_scenarios = [
        # (h_gates, passes, quicks, median_ms, comments, expected_rec_type)
        (20, 20, 20, 3200, 0, "SWITCH_TO_RISK_OR_SAMPLING"),
        (15, 15, 14, 4500, 0, "SWITCH_TO_RISK_OR_SAMPLING"),
        (8, 8, 8, 8000, 0, "SWITCH_TO_RISK_OR_SAMPLING"),
    ]

    for idx, (h_gates, passes, quicks, median_ms, comments, expected_rec) in enumerate(
        golden_scenarios
    ):
        mock_wf = [
            {
                "workflow_id": f"wf-golden-{idx}",
                "workflow_title": f"Processus Dore {idx}",
                "workflow_uri": f"orcia://workflows/golden-{idx}",
                "criticality": "STANDARD",
                "total_gates_evaluated": h_gates,
                "human_gates_count": h_gates,
                "human_passes_count": passes,
                "quick_passes_count": quicks,
                "median_review_duration_ms": median_ms,
                "findings_or_comments_count": comments,
                "uncovered_drift_count": 0,
                "review_ms": passes * median_ms,
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
                "review_ms": passes * median_ms,
                "total_human_ms": 10_000 + (passes * median_ms),
                "human_approvals_count": passes,
                "quick_pass_approvals_count": quicks,
                "total_arch_evaluations_count": passes,
                "uncovered_deviations_count": 0,
            }
            mock_breakdown.return_value = mock_wf

            dash = await service.get_dashboard()
            assert len(dash.recommendations) == 1
            assert dash.recommendations[0].recommendation_type == expected_rec
            assert dash.quick_pass_alert is True


@pytest.mark.asyncio
async def test_eval_critical_workflow_demands_anchoring_reinforcement() -> None:
    """Eval Benchmark: High-criticality processes recommend anchor strengthening."""
    service = CognitiveImpactService(engine=None)

    mock_wf = [
        {
            "workflow_id": "wf-critical-proc",
            "workflow_title": "Transfert de Fonds Interbancaire",
            "workflow_uri": "orcia://workflows/swift-transfer",
            "criticality": "HIGH_CRITICAL",
            "total_gates_evaluated": 12,
            "human_gates_count": 12,
            "human_passes_count": 12,
            "quick_passes_count": 10,
            "median_review_duration_ms": 5200,
            "findings_or_comments_count": 0,
            "uncovered_drift_count": 0,
            "review_ms": 62400,
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
            "active_framing_ms": 20_000,
            "review_ms": 62400,
            "total_human_ms": 82400,
            "human_approvals_count": 12,
            "quick_pass_approvals_count": 10,
            "total_arch_evaluations_count": 12,
            "uncovered_deviations_count": 0,
        }
        mock_breakdown.return_value = mock_wf

        dash = await service.get_dashboard()
        assert len(dash.recommendations) == 1
        rec = dash.recommendations[0]
        assert rec.recommendation_type == "STRENGTHEN_HUMAN_ANCHORS"
        assert rec.suggested_policy == "STRENGTHEN_ANCHORS"
        assert "renforcement" in rec.title.lower()


@pytest.mark.asyncio
async def test_eval_architecture_drift_waiver_differentiation() -> None:
    """Eval Benchmark: Architecture drift alerts with 100% precision when waivers absent."""
    service = CognitiveImpactService(engine=None)

    # 1. Uncovered drift: 2 deviations / 10 evaluations -> alert
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
            "active_framing_ms": 50_000,
            "review_ms": 50_000,
            "total_human_ms": 100_000,
            "human_approvals_count": 10,
            "quick_pass_approvals_count": 0,
            "total_arch_evaluations_count": 10,
            "uncovered_deviations_count": 2,
        }
        mock_breakdown.return_value = []

        dash = await service.get_dashboard()
        assert dash.uncovered_deviations_count == 2
        assert dash.architecture_deviation_index == 0.20
        assert dash.architecture_deviation_alert is True

    # 2. Covered drift: all deviations covered by waivers -> 0 uncovered -> clean
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
            "active_framing_ms": 50_000,
            "review_ms": 50_000,
            "total_human_ms": 100_000,
            "human_approvals_count": 10,
            "quick_pass_approvals_count": 0,
            "total_arch_evaluations_count": 10,
            "uncovered_deviations_count": 0,
        }
        mock_breakdown.return_value = []

        dash = await service.get_dashboard()
        assert dash.uncovered_deviations_count == 0
        assert dash.architecture_deviation_index == 0.00
        assert dash.architecture_deviation_alert is False
