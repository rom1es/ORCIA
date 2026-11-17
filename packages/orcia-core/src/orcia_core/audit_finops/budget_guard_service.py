"""Budget circuit guard implementing `BudgetCircuitGuardPort` (`Story 6.2`, `AD-12`, `AD-21`).

Pure domain service — zero float drift, zero direct HTTP/framework coupling.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal._sql_scope_filter import fetch_monthly_scope_spend_sql
from orcia_core.audit_finops._internal.sql_finops_accounting import (
    fetch_run_finops_state_sql,
    list_scope_budgets_sql,
)
from orcia_core.audit_finops.finops_models import FinopsScopeBudget
from orcia_core.ports.finops_telemetry import (
    BudgetCircuitGuardPort,
    CircuitBreakerDecision,
)

HUNDRED = Decimal("100")


def _compute_scope_burn(
    budget: FinopsScopeBudget,
    *,
    workspace_id: str | None,
    current_run_burn: Decimal,
    monthly_spend: dict[str, Any] | None,
) -> tuple[bool, Decimal]:
    """Return `(applies_to_run, aggregated_monthly_burn_usd)` for `budget`."""
    if budget.scope_type == "WORKSPACE":
        if budget.scope_id != workspace_id:
            return False, Decimal("0")
        base = (
            Decimal(str(monthly_spend["workspace_monthly_usd"]))
            if monthly_spend is not None
            else current_run_burn
        )
        return True, max(base, current_run_burn)

    if budget.scope_type == "GLOBAL":
        base = (
            Decimal(str(monthly_spend["global_monthly_usd"]))
            if monthly_spend is not None
            else current_run_burn
        )
        return True, max(base, current_run_burn)

    if budget.scope_type in ("BU", "TEAM") and budget.scope_id is not None:
        if monthly_spend is None:
            return False, Decimal("0")
        ancestors: set[str] = set(monthly_spend.get("ancestor_org_unit_ids", ()))
        if budget.scope_id not in ancestors:
            return False, Decimal("0")
        ou_map: dict[str, Decimal] = monthly_spend.get("org_unit_monthly_usd", {})
        base = Decimal(str(ou_map.get(budget.scope_id, Decimal("0"))))
        return True, max(base, current_run_burn)

    return False, Decimal("0")


class BudgetGuardService(BudgetCircuitGuardPort):
    """Evaluates hierarchical workflow run and scope budgets against actual DB expenditures."""

    def __init__(self, *, engine: AsyncEngine) -> None:
        self._engine = engine

    async def evaluate_budget_allowance(
        self,
        run_id: str,
        estimated_step_cost_usd: float,
    ) -> CircuitBreakerDecision:
        estimated_dec = Decimal(str(round(estimated_step_cost_usd, 6)))
        run_state = await fetch_run_finops_state_sql(self._engine, run_id)
        if run_state is None:
            return CircuitBreakerDecision(
                is_allowed=True,
                circuit_state="CLOSED",
                reason="Run state not yet recorded in database.",
            )

        budget_max = run_state["budget_max_usd"]
        current_burn = max(run_state["total_steps_cost"], run_state["total_audit_cost"])
        projected_burn = current_burn + estimated_dec

        # 1. Run ceiling check
        if budget_max > Decimal("0") and projected_burn >= budget_max:
            remaining = max(Decimal("0"), budget_max - current_burn)
            return CircuitBreakerDecision(
                is_allowed=False,
                circuit_state="CIRCUIT_OPEN",
                reason=(
                    f"Workflow run budget ceiling exceeded: projected {projected_burn:.4f} USD "
                    f"reached limit {budget_max:.4f} USD."
                ),
                remaining_budget_usd=float(remaining),
                current_burn_usd=float(projected_burn),
            )

        # 2. Hierarchical monthly scope budgets check (GLOBAL -> BU -> TEAM -> WORKSPACE)
        workspace_id = run_state.get("workspace_id")
        scope_budgets = await list_scope_budgets_sql(self._engine)
        monthly_spend = await fetch_monthly_scope_spend_sql(self._engine, workspace_id)

        warning_reasons: list[str] = []
        scope_labels = {
            "WORKSPACE": "Workspace",
            "TEAM": "Team",
            "BU": "BU",
            "GLOBAL": "Platform global",
        }
        for b in scope_budgets:
            applies, scope_burn = _compute_scope_burn(
                b,
                workspace_id=workspace_id,
                current_run_burn=current_burn,
                monthly_spend=monthly_spend,
            )
            if not applies or b.monthly_budget_usd <= Decimal("0"):
                continue

            projected_scope = scope_burn + estimated_dec
            hard_limit = (b.monthly_budget_usd * Decimal(b.hard_stop_pct)) / HUNDRED
            warn_limit = (b.monthly_budget_usd * Decimal(b.warning_threshold_pct)) / HUNDRED
            label = scope_labels.get(b.scope_type, b.scope_type)

            if hard_limit > Decimal("0") and projected_scope >= hard_limit:
                return CircuitBreakerDecision(
                    is_allowed=False,
                    circuit_state="CIRCUIT_OPEN",
                    reason=(
                        f"{label} budget ceiling exceeded: {projected_scope:.4f} USD "
                        f">= {hard_limit:.4f} USD "
                        f"({b.hard_stop_pct}% of {b.monthly_budget_usd:.4f} USD)."
                    ),
                    remaining_budget_usd=0.0,
                    current_burn_usd=float(projected_scope),
                )
            if warn_limit > Decimal("0") and projected_scope >= warn_limit:
                warning_reasons.append(
                    f"{label} warning threshold ({b.warning_threshold_pct}%) reached: "
                    f"{projected_scope:.4f} USD >= {warn_limit:.4f} USD"
                )

        remaining_run = max(Decimal("0"), budget_max - current_burn)
        return CircuitBreakerDecision(
            is_allowed=True,
            circuit_state="HALF_OPEN" if warning_reasons else "CLOSED",
            reason="; ".join(warning_reasons)
            if warning_reasons
            else "Budget allowance verified under all ceilings.",
            remaining_budget_usd=float(remaining_run),
            current_burn_usd=float(current_burn),
        )


__all__ = [
    "BudgetGuardService",
]
