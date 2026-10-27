"""Layer 4 AI Orchestration Cassette Tests (`DeterministicCassetteLLM`, 0 $ CI calls, AD-17)."""

from __future__ import annotations

import pytest

from orcia_core.gates.errors import ModelOrthogonalityViolationError
from orcia_core.ports.llm_port import (
    LlmPromptRequest,
    assert_model_orthogonality,
    compute_prompt_sha256,
)
from orcia_core.testing.cassette_llm import CassetteEntry, DeterministicCassetteLLM


async def test_deterministic_cassette_llm_scenarios_and_orthogonality() -> None:
    """Verify 0 $ deterministic replay, ambiguity pause, Fast-Path assumption, and AD-10 check."""
    cassette = DeterministicCassetteLLM()

    # 1. Exact SHA-256 prompt registration & replay
    req_standard = LlmPromptRequest(
        system_prompt="You are ORCIA Architect.",
        user_prompt="Generate step summary.",
        model_family="anthropic",
        model_id="claude-3-7-sonnet",
    )
    expected_sha = compute_prompt_sha256(req_standard)
    cassette.register(
        expected_sha,
        CassetteEntry(content="Structured Step Summary", scenario_tag="EXACT_SHA_MATCH"),
    )
    res_standard = await cassette.complete(req_standard)
    assert res_standard.content == "Structured Step Summary"
    assert res_standard.scenario_tag == "EXACT_SHA_MATCH"
    assert res_standard.estimated_cost_usd == 0.0
    assert res_standard.prompt_sha256 == expected_sha

    # 2. Coaching mode ambiguity -> WAITING_FOR_HUMAN_ARBITRATION
    req_ambiguity = LlmPromptRequest(
        system_prompt="Coach mode",
        user_prompt="Choix AMBIGU entre deux topologies Kafka vs RabbitMQ",
        model_family="anthropic",
        model_id="claude-3-7-sonnet",
        execution_mode="COACHING",
    )
    res_ambiguity = await cassette.complete(req_ambiguity)
    assert res_ambiguity.scenario_tag == "WAITING_FOR_HUMAN_ARBITRATION"
    assert "WAITING_FOR_HUMAN_ARBITRATION" in res_ambiguity.content

    # 3. Fast-Path mode -> [ASSUMPTION] tag
    req_fast_path = LlmPromptRequest(
        system_prompt="Fast-Path background audit",
        user_prompt="Analyse du module de facturation",
        model_family="openai",
        model_id="gpt-4o",
        execution_mode="FAST_PATH",
    )
    res_fast = await cassette.complete(req_fast_path)
    assert res_fast.scenario_tag == "FAST_PATH_ASSUMPTION"
    assert "[ASSUMPTION]" in res_fast.content

    # 4. Keyword trigger match & default cassette fallback
    cassette.register(
        "PERMISSION_403",
        CassetteEntry(content="WAITING_FOR_PERMISSION:jira://IAM/1", scenario_tag="BROKER_403"),
    )
    res_kw = await cassette.complete(
        LlmPromptRequest(
            system_prompt="Sys",
            user_prompt="Trigger PERMISSION_403 now",
            model_family="openai",
            model_id="gpt-4o",
        )
    )
    assert res_kw.scenario_tag == "BROKER_403"

    res_default = await cassette.complete(
        LlmPromptRequest(
            system_prompt="Sys",
            user_prompt="Unregistered prompt",
            model_family="openai",
            model_id="gpt-4o",
        )
    )
    assert res_default.scenario_tag == "DEFAULT_CASSETTE"
    assert len(cassette.call_history) == 5

    # 5. AD-10 Model Orthogonality enforcement
    assert_model_orthogonality("anthropic", "openai")
    with pytest.raises(ModelOrthogonalityViolationError):
        await cassette.complete(
            LlmPromptRequest(
                system_prompt="Gate Evaluator",
                user_prompt="Evaluate artifact",
                model_family="anthropic",
                model_id="claude-3-7-sonnet",
                executor_model_family="anthropic",
            )
        )
