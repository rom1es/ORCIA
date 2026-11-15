"""Unit tests for Story 19.4 (D4) — Clean Day-0 Seeds, Empty Tiers & Errors."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from orcia_api.routers.assistant_llm_gemini_adapter import build_gemini_native_url
from orcia_api.routers.assistant_llm_providers import normalize_chat_completions_url
from orcia_core.bootstrap.workflow_bootstrap_seeds import (
    DEFAULT_LLM_MODEL_ENDPOINT_SEEDS,
    DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS,
)
from orcia_core.orchestration.cognitive_router import (
    CognitiveModelRouterService,
    TierModelNotConfiguredError,
    WorkspaceLlmTierMapping,
    build_default_tier_mappings,
)
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.secret_ports import SecretRef


def _load_purge_maintenance_function() -> Any:
    script_path = (
        Path(__file__).resolve().parents[2]
        / "infra"
        / "scripts"
        / "maintenance"
        / "11_purge_legacy_fictional_llm_seeds.py"
    )
    spec = importlib.util.spec_from_file_location(
        "purge_legacy_fictional_llm_seeds_module", script_path
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.purge_legacy_fictional_llm_seeds


def test_story_19_4_default_seeds_and_tier_mappings_are_empty() -> None:
    """AC-1: DEFAULT_LLM_MODEL_ENDPOINT_SEEDS and build_default_tier_mappings are empty tuples."""
    assert DEFAULT_LLM_MODEL_ENDPOINT_SEEDS == ()
    assert build_default_tier_mappings() == ()
    assert build_default_tier_mappings("custom-ws-id") == ()

    # Verify Day-0 bootstrap run seed does not claim verified LLM families
    day0_run = DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS[0]
    gate_report = json.loads(day0_run.gate_report_json)
    assert gate_report["verified_llm_families"] == []
    assert gate_report["distinct_families_count"] == 0


def test_story_19_4_resolve_mapping_raises_err_tier_model_not_configured() -> None:
    """AC-2: Empty router raises RFC 9457 ERR_TIER_MODEL_NOT_CONFIGURED."""
    llm = DeterministicCassetteLLM()
    router = CognitiveModelRouterService(llm_gateway=llm)
    assert router.list_mappings() == []

    for tier in ("simple", "medium", "complex"):
        with pytest.raises(TierModelNotConfiguredError) as exc_info:
            router.resolve_mapping(
                scope_id="0195f000-0000-7000-8000-000000000301",
                tier=tier,  # type: ignore[arg-type]
            )
        err = exc_info.value
        assert err.error_code == "ERR_TIER_MODEL_NOT_CONFIGURED"
        assert err.http_status == 422
        assert err.type_slug == "tier-model-not-configured"
        assert "/settings/ai-models" in err.detail_override

        copy_fr = err.localize("fr")
        assert "Modèle IA non configuré" in copy_fr.title
        assert "/settings/ai-models" in copy_fr.detail

        copy_en = err.localize("en")
        assert "AI model not configured" in copy_en.title
        assert "/settings/ai-models" in copy_en.detail


def test_story_19_4_execute_with_tier_routing_raises_err_tier_model_not_configured() -> None:
    """AC-3: Invocations through execute_with_tier_routing fail immediately."""
    llm = DeterministicCassetteLLM()
    router = CognitiveModelRouterService(llm_gateway=llm)

    with pytest.raises(TierModelNotConfiguredError) as exc_info:
        asyncio.run(
            router.execute_with_tier_routing(
                run_id="run-unconfigured",
                step_execution_id="step-unconfigured",
                scope_id="0195f000-0000-7000-8000-000000000301",
                system_prompt="System",
                user_prompt="Hello",
                inference_tier="medium",
            )
        )
    assert exc_info.value.error_code == "ERR_TIER_MODEL_NOT_CONFIGURED"


def test_story_19_4_router_functions_when_model_is_configured_by_admin() -> None:
    """AC-4: Once an admin adds a model mapping, routing succeeds normally."""
    llm = DeterministicCassetteLLM()
    ws_id = "0195f000-0000-7000-8000-000000000301"
    mapping = WorkspaceLlmTierMapping(
        id="admin-mapped-medium",
        scope_level="WORKSPACE",
        scope_id=ws_id,
        inference_tier="medium",
        effort="default",
        provider_slug="anthropic",
        model_family="anthropic-claude",
        model_name="claude-3-7-sonnet",
        secret_ref=SecretRef(f"secret://workspace/{ws_id}/ai-models/medium"),
        max_tokens_budget=8192,
        max_cost_usd=5.0,
    )
    router = CognitiveModelRouterService(llm_gateway=llm, initial_mappings=(mapping,))
    resolved = router.resolve_mapping(scope_id=ws_id, tier="medium")
    assert resolved.id == "admin-mapped-medium"
    assert resolved.model_name == "claude-3-7-sonnet"


def test_story_19_4_mandatory_model_name_on_url_helpers() -> None:
    """AC-5: build_gemini_native_url and normalize_chat_completions_url require model_name."""
    with pytest.raises(ValueError, match="model_name is mandatory"):
        build_gemini_native_url("https://generativelanguage.googleapis.com", "")

    with pytest.raises(ValueError, match="model_name is mandatory"):
        build_gemini_native_url("https://generativelanguage.googleapis.com", "   ")

    valid_gemini = build_gemini_native_url(
        "https://generativelanguage.googleapis.com", "gemini-2.5-flash"
    )
    assert "models/gemini-2.5-flash:generateContent" in valid_gemini

    norm_url = normalize_chat_completions_url(
        "https://api.openai.com", "openai", model_name="gpt-4o"
    )
    assert norm_url == "https://api.openai.com/v1/chat/completions"


@pytest.mark.asyncio
async def test_story_19_4_purge_maintenance_script_dry_run_and_apply() -> None:
    """AC-6: Maintenance script 11_purge_legacy_fictional_llm_seeds dry-run and apply."""
    purge_legacy_fictional_llm_seeds = _load_purge_maintenance_function()

    mock_engine = MagicMock()
    mock_conn = AsyncMock()
    mock_trans = AsyncMock()
    mock_conn.begin.return_value = mock_trans

    mock_tables_result = MagicMock()
    mock_tables_result.fetchall.return_value = [
        ("llm_model_endpoints",),
        ("workspace_llm_tier_mappings",),
        ("platform_settings",),
    ]

    mock_del_result = MagicMock()
    mock_del_result.rowcount = 2

    mock_settings_result = MagicMock()
    mock_settings_result.fetchall.return_value = []

    async def fake_execute(clause: object, *args: object, **kwargs: object) -> object:
        sql = str(clause)
        if "SELECT tablename FROM pg_tables" in sql:
            return mock_tables_result
        if "DELETE FROM" in sql:
            return mock_del_result
        if "SELECT id, value_jsonb FROM platform_settings" in sql:
            return mock_settings_result
        return MagicMock()

    mock_conn.execute.side_effect = fake_execute
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # 1. Dry run
    report_dry = await purge_legacy_fictional_llm_seeds(mock_engine, apply_changes=False)
    assert report_dry.dry_run is True
    assert report_dry.committed is False
    assert mock_trans.rollback.called
    assert not mock_trans.commit.called

    # 2. Apply
    mock_trans.reset_mock()
    report_apply = await purge_legacy_fictional_llm_seeds(mock_engine, apply_changes=True)
    assert report_apply.dry_run is False
    assert report_apply.committed is True
    assert mock_trans.commit.called
