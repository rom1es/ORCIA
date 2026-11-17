"""Unit tests for cognitive budget guards, circuit breakers, and reversibility (`Story 6.2`)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

from orcia_core.kernel._finops_audit_events import BudgetCircuitTripped
from orcia_core.orchestration._cognitive_budget_guard import (
    CognitiveBudgetGuard,
)


class DummySseBroker:
    def __init__(self) -> None:
        self.published: list[dict[str, Any]] = []

    def publish(
        self,
        *,
        workspace_id: str,
        event_name: str,
        run_id: str,
        step_execution_id: str,
        payload: dict[str, Any],
    ) -> None:
        self.published.append(
            {
                "workspace_id": workspace_id,
                "event_name": event_name,
                "run_id": run_id,
                "step_execution_id": step_execution_id,
                "payload": payload,
            }
        )


def test_anti_infinite_loop_circuit_breaker() -> None:
    """Verifies that reaching max_agent_retries triggers PAUSED_MAX_RETRIES and SSE event."""
    sse = DummySseBroker()
    guard = CognitiveBudgetGuard(sse_broker=sse)  # type: ignore[arg-type]

    # Attempt 2 of 3 -> allowed
    res1 = guard.check_retries_ceiling(
        attempt_count=2,
        max_agent_retries=3,
        run_id="run-1",
        step_execution_id="step-1",
        workspace_id="ws-1",
    )
    assert res1.allowed is True
    assert res1.paused_max_retries is False
    assert len(sse.published) == 0

    # Attempt 3 of 3 -> hard stop PAUSED_MAX_RETRIES
    res2 = guard.check_retries_ceiling(
        attempt_count=3,
        max_agent_retries=3,
        run_id="run-1",
        step_execution_id="step-1",
        workspace_id="ws-1",
    )
    assert res2.allowed is False
    assert res2.paused_max_retries is True
    assert "maximum allowed retries" in res2.reason
    assert len(sse.published) == 1
    assert sse.published[0]["event_name"] == "StepPausedMaxRetries"


@pytest.mark.asyncio
async def test_hierarchical_budget_80_percent_warning_and_100_percent_hard_stop() -> None:
    """Verifies that 80% spending emits a warning, and 100% halts with PAUSED_BUDGET_EXCEEDED."""
    sse = DummySseBroker()
    outbox: list[Any] = []
    guard = CognitiveBudgetGuard(sse_broker=sse, outbox_collector=outbox)  # type: ignore[arg-type]

    # 1. Below 80% threshold ($6 spent on $10 ceiling) -> Allowed, no warning
    res1 = await guard.evaluate_allowance(
        run_id="run-abc",
        step_execution_id="step-1",
        workspace_id="ws-1",
        all_scopes=("GLOBAL", "ws-1"),
        scope_budgets_usd={"GLOBAL": 100.0, "ws-1": 10.0},
        scope_spent_usd={"GLOBAL": 10.0, "ws-1": 6.0},
        estimated_step_cost_usd=0.5,
        run_budget_ceiling_usd=10.0,
        run_spent_usd=6.0,
    )
    assert res1.allowed is True
    assert res1.warning_emitted is False
    assert len(outbox) == 0

    # 2. At 85% threshold ($8.5 spent on $10 ceiling) -> Allowed, warning emitted once
    res2 = await guard.evaluate_allowance(
        run_id="run-abc",
        step_execution_id="step-2",
        workspace_id="ws-1",
        all_scopes=("GLOBAL", "ws-1"),
        scope_budgets_usd={"GLOBAL": 100.0, "ws-1": 10.0},
        scope_spent_usd={"GLOBAL": 10.0, "ws-1": 8.5},
        estimated_step_cost_usd=0.2,
        run_budget_ceiling_usd=10.0,
        run_spent_usd=8.5,
    )
    assert res2.allowed is True
    assert res2.warning_emitted is True
    # 2 warnings emitted: 1 for run ceiling and 1 for scope ws-1 ceiling
    assert len(outbox) == 2
    event = outbox[0]
    assert isinstance(event, BudgetCircuitTripped)
    assert event.run_id == "run-abc"
    assert "warning threshold" in event.trip_reason
    assert len(sse.published) == 2

    # 3. Repeat warning check -> Should not duplicate Outbox event
    res2_repeat = await guard.evaluate_allowance(
        run_id="run-abc",
        step_execution_id="step-3",
        workspace_id="ws-1",
        all_scopes=("GLOBAL", "ws-1"),
        scope_budgets_usd={"GLOBAL": 100.0, "ws-1": 10.0},
        scope_spent_usd={"GLOBAL": 10.0, "ws-1": 8.7},
        estimated_step_cost_usd=0.2,
        run_budget_ceiling_usd=10.0,
        run_spent_usd=8.7,
    )
    assert res2_repeat.allowed is True
    assert len(outbox) == 2  # Both run and scope warnings are deduplicated

    # 4. At 100% hard stop ($10.1 spent on $10 ceiling) -> Blocked PAUSED_BUDGET_EXCEEDED
    res3 = await guard.evaluate_allowance(
        run_id="run-abc",
        step_execution_id="step-4",
        workspace_id="ws-1",
        all_scopes=("GLOBAL", "ws-1"),
        scope_budgets_usd={"GLOBAL": 100.0, "ws-1": 10.0},
        scope_spent_usd={"GLOBAL": 10.0, "ws-1": 10.1},
        estimated_step_cost_usd=0.2,
        run_budget_ceiling_usd=10.0,
        run_spent_usd=10.1,
    )
    assert res3.allowed is False
    assert res3.paused_budget_exceeded is True
    assert "ceiling reached" in res3.reason.lower()
    assert len(outbox) == 3
    stop_event = outbox[2]
    assert isinstance(stop_event, BudgetCircuitTripped)
    assert "budget ceiling reached" in stop_event.trip_reason


def test_migration_story_6_2_upgrade_and_downgrade_reversibility() -> None:
    """Verifies that the Alembic migration 20261116_0602 defines reversible SQL operations."""
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "migrations"
        / "versions"
        / "20261116_0602_story_6_2_finops_budgets_baselines_and_pauses.py"
    )
    assert migration_path.exists(), f"Migration file missing at {migration_path}"

    spec = importlib.util.spec_from_file_location("story_6_2_migration", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "upgrade"), "Migration must implement upgrade()"
    assert hasattr(module, "downgrade"), "Migration must implement downgrade()"
    assert module.revision == "20261116_0602"
    assert module.down_revision == "20261116_0601"

    content = migration_path.read_text(encoding="utf-8")
    assert "finops_scope_budgets" in content
    assert "finops_workflow_baselines" in content
    assert "finops_budget_overrides" in content
    assert "PAUSED_MAX_RETRIES" in content
    assert "PAUSED_BUDGET_EXCEEDED" in content
    assert "DROP TABLE IF EXISTS finops_budget_overrides" in content
    assert "DROP TABLE IF EXISTS finops_workflow_baselines" in content
    assert "DROP TABLE IF EXISTS finops_scope_budgets" in content


@pytest.mark.asyncio
async def test_budget_guard_service_hierarchical_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies BudgetGuardService allowance evaluation against run and scope states."""
    from decimal import Decimal
    from unittest.mock import MagicMock

    from orcia_core.audit_finops.budget_guard_service import BudgetGuardService
    from orcia_core.audit_finops.finops_models import FinopsScopeBudget

    svc = BudgetGuardService(engine=MagicMock())

    # Branch 1: run_state is None -> Allowed by default
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.fetch_run_finops_state_sql",
        pytest.importorskip("unittest.mock").AsyncMock(return_value=None),
    )
    dec1 = await svc.evaluate_budget_allowance("run-none", 0.05)
    assert dec1.is_allowed is True
    assert dec1.circuit_state == "CLOSED"

    # Branch 2: run budget ceiling exceeded
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.fetch_run_finops_state_sql",
        pytest.importorskip("unittest.mock").AsyncMock(
            return_value={
                "budget_max_usd": Decimal("10.00"),
                "total_steps_cost": Decimal("9.98"),
                "total_audit_cost": Decimal("9.95"),
                "workspace_id": "ws-1",
            }
        ),
    )
    dec2 = await svc.evaluate_budget_allowance("run-exceeded", 0.05)
    assert dec2.is_allowed is False
    assert dec2.circuit_state == "CIRCUIT_OPEN"
    assert "Workflow run budget ceiling exceeded" in dec2.reason

    # Branch 3: workspace budget exceeded
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.fetch_run_finops_state_sql",
        pytest.importorskip("unittest.mock").AsyncMock(
            return_value={
                "budget_max_usd": Decimal("100.00"),
                "total_steps_cost": Decimal("5.00"),
                "total_audit_cost": Decimal("5.00"),
                "workspace_id": "ws-1",
            }
        ),
    )
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.list_scope_budgets_sql",
        pytest.importorskip("unittest.mock").AsyncMock(
            return_value=[
                FinopsScopeBudget(
                    id="b-1",
                    scope_type="WORKSPACE",
                    scope_id="ws-1",
                    monthly_budget_usd=Decimal("5.02"),
                    warning_threshold_pct=80,
                    hard_stop_pct=100,
                )
            ]
        ),
    )
    dec3 = await svc.evaluate_budget_allowance("run-ws-exceeded", 0.05)
    assert dec3.is_allowed is False
    assert "Workspace budget ceiling exceeded" in dec3.reason

    # Branch 4: global budget exceeded
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.list_scope_budgets_sql",
        pytest.importorskip("unittest.mock").AsyncMock(
            return_value=[
                FinopsScopeBudget(
                    id="b-2",
                    scope_type="GLOBAL",
                    scope_id=None,
                    monthly_budget_usd=Decimal("5.02"),
                    warning_threshold_pct=80,
                    hard_stop_pct=100,
                )
            ]
        ),
    )
    dec4 = await svc.evaluate_budget_allowance("run-global-exceeded", 0.05)
    assert dec4.is_allowed is False
    assert "Platform global budget ceiling exceeded" in dec4.reason

    # Branch 5: nominal allowed
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.list_scope_budgets_sql",
        pytest.importorskip("unittest.mock").AsyncMock(
            return_value=[
                FinopsScopeBudget(
                    id="b-3",
                    scope_type="GLOBAL",
                    scope_id=None,
                    monthly_budget_usd=Decimal("50.00"),
                    warning_threshold_pct=80,
                    hard_stop_pct=100,
                )
            ]
        ),
    )
    dec5 = await svc.evaluate_budget_allowance("run-nominal", 0.05)
    assert dec5.is_allowed is True
    assert dec5.circuit_state == "CLOSED"

    # Branch 6: preventive warning threshold (80%) allowed with warning reason,
    # and TEAM / BU monthly scope budget breach
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.fetch_monthly_scope_spend_sql",
        pytest.importorskip("unittest.mock").AsyncMock(
            return_value={
                "workspace_monthly_usd": Decimal("12.00"),
                "global_monthly_usd": Decimal("42.00"),
                "org_unit_monthly_usd": {"team-1": Decimal("19.60")},
                "ancestor_org_unit_ids": ("bu-1", "team-1"),
            }
        ),
    )
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.list_scope_budgets_sql",
        pytest.importorskip("unittest.mock").AsyncMock(
            return_value=[
                FinopsScopeBudget(
                    id="b-warn",
                    scope_type="GLOBAL",
                    scope_id=None,
                    monthly_budget_usd=Decimal("50.00"),
                    warning_threshold_pct=80,
                    hard_stop_pct=100,
                )
            ]
        ),
    )
    dec6 = await svc.evaluate_budget_allowance("run-warn", 1.00)
    assert dec6.is_allowed is True
    assert dec6.circuit_state == "HALF_OPEN"
    assert "warning" in dec6.reason.lower()

    # Branch 7: TEAM hard_stop_pct < 100 triggers block on monthly org aggregation
    monkeypatch.setattr(
        "orcia_core.audit_finops.budget_guard_service.list_scope_budgets_sql",
        pytest.importorskip("unittest.mock").AsyncMock(
            return_value=[
                FinopsScopeBudget(
                    id="b-team-90",
                    scope_type="TEAM",
                    scope_id="team-1",
                    monthly_budget_usd=Decimal("22.00"),
                    warning_threshold_pct=70,
                    hard_stop_pct=90,
                )
            ]
        ),
    )
    dec7 = await svc.evaluate_budget_allowance("run-hardstop-90", 0.50)
    assert dec7.is_allowed is False
    assert dec7.circuit_state == "CIRCUIT_OPEN"
    assert "90%" in dec7.reason
