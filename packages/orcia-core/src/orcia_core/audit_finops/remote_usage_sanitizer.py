"""Remote usage telemetry sanitizer for MCP & A2A external services (`Story 6.4`, `AD-12`, `AD-19`).

Strict security validation:
- Rejects negative numbers, NaN, Infinity, booleans, and invalid currencies
- Supports 3 metric formats (remote tokens, direct monetary cost, business units)
- Supports 3 valuation modes (`NATIVE_TELEMETRY`, `FIXED_SCALE`, `VOLUMETRIC_ONLY`)
- Caps reported per-call cost at `max_reported_cost_per_call_eur` (default 5.00 EUR) and emits
  `RemoteUsageAnomalyCapped`
- Converts all monetary values via `Decimal` into `NUMERIC(12, 6)` USD pivot
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from orcia_core.audit_finops._remote_usage_parser import extract_remote_usage_payload
from orcia_core.audit_finops.finops_models import DEFAULT_EUR_USD_RATE
from orcia_core.kernel._finops_audit_events import RemoteUsageAnomalyCapped
from orcia_core.ports.finops_telemetry import (
    RemoteUsageRawPayload,
    RemoteUsageSanitizerPort,
    SanitizedRemoteUsage,
    ValuationMode,
)
from orcia_kernel.errors import ValidationDomainError

DEC_SIX = Decimal("0.000001")
DEC_ZERO = Decimal("0.000000")

_DEFAULT_CURRENCY_TO_EUR: dict[str, Decimal] = {
    "EUR": Decimal("1.000000"),
    "GBP": Decimal("1.170000"),
    "CHF": Decimal("1.060000"),
}


def _validate_non_negative_int(value: int | None, field_name: str) -> int:
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationDomainError(
            detail_override=f"Telemetry field '{field_name}' must be a non-negative integer."
        )
    if value < 0:
        raise ValidationDomainError(
            detail_override=f"Telemetry field '{field_name}' cannot be negative ({value})."
        )
    return value


def _validate_non_negative_decimal(
    value: float | int | Decimal | None,
    field_name: str,
    *,
    allow_none: bool = False,
) -> Decimal | None:
    if value is None:
        return None if allow_none else DEC_ZERO
    if isinstance(value, bool):
        raise ValidationDomainError(
            detail_override=f"Telemetry field '{field_name}' cannot be a boolean."
        )
    if isinstance(value, float) and (not math.isfinite(value) or value < 0.0):
        raise ValidationDomainError(
            detail_override=f"Telemetry field '{field_name}' must be finite and >= 0 ({value!r})."
        )
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValidationDomainError(
            detail_override=f"Invalid numeric telemetry value for '{field_name}': {value!r}."
        ) from exc
    if not dec.is_finite() or dec < DEC_ZERO:
        raise ValidationDomainError(
            detail_override=f"Telemetry field '{field_name}' must be finite and >= 0 ({value!r})."
        )
    return dec


class RemoteUsageSanitizer(RemoteUsageSanitizerPort):
    """Sanitizer normalizing external MCP/A2A telemetry to USD pivot with safety capping."""

    def __init__(
        self,
        *,
        eur_usd_rate: Decimal = DEFAULT_EUR_USD_RATE,
        outbox_collector: list[Any] | None = None,
    ) -> None:
        if eur_usd_rate <= DEC_ZERO or not eur_usd_rate.is_finite():
            raise ValidationDomainError(detail_override=f"Invalid eur_usd_rate: {eur_usd_rate!r}")
        self._eur_usd_rate = eur_usd_rate
        self._currency_to_eur: dict[str, Decimal] = {
            **_DEFAULT_CURRENCY_TO_EUR,
            "USD": eur_usd_rate,
        }
        self._outbox_collector: list[Any] = outbox_collector if outbox_collector is not None else []

    @property
    def collected_outbox_events(self) -> list[Any]:
        return self._outbox_collector

    def sanitize(
        self,
        raw: RemoteUsageRawPayload,
        *,
        valuation_mode: ValuationMode = "NATIVE_TELEMETRY",
        fixed_cost_per_call_eur: float = 0.0,
        fixed_cost_per_unit_eur: float = 0.0,
        max_reported_cost_per_call_eur: float = 5.0,
        connector_id: str | None = None,
        workspace_id: str | None = None,
        run_id: str | None = None,
        trace_id: str | None = None,
    ) -> SanitizedRemoteUsage:
        in_tokens = _validate_non_negative_int(raw.input_tokens, "input_tokens")
        out_tokens = _validate_non_negative_int(raw.output_tokens, "output_tokens")
        cost_dec = _validate_non_negative_decimal(raw.cost_amount, "cost_amount", allow_none=True)
        unit_dec = _validate_non_negative_decimal(raw.unit_count, "unit_count", allow_none=True)
        fixed_call_dec = _validate_non_negative_decimal(
            fixed_cost_per_call_eur, "fixed_cost_per_call_eur"
        )
        fixed_unit_dec = _validate_non_negative_decimal(
            fixed_cost_per_unit_eur, "fixed_cost_per_unit_eur"
        )
        max_cap_dec = _validate_non_negative_decimal(
            max_reported_cost_per_call_eur, "max_reported_cost_per_call_eur"
        )
        assert fixed_call_dec is not None
        assert fixed_unit_dec is not None
        assert max_cap_dec is not None

        norm_currency: str | None = None
        if raw.currency is not None:
            norm_currency = raw.currency.strip().upper()
            if norm_currency not in self._currency_to_eur:
                raise ValidationDomainError(
                    detail_override=f"Unsupported remote telemetry currency: {raw.currency!r}."
                )
        elif cost_dec is not None:
            norm_currency = "EUR"

        computed_eur: Decimal
        if valuation_mode == "VOLUMETRIC_ONLY":
            computed_eur = DEC_ZERO
        elif valuation_mode == "FIXED_SCALE":
            if unit_dec is not None and fixed_unit_dec > DEC_ZERO:
                computed_eur = unit_dec * fixed_unit_dec + fixed_call_dec
            else:
                computed_eur = fixed_call_dec
        else:
            if cost_dec is not None:
                computed_eur = cost_dec * self._currency_to_eur[norm_currency or "EUR"]
            elif unit_dec is not None and fixed_unit_dec > DEC_ZERO:
                computed_eur = unit_dec * fixed_unit_dec
            elif (in_tokens + out_tokens) > 0 and fixed_unit_dec > DEC_ZERO:
                computed_eur = (Decimal(in_tokens + out_tokens) / Decimal("1000")) * fixed_unit_dec
            else:
                computed_eur = fixed_call_dec

        is_anomaly_capped = False
        original_reported_eur: float | None = None
        final_eur = computed_eur
        if computed_eur > max_cap_dec:
            is_anomaly_capped = True
            original_reported_eur = float(computed_eur.quantize(DEC_SIX, rounding=ROUND_HALF_UP))
            final_eur = max_cap_dec
            self._outbox_collector.append(
                RemoteUsageAnomalyCapped.create(
                    connector_id=connector_id or "remote_connector",
                    reported_cost_eur=original_reported_eur,
                    capped_cost_eur=float(final_eur.quantize(DEC_SIX, rounding=ROUND_HALF_UP)),
                    workspace_id=workspace_id,
                    run_id=run_id,
                    trace_id=trace_id or "00000000000000000000000000000000",
                )
            )

        final_eur_q = final_eur.quantize(DEC_SIX, rounding=ROUND_HALF_UP)
        final_usd_q = (final_eur / self._eur_usd_rate).quantize(DEC_SIX, rounding=ROUND_HALF_UP)

        native_metric_type: str | None = None
        native_metric_value: float | None = None
        if unit_dec is not None:
            native_metric_type = (raw.unit_name or "units").strip() or "units"
            native_metric_value = float(unit_dec)
        elif cost_dec is not None:
            native_metric_type = "direct_cost"
            native_metric_value = float(cost_dec)
        elif (in_tokens + out_tokens) > 0:
            native_metric_type = "remote_tokens"
            native_metric_value = float(in_tokens + out_tokens)
        else:
            native_metric_type = "calls"
            native_metric_value = 1.0

        return SanitizedRemoteUsage(
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            cost_usd=float(final_usd_q),
            cost_eur=float(final_eur_q),
            cost_source="EXTERNAL_REPORTED",
            native_metric_type=native_metric_type,
            native_metric_value=native_metric_value,
            native_currency=norm_currency,
            reported_by_remote=True,
            is_anomaly_capped=is_anomaly_capped,
            original_reported_cost_eur=original_reported_eur,
        )


__all__ = [
    "RemoteUsageSanitizer",
    "extract_remote_usage_payload",
]
