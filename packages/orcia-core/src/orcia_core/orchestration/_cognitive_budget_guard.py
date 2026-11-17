"""Hierarchical cognitive budget guard and anti-infinite-loop circuit breaker (`Story 6.2`).

Extracted from `cognitive_router.py` to enforce strict modularity (< 300 lines) and provide:
- Hierarchical budget quota checks (`GLOBAL -> BU -> TEAM -> WORKSPACE`) + run ceiling
- 80% preventive warning: emits `BudgetCircuitTripped` outbox event & SSE broadcast
- 100% hard stop: pauses execution with `PAUSED_BUDGET_EXCEEDED`
- Anti-infinite loop circuit breaker: halts when attempts reach `max_agent_retries` (default: 3)
  with `PAUSED_MAX_RETRIES`
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from orcia_core.kernel._finops_audit_events import BudgetCircuitTripped
from orcia_core.observability.logging import get_logger
from orcia_core.ports.finops_telemetry import BudgetCircuitGuardPort

if TYPE_CHECKING:
    from orcia_core.orchestration.presence_and_sse import SseBroadcastPort

logger = get_logger("orcia.core.orchestration.budget_guard")


@dataclass(frozen=True, slots=True)
class BudgetCheckResult:
    """Outcome of a cognitive budget ceiling or retry evaluation."""

    allowed: bool
    paused_budget_exceeded: bool = False
    paused_max_retries: bool = False
    warning_emitted: bool = False
    reason: str = ""
    current_burn_usd: float = 0.0
    budget_limit_usd: float = 0.0


class CognitiveBudgetGuard:
    """Evaluates hierarchical budget allowances and agent retries with Outbox + SSE side effects."""

    def __init__(
        self,
        *,
        external_guard_port: BudgetCircuitGuardPort | None = None,
        sse_broker: SseBroadcastPort | None = None,
        outbox_collector: list[Any] | None = None,
    ) -> None:
        self._external_guard_port = external_guard_port
        self._sse_broker = sse_broker
        self._outbox_collector = outbox_collector if outbox_collector is not None else []
        self._emitted_warnings: set[str] = set()

    @property
    def collected_outbox_events(self) -> list[Any]:
        return self._outbox_collector

    def set_external_guard_port(self, port: BudgetCircuitGuardPort) -> None:
        """Bind a persistent `BudgetCircuitGuardPort` implementation at runtime."""
        self._external_guard_port = port

    def check_retries_ceiling(
        self,
        *,
        attempt_count: int,
        max_agent_retries: int = 3,
        run_id: str = "",
        step_execution_id: str = "",
        workspace_id: str | None = None,
    ) -> BudgetCheckResult:
        """Check if agent loop attempts have exceeded the allowed limit."""
        if attempt_count >= max_agent_retries:
            reason = (
                f"Agent reached maximum allowed retries ({attempt_count}/{max_agent_retries}). "
                "Halting infinite loop."
            )
            if self._sse_broker is not None and workspace_id:
                try:
                    self._sse_broker.publish(
                        workspace_id=workspace_id,
                        event_name="StepPausedMaxRetries",
                        run_id=run_id,
                        step_execution_id=step_execution_id,
                        payload={
                            "attempt_count": attempt_count,
                            "max_agent_retries": max_agent_retries,
                            "reason": reason,
                        },
                    )
                except Exception as exc:
                    logger.warning(
                        "finops_budget_guard_retries_sse_publish_failed",
                        run_id=run_id,
                        workspace_id=workspace_id,
                        error_type=type(exc).__name__,
                        detail=str(exc),
                    )
            return BudgetCheckResult(
                allowed=False,
                paused_max_retries=True,
                reason=reason,
            )
        return BudgetCheckResult(allowed=True)

    async def evaluate_allowance(
        self,
        *,
        run_id: str,
        step_execution_id: str,
        workspace_id: str | None,
        all_scopes: tuple[str, ...],
        scope_budgets_usd: dict[str, float],
        scope_spent_usd: dict[str, float],
        estimated_step_cost_usd: float = 0.0,
        run_budget_ceiling_usd: float | None = None,
        run_spent_usd: float = 0.0,
        trace_id: str = "00000000000000000000000000000000",
    ) -> BudgetCheckResult:
        """Evaluate hierarchical budgets (scopes + run) and trigger warning/hard stop."""
        warning_triggered = False
        # 1. External guard port delegation if configured
        if self._external_guard_port is not None:
            decision = await self._external_guard_port.evaluate_budget_allowance(
                run_id=run_id,
                estimated_step_cost_usd=estimated_step_cost_usd,
            )
            if not decision.is_allowed:
                self._emit_budget_tripped(
                    run_id=run_id,
                    step_execution_id=step_execution_id,
                    workspace_id=workspace_id,
                    burn=decision.current_burn_usd or 0.0,
                    limit=(decision.current_burn_usd or 0.0)
                    + (decision.remaining_budget_usd or 0.0),
                    reason=decision.reason,
                    trace_id=trace_id,
                    is_hard_stop=True,
                )
                return BudgetCheckResult(
                    allowed=False,
                    paused_budget_exceeded=True,
                    reason=decision.reason,
                    current_burn_usd=decision.current_burn_usd or 0.0,
                )

        # 2. Run-level budget ceiling check
        if run_budget_ceiling_usd is not None and run_budget_ceiling_usd > 0:
            projected_run_burn = round(run_spent_usd + estimated_step_cost_usd, 6)
            if projected_run_burn >= run_budget_ceiling_usd:
                reason = (
                    f"Run budget ceiling reached ({projected_run_burn:.4f} USD >= "
                    f"{run_budget_ceiling_usd:.4f} USD)."
                )
                self._emit_budget_tripped(
                    run_id=run_id,
                    step_execution_id=step_execution_id,
                    workspace_id=workspace_id,
                    burn=projected_run_burn,
                    limit=run_budget_ceiling_usd,
                    reason=reason,
                    trace_id=trace_id,
                    is_hard_stop=True,
                )
                return BudgetCheckResult(
                    allowed=False,
                    paused_budget_exceeded=True,
                    reason=reason,
                    current_burn_usd=projected_run_burn,
                    budget_limit_usd=run_budget_ceiling_usd,
                )
            # 80% warning threshold for run budget
            warning_threshold = run_budget_ceiling_usd * 0.8
            if projected_run_burn >= warning_threshold:
                warn_key = f"{run_id}:warning:80pct"
                if warn_key not in self._emitted_warnings:
                    self._emitted_warnings.add(warn_key)
                    warning_triggered = True
                    self._emit_budget_tripped(
                        run_id=run_id,
                        step_execution_id=step_execution_id,
                        workspace_id=workspace_id,
                        burn=projected_run_burn,
                        limit=run_budget_ceiling_usd,
                        reason=(
                            f"Run budget 80% warning threshold reached "
                            f"({projected_run_burn:.4f} USD)."
                        ),
                        trace_id=trace_id,
                        is_hard_stop=False,
                    )

        # 3. Hierarchical scope ceilings
        for sc_id in all_scopes:
            ceiling = scope_budgets_usd.get(sc_id)
            if ceiling is None or ceiling < 0:
                continue
            spent = scope_spent_usd.get(sc_id, 0.0)
            projected_spent = round(spent + estimated_step_cost_usd, 6)

            # Hard stop (100% or spent >= ceiling)
            if spent >= ceiling or projected_spent >= ceiling:
                reason = (
                    f"Scope {sc_id} budget ceiling reached ({projected_spent:.4f} USD >= "
                    f"{ceiling:.4f} USD)."
                )
                self._emit_budget_tripped(
                    run_id=run_id,
                    step_execution_id=step_execution_id,
                    workspace_id=workspace_id,
                    burn=projected_spent,
                    limit=ceiling,
                    reason=reason,
                    trace_id=trace_id,
                    is_hard_stop=True,
                )
                return BudgetCheckResult(
                    allowed=False,
                    paused_budget_exceeded=True,
                    reason=reason,
                    current_burn_usd=projected_spent,
                    budget_limit_usd=ceiling,
                )

            # Warning threshold (80%)
            warning_threshold = ceiling * 0.8
            if projected_spent >= warning_threshold:
                warn_key = f"{sc_id}:warning:80pct"
                if warn_key not in self._emitted_warnings:
                    self._emitted_warnings.add(warn_key)
                    warning_triggered = True
                    self._emit_budget_tripped(
                        run_id=run_id,
                        step_execution_id=step_execution_id,
                        workspace_id=workspace_id,
                        burn=projected_spent,
                        limit=ceiling,
                        reason=(
                            f"Scope {sc_id} reached 80% warning threshold "
                            f"({projected_spent:.4f} USD)."
                        ),
                        trace_id=trace_id,
                        is_hard_stop=False,
                    )

        return BudgetCheckResult(allowed=True, warning_emitted=warning_triggered)

    def _emit_budget_tripped(
        self,
        *,
        run_id: str,
        step_execution_id: str,
        workspace_id: str | None,
        burn: float,
        limit: float,
        reason: str,
        trace_id: str,
        is_hard_stop: bool,
    ) -> None:
        event = BudgetCircuitTripped.create(
            run_id=run_id,
            workspace_id=workspace_id,
            current_burn_usd=burn,
            budget_limit_usd=limit,
            trip_reason=reason,
            trace_id=trace_id,
        )
        self._outbox_collector.append(event)
        if self._sse_broker is not None and workspace_id:
            event_name = "BudgetCircuitTripped" if is_hard_stop else "BudgetWarningTripped"
            try:
                self._sse_broker.publish(
                    workspace_id=workspace_id,
                    event_name=event_name,
                    run_id=run_id,
                    step_execution_id=step_execution_id,
                    payload={
                        "current_burn_usd": burn,
                        "budget_limit_usd": limit,
                        "trip_reason": reason,
                        "is_hard_stop": is_hard_stop,
                    },
                )
            except Exception as exc:
                logger.warning(
                    "finops_budget_guard_tripped_sse_publish_failed",
                    run_id=run_id,
                    workspace_id=workspace_id,
                    event_name=event_name,
                    error_type=type(exc).__name__,
                    detail=str(exc),
                )


__all__ = [
    "BudgetCheckResult",
    "CognitiveBudgetGuard",
]
