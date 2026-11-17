"""Unit tests for FinOps accounting calculations with Decimal arithmetic (`Story 6.2`)."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from orcia_core.audit_finops.finops_accounting_service import (
    _round_usd,
    _usd_to_eur,
)
from orcia_core.audit_finops.finops_models import (
    DEFAULT_EUR_USD_RATE,
    DEFAULT_HOURLY_RATE_USD,
    FinopsBudgetOverride,
    FinopsProcessItem,
    FinopsScopeBudget,
    FinopsTierEffortItem,
)


def test_finops_domain_models_immutability() -> None:
    """Verifies that FinOps domain dataclasses are strictly frozen."""
    budget = FinopsScopeBudget(
        id="018d0000-0000-7000-8000-000000000001",
        scope_type="GLOBAL",
        scope_id=None,
        monthly_budget_usd=Decimal("150.000000"),
        warning_threshold_pct=80,
        hard_stop_pct=100,
    )
    with pytest.raises(FrozenInstanceError):
        budget.monthly_budget_usd = Decimal("200.000000")  # type: ignore[misc]

    override = FinopsBudgetOverride(
        id="018d0000-0000-7000-8000-000000000002",
        run_id="018d0000-0000-7000-8000-000000000003",
        requested_by="user-1",
        approved_by="user-admin",
        override_amount_usd=Decimal("50.000000"),
        reason="Sprint emergency run extension",
    )
    with pytest.raises(FrozenInstanceError):
        override.override_amount_usd = Decimal("100.000000")  # type: ignore[misc]


def test_complete_economic_equation_three_components() -> None:
    """Tests the 3-component economic equation: Setup amortized + Run + Human time."""
    manual_baseline_cost = Decimal("1200.000000")
    amortization_runs = Decimal("100")
    amortized_setup_usd = manual_baseline_cost / amortization_runs
    assert amortized_setup_usd == Decimal("12.000000")

    run_verified_internal = Decimal("0.084500")
    run_reported_external = Decimal("0.015500")
    run_cost_usd = run_verified_internal + run_reported_external
    assert run_cost_usd == Decimal("0.100000")

    human_active_minutes = Decimal("6")
    hourly_rate = DEFAULT_HOURLY_RATE_USD
    human_time_cost_usd = (human_active_minutes / Decimal("60")) * hourly_rate
    assert human_time_cost_usd == Decimal("7.500000")

    total_cost_usd = _round_usd(amortized_setup_usd + run_cost_usd + human_time_cost_usd)
    assert total_cost_usd == Decimal("19.600000")

    total_cost_eur = _usd_to_eur(total_cost_usd, DEFAULT_EUR_USD_RATE)
    # 19.6 * 0.92 = 18.032 -> 18.03
    assert total_cost_eur == Decimal("18.03")


def test_process_item_and_ttm_reduction_calculation() -> None:
    """Verifies baseline comparison and TTM reduction percentage formatting."""
    manual_cost_usd = Decimal("500.000000")
    amort_setup_usd = Decimal("5.000000")
    run_cost_usd = Decimal("0.250000")
    human_time_cost_usd = Decimal("0.000000")
    total_cost_usd = amort_setup_usd + run_cost_usd + human_time_cost_usd

    item = FinopsProcessItem(
        workflow_id="wf-doc-review",
        workflow_title="Revue documentaire automatisée",
        runs_count=12,
        amortized_setup_cost_usd=amort_setup_usd,
        amortized_setup_cost_eur=_usd_to_eur(amort_setup_usd),
        run_cost_usd=run_cost_usd,
        run_cost_eur=_usd_to_eur(run_cost_usd),
        human_time_cost_usd=human_time_cost_usd,
        human_time_cost_eur=Decimal("0.00"),
        total_cost_usd=total_cost_usd,
        total_cost_eur=_usd_to_eur(total_cost_usd),
        baseline_manual_cost_usd=manual_cost_usd,
        baseline_manual_cost_eur=_usd_to_eur(manual_cost_usd),
        ttm_reduction_pct=Decimal("45"),
        active_budget_override=False,
        paused_runs_count=0,
    )
    assert item.runs_count == 12
    assert item.ttm_reduction_pct == Decimal("45")
    assert item.total_cost_eur == Decimal("4.83")  # 5.25 * 0.92 = 4.83


def test_tier_effort_item_aggregation() -> None:
    """Verifies cognitive inference tier breakdown calculations."""
    tier = FinopsTierEffortItem(
        inference_tier="complex",
        effort="deep",
        invocations_count=42,
        input_tokens=150_000,
        output_tokens=30_000,
        total_tokens=180_000,
        cost_usd=Decimal("1.440000"),
        cost_eur=Decimal("1.32"),
        escalated_from_auto_count=5,
    )
    assert tier.inference_tier == "complex"
    assert tier.effort == "deep"
    assert tier.total_tokens == 180_000
    assert tier.escalated_from_auto_count == 5


@settings(max_examples=100)
@given(
    amount=st.decimals(
        min_value=Decimal("0.000000"),
        max_value=Decimal("100000.000000"),
        places=6,
    ),
    rate=st.decimals(
        min_value=Decimal("0.500000"),
        max_value=Decimal("2.000000"),
        places=6,
    ),
)
def test_hypothesis_decimal_quantization_properties(amount: Decimal, rate: Decimal) -> None:
    """Property-based verification: Decimal quantization never drifts or throws floats."""
    rounded_usd = _round_usd(amount)
    assert rounded_usd.as_tuple().exponent == -6

    converted_eur = _usd_to_eur(rounded_usd, rate)
    assert converted_eur.as_tuple().exponent == -2
    assert converted_eur >= Decimal("0.00")


def test_round_usd_precision_overflow_raises_validation_domain_error() -> None:
    """Verifies that invalid or overflowing numbers raise ValidationDomainError."""
    from orcia_core.audit_finops.finops_accounting_service import _round_eur
    from orcia_kernel.errors import ValidationDomainError

    with pytest.raises(ValidationDomainError):
        _round_usd(Decimal("1e+28"))

    with pytest.raises(ValidationDomainError):
        _round_eur(Decimal("1e+28"))


@pytest.mark.asyncio
async def test_finops_accounting_service_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies FinopsAccountingService domain methods with mocked internal queries."""
    from unittest.mock import AsyncMock, MagicMock

    from orcia_core.audit_finops.finops_accounting_service import FinopsAccountingService
    from orcia_core.audit_finops.finops_models import (
        FinopsBudgetOverride,
        FinopsScopeBudget,
        FinopsWorkflowBaseline,
    )

    outbox_events: list[Any] = []
    sse_events: list[dict[str, Any]] = []

    class MockSse:
        def publish(self, **kwargs: Any) -> None:
            sse_events.append(kwargs)

    svc = FinopsAccountingService(
        engine=MagicMock(),
        outbox_collector=outbox_events,
        sse_broker=MockSse(),
    )

    # Mock dashboard queries
    overview_mock = {
        "total_cost_usd": Decimal("10.000000"),
        "verified_internal_cost_usd": Decimal("8.000000"),
        "reported_external_cost_usd": Decimal("2.000000"),
        "total_input_tokens": 800,
        "total_output_tokens": 200,
        "internal_tokens": 800,
        "remote_tokens": 200,
        "total_external_calls": 5,
        "accounted_runs_count": 1,
        "paused_runs_count": 0,
    }
    monkeypatch.setattr(
        "orcia_core.audit_finops.finops_accounting_service.fetch_dashboard_overview_sql",
        AsyncMock(return_value=overview_mock),
    )
    proc_mock = [
        {
            "workflow_id": "wf-1",
            "workflow_title": "Process Alpha",
            "runs_count": 5,
            "run_cost_usd": Decimal("1.250000"),
            "manual_cost_usd": Decimal("500.000000"),
            "target_ttm_reduction_pct": 30,
            "overrides_usd": Decimal("10.000000"),
            "paused_runs": 0,
        }
    ]
    tier_mock = [
        {
            "inference_tier": "complex",
            "effort": "deep",
            "invocations_count": 10,
            "input_tokens": 5000,
            "output_tokens": 1000,
            "cost_usd": Decimal("0.850000"),
            "escalated_from_auto_count": 2,
        }
    ]
    monkeypatch.setattr(
        "orcia_core.audit_finops.finops_accounting_service.fetch_dashboard_processes_sql",
        AsyncMock(return_value=proc_mock),
    )
    monkeypatch.setattr(
        "orcia_core.audit_finops.finops_accounting_service.fetch_dashboard_tiers_sql",
        AsyncMock(return_value=tier_mock),
    )
    monkeypatch.setattr(
        "orcia_core.audit_finops.finops_accounting_service.list_scope_budgets_sql",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "orcia_core.audit_finops.finops_accounting_service.list_workflow_baselines_sql",
        AsyncMock(return_value=[]),
    )

    bd = await svc.get_breakdown(scope_id="018d0000-0000-7000-8000-000000000001")
    assert bd.overview.total_cost_usd == Decimal("10.000000")

    # Mock upsert budget
    expected_budget = FinopsScopeBudget(
        id="b-1",
        scope_type="GLOBAL",
        scope_id=None,
        monthly_budget_usd=Decimal("150.000000"),
        warning_threshold_pct=80,
        hard_stop_pct=100,
    )
    monkeypatch.setattr(
        "orcia_core.audit_finops.finops_accounting_service.upsert_scope_budget_sql",
        AsyncMock(return_value=expected_budget),
    )
    b_res = await svc.set_scope_budget(
        scope_type="GLOBAL",
        scope_id=None,
        monthly_budget_usd=Decimal("150.00"),
        warning_threshold_pct=80,
        hard_stop_pct=100,
    )
    assert b_res.monthly_budget_usd == Decimal("150.000000")

    # Mock upsert baseline
    expected_baseline = FinopsWorkflowBaseline(
        id="bl-1",
        workflow_definition_id="wf-1",
        scope_id=None,
        manual_time_minutes=60,
        manual_cost_usd=Decimal("200.000000"),
        target_ttm_reduction_pct=30,
    )
    monkeypatch.setattr(
        "orcia_core.audit_finops.finops_accounting_service.upsert_workflow_baseline_sql",
        AsyncMock(return_value=expected_baseline),
    )
    bl_res = await svc.set_workflow_baseline(
        workflow_definition_id="wf-1",
        scope_id=None,
        manual_time_minutes=60,
        manual_cost_usd=Decimal("200.00"),
        target_ttm_reduction_pct=30,
    )
    assert bl_res.manual_time_minutes == 60

    # Mock approve override
    expected_override = FinopsBudgetOverride(
        id="ov-1",
        run_id="run-1",
        requested_by="user-1",
        approved_by="admin-1",
        override_amount_usd=Decimal("50.000000"),
        reason="Extension budgetaire",
    )
    monkeypatch.setattr(
        "orcia_core.audit_finops.finops_accounting_service.insert_budget_override_sql",
        AsyncMock(return_value=expected_override),
    )
    ov_res = await svc.approve_budget_override(
        run_id="run-1",
        requested_by="user-1",
        approved_by="admin-1",
        override_amount_usd=Decimal("50.00"),
        reason="Extension budgetaire",
        workspace_id="ws-1",
    )
    assert ov_res.override_amount_usd == Decimal("50.000000")
    assert len(outbox_events) == 1
    assert outbox_events[0].run_id == "run-1"
    assert len(sse_events) == 1
    assert sse_events[0]["event_name"] == "BudgetOverrideApproved"
    assert len(svc.collected_outbox_events) == 1
