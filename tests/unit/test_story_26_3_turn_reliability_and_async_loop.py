"""Story 26.3 — TDD Unit Tests: Turn Reliability, Async Event Loop, Resilience & Rate Limits."""

from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ports_and_zero_module_level_active_workspace_turns_and_file_caps() -> None:
    """Verify `AssistantTurnRegistryPort` exists with zero SDK imports & zero RAM globals."""
    from orcia_core.ports.assistant_turn_stream_port import (
        AssistantRateLimiterPort,
        AssistantTurnRecord,
        AssistantTurnRegistryPort,
        AssistantTurnStreamEvent,
        AssistantTurnStreamPort,
    )

    assert AssistantTurnRegistryPort is not None
    assert AssistantTurnStreamPort is not None
    assert AssistantRateLimiterPort is not None
    rec = AssistantTurnRecord(
        turn_id="turn-1",
        workspace_id="ws-1",
        user_id="user-1",
        status="RUNNING",
        user_prompt="Hello",
        assembled_system_prompt="Sys",
    )
    evt = AssistantTurnStreamEvent(cursor="1-0", seq=1, event="token_delta", data={"delta": "Hi"})
    assert rec.turn_id == "turn-1" and evt.cursor == "1-0"

    port_src = (
        REPO_ROOT
        / "packages"
        / "orcia-core"
        / "src"
        / "orcia_core"
        / "ports"
        / "assistant_turn_stream_port.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("redis", "fastapi", "sqlalchemy", "httpx", "dbos", "dramatiq"):
        assert forbidden not in port_src

    for fname in ("_assistant_background_registry.py", "assistant_background_turns.py"):
        p = REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "routers" / fname
        assert "ACTIVE_WORKSPACE_TURNS" not in p.read_text(encoding="utf-8")


def test_zero_event_loop_blocking_and_zero_silent_except_ast_invariants() -> None:
    """Verify zero `ThreadPoolExecutor`, zero `loop.is_running(): pass`, and <= 300 L files."""
    targets = [
        REPO_ROOT / "packages/orcia-core/src/orcia_core/orchestration/step_executors.py",
        REPO_ROOT / "packages/orcia-core/src/orcia_core/orchestration/_step_executors_actions.py",
        REPO_ROOT / "packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py",
        REPO_ROOT / "packages/orcia-core/src/orcia_core/orchestration/assistant_agent_synthesis.py",
        REPO_ROOT / "packages/orcia-core/src/orcia_core/rag/context_adapters.py",
        REPO_ROOT / "packages/orcia-core/src/orcia_core/rag/hybrid_rag_service.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/assistant.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/assistant_turns.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/_assistant_turn_controls_routes.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/_assistant_turn_finalizer.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/assistant_background_turns.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/_assistant_background_registry.py",
    ]
    for path in targets:
        assert path.exists(), f"Expected module missing: {path}"
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 300, f"{path.relative_to(REPO_ROOT)} has {len(lines)} lines > 300"
        src = "\n".join(lines)
        assert "ThreadPoolExecutor" not in src, f"ThreadPoolExecutor found in {path}"
        assert "loop.is_running()" not in src, f"loop.is_running() found in {path}"

    # Verify zero bare `except Exception: pass` across target orchestration/rag/router modules
    for path in targets:
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                seg = ast.get_source_segment(src, node) or ""
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    raise AssertionError(f"Silent pass in {path}:{node.lineno}: {seg}")

    # Verify assistant_turns.py SSE generator is async def
    turns_src = (REPO_ROOT / "apps/api/src/orcia_api/routers/assistant_turns.py").read_text(
        encoding="utf-8"
    )
    assert "async def _sse()" in turns_src


@pytest.mark.asyncio
async def test_async_hybrid_rag_and_async_agent_step_executor_without_threads() -> None:
    """Verify `HybridRagVectorStoreAdapter.hybrid_search_async` & `AgentStepExecutor` work async."""
    from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

    from orcia_core.orchestration.step_executors import AgentStepExecutor
    from orcia_core.rag import HybridRagService, build_seeded_rag_service
    from orcia_core.rag.context_adapters import HybridRagVectorStoreAdapter
    from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
    from orcia_kernel.ports import StepExecutorContext

    fake_emb = FakeDeterministicEmbeddingAdapter()
    seeded_rag, _ = build_seeded_rag_service(embedding_port=fake_emb)
    adapter = HybridRagVectorStoreAdapter(seeded_rag, embedding_port=fake_emb)
    hits = await adapter.hybrid_search_async(
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        query_text="architecture payment",
        allowed_datasource_aliases=frozenset(),
        top_k=3,
    )
    assert isinstance(hits, tuple)

    rag_no_emb = HybridRagService(embedding_port=None)
    with pytest.raises(Exception) as exc_info:
        await rag_no_emb.search_hybrid_rrf_async(
            workspace_id="ws-1",
            query_text="hello",
        )
    assert "NoActiveEmbeddingModelError" in type(exc_info.value).__name__

    executor = AgentStepExecutor(llm_gateway=DeterministicCassetteLLM())
    res = await executor.execute_step_async(
        StepExecutorContext(
            run_id="run-1",
            root_run_id="run-1",
            workspace_id="ws-1",
            workflow_uri="orcia://workflows/test",
            step_key="step-1",
            step_title="Step 1",
            step_type="AGENT",
            execution_regime="INTERACTIVE_COACHING",
            directive="Synthesize status",
            declared_input_uris=(),
            resolved_inputs={},
        )
    )
    assert res.status == "EXECUTED"


@pytest.mark.asyncio
async def test_multi_tab_isolation_liveness_and_task_drain_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `(workspace, user, turn_id)` multi-tab isolation, tracked tasks & bounded drain."""
    from orcia_api.main import create_app
    from orcia_core.ports.llm_streaming_port import LlmStreamDelta, LlmStreamRequest

    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV_FILE", "/tmp/orcia-unit-none.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("ORCIA_ASSISTANT_DRAIN_TIMEOUT_S", "0.25")
    app = create_app()

    started_events = [asyncio.Event(), asyncio.Event()]
    release_turn = asyncio.Event()

    class _SlowStreamingPort:
        is_cassette_adapter = True

        async def complete_chat(self, _req: LlmStreamRequest) -> None:
            return None

        async def stream_chat_sse(self, req: LlmStreamRequest):
            prompt = str(req.messages[-1]["content"])
            idx = 0 if "Tab-1" in prompt else 1
            yield LlmStreamDelta(
                event="token_delta", delta=f"chunk-{idx}", accumulated_text=f"chunk-{idx}"
            )
            started_events[idx].set()
            await release_turn.wait()
            yield LlmStreamDelta(
                event="turn_completed",
                accumulated_text=f"chunk-{idx}",
                input_tokens=10,
                output_tokens=5,
                usage_source="provider",
            )

    app.state.llm_streaming_port = _SlowStreamingPort()
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.post(
                "/api/v1/assistant/turns",
                params={"persona_key": "marc"},
                json={
                    "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                    "user_prompt": "Tab-1",
                },
            )
            r2 = await client.post(
                "/api/v1/assistant/turns",
                params={"persona_key": "marc"},
                json={
                    "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                    "user_prompt": "Tab-2",
                },
            )
            assert r1.status_code == 202 and r2.status_code == 202
            t1 = r1.json()["turn_id"]
            t2 = r2.json()["turn_id"]
            assert t1 != t2

            await asyncio.wait_for(
                asyncio.gather(started_events[0].wait(), started_events[1].wait()), timeout=2.0
            )
            active_resp = await client.get(
                "/api/v1/assistant/turns/active",
                params={
                    "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                    "persona_key": "marc",
                },
            )
            assert active_resp.status_code == 200
            active_ids = {t["turn_id"] for t in active_resp.json()["turns"]}
            assert {t1, t2}.issubset(active_ids)
            assert len(app.state.assistant_turn_tasks) >= 2

            # Enforce per-user concurrency semaphore -> 429 ERR_ASSISTANT_CONCURRENCY_LIMIT
            monkeypatch.setenv("ORCIA_ASSISTANT_MAX_CONCURRENT_TURNS_PER_USER", "2")
            r3 = await client.post(
                "/api/v1/assistant/turns",
                params={"persona_key": "marc"},
                json={
                    "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                    "user_prompt": "Tab-3 blocked",
                },
            )
            assert r3.status_code == 429
            assert r3.json()["error_code"] == "ERR_ASSISTANT_CONCURRENCY_LIMIT"
            assert r3.json()["trace_id"]

        # Lifespan exit triggers bounded drain; remaining tasks are cleanly cancelled & discarded
    assert len(app.state.assistant_turn_tasks) == 0


@pytest.mark.asyncio
async def test_streaming_pre_first_byte_retry_idle_timeout_and_rfc9457_stream_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify 2x pre-first-byte retry (`429/502/503`), idle timeout, and RFC 9457 `stream_error`."""
    from orcia_core.orchestration.llm_streaming_httpx import HttpxOpenAiCompatibleLlmAdapter
    from orcia_core.ports.llm_streaming_port import LlmEndpointConfig, LlmStreamRequest

    monkeypatch.setenv("ORCIA_LLM_STREAM_RETRY_BASE_S", "0.01")
    ep = LlmEndpointConfig(
        provider="OpenAI",
        model_name="gpt-4o",
        endpoint_uri="https://llm.enterprise.internal/v1",
        auth_mode="api_key",
        api_key="sk-test",  # pragma: allowlist secret
    )

    # 1. Pre-first-byte retry: 429 -> 503 -> 200 succeeds cleanly
    attempts = 0

    def _retry_transport(_req: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, json={"error": "rate_limit"})
        if attempts == 2:
            return httpx.Response(503, json={"error": "overloaded"})
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"choices": [{"delta": {"content": "Recovered"}}]}\n\ndata: [DONE]\n\n',
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_retry_transport)) as client:
        adapter = HttpxOpenAiCompatibleLlmAdapter(http_client=client)
        deltas = [
            d
            async for d in adapter.stream_chat_sse(
                LlmStreamRequest(endpoint=ep, messages=({"role": "user", "content": "hi"},))
            )
        ]
    assert attempts == 3
    assert any(d.event == "token_delta" and d.delta == "Recovered" for d in deltas)
    assert deltas[-1].event == "turn_completed"

    # 2. Exhausted retries emit structured `stream_error` with HTTP status + error_code
    def _always_502(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"error": "bad_gateway"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(_always_502)) as client:
        adapter = HttpxOpenAiCompatibleLlmAdapter(http_client=client)
        err_deltas = [
            d
            async for d in adapter.stream_chat_sse(
                LlmStreamRequest(endpoint=ep, messages=({"role": "user", "content": "hi"},))
            )
        ]
    assert err_deltas[-1].event == "stream_error"
    assert err_deltas[-1].http_status == 502

    # 3. Inter-chunk idle timeout emits structured `stream_error` `ERR_UPSTREAM_TIMEOUT`
    class _HangingByteStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"choices": [{"delta": {"content": "Part1"}}]}\n\n'
            await asyncio.sleep(1.0)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _r: httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=_HangingByteStream()
            )
        )
    ) as client:
        adapter = HttpxOpenAiCompatibleLlmAdapter(http_client=client, inter_chunk_timeout_s=0.05)
        timeout_deltas = [
            d
            async for d in adapter.stream_chat_sse(
                LlmStreamRequest(endpoint=ep, messages=({"role": "user", "content": "hi"},))
            )
        ]
    assert timeout_deltas[-1].event == "stream_error"
    assert timeout_deltas[-1].error_code == "ERR_UPSTREAM_TIMEOUT"


def test_rate_limit_and_per_user_concurrency_return_429_rfc9457(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify sliding-window rate limit and concurrency semaphore enforce HTTP 429 RFC 9457."""
    from orcia_api.main import create_app

    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV_FILE", "/tmp/orcia-unit-none.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("ORCIA_ASSISTANT_RATE_LIMIT_MAX", "2")
    monkeypatch.setenv("ORCIA_ASSISTANT_RATE_LIMIT_WINDOW_S", "60")

    app = create_app()
    with TestClient(app) as client:
        ws = "0192c4e0-0000-7000-8000-000000000201"
        for idx in range(2):
            ok = client.post(
                "/api/v1/assistant/turns",
                params={"persona_key": "marc"},
                json={"workspace_id": ws, "user_prompt": f"Prompt {idx}"},
            )
            assert ok.status_code == 202
        limited = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            json={"workspace_id": ws, "user_prompt": "Prompt 3"},
        )
        assert limited.status_code == 429
        assert "application/problem+json" in limited.headers["content-type"]
        body = limited.json()
        assert body["error_code"] == "ERR_ASSISTANT_RATE_LIMITED"
        assert body["trace_id"]

    # Empty stream failure emits RFC 9457 `stream_error` + `trace_id`
    monkeypatch.setenv("ORCIA_ASSISTANT_RATE_LIMIT_MAX", "60")
    app2 = create_app()

    class _EmptyPort:
        is_cassette_adapter = True

        async def complete_chat(self, _req: Any) -> None:
            return None

        async def stream_chat_sse(self, _req: Any):
            if False:
                yield None

    app2.state.llm_streaming_port = _EmptyPort()
    with TestClient(app2) as client2:
        r_turn = client2.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            headers={"X-Trace-Id": "trace-26-3-empty"},
            json={"workspace_id": "0192c4e0-0000-7000-8000-000000000201", "user_prompt": "Empty"},
        )
        assert r_turn.status_code == 202
        turn_id = r_turn.json()["turn_id"]
        sse_resp = client2.get(
            f"/api/v1/assistant/turns/{turn_id}/stream",
            params={"persona_key": "marc"},
            headers={"X-Trace-Id": "trace-26-3-empty"},
        )
        assert sse_resp.status_code == 200
        assert "event: stream_error" in sse_resp.text
        for line in sse_resp.text.splitlines():
            if line.startswith("data:") and "ERR_" in line:
                payload = json.loads(line[5:].strip())
                assert payload["trace_id"]
                assert payload["status"] >= 400
                assert payload["error_code"]
                break
        else:
            raise AssertionError(f"Expected RFC 9457 stream_error payload in:\n{sse_resp.text}")


@pytest.mark.asyncio
async def test_sse_utils_redis_helpers_and_rate_limiter_edge_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover SSE parsing utils, cursor helpers, local semaphore, and invalid env fallbacks."""
    from orcia_core.orchestration._redis_turn_helpers import (
        cursor_gt,
        record_from_json,
        resolve_liveness_ttl_seconds,
    )
    from orcia_core.orchestration.llm_streaming_sse_utils import (
        delta_to_sse_dict,
        emit_chunk_deltas,
        resolve_inter_chunk_timeout_s,
        resolve_stream_retry_base_delay_s,
        stream_error_code_for_status,
    )
    from orcia_core.orchestration.redis_rate_limiter import (
        RedisAssistantRateLimiter,
        resolve_rate_limit_settings,
    )
    from orcia_core.ports.llm_streaming_port import LlmStreamDelta

    monkeypatch.setenv("ORCIA_LLM_STREAM_RETRY_BASE_S", "invalid")
    monkeypatch.setenv("ORCIA_LLM_STREAM_IDLE_TIMEOUT_S", "invalid")
    monkeypatch.setenv("ORCIA_ASSISTANT_RATE_LIMIT_MAX", "invalid")
    monkeypatch.setenv("ORCIA_ASSISTANT_RATE_LIMIT_WINDOW_S", "invalid")
    monkeypatch.setenv("ORCIA_ASSISTANT_MAX_CONCURRENT_TURNS_PER_USER", "invalid")
    monkeypatch.setenv("ORCIA_ASSISTANT_LIVENESS_TTL_S", "invalid")

    assert resolve_stream_retry_base_delay_s() == 0.25
    assert resolve_inter_chunk_timeout_s() == 30.0
    assert resolve_rate_limit_settings() == (60, 60, 8)
    assert resolve_liveness_ttl_seconds() == 15
    assert stream_error_code_for_status(429) == "ERR_RATE_LIMITED"
    assert stream_error_code_for_status(503) == "ERR_TRANSIENT_INFRA_ERROR"
    assert stream_error_code_for_status(504) == "ERR_UPSTREAM_TIMEOUT"
    assert stream_error_code_for_status(400) == "ERR_INTERNAL_SERVER_ERROR"

    acc_c: list[str] = []
    acc_t: list[str] = []
    in_t, d1 = emit_chunk_deltas(
        "<think>part1", "reason0", acc_content=acc_c, acc_thinking=acc_t, in_think=False, t0=0.0
    )
    assert in_t is True and len(d1) == 2
    in_t, d2 = emit_chunk_deltas(
        "part2</think>Hello", "", acc_content=acc_c, acc_thinking=acc_t, in_think=in_t, t0=0.0
    )
    assert in_t is False and d2[-1].delta == "Hello"
    assert delta_to_sse_dict(d1[0])["event"] == "thinking_delta"
    err_dict = delta_to_sse_dict(
        LlmStreamDelta(
            event="stream_error",
            error_message="Downstream failure",
            error_code="ERR_UPSTREAM_TIMEOUT",
            http_status=504,
        )
    )
    assert err_dict["data"]["status"] == 504

    assert cursor_gt("10-1", "10-0") is True
    assert cursor_gt("0-bad", "10-0") is False
    assert cursor_gt("bad-cursor", "10-0") is True
    assert record_from_json(None) is None
    assert record_from_json(b'"not-a-dict"') is None
    assert record_from_json("{bad-json") is None

    limiter = RedisAssistantRateLimiter(None)
    t1 = await limiter.acquire_concurrency_slot("u-conc", limit=1, ttl_seconds=60)
    assert t1 is not None
    assert await limiter.acquire_concurrency_slot("u-conc", limit=1, ttl_seconds=60) is None
    await limiter.release_concurrency_slot("u-conc", t1)
    assert await limiter.acquire_concurrency_slot("u-conc", limit=1, ttl_seconds=60) is not None


@pytest.mark.asyncio
async def test_producer_fallback_exception_and_consumer_terminal_paths() -> None:
    """Cover producer fallback text, runtime exception -> stream_error, and consumer edge paths."""
    from orcia_api.routers._assistant_turn_consumer import stream_assistant_turn_events
    from orcia_api.routers._assistant_turn_producer import execute_turn_producer_task
    from orcia_core.orchestration.redis_rate_limiter import RedisAssistantRateLimiter
    from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
    from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord

    registry = RedisAssistantTurnRegistry(None)
    limiter = RedisAssistantRateLimiter(None)
    rec = AssistantTurnRecord(
        turn_id="turn-fb-1",
        workspace_id="ws-1",
        user_id="u-1",
        status="RUNNING",
        user_prompt="Hello",
        assembled_system_prompt="Sys",
        trace_id="trace-fb-1",
    )
    await registry.register_turn(rec)
    assert await registry.get_turn("ws-1", "u-1", "turn-fb-1") is not None
    assert await registry.get_turn("ws-other", "u-1", "turn-fb-1") is None
    lease = await limiter.acquire_concurrency_slot("u-1", limit=4) or "l1"
    await execute_turn_producer_task(
        registry=registry,
        rate_limiter=limiter,
        initial_record=rec,
        lease_token=lease,
        liveness_ttl_s=30,
        t0=0.0,
        default_thinking="Analyzing...",
        fallback_response_text="Line 1\nLine 2",
        ep=None,
        http_client_getter=lambda: httpx.AsyncClient(),
        messages_builder=lambda: [],
        tools_builder=lambda: [],
        conversation_history_count=0,
        folder_pinned_notes=None,
        llm_port=None,
        user_email="u1@orcia.io",
        user_display_name="U1",
        audit_ledger_sink=None,
        locale="en",
        instance="/api/v1/assistant/turns",
    )
    await registry.set_stream_ttl("turn-fb-1", ttl_seconds=60)
    events = [e async for e in stream_assistant_turn_events(registry, turn_id="turn-fb-1")]
    assert events[-1]["event"] == "turn_completed"

    # Tail drain after already-completed cursor & missing turn_id
    tail_evts = [
        e
        async for e in stream_assistant_turn_events(
            registry, turn_id="turn-fb-1", after_cursor=events[-1]["cursor"]
        )
    ]
    assert tail_evts == []
    missing_evts = [
        e async for e in stream_assistant_turn_events(registry, turn_id="does-not-exist")
    ]
    assert missing_evts == []

    # Unexpected exception in llm_port triggers handle_turn_failure & stream_error
    class _ExplodingPort:
        is_cassette_adapter = True

        async def stream_chat_sse(self, _req: Any):
            if False:
                yield None
            raise RuntimeError("boom-stream-failure")

    rec2 = AssistantTurnRecord(
        turn_id="turn-err-1",
        workspace_id="ws-1",
        user_id="u-1",
        status="RUNNING",
        user_prompt="Boom",
        assembled_system_prompt="Sys",
        trace_id="trace-err-1",
    )
    await registry.register_turn(rec2)
    lease2 = await limiter.acquire_concurrency_slot("u-1", limit=4) or "l2"
    await execute_turn_producer_task(
        registry=registry,
        rate_limiter=limiter,
        initial_record=rec2,
        lease_token=lease2,
        liveness_ttl_s=30,
        t0=0.0,
        default_thinking="Analyzing...",
        fallback_response_text=None,
        ep=None,
        http_client_getter=lambda: httpx.AsyncClient(),
        messages_builder=lambda: [],
        tools_builder=lambda: [],
        conversation_history_count=0,
        folder_pinned_notes=None,
        llm_port=_ExplodingPort(),  # type: ignore[arg-type]
        user_email="u1@orcia.io",
        user_display_name="U1",
        audit_ledger_sink=None,
        locale="en",
        instance="/api/v1/assistant/turns",
    )
    err_evts = [e async for e in stream_assistant_turn_events(registry, turn_id="turn-err-1")]
    assert err_evts[-1]["event"] == "stream_error"
    assert err_evts[-1]["data"]["status"] == 500


@pytest.mark.asyncio
async def test_background_turn_wrappers_registry_fallbacks_and_telemetry_upsert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover background turn wrapper helpers, app.state fallbacks, consumer, and telemetry."""
    from types import SimpleNamespace

    from orcia_api.routers._assistant_background_registry import (
        PROMPT_TELEMETRY_LOG,
        get_rate_limiter_from_request,
        get_tracked_turn_tasks_from_request,
        get_turn_registry_from_request,
        record_prompt_telemetry_entry,
    )
    from orcia_api.routers._assistant_turn_consumer import stream_assistant_turn_events
    from orcia_api.routers.assistant_background_turns import (
        get_active_turn_for_workspace,
        run_and_consume_decoupled_turn_stream,
        stop_active_turn_for_workspace,
        stop_assistant_turn_by_id,
    )
    from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord

    dummy_req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    reg = get_turn_registry_from_request(dummy_req)
    lim = get_rate_limiter_from_request(dummy_req)
    tasks = get_tracked_turn_tasks_from_request(dummy_req)
    assert reg is dummy_req.app.state.assistant_turn_registry
    assert lim is dummy_req.app.state.assistant_rate_limiter
    assert tasks is dummy_req.app.state.assistant_turn_tasks

    record_prompt_telemetry_entry(
        workspace_id="ws-tel-26-3",
        turn_id="t-tel-1",
        user_prompt="First prompt",
        assembled_system_prompt="Sys v1",
        assistant_reply="Draft 1",
        thinking_text="Think 1",
    )
    upserted = record_prompt_telemetry_entry(
        workspace_id="ws-tel-26-3",
        turn_id="t-tel-1",
        user_prompt="Updated prompt",
        assembled_system_prompt="Sys v2",
        assistant_reply="Final reply",
        thinking_text="Think 2",
        user_feedback="LIKE",
    )
    assert upserted["user_feedback"] == "LIKE"
    assert len(PROMPT_TELEMETRY_LOG["ws-tel-26-3"]) >= 1

    streamed = [
        evt
        async for evt in run_and_consume_decoupled_turn_stream(
            request=dummy_req,
            workspace_id="ws-bg-wrap",
            user_prompt="Hello wrapper",
            system_msg="Sys prompt",
            default_thinking="Thinking...",
            fallback_response_text="Done!",
            ep=None,
            http_client_getter=lambda: httpx.AsyncClient(),
            messages_builder=lambda: [],
            tools_builder=lambda: [],
            conversation_history_count=0,
            folder_pinned_notes=None,
            thinking_effort="balanced",
            user_id="u-bg-wrap",
            trace_id="trace-bg-wrap",
        )
    ]
    assert streamed[-1]["event"] == "turn_completed"
    active = await get_active_turn_for_workspace(
        "ws-bg-wrap", request=dummy_req, user_id="u-bg-wrap"
    )
    assert active is not None and active.status == "COMPLETED"

    assert (
        await stop_assistant_turn_by_id(
            "does-not-exist", request=dummy_req, stopped_by_user_id="u-bg-wrap"
        )
        is None
    )
    assert (
        await stop_active_turn_for_workspace("ws-none", request=dummy_req, user_id="u-bg-wrap")
        is None
    )

    orphan = AssistantTurnRecord(
        turn_id="turn-orphan-stop",
        workspace_id="ws-bg-orphan",
        user_id="u-bg-wrap",
        status="RUNNING",
        user_prompt="Orphan",
        assembled_system_prompt="Sys",
        trace_id="trace-orphan",
    )
    await reg.register_turn(orphan)
    real_sleep = asyncio.sleep

    async def _fast_sleep(_delay: float) -> None:
        await real_sleep(0)

    monkeypatch.setattr(asyncio, "sleep", _fast_sleep)
    stopped = await stop_active_turn_for_workspace(
        "ws-bg-orphan", request=dummy_req, user_id="u-bg-wrap"
    )
    assert stopped is not None and stopped.status == "STOPPED"

    # Consumer liveness expiry -> ERR_ASSISTANT_TURN_INTERRUPTED
    crashed = AssistantTurnRecord(
        turn_id="turn-dead-local",
        workspace_id="ws-bg-orphan",
        user_id="u-bg-wrap",
        status="RUNNING",
        user_prompt="Dead",
        assembled_system_prompt="Sys",
        trace_id="trace-dead-local",
    )
    await reg.register_turn(crashed)
    dead_evts = [e async for e in stream_assistant_turn_events(reg, turn_id="turn-dead-local")]
    assert dead_evts[-1]["event"] == "stream_error"
    assert dead_evts[-1]["data"]["error_code"] == "ERR_ASSISTANT_TURN_INTERRUPTED"
