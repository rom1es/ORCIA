"""Unit & Hypothesis property tests for `RemoteUsageSanitizer` (`Story 6.4`, `AD-17 Layer 1a`)."""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from orcia_core.audit_finops.remote_usage_sanitizer import (
    RemoteUsageSanitizer,
    extract_remote_usage_payload,
)
from orcia_core.kernel._finops_audit_events import RemoteUsageAnomalyCapped
from orcia_core.ports.finops_telemetry import RemoteUsageRawPayload
from orcia_kernel.errors import ValidationDomainError


def test_extract_remote_usage_from_mcp_meta_a2a_and_header() -> None:
    mcp_payload = {
        "_meta": {
            "usage": {
                "input_tokens": 1200,
                "output_tokens": 300,
                "cost_amount": 0.45,
                "currency": "EUR",
            }
        }
    }
    raw_mcp = extract_remote_usage_payload(mcp_payload)
    assert raw_mcp.input_tokens == 1200
    assert raw_mcp.output_tokens == 300
    assert raw_mcp.cost_amount == 0.45
    assert raw_mcp.currency == "EUR"

    a2a_payload = {"usage": {"unit_count": 12, "unit_name": "pages_ocr", "currency": "EUR"}}
    raw_a2a = extract_remote_usage_payload(a2a_payload)
    assert raw_a2a.unit_count == 12.0
    assert raw_a2a.unit_name == "pages_ocr"

    hdr_json = {"X-Orcia-Usage": '{"cost": 1.25, "currency": "USD", "unit_count": 5}'}
    raw_hdr_json = extract_remote_usage_payload(headers=hdr_json)
    assert raw_hdr_json.cost_amount == 1.25
    assert raw_hdr_json.currency == "USD"
    assert raw_hdr_json.unit_count == 5.0

    hdr_kv = {"x-orcia-usage": "input_tokens=500, output_tokens=100, cost=0.20, currency=EUR"}
    raw_hdr_kv = extract_remote_usage_payload(headers=hdr_kv)
    assert raw_hdr_kv.input_tokens == 500
    assert raw_hdr_kv.output_tokens == 100
    assert raw_hdr_kv.cost_amount == 0.20


def test_sanitize_three_valuation_modes_and_anomaly_capping() -> None:
    outbox: list[object] = []
    sanitizer = RemoteUsageSanitizer(outbox_collector=outbox)

    # 1. NATIVE_TELEMETRY within cap (0.92 EUR = 1.000000 USD)
    res_ok = sanitizer.sanitize(
        RemoteUsageRawPayload(cost_amount=0.92, currency="EUR"),
        valuation_mode="NATIVE_TELEMETRY",
        fixed_cost_per_call_eur=0.0,
        fixed_cost_per_unit_eur=0.0,
        max_reported_cost_per_call_eur=5.0,
    )
    assert res_ok.cost_eur == 0.92
    assert res_ok.cost_usd == 1.0
    assert res_ok.cost_source == "EXTERNAL_REPORTED"
    assert res_ok.reported_by_remote is True
    assert res_ok.is_anomaly_capped is False
    assert len(outbox) == 0

    # 2. Excessive cost (250.00 EUR) -> capped to 5.00 EUR and emits RemoteUsageAnomalyCapped
    res_capped = sanitizer.sanitize(
        RemoteUsageRawPayload(cost_amount=250.0, currency="EUR"),
        valuation_mode="NATIVE_TELEMETRY",
        fixed_cost_per_call_eur=0.0,
        fixed_cost_per_unit_eur=0.0,
        max_reported_cost_per_call_eur=5.0,
        connector_id="mcp-ocr-vendor",
    )
    assert res_capped.cost_eur == 5.0
    assert res_capped.is_anomaly_capped is True
    assert res_capped.original_reported_cost_eur == 250.0
    assert len(outbox) == 1
    assert isinstance(outbox[0], RemoteUsageAnomalyCapped)
    assert outbox[0].connector_id == "mcp-ocr-vendor"
    assert outbox[0].reported_cost_eur == 250.0
    assert outbox[0].capped_cost_eur == 5.0

    # 3. FIXED_SCALE with business units (10 pages_ocr * 0.05 EUR + 0.10 EUR fixed)
    res_scale = sanitizer.sanitize(
        RemoteUsageRawPayload(unit_count=10.0, unit_name="pages_ocr"),
        valuation_mode="FIXED_SCALE",
        fixed_cost_per_call_eur=0.10,
        fixed_cost_per_unit_eur=0.05,
        max_reported_cost_per_call_eur=5.0,
    )
    assert res_scale.cost_eur == 0.6
    assert res_scale.native_metric_type == "pages_ocr"
    assert res_scale.native_metric_value == 10.0

    # 4. VOLUMETRIC_ONLY tracks units/tokens with 0 cost
    res_vol = sanitizer.sanitize(
        RemoteUsageRawPayload(input_tokens=400, output_tokens=100, cost_amount=3.0, currency="EUR"),
        valuation_mode="VOLUMETRIC_ONLY",
        fixed_cost_per_call_eur=1.0,
        fixed_cost_per_unit_eur=0.5,
        max_reported_cost_per_call_eur=5.0,
    )
    assert res_vol.cost_eur == 0.0
    assert res_vol.cost_usd == 0.0
    assert res_vol.input_tokens == 400
    assert res_vol.output_tokens == 100


@pytest.mark.parametrize(
    "bad_payload",
    [
        RemoteUsageRawPayload(cost_amount=-1.0, currency="EUR"),
        RemoteUsageRawPayload(cost_amount=float("nan"), currency="EUR"),
        RemoteUsageRawPayload(cost_amount=float("inf"), currency="EUR"),
        RemoteUsageRawPayload(cost_amount=float("-inf"), currency="EUR"),
        RemoteUsageRawPayload(input_tokens=-5),
        RemoteUsageRawPayload(output_tokens=-1),
        RemoteUsageRawPayload(unit_count=-0.5, unit_name="pages_ocr"),
        RemoteUsageRawPayload(unit_count=float("nan")),
        RemoteUsageRawPayload(cost_amount=1.0, currency="XYZ_UNKNOWN"),
    ],
)
def test_sanitize_rejects_malformed_or_negative_payloads(
    bad_payload: RemoteUsageRawPayload,
) -> None:
    sanitizer = RemoteUsageSanitizer()
    with pytest.raises(ValidationDomainError):
        sanitizer.sanitize(
            bad_payload,
            valuation_mode="NATIVE_TELEMETRY",
            fixed_cost_per_call_eur=0.0,
            fixed_cost_per_unit_eur=0.0,
            max_reported_cost_per_call_eur=5.0,
        )


def test_extract_rejects_malformed_header_and_negative_values() -> None:
    assert extract_remote_usage_payload() == RemoteUsageRawPayload()
    assert extract_remote_usage_payload(headers={"X-Orcia-Usage": "   "}) == RemoteUsageRawPayload()
    raw_usd = extract_remote_usage_payload({"_meta": {"usage": {"cost_usd": 2.5, "units": 3.0}}})
    assert raw_usd.currency == "USD"
    assert raw_usd.unit_count == 3.0
    raw_eur = extract_remote_usage_payload(
        {"usage": {"cost_eur": 1.2, "prompt_tokens": 10.0, "completion_tokens": 5.0}}
    )
    assert raw_eur.currency == "EUR"
    assert raw_eur.input_tokens == 10

    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload({"_meta": {"usage": {"cost_amount": -10.0}}})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload(headers={"X-Orcia-Usage": "{bad-json"})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload(headers={"X-Orcia-Usage": "[1, 2, 3]"})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload(headers={"X-Orcia-Usage": "cost=abc, currency=EUR"})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload(headers={"X-Orcia-Usage": "cost=-1.0, currency=EUR"})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload({"usage": {"input_tokens": True}})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload({"usage": {"input_tokens": 1.5}})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload({"usage": {"input_tokens": "bad"}})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload({"usage": {"cost_amount": True}})
    with pytest.raises(ValidationDomainError):
        extract_remote_usage_payload({"usage": {"cost_amount": "nan-text"}})


def test_sanitizer_edge_cases_tokens_and_rate_validation() -> None:
    with pytest.raises(ValidationDomainError):
        RemoteUsageSanitizer(eur_usd_rate=Decimal("0"))

    s = RemoteUsageSanitizer()
    assert s.collected_outbox_events == []
    # FIXED_SCALE without units uses fixed_cost_per_call_eur
    res_fixed = s.sanitize(
        RemoteUsageRawPayload(),
        valuation_mode="FIXED_SCALE",
        fixed_cost_per_call_eur=0.35,
        fixed_cost_per_unit_eur=0.0,
        max_reported_cost_per_call_eur=5.0,
    )
    assert res_fixed.cost_eur == 0.35
    assert res_fixed.native_metric_type == "calls"

    # NATIVE_TELEMETRY with tokens + unit_tariff_eur and with cost=None fallback
    res_tok = s.sanitize(
        RemoteUsageRawPayload(input_tokens=1000, output_tokens=1000),
        valuation_mode="NATIVE_TELEMETRY",
        fixed_cost_per_call_eur=0.0,
        fixed_cost_per_unit_eur=0.20,
        max_reported_cost_per_call_eur=5.0,
    )
    assert res_tok.cost_eur == 0.4
    assert res_tok.native_metric_type == "remote_tokens"

    res_empty = s.sanitize(
        RemoteUsageRawPayload(),
        valuation_mode="NATIVE_TELEMETRY",
        fixed_cost_per_call_eur=0.15,
        fixed_cost_per_unit_eur=0.0,
        max_reported_cost_per_call_eur=5.0,
    )
    assert res_empty.cost_eur == 0.15

    # Reject boolean and non-int tokens
    with pytest.raises(ValidationDomainError):
        s.sanitize(RemoteUsageRawPayload(input_tokens=True))  # type: ignore[arg-type]
    with pytest.raises(ValidationDomainError):
        s.sanitize(RemoteUsageRawPayload(cost_amount=True))  # type: ignore[arg-type]
    with pytest.raises(ValidationDomainError):
        s.sanitize(RemoteUsageRawPayload(cost_amount="bad"))  # type: ignore[arg-type]


@given(
    bad_cost=st.one_of(
        st.floats(max_value=-1e-9, allow_nan=False, allow_infinity=False),
        st.just(float("nan")),
        st.just(float("inf")),
        st.just(float("-inf")),
    )
)
@settings(max_examples=50, deadline=None)
def test_hypothesis_rejects_all_negative_nan_and_infinite_costs(bad_cost: float) -> None:
    sanitizer = RemoteUsageSanitizer()
    with pytest.raises(ValidationDomainError):
        sanitizer.sanitize(
            RemoteUsageRawPayload(cost_amount=bad_cost, currency="EUR"),
            valuation_mode="NATIVE_TELEMETRY",
            fixed_cost_per_call_eur=0.0,
            fixed_cost_per_unit_eur=0.0,
            max_reported_cost_per_call_eur=5.0,
        )


@given(
    bad_tokens=st.integers(max_value=-1),
)
@settings(max_examples=50, deadline=None)
def test_hypothesis_rejects_negative_token_counts(bad_tokens: int) -> None:
    sanitizer = RemoteUsageSanitizer()
    with pytest.raises(ValidationDomainError):
        sanitizer.sanitize(
            RemoteUsageRawPayload(input_tokens=bad_tokens, output_tokens=0),
            valuation_mode="NATIVE_TELEMETRY",
            fixed_cost_per_call_eur=0.0,
            fixed_cost_per_unit_eur=0.0,
            max_reported_cost_per_call_eur=5.0,
        )


@given(
    cost=st.floats(min_value=0.0, max_value=10_000.0, allow_nan=False, allow_infinity=False),
    currency=st.sampled_from(["EUR", "USD", "GBP", "CHF"]),
    cap_eur=st.floats(min_value=0.5, max_value=50.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=80, deadline=None)
def test_hypothesis_caps_cost_and_preserves_decimal_usd_pivot(
    cost: float,
    currency: str,
    cap_eur: float,
) -> None:
    outbox: list[object] = []
    sanitizer = RemoteUsageSanitizer(outbox_collector=outbox)
    res = sanitizer.sanitize(
        RemoteUsageRawPayload(cost_amount=cost, currency=currency),
        valuation_mode="NATIVE_TELEMETRY",
        fixed_cost_per_call_eur=0.0,
        fixed_cost_per_unit_eur=0.0,
        max_reported_cost_per_call_eur=cap_eur,
    )
    assert math.isfinite(res.cost_eur)
    assert math.isfinite(res.cost_usd)
    assert res.cost_eur >= 0.0
    assert res.cost_usd >= 0.0
    cap_rounded = float(Decimal(str(cap_eur)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
    assert res.cost_eur <= cap_rounded + 1e-6
    assert res.cost_source == "EXTERNAL_REPORTED"
    assert res.reported_by_remote is True
    assert bool(outbox) == res.is_anomaly_capped
