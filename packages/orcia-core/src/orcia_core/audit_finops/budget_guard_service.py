"""Budget circuit guard implementing `BudgetCircuitGuardPort` (`Story 6.2`, `AD-12`, `AD-21`).

Pure domain service — zero float drift, zero direct HTTP/framework coupling.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.audit_finops._internal.sql_finops_accounting import (
    fetch_run_finops_state_sql,
    list_scope_budgets_sql,
)
from orcia_core.ports.finops_telemetry import (
    BudgetCircuitGuardPort,
    CircuitBreakerDecision,
)


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
            # If run state is not in DB yet, allow by default
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

        # 2. Scope budget ceilings check (workspace and global)
        workspace_id = run_state.get("workspace_id")
        scope_budgets = await list_scope_budgets_sql(self._engine)
        for b in scope_budgets:
            if b.scope_type == "WORKSPACE" and b.scope_id == workspace_id:
                if projected_burn >= b.monthly_budget_usd:
                    return CircuitBreakerDecision(
                        is_allowed=False,
                        circuit_state="CIRCUIT_OPEN",
                        reason=(
                            f"Workspace budget ceiling exceeded: {projected_burn:.4f} USD "
                            f">= {b.monthly_budget_usd:.4f} USD."
                        ),
                        remaining_budget_usd=0.0,
                        current_burn_usd=float(projected_burn),
                    )
            elif b.scope_type == "GLOBAL" and projected_burn >= b.monthly_budget_usd:
                return CircuitBreakerDecision(
                    is_allowed=False,
                    circuit_state="CIRCUIT_OPEN",
                    reason=(
                        f"Platform global budget ceiling exceeded: {projected_burn:.4f} USD "
                        f">= {b.monthly_budget_usd:.4f} USD."
                    ),
                    remaining_budget_usd=0.0,
                    current_burn_usd=float(projected_burn),
                )

        remaining_run = max(Decimal("0"), budget_max - current_burn)
        return CircuitBreakerDecision(
            is_allowed=True,
            circuit_state="CLOSED",
            reason="Budget allowance verified under all ceilings.",
            remaining_budget_usd=float(remaining_run),
            current_burn_usd=float(current_burn),
        )


__all__ = [
    "BudgetGuardService",
]
