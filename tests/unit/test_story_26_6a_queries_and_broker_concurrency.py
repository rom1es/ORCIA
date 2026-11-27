"""Story 26.6a — Broker Concurrent Seed Idempotency & Remaining 26-Module Branch Coverage."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest


def test_ai_models_governance_embedding_update_deactivates_other_active() -> None:
    """Cover `_ai_models_governance_helpers` embedding active uniqueness."""
    from orcia_core.orchestration._ai_models_governance_helpers import apply_inmemory_mapping_update
    from orcia_core.orchestration.ai_models_governance import AiModelsHubService

    # Governance helper: embedding update deactivates other active GLOBAL embedding mappings
    hub = AiModelsHubService()
    e1 = hub.create_mapping(
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000000",
        display_name="Emb 1",
        inference_tier="simple",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-small",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none_local",
        protocol_mode="openai_compatible",
        usage="embedding",
    )
    e2 = hub.create_mapping(
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000000",
        display_name="Emb 2",
        inference_tier="simple",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-large",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none_local",
        protocol_mode="openai_compatible",
        usage="embedding",
    )
    updated_e1 = apply_inmemory_mapping_update(
        mappings=hub._mappings,
        cipher=hub._cipher,
        current=e1,
        now_iso="2026-11-22T00:00:00Z",
        display_name=None,
        fallback_model_name=None,
        endpoint_uri=None,
        auth_mode=None,
        protocol_mode=None,
        usage="embedding",
        env_var_name=None,
        is_active=True,
        secret_input=None,
        supports_tools=None,
        supports_tools_override=None,
        clear_supports_tools_override=False,
        actor_id="admin",
        instance=None,
    )
    assert updated_e1.is_active is True
    assert hub.get_mapping(e2.id).is_active is False


@pytest.mark.asyncio
async def test_gemini_dialect_cassettes_budgets_and_resolver_remaining_branches() -> None:
    """Cover branches in `llm_gemini_dialect`, `cassette_llm`, budgets, and resolver."""
    from orcia_core.orchestration.assistant_loop_budgets import (
        AssistantLoopBudgetController,
        AssistantLoopBudgetPolicy,
        run_bounded_tool_loop,
    )
    from orcia_core.orchestration.llm_endpoint_resolver import (
        extract_tier_endpoint_from_dict,
        resolve_configured_llm_endpoint_from_sources,
    )
    from orcia_core.orchestration.llm_gemini_dialect import (
        build_anthropic_native_request_body,
        build_gemini_native_headers,
        build_gemini_native_request_body,
        build_gemini_native_url,
        extract_gemini_stream_chunk_deltas,
        separate_think_tags,
    )
    from orcia_core.ports.llm_streaming_port import (
        ContentDelta,
        LlmEndpointConfig,
        LlmStreamRequest,
    )
    from orcia_core.testing.cassette_llm import (
        DeterministicCassetteEmbedding,
        DeterministicCassetteLlmStreamingAdapter,
    )

    # 1. llm_gemini_dialect branches
    c, t = separate_think_tags("<think>  </think><think>unclosed")
    assert c == "" and t == "unclosed"
    with pytest.raises(ValueError):
        build_gemini_native_url("https://generativelanguage.googleapis.com", "")
    assert ":streamGenerateContent" in build_gemini_native_url(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        "gemini-2.5-flash",
        stream=True,
    )
    assert build_gemini_native_url(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash",
        "models/gemini-2.5-flash",
    ).endswith("/models/gemini-2.5-flash:generateContent")
    assert build_gemini_native_url(
        "https://generativelanguage.googleapis.com/v1beta/models",
        "gemini-2.5-flash",
    ).endswith("/models/gemini-2.5-flash:generateContent")
    assert build_gemini_native_headers("  ") == {"Content-Type": "application/json"}
    assert build_gemini_native_headers("goog-key")["x-goog-api-key"] == "goog-key"
    gem_body = build_gemini_native_request_body(
        [{"role": "user", "content": "hi"}],
        include_thoughts=False,
        tools=["ignored-non-dict"],  # type: ignore[list-item]
    )
    assert "generationConfig" not in gem_body and "tools" not in gem_body
    assert extract_gemini_stream_chunk_deltas({}) == ("", "")
    assert extract_gemini_stream_chunk_deltas({"candidates": [{"content": {}}]}) == ("", "")
    assert extract_gemini_stream_chunk_deltas(
        {"candidates": [{"content": {"parts": [{"thought": True, "text": "R"}, {"text": "C"}]}}]}
    ) == ("C", "R")
    ant_dict = build_anthropic_native_request_body(
        "claude-3-7-sonnet",
        [{"role": "user", "content": "hi"}],
        stream=False,
        tools=[{"function": {"name": "s", "parameters": {"type": "object"}}}],
        tool_choice={"type": "tool", "name": "s"},
    )
    assert ant_dict["tool_choice"] == {"type": "tool", "name": "s"}
    ant_req = build_anthropic_native_request_body(
        "claude-3-7-sonnet",
        [{"role": "user", "content": "hi"}],
        stream=False,
        tools=[{"function": {"name": "s", "parameters": {"type": "object"}}}],
        tool_choice="required",
    )
    assert ant_req["tool_choice"] == {"type": "any"}
    ant_auto = build_anthropic_native_request_body(
        "claude-3-7-sonnet",
        [{"role": "user", "content": "hi"}],
        stream=False,
        tools=[{"function": {"name": "s", "parameters": {"type": "object"}}}],
        tool_choice="auto",
    )
    assert ant_auto["tool_choice"] == {"type": "auto"}

    # 2. cassette_llm + _cassette_tool_cassettes + forced_synthesis loop budgets
    emb = DeterministicCassetteEmbedding()
    assert emb.dimension == 1024
    assert len(await emb.embed_texts(["a"])) == 1
    assert len(await emb.embed_query("q")) == 1024
    assert len(emb.embed_query_sync("q")) == 1024

    cassette = DeterministicCassetteLlmStreamingAdapter()
    ep_oai = LlmEndpointConfig(
        provider="OpenAI",
        model_name="gpt-4o",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none",
        supports_tools=True,
    )
    evs_synth = [
        ev
        async for ev in cassette.stream_chat_events(
            LlmStreamRequest(
                endpoint=ep_oai,
                messages=(
                    {"role": "user", "content": "[CASSETTE_TOOL_LOOP] Verify"},
                    {"role": "tool", "tool_call_id": "c1", "name": "search", "content": "OK"},
                ),
                tools=("non-dict", {"type": "function"}),  # type: ignore[arg-type]
            )
        )
    ]
    assert any(
        isinstance(ev, ContentDelta) and "DETERMINISTIC_TOOL_SYNTHESIS" in ev.delta
        for ev in evs_synth
    )

    ticks = iter([10.0, 5.0])  # backward clock branch -> 0.0
    ctrl = AssistantLoopBudgetController(
        AssistantLoopBudgetPolicy(), clock_fn=lambda: next(ticks, 5.0)
    )
    assert ctrl.elapsed_seconds() == 0.0
    ctrl.record_usage(5, 7, increment_iteration=False)
    assert ctrl.iterations_used == 0 and ctrl.total_tokens == 12

    async def _exec_tc(_tc: dict[str, Any]) -> str:
        return "evidence"

    forced = await run_bounded_tool_loop(
        llm_port=cassette,
        endpoint=ep_oai,
        messages=[{"role": "user", "content": "[CASSETTE_MULTI_STEP_LOOP] Check"}],
        tools=[
            {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
        ],
        tool_executor=_exec_tc,
        policy=AssistantLoopBudgetPolicy(max_iterations=1, force_synthesis_on_limit=True),
    )
    assert forced.forced_synthesis is True and forced.limit_reached == "iterations"

    # 3. llm_endpoint_resolver branches
    ep_explicit = extract_tier_endpoint_from_dict(
        {
            "primaryModel": "gpt-4o",
            "endpointUrl": "https://api.openai.com/v1",
            "maxTokensBudget": "bad",
            "supportsTools": False,
        }
    )
    assert (
        ep_explicit is not None
        and ep_explicit.max_tokens_budget == 8192
        and ep_explicit.supports_tools is False
    )

    assert await resolve_configured_llm_endpoint_from_sources(
        engine=None,
        vault_cipher=None,
        snapshot=None,
        hub_svc=None,
        resolved_scope_id="0195f000-0000-7000-8000-000000000000",
        use_cassette=True,
    ) == (None, None)

    class _MockHub:
        def __init__(self, items: list[Any]) -> None:
            self._items = items

        def list_mappings(self, **_kw: Any) -> list[Any]:
            return self._items

    active_hub_item = SimpleNamespace(
        provider_slug="openai",
        model_name="gpt-4o",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none",
        inference_tier="complex",
        protocol_mode="openai_compatible",
        max_tokens_budget=4096,
        supports_tools=True,
        draining=False,
    )
    ep_hub, _ = await resolve_configured_llm_endpoint_from_sources(
        engine=None,
        vault_cipher=None,
        snapshot=None,
        hub_svc=_MockHub([active_hub_item]),
        resolved_scope_id="s",
        requested_tier="medium",
    )
    assert ep_hub is not None and ep_hub.model_name == "gpt-4o"

    draining_only = SimpleNamespace(**{**active_hub_item.__dict__, "draining": True})
    assert await resolve_configured_llm_endpoint_from_sources(
        engine=None,
        vault_cipher=None,
        snapshot=None,
        hub_svc=_MockHub([draining_only]),
        resolved_scope_id="s",
    ) == (None, None)

    class _BeginCtx:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_a: Any) -> None:
            return None

    class _NoopBeginCtxProvider:
        def begin(self) -> _BeginCtx:
            return _BeginCtx()

    import orcia_core.orchestration._internal.sql_ai_model_mappings as bm

    async def _fake_loader(_eng: Any, _env: str) -> Any:
        return SimpleNamespace(
            llm_tiers=[
                {
                    "tier": "medium",
                    "primaryModel": "gpt-4o",
                    "endpointUrl": "https://api.openai.com/v1",
                }
            ]
        )

    async def _empty_loader(_eng: Any, _env: str) -> Any:
        return SimpleNamespace(llm_tiers=[])

    orig_resolve = bm.resolve_decrypted_ai_model_for_tier_pg18
    try:

        async def _ret_none(*_a: Any, **_kw: Any) -> None:
            return None

        bm.resolve_decrypted_ai_model_for_tier_pg18 = _ret_none  # type: ignore[assignment]
        ep_snap, _ = await resolve_configured_llm_endpoint_from_sources(
            engine=_NoopBeginCtxProvider(),  # type: ignore[arg-type]
            vault_cipher="cipher",
            snapshot=None,
            hub_svc=None,
            resolved_scope_id="s",
            snapshot_loader=_fake_loader,
        )
        assert ep_snap is not None and ep_snap.model_name == "gpt-4o"
        assert await resolve_configured_llm_endpoint_from_sources(
            engine=_NoopBeginCtxProvider(),  # type: ignore[arg-type]
            vault_cipher="cipher",
            snapshot=None,
            hub_svc=None,
            resolved_scope_id="s",
            snapshot_loader=_empty_loader,
        ) == (None, None)

        async def _ret_ssrf(*_a: Any, **_kw: Any) -> tuple[Any, str]:
            return (
                SimpleNamespace(
                    provider_slug="openai",
                    model_name="gpt-4o",
                    endpoint_uri="http://169.254.169.254/latest",
                    auth_mode="none",
                    inference_tier="medium",
                    protocol_mode="openai_compatible",
                    max_tokens_budget=4096,
                    supports_tools=True,
                ),
                "k",
            )

        bm.resolve_decrypted_ai_model_for_tier_pg18 = _ret_ssrf  # type: ignore[assignment]
        assert await resolve_configured_llm_endpoint_from_sources(
            engine=_NoopBeginCtxProvider(),  # type: ignore[arg-type]
            vault_cipher="cipher",
            snapshot=None,
            hub_svc=None,
            resolved_scope_id="s",
        ) == (None, None)
    finally:
        bm.resolve_decrypted_ai_model_for_tier_pg18 = orig_resolve  # type: ignore[assignment]
