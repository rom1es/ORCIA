"""Domain service computing the complete 3-component FinOps economic equation (`Story 6.2`).

Calculates:
- Amortized setup cost = manual_cost / forecast_runs (only when baseline is declared)
- Consolidated run cost = internal verified + external reported tokens & costs
- Human time cost = (human_active_ms / 3_600_000) * hourly_rate
- TTM reduction differential vs declared baseline
- Approves budget overrides, awakening paused runs with transactional Outbox + audit ledger

All monetary arithmetic strictly uses `decimal.Decimal` (`NUMERIC(12, 6)`).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._finops_accounting_helpers import (
    FinopsSseNotifierPort,
    build_process_item,
    build_tier_item,
    round_eur,
    round_usd,
    usd_to_eur,
)
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
    FinopsScopeBudget,
    FinopsWorkflowBaseline,
    ScopeType,
)
from orcia_core.kernel._finops_audit_events import BudgetOverrideApproved
from orcia_core.observability.logging import get_logger
from orcia_kernel.errors import ValidationDomainError

logger = get_logger("orcia.core.audit_finops.service")

# Keep module-level compatibility aliases for unit tests / internal imports
_round_eur = round_eur
_round_usd = round_usd
_usd_to_eur = usd_to_eur


class FinopsAccountingService:
    """Consolidated accounting service for FinOps budgets, baselines, and execution costs."""

    def __init__(
        self,
        *,
        engine: AsyncEngine | None,
        eur_usd_rate: Decimal = DEFAULT_EUR_USD_RATE,
        hourly_rate_usd: Decimal = DEFAULT_HOURLY_RATE_USD,
        amortization_runs: Decimal = DEFAULT_AMORTIZATION_RUNS,
        sse_broker: FinopsSseNotifierPort | None = None,
        outbox_collector: list[Any] | None = None,
        run_resumer: Callable[[str], Awaitable[None]] | None = None,
    ) -> None:
        self._engine = engine
        self._eur_usd_rate = eur_usd_rate
        self._hourly_rate_usd = hourly_rate_usd
        self._amortization_runs = amortization_runs
        self._sse_broker = sse_broker
        self._outbox_collector = outbox_collector if outbox_collector is not None else []
        self._run_resumer = run_resumer

    @property
    def collected_outbox_events(self) -> list[Any]:
        return self._outbox_collector

    async def get_overview(
        self,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str | None = None,
        allowed_workspace_ids: tuple[str, ...] | None = None,
    ) -> FinopsOverview:
        data = await fetch_dashboard_overview_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            allowed_workspace_ids=allowed_workspace_ids,
        )
        total_usd = round_usd(data["total_cost_usd"])
        verified_usd = round_usd(data["verified_internal_cost_usd"])
        reported_usd = round_usd(data["reported_external_cost_usd"])
        cache_usd = round_usd(Decimal(str(data.get("cache_savings_usd", Decimal("0.000000")))))

        return FinopsOverview(
            total_cost_usd=total_usd,
            total_cost_eur=usd_to_eur(total_usd, self._eur_usd_rate),
            verified_internal_cost_usd=verified_usd,
            verified_internal_cost_eur=usd_to_eur(verified_usd, self._eur_usd_rate),
            reported_external_cost_usd=reported_usd,
            reported_external_cost_eur=usd_to_eur(reported_usd, self._eur_usd_rate),
            total_llm_tokens=data["total_input_tokens"] + data["total_output_tokens"],
            internal_tokens=data["internal_tokens"],
            remote_tokens=data["remote_tokens"],
            total_external_calls=data["total_external_calls"],
            external_units_breakdown=data.get("external_units_breakdown", {}),
            cache_savings_usd=cache_usd,
            cache_savings_eur=usd_to_eur(cache_usd, self._eur_usd_rate),
            active_circuit_breakers_count=data.get("active_circuit_breakers_count", 0),
            paused_runs_count=data["paused_runs_count"],
            accounted_runs_count=data["accounted_runs_count"],
        )

    async def get_breakdown(
        self,
        *,
        scope_type: ScopeType = "GLOBAL",
        scope_id: str | None = None,
        allowed_workspace_ids: tuple[str, ...] | None = None,
    ) -> FinopsBreakdown:
        overview = await self.get_overview(
            scope_type=scope_type,
            scope_id=scope_id,
            allowed_workspace_ids=allowed_workspace_ids,
        )
        if self._engine is None:
            return FinopsBreakdown(
                overview=overview,
                processes=[],
                tiers=[],
                scope_budgets=[],
                baselines=[],
            )
        raw_procs = await fetch_dashboard_processes_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            allowed_workspace_ids=allowed_workspace_ids,
        )
        raw_tiers = await fetch_dashboard_tiers_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            allowed_workspace_ids=allowed_workspace_ids,
        )
        scope_budgets = await list_scope_budgets_sql(
            self._engine, scope_type=scope_type, scope_id=scope_id
        )
        baselines = await list_workflow_baselines_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            allowed_workspace_ids=allowed_workspace_ids,
        )

        processes = [
            build_process_item(
                p,
                eur_usd_rate=self._eur_usd_rate,
                hourly_rate_usd=self._hourly_rate_usd,
                amortization_runs=self._amortization_runs,
            )
            for p in raw_procs
        ]
        tiers = [build_tier_item(t, eur_usd_rate=self._eur_usd_rate) for t in raw_tiers]

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
        if self._engine is None:
            raise ValidationDomainError(
                detail_override="PostgreSQL database engine is required for FinOps budgets."
            )
        return await upsert_scope_budget_sql(
            self._engine,
            scope_type=scope_type,
            scope_id=scope_id,
            monthly_budget_usd=round_usd(monthly_budget_usd),
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
        if self._engine is None:
            raise ValidationDomainError(
                detail_override="PostgreSQL database engine is required for FinOps baselines."
            )
        return await upsert_workflow_baseline_sql(
            self._engine,
            workflow_definition_id=workflow_definition_id,
            scope_id=scope_id,
            manual_time_minutes=manual_time_minutes,
            manual_cost_usd=round_usd(manual_cost_usd),
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
        if self._engine is None:
            raise ValidationDomainError(
                detail_override="PostgreSQL database engine is required for budget overrides."
            )
        rounded_amount = round_usd(override_amount_usd)
        event = BudgetOverrideApproved.create(
            run_id=run_id,
            workspace_id=workspace_id,
            override_amount_usd=float(rounded_amount),
            approved_by_user_id=approved_by,
            justification=reason,
            trace_id=trace_id,
        )
        override = await insert_budget_override_sql(
            self._engine,
            run_id=run_id,
            requested_by=requested_by,
            approved_by=approved_by,
            override_amount_usd=rounded_amount,
            reason=reason,
            outbox_event=event,
        )
        self._outbox_collector.append(event)

        if self._sse_broker is not None and workspace_id:
            try:
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
            except Exception as exc:
                logger.warning(
                    "finops_sse_budget_override_publish_failed",
                    run_id=run_id,
                    workspace_id=workspace_id,
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )

        if self._run_resumer is not None:
            try:
                await self._run_resumer(run_id)
            except Exception as exc:
                logger.warning(
                    "finops_budget_override_run_resume_failed",
                    run_id=run_id,
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )

        return override


__all__ = [
    "FinopsAccountingService",
    "FinopsSseNotifierPort",
]
