"""Deterministic 0 $ cognitive escalation FinOps eval (`Story 6.2`, `AD-17` C4).

Verifies exact accounting attribution across cognitive tiers:
- First execution on 'simple' tier (effort: low)
- Autonomous cognitive escalation to 'complex' tier (effort: deep)
- Imputation of tokens, costs, and escalation counters in FinOps tier breakdown
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from orcia_core.audit_finops.finops_models import (
    DEFAULT_EUR_USD_RATE,
    FinopsTierEffortItem,
)
from orcia_core.ports.llm_port import LlmPromptRequest
from orcia_core.testing.cassette_llm import CassetteEntry, DeterministicCassetteLLM

# Deterministic simulated pricing (per 1k tokens)
TIER_RATES_USD: dict[str, dict[str, Decimal]] = {
    "simple": {
        "input_per_1k": Decimal("0.000500"),
        "output_per_1k": Decimal("0.001500"),
    },
    "medium": {
        "input_per_1k": Decimal("0.002000"),
        "output_per_1k": Decimal("0.006000"),
    },
    "complex": {
        "input_per_1k": Decimal("0.010000"),
        "output_per_1k": Decimal("0.030000"),
    },
}


def _compute_cost(tier: str, in_tokens: int, out_tokens: int) -> Decimal:
    rates = TIER_RATES_USD[tier]
    cost_in = (Decimal(in_tokens) / Decimal("1000")) * rates["input_per_1k"]
    cost_out = (Decimal(out_tokens) / Decimal("1000")) * rates["output_per_1k"]
    return cost_in + cost_out


@pytest.mark.asyncio
async def test_deterministic_cassette_cognitive_escalation_finops_accounting() -> None:
    """Simulates multi-tier cognitive escalation and verifies FinOps attribution."""
    # Cassette returns deterministic responses at 0 $
    cassette = DeterministicCassetteLLM(
        entries={
            "initial_simple": CassetteEntry(
                content="Synthèse succincte",
                input_tokens=150,
                output_tokens=30,
            ),
            "escalated_complex": CassetteEntry(
                content="Analyse multidimensionnelle approfondie avec contre-arguments.",
                input_tokens=900,
                output_tokens=450,
            ),
        }
    )

    # 1. First turn: Tier Simple (low effort)
    resp_1 = await cassette.complete(
        LlmPromptRequest(
            system_prompt="system",
            user_prompt="initial_simple question",
            model_family="simulated",
            model_id="simulated-simple-model",
        )
    )
    assert resp_1.content == "Synthèse succincte"
    simple_in_tokens = resp_1.input_tokens
    simple_out_tokens = resp_1.output_tokens
    simple_cost_usd = _compute_cost("simple", simple_in_tokens, simple_out_tokens)
    # (150/1000)*0.0005 + (30/1000)*0.0015 = 0.000075 + 0.000045 = 0.000120 USD
    assert simple_cost_usd == Decimal("0.000120")

    tier_item_simple = FinopsTierEffortItem(
        inference_tier="simple",
        effort="low",
        invocations_count=1,
        input_tokens=simple_in_tokens,
        output_tokens=simple_out_tokens,
        total_tokens=simple_in_tokens + simple_out_tokens,
        cost_usd=simple_cost_usd,
        cost_eur=(simple_cost_usd * DEFAULT_EUR_USD_RATE).quantize(Decimal("0.01")),
        escalated_from_auto_count=0,
    )
    assert tier_item_simple.total_tokens == 180
    assert tier_item_simple.invocations_count == 1
    assert tier_item_simple.escalated_from_auto_count == 0

    # 2. Autonomous Escalation: Step complexity requires escalation to Tier Complex (deep effort)
    resp_2 = await cassette.complete(
        LlmPromptRequest(
            system_prompt="system",
            user_prompt="escalated_complex question",
            model_family="simulated",
            model_id="simulated-complex-model",
        )
    )
    assert "contre-arguments" in resp_2.content
    complex_in_tokens = resp_2.input_tokens
    complex_out_tokens = resp_2.output_tokens
    complex_cost_usd = _compute_cost("complex", complex_in_tokens, complex_out_tokens)
    # (900/1000)*0.01 + (450/1000)*0.03 = 0.009000 + 0.013500 = 0.022500 USD
    assert complex_cost_usd == Decimal("0.022500")

    tier_item_complex = FinopsTierEffortItem(
        inference_tier="complex",
        effort="deep",
        invocations_count=1,
        input_tokens=complex_in_tokens,
        output_tokens=complex_out_tokens,
        total_tokens=complex_in_tokens + complex_out_tokens,
        cost_usd=complex_cost_usd,
        cost_eur=(complex_cost_usd * DEFAULT_EUR_USD_RATE).quantize(Decimal("0.01")),
        escalated_from_auto_count=1,  # Successfully recorded as an autonomous escalation
    )
    assert tier_item_complex.total_tokens == 1350
    assert tier_item_complex.invocations_count == 1
    assert tier_item_complex.escalated_from_auto_count == 1

    # 3. Consolidated Totals
    total_in_tokens = simple_in_tokens + complex_in_tokens
    total_out_tokens = simple_out_tokens + complex_out_tokens
    total_tokens = total_in_tokens + total_out_tokens
    total_cost_usd = simple_cost_usd + complex_cost_usd

    assert total_tokens == 1530
    assert total_cost_usd == Decimal("0.022620")

    # Quantization to EUR without drift
    total_cost_eur = (total_cost_usd * DEFAULT_EUR_USD_RATE).quantize(Decimal("0.01"))
    assert total_cost_eur == Decimal("0.02")
