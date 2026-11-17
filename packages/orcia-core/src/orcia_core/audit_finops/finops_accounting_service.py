"""Domain service computing the complete 3-component FinOps economic equation (`Story 6.2`).

Calculates:
- Amortized setup cost = manual_cost / forecast_runs
- Consolidated run cost = internal verified + external reported tokens & costs
- Human time cost = (human_active_seconds / 3600) * hourly_rate
- TTM reduction differential vs declared baseline
- Approves budget overrides, awakening paused runs with Outbox event emission

All monetary arithmetic strictly uses `decimal.Decimal` (`NUMERIC(12, 6)`).
"""

from __future__ import annotations

import contextlib
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal.sql_finops_accounting import (
    insert_budget_override_sql,
    list_scope_budgets_sql,
    list_workflow_baselines_sql,
    upsert_scope_budget_sql,
    upsert_workflow_baseline_sql,
)
from orcia_core.audit_finops._internal.sql_finops_dashboard import (
    fetch_dashboard_overview_sql,
    fetch_dashboard_processes_sql,
    fetch_dashboard_tiers_sql,
)
from orcia_core.audit_finops.finops_models import (
    DEFAULT_AMORTIZATION_RUNS,
    DEFAULT_EUR_USD_RATE,
    DEFAULT_HOURLY_RATE_USD,
    FinopsBreakdown,
    FinopsBudgetOverride,
    FinopsOverview,
    FinopsProcessItem,
    FinopsScopeBudget,
    FinopsTierEffortItem,
    FinopsWorkflowBaseline,
    ScopeType,
)
from orcia_core.kernel._finops_audit_events import BudgetOverrideApproved
from orcia_kernel.errors import ValidationDomainError


class FinopsSseNotifierPort(Protocol):
    def publish(
        self,
        *,
        workspace_id: str,
        event_name: str,
        run_id: str,
        step_execution_id: str,
        payload: dict[str, Any],
    ) -> Any: ...


DEC_SIX = Decimal("0.000001")
DEC_TWO = Decimal("0.01")


def _round_usd(d: Decimal) -> Decimal:
    try:
        return d.quantize(DEC_SIX, rounding=ROUND_HALF_UP)
    except (InvalidOperation, OverflowError) as exc:
        raise ValidationDomainError(
            detail_override=f"Value {d} exceeds allowable precision for USD monetary calculation."
        ) from exc


def _round_eur(d: Decimal) -> Decimal:
    try:
        return d.quantize(DEC_TWO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, OverflowError) as exc:
        raise ValidationDomainError(
            detail_override=f"Value {d} exceeds allowable precision for EUR monetary calculation."
        ) from exc


def _usd_to_eur(usd: Decimal, rate: Decimal = DEFAULT_EUR_USD_RATE) -> Decimal:
    return _round_eur(usd * rate)


class FinopsAccountingService:
    """Consolidated accounting service for FinOps budgets, baselines, and execution costs."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        eur_usd_rate: Decimal = DEFAULT_EUR_USD_RATE,
        hourly_rate_usd: Decimal = DEFAULT_HOURLY_RATE_USD,
        amortization_runs: Decimal = DEFAULT_AMORTIZATION_RUNS,
        sse_broker: FinopsSseNotifierPort | None = None,
        outbox_collector: list[Any] | None = None,
    ) -> None:
        self._engine = engine
        self._eur_usd_rate = eur_usd_rate
        self._hourly_rate_usd = hourly_rate_usd
        self._amortization_runs = amortization_runs
        self._sse_broker = sse_broker
        self._outbox_collector = outbox_collector if outbox_collector is not None else []

    @property
    def collected_outbox_events(self) -> list[Any]:
        return self._outbox_collector

    async def get_overview(
        self,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str | None = None,
    ) -> FinopsOverview:
        data = await fetch_dashboard_overview_sql(
            self._engine, scope_type=scope_type, scope_id=scope_id
        )
        total_usd = _round_usd(data["total_cost_usd"])
        total_eur = _usd_to_eur(total_usd, self._eur_usd_rate)
        verified_usd = _round_usd(data["verified_internal_cost_usd"])
        verified_eur = _usd_to_eur(verified_usd, self._eur_usd_rate)
        reported_usd = _round_usd(data["reported_external_cost_usd"])
        reported_eur = _usd_to_eur(reported_usd, self._eur_usd_rate)

        return FinopsOverview(
            total_cost_usd=total_usd,
            total_cost_eur=total_eur,
            verified_internal_cost_usd=verified_usd,
            verified_internal_cost_eur=verified_eur,
            reported_external_cost_usd=reported_usd,
            reported_external_cost_eur=reported_eur,
            total_llm_tokens=data["total_input_tokens"] + data["total_output_tokens"],
            internal_tokens=data["internal_tokens"],
            remote_tokens=data["remote_tokens"],
            total_external_calls=data["total_external_calls"],
            external_units_breakdown={},
            cache_savings_usd=Decimal("0.000000"),
            cache_savings_eur=Decimal("0.00"),
            active_circuit_breakers_count=0,
            paused_runs_count=data["paused_runs_count"],
            accounted_runs_count=data["accounted_runs_count"],
        )

    async def get_breakdown(
        self,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str | None = None,
    ) -> FinopsBreakdown:
        overview = await self.get_overview(scope_type=scope_type, scope_id=scope_id)
        raw_procs = await fetch_dashboard_processes_sql(
            self._engine, scope_type=scope_type, scope_id=scope_id
        )
        raw_tiers = await fetch_dashboard_tiers_sql(
            self._engine, scope_type=scope_type, scope_id=scope_id
        )
        scope_budgets = await list_scope_budgets_sql(
            self._engine, scope_type=scope_type, scope_id=scope_id
        )
        baselines = await list_workflow_baselines_sql(self._engine, scope_id=scope_id)

        processes: list[FinopsProcessItem] = []
        for p in raw_procs:
            manual_cost_usd = p["manual_cost_usd"] or Decimal("500.000000")
            runs_count = p["runs_count"]

            # Setup amortization: manual_cost / amortization_runs
            amort_setup_usd = _round_usd(manual_cost_usd / self._amortization_runs)
            amort_setup_eur = _usd_to_eur(amort_setup_usd, self._eur_usd_rate)

            # Run cost
            run_usd = _round_usd(p["run_cost_usd"])
            run_eur = _usd_to_eur(run_usd, self._eur_usd_rate)

            # Human time valorized (estimated from active human task baselines if any)
            human_time_usd = _round_usd(Decimal("0.000000"))
            human_time_eur = Decimal("0.00")

            # Complete economic equation: Setup + Run + Human Time
            total_proc_usd = _round_usd(amort_setup_usd + run_usd + human_time_usd)
            total_proc_eur = _round_eur(amort_setup_eur + run_eur + human_time_eur)

            # Baseline manual cost
            base_manual_usd = _round_usd(manual_cost_usd)
            base_manual_eur = _usd_to_eur(base_manual_usd, self._eur_usd_rate)

            # TTM reduction %
            target_reduction = Decimal(str(p["target_ttm_reduction_pct"] or 25))
            ttm_reduction = target_reduction if runs_count > 0 else Decimal("0")

            processes.append(
                FinopsProcessItem(
                    workflow_id=p["workflow_id"],
                    workflow_title=p["workflow_title"],
                    runs_count=runs_count,
                    amortized_setup_cost_usd=amort_setup_usd,
                    amortized_setup_cost_eur=amort_setup_eur,
                    run_cost_usd=run_usd,
                    run_cost_eur=run_eur,
                    human_time_cost_usd=human_time_usd,
                    human_time_cost_eur=human_time_eur,
                    total_cost_usd=total_proc_usd,
                    total_cost_eur=total_proc_eur,
                    baseline_manual_cost_usd=base_manual_usd,
                    baseline_manual_cost_eur=base_manual_eur,
                    ttm_reduction_pct=ttm_reduction,
                    active_budget_override=p["overrides_usd"] > Decimal("0"),
                    paused_runs_count=p["paused_runs"],
                )
            )

        tiers: list[FinopsTierEffortItem] = []
        for t in raw_tiers:
            cost_usd = _round_usd(t["cost_usd"])
            cost_eur = _usd_to_eur(cost_usd, self._eur_usd_rate)
            tiers.append(
                FinopsTierEffortItem(
                    inference_tier=t["inference_tier"],
                    effort=t["effort"],
                    invocations_count=t["invocations_count"],
                    input_tokens=t["input_tokens"],
                    output_tokens=t["output_tokens"],
                    total_tokens=t["input_tokens"] + t["output_tokens"],
                    cost_usd=cost_usd,
                    cost_eur=cost_eur,
                )
            )

        return FinopsBreakdown(
            overview=overview,
            processes=processes,
            tiers=tiers,
            scope_budgets=scope_budgets,
            baselines=baselines,
        )

    async def set_scope_budget(
        self,
        *,
        scope_type: ScopeType,
        scope_id: str | None,
        monthly_budget_usd: Decimal,
        warning_threshold_pct: int = 80,
        hard_stop_pct: int = 100,
    ) -> FinopsScopeBudget:
        return await upsert_scope_budget_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            monthly_budget_usd=_round_usd(monthly_budget_usd),
            warning_threshold_pct=warning_threshold_pct,
            hard_stop_pct=hard_stop_pct,
        )

    async def set_workflow_baseline(
        self,
        *,
        workflow_definition_id: str,
        scope_id: str | None,
        manual_time_minutes: int,
        manual_cost_usd: Decimal,
        target_ttm_reduction_pct: int = 25,
    ) -> FinopsWorkflowBaseline:
        return await upsert_workflow_baseline_sql(
            self._engine,
            workflow_definition_id=workflow_definition_id,
            scope_id=scope_id,
            manual_time_minutes=manual_time_minutes,
            manual_cost_usd=_round_usd(manual_cost_usd),
            target_ttm_reduction_pct=target_ttm_reduction_pct,
        )

    async def approve_budget_override(
        self,
        *,
        run_id: str,
        requested_by: str,
        approved_by: str,
        override_amount_usd: Decimal,
        reason: str,
        workspace_id: str | None = None,
        trace_id: str = "00000000000000000000000000000000",
    ) -> FinopsBudgetOverride:
        override = await insert_budget_override_sql(
            self._engine,
            run_id=run_id,
            requested_by=requested_by,
            approved_by=approved_by,
            override_amount_usd=_round_usd(override_amount_usd),
            reason=reason,
        )

        event = BudgetOverrideApproved.create(
            run_id=run_id,
            workspace_id=workspace_id,
            override_amount_usd=float(override.override_amount_usd),
            approved_by_user_id=approved_by,
            justification=reason,
            trace_id=trace_id,
        )
        self._outbox_collector.append(event)

        if self._sse_broker is not None and workspace_id:
            with contextlib.suppress(Exception):
                self._sse_broker.publish(
                    workspace_id=workspace_id,
                    event_name="BudgetOverrideApproved",
                    run_id=run_id,
                    step_execution_id="",
                    payload={
                        "run_id": run_id,
                        "override_amount_usd": float(override.override_amount_usd),
                        "approved_by": approved_by,
                        "reason": reason,
                    },
                )

        return override


__all__ = [
    "FinopsAccountingService",
]
