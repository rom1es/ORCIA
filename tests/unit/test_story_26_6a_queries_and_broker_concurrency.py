"""Story 26.6a — Broker Concurrent Seed Idempotency & Remaining 26-Module Branch Coverage."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.mark.asyncio
async def test_permission_broker_concurrent_seed_and_conflict_fallback_idempotent() -> None:
    """Concurrent `ensure_policies_seeded` and conflict-skipped INSERT avoid UniqueViolation."""
    from orcia_core.permissions._internal import _sql_permission_broker_queries as sbq
    from orcia_core.permissions._internal.sql_permission_broker import SqlPermissionBrokerRepository
    from orcia_core.permissions.broker_models import PermissionBrokerPolicy

    pol = PermissionBrokerPolicy(
        id="0192c4e0-0000-7000-8000-000000001001",
        policy_key="pol-git-payments",
        uri_pattern="git://*/payments/*",
        connector_scheme="git",
        required_role="SECURITY_LEAD",
        approver_team="platform-sec",
        request_url_template="https://jira.internal/new",
        sla_hours=24,
        procedure_markdown="Check access",
        service_principal_allowed=False,
    )
    persisted_row = {
        "id": pol.id,
        "policy_key": pol.policy_key,
        "uri_pattern": pol.uri_pattern,
        "connector_scheme": pol.connector_scheme,
        "required_role": pol.required_role,
        "approver_team": pol.approver_team,
        "request_url_template": pol.request_url_template,
        "sla_hours": pol.sla_hours,
        "procedure_markdown": pol.procedure_markdown,
        "service_principal_allowed": pol.service_principal_allowed,
        "approved_by_admin_id": None,
        "human_anchor_author_id": None,
        "human_anchor_signature": None,
        "freshness_ttl_days": 90,
    }

    class _FakeMappings:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def first(self) -> dict[str, Any] | None:
            return self._rows[0] if self._rows else None

        def one(self) -> dict[str, Any]:
            assert self._rows, "Expected exactly 1 row"
            return self._rows[0]

        def all(self) -> list[dict[str, Any]]:
            return list(self._rows)

    class _FakeResult:
        def __init__(self, rows: list[dict[str, Any]]) -> None:
            self._rows = rows

        def mappings(self) -> _FakeMappings:
            return _FakeMappings(self._rows)

    class _ConcurrentRaceConn:
        def __init__(self) -> None:
            self.insert_calls = 0
            self.seeded = False

        async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
            sql_txt = str(stmt)
            if "INSERT INTO connector_schemes" in sql_txt:
                return _FakeResult([])
            if "SELECT * FROM permission_broker_policies" in sql_txt:
                # 1st lookup sees empty (simulating race), subsequent lookup sees concurrent row
                return _FakeResult([persisted_row] if self.seeded else [])
            if "INSERT INTO permission_broker_policies" in sql_txt:
                self.insert_calls += 1
                self.seeded = True
                # Simulate ON CONFLICT DO NOTHING returning 0 rows due to concurrent tx!
                return _FakeResult([])
            if "UPDATE permission_broker_policies" in sql_txt:
                return _FakeResult([persisted_row])
            return _FakeResult([])

    race_conn = _ConcurrentRaceConn()
    res_no_upd = await sbq.upsert_policy_on_conn(race_conn, pol, update_existing=False)  # type: ignore[arg-type]
    assert res_no_upd.policy_key == pol.policy_key
    assert race_conn.insert_calls == 1

    # Concurrent ensure_policies_seeded across asyncio.gather serializes cleanly to 1 batch
    class _Ctx:
        def __init__(self, conn: Any) -> None:
            self._conn = conn

        async def __aenter__(self) -> Any:
            return self._conn

        async def __aexit__(self, *_a: Any) -> None:
            return None

    class _FakeEngine:
        def __init__(self) -> None:
            self.begin_calls = 0
            self.conn = _ConcurrentRaceConn()

        def begin(self) -> _Ctx:
            self.begin_calls += 1
            return _Ctx(self.conn)

        def connect(self) -> _Ctx:
            return _Ctx(self.conn)

    eng = _FakeEngine()
    repo = SqlPermissionBrokerRepository(eng)
    r1, r2 = await asyncio.gather(
        repo.ensure_policies_seeded((pol,)),
        repo.ensure_policies_seeded((pol,)),
    )
    assert len(r1) == 1 and len(r2) == 1
    assert eng.begin_calls == 1


@pytest.mark.asyncio
async def test_sql_ai_model_queries_and_governance_helpers_coverage() -> None:
    """Cover `sql_ai_model_queries.py` filters/decrypt/404 and `_ai_models_governance_helpers`."""
    from orcia_core.orchestration._ai_models_governance_helpers import apply_inmemory_mapping_update
    from orcia_core.orchestration._internal.sql_ai_model_queries import (
        get_active_global_embedding_model_pg18,
        get_ai_model_mapping_pg18,
        list_ai_model_mappings_pg18,
        resolve_decrypted_ai_model_for_tier_pg18,
    )
    from orcia_core.orchestration.ai_models_crypto import pack_encrypted_api_key
    from orcia_core.orchestration.ai_models_governance import AiModelsHubService
    from orcia_core.orchestration.errors import ResourceNotFoundError
    from orcia_core.permissions.crypto import PassthroughVaultCipher

    cipher = PassthroughVaultCipher(master_key=b"0" * 32)
    mid = "0195f000-0000-7000-8000-000000000401"
    packed = pack_encrypted_api_key(
        cipher, mapping_id=mid, target_host="api.openai.com", plaintext_key="sk-secret-row"
    )
    now = datetime.now(UTC)
    sample_row = (
        mid,
        "GLOBAL",
        "0195f000-0000-7000-8000-000000000000",
        "medium",
        "balanced",
        "openai",
        "OpenAI",
        "gpt-4o",
        None,
        {},
        8192,
        10.0,
        1,
        True,
        False,
        now,
        "GPT-4o",
        None,
        "https://api.openai.com/v1",
        "api_key",
        "openai_compatible",
        None,
        packed,
        "fp-1",
        "sk-...row",
        now,
        "admin",
        "HEALTHY",
        now,
        42,
        now,
        "chat",
        True,
        None,
    )

    class _FakeRes:
        def __init__(self, rows: list[Any]) -> None:
            self._rows = rows

        def fetchall(self) -> list[Any]:
            return self._rows

        def fetchone(self) -> Any:
            return self._rows[0] if self._rows else None

    class _FakeConn:
        def __init__(self, rows: list[Any]) -> None:
            self._rows = rows
            self.queries: list[tuple[str, Any]] = []

        async def execute(self, stmt: Any, params: Any = None) -> _FakeRes:
            self.queries.append((str(stmt), params))
            return _FakeRes(self._rows)

    conn_hit = _FakeConn([sample_row])
    items = await list_ai_model_mappings_pg18(
        conn_hit,  # type: ignore[arg-type]
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000000",
        inference_tier="medium",
        is_active=True,
        usage="chat",
    )
    assert len(items) == 1 and items[0].supports_tools is True
    all_items = await list_ai_model_mappings_pg18(conn_hit)  # type: ignore[arg-type]
    assert len(all_items) == 1

    fetched = await get_ai_model_mapping_pg18(conn_hit, mid)  # type: ignore[arg-type]
    assert fetched.id == mid

    resolved_chat = await resolve_decrypted_ai_model_for_tier_pg18(
        conn_hit,  # type: ignore[arg-type]
        cipher=cipher,
        scope_id="0195f000-0000-7000-8000-000000000000",
        inference_tier="medium",
    )
    assert resolved_chat is not None and resolved_chat[1] == "sk-secret-row"

    resolved_emb = await get_active_global_embedding_model_pg18(conn_hit, cipher=cipher)  # type: ignore[arg-type]
    assert resolved_emb is not None and resolved_emb[1] == "sk-secret-row"

    conn_empty = _FakeConn([])
    with pytest.raises(ResourceNotFoundError):
        await get_ai_model_mapping_pg18(conn_empty, mid)  # type: ignore[arg-type]
    assert (
        await resolve_decrypted_ai_model_for_tier_pg18(
            conn_empty,
            cipher=cipher,
            scope_id="s",
            inference_tier="medium",  # type: ignore[arg-type]
        )
        is None
    )
    assert await get_active_global_embedding_model_pg18(conn_empty, cipher=cipher) is None  # type: ignore[arg-type]

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

    class _StubEngine:
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
            engine=_StubEngine(),  # type: ignore[arg-type]
            vault_cipher="cipher",
            snapshot=None,
            hub_svc=None,
            resolved_scope_id="s",
            snapshot_loader=_fake_loader,
        )
        assert ep_snap is not None and ep_snap.model_name == "gpt-4o"
        assert await resolve_configured_llm_endpoint_from_sources(
            engine=_StubEngine(),  # type: ignore[arg-type]
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
            engine=_StubEngine(),  # type: ignore[arg-type]
            vault_cipher="cipher",
            snapshot=None,
            hub_svc=None,
            resolved_scope_id="s",
        ) == (None, None)
    finally:
        bm.resolve_decrypted_ai_model_for_tier_pg18 = orig_resolve  # type: ignore[assignment]
