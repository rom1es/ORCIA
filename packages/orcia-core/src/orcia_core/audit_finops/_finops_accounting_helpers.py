"""Pure monetary rounding, currency conversion, and item builders for FinOps accounting."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Literal, Protocol

from orcia_core.audit_finops.finops_models import (
    DEFAULT_EUR_USD_RATE,
    FinopsProcessItem,
    FinopsTierEffortItem,
)
from orcia_kernel.errors import ValidationDomainError


class FinopsSseNotifierPort(Protocol):
    """Protocol implemented by workspace SSE brokers used to push FinOps events."""

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
MS_PER_HOUR = Decimal("3600000")


def round_usd(d: Decimal) -> Decimal:
    """Round USD monetary amount strictly to `NUMERIC(12, 6)`."""
    try:
        return d.quantize(DEC_SIX, rounding=ROUND_HALF_UP)
    except (InvalidOperation, OverflowError) as exc:
        raise ValidationDomainError(
            detail_override=f"Value {d} exceeds allowable precision for USD monetary calculation."
        ) from exc


def round_eur(d: Decimal) -> Decimal:
    """Round EUR monetary amount strictly to 2 decimal places."""
    try:
        return d.quantize(DEC_TWO, rounding=ROUND_HALF_UP)
    except (InvalidOperation, OverflowError) as exc:
        raise ValidationDomainError(
            detail_override=f"Value {d} exceeds allowable precision for EUR monetary calculation."
        ) from exc


def usd_to_eur(usd: Decimal, rate: Decimal = DEFAULT_EUR_USD_RATE) -> Decimal:
    """Convert a USD `Decimal` value to EUR using the configured FX rate."""
    return round_eur(usd * rate)


def paused_reason_from_status(
    status: str | None,
) -> Literal["BUDGET", "RETRIES"] | None:
    """Map workflow pause DB status onto UI-facing pause reason enum."""
    if status == "PAUSED_MAX_RETRIES":
        return "RETRIES"
    if status == "PAUSED_BUDGET_EXCEEDED":
        return "BUDGET"
    return None


def build_process_item(
    p: dict[str, Any],
    *,
    eur_usd_rate: Decimal,
    hourly_rate_usd: Decimal,
    amortization_runs: Decimal,
) -> FinopsProcessItem:
    """Build a complete 3-component FinOps process breakdown item from raw SQL row."""
    has_declared = bool(p.get("has_declared_baseline", p.get("manual_cost_usd") is not None))
    manual_cost_usd = (
        Decimal(str(p["manual_cost_usd"]))
        if has_declared and p.get("manual_cost_usd") is not None
        else Decimal("0.000000")
    )
    runs_count = int(p["runs_count"])

    amort_setup_usd = (
        round_usd(manual_cost_usd / amortization_runs) if has_declared else Decimal("0.000000")
    )
    amort_setup_eur = usd_to_eur(amort_setup_usd, eur_usd_rate)

    run_usd = round_usd(p["run_cost_usd"])
    run_eur = usd_to_eur(run_usd, eur_usd_rate)

    human_ms = int(p.get("human_ms", 0) or 0)
    human_time_usd = round_usd((Decimal(human_ms) / MS_PER_HOUR) * hourly_rate_usd)
    human_time_eur = usd_to_eur(human_time_usd, eur_usd_rate)

    total_proc_usd = round_usd(amort_setup_usd + run_usd + human_time_usd)
    total_proc_eur = round_eur(amort_setup_eur + run_eur + human_time_eur)

    base_manual_usd = round_usd(manual_cost_usd)
    base_manual_eur = usd_to_eur(base_manual_usd, eur_usd_rate)

    if has_declared and runs_count > 0 and p.get("target_ttm_reduction_pct") is not None:
        ttm_reduction = Decimal(str(p["target_ttm_reduction_pct"]))
    else:
        ttm_reduction = Decimal("0")

    return FinopsProcessItem(
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
        sample_paused_run_id=p.get("sample_paused_run_id"),
        paused_reason=paused_reason_from_status(p.get("sample_paused_status")),
        has_declared_baseline=has_declared,
    )


def build_tier_item(t: dict[str, Any], *, eur_usd_rate: Decimal) -> FinopsTierEffortItem:
    """Build a FinOps tier/effort aggregation item from raw SQL row."""
    cost_usd = round_usd(t["cost_usd"])
    return FinopsTierEffortItem(
        inference_tier=t["inference_tier"],
        effort=t["effort"],
        invocations_count=t["invocations_count"],
        input_tokens=t["input_tokens"],
        output_tokens=t["output_tokens"],
        total_tokens=t["input_tokens"] + t["output_tokens"],
        cost_usd=cost_usd,
        cost_eur=usd_to_eur(cost_usd, eur_usd_rate),
    )


__all__ = [
    "DEC_SIX",
    "DEC_TWO",
    "FinopsSseNotifierPort",
    "MS_PER_HOUR",
    "build_process_item",
    "build_tier_item",
    "paused_reason_from_status",
    "round_eur",
    "round_usd",
    "usd_to_eur",
]
