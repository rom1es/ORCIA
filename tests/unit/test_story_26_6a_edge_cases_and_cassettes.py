"""Story 26.6a — Edge Cases, Cassettes, Retry/Error Streaming & Dialect Coverage Tests."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest


def test_ai_models_capabilities_and_port_conversions() -> None:
    """Cover 0-token capability detection variants and typed stream event conversions."""
    from orcia_core.orchestration.ai_models_capabilities import (
        detect_discovered_model_supports_tools,
        infer_default_supports_tools,
    )
    from orcia_core.orchestration.llm_streaming_sse_utils import (
        delta_to_sse_dict,
        resolve_inter_chunk_timeout_s,
        resolve_stream_retry_base_delay_s,
        stream_error_code_for_status,
    )
    from orcia_core.ports.llm_streaming_port import (
        ContentDelta,
        Finish,
        LlmStreamDelta,
        ReasoningDelta,
        StreamErrorEvent,
        ToolCallDelta,
        Usage,
        delta_to_typed_event,
        typed_event_to_delta,
    )

    assert not detect_discovered_model_supports_tools(
        {},
        protocol_mode="openai_compatible",
        endpoint_uri="https://x/v1",
        provider_slug="openai",
        usage_hint="embedding",
    )
    assert not detect_discovered_model_supports_tools(
        {},
        protocol_mode="gemini_native",
        endpoint_uri="https://g",
        provider_slug="google",
    )
    assert not detect_discovered_model_supports_tools(
        {},
        protocol_mode="openai_compatible",
        endpoint_uri="http://localhost:11434/api",
        provider_slug="ollama",
    )
    assert not detect_discovered_model_supports_tools(
        {"supports_tools": False},
        protocol_mode="openai_compatible",
        endpoint_uri="https://x/v1",
        provider_slug="openai",
    )
    assert detect_discovered_model_supports_tools(
        {"capabilities": {"tool_calling": True}},
        protocol_mode="openai_compatible",
        endpoint_uri="https://x/v1",
        provider_slug="openai",
    )
    assert detect_discovered_model_supports_tools(
        {"supported_features": ["function_calling"]},
        protocol_mode="openai_compatible",
        endpoint_uri="https://x/v1",
        provider_slug="openai",
    )
    assert infer_default_supports_tools(endpoint_uri="https://x/v1", model_name="bge-m3") is False

    pairs = [
        ReasoningDelta(delta="r", thinking_text="r"),
        ContentDelta(delta="c", accumulated_text="c"),
        ToolCallDelta(index=0, tool_call_id="c1", name="fn", arguments_delta="{}"),
        Usage(input_tokens=3, output_tokens=4, usage_source="provider"),
        StreamErrorEvent(error_message="err", error_code="ERR_RATE_LIMITED", http_status=429),
        Finish(finish_reason="tool_calls", tool_calls=({"id": "c1", "name": "fn"},)),
    ]
    for ev in pairs:
        delta = typed_event_to_delta(ev)
        assert delta_to_typed_event(delta) is not None
        sse = delta_to_sse_dict(delta)
        assert "event" in sse and "data" in sse
    assert (
        delta_to_sse_dict(LlmStreamDelta(event="usage", input_tokens=1, output_tokens=2))["event"]
        == "usage"
    )
    assert stream_error_code_for_status(429) == "ERR_RATE_LIMITED"
    assert stream_error_code_for_status(503) == "ERR_TRANSIENT_INFRA_ERROR"
    assert stream_error_code_for_status(504) == "ERR_UPSTREAM_TIMEOUT"
    assert stream_error_code_for_status(500) == "ERR_INTERNAL_SERVER_ERROR"
    assert resolve_inter_chunk_timeout_s(2.5) == 2.5
    assert resolve_stream_retry_base_delay_s() >= 0.005


def test_tool_dialects_edge_cases_and_coalescing() -> None:
    """Cover JSON argument parsing edge cases and Anthropic tool_result coalescing."""
    from orcia_core.orchestration.llm_tool_dialects import (
        ToolCallAccumulator,
        format_messages_for_dialect,
        parse_json_arguments,
    )

    assert parse_json_arguments("   ") == {}
    assert parse_json_arguments("[1, 2]") == {"value": [1, 2]}
    assert parse_json_arguments("{bad") == {"_raw": "{bad"}
    assert parse_json_arguments(123) == {}

    ant_msgs = format_messages_for_dialect(
        [
            {"role": "system", "content": "sys"},
            {
                "role": "assistant",
                "content": "working",
                "tool_calls": [{"id": "t1", "name": "fn", "arguments": {"a": 1}}],
            },
            {"role": "tool", "tool_call_id": "t1", "name": "fn", "content": "r1"},
            {"role": "tool", "tool_call_id": "t2", "name": "fn", "content": "r2"},
        ],
        dialect="anthropic_messages",
    )
    assert len(ant_msgs) == 2
    assert len(ant_msgs[1]["content"]) == 2
    oai_msgs = format_messages_for_dialect(
        [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "c1", "name": "fn", "arguments": '{"k":1}'}],
            }
        ],
        dialect="openai_compatible",
    )
    assert oai_msgs[0]["tool_calls"][0]["function"]["arguments"] == '{"k":1}'

    acc = ToolCallAccumulator()
    assert acc.process_chunk({"type": "message_delta", "delta": {"stop_reason": "end_turn"}}) == []
    assert acc.finish_reason == "end_turn"


@pytest.mark.asyncio
async def test_cassette_adapter_stream_events_sse_and_iter_typed() -> None:
    """Cover `DeterministicCassetteLlmStreamingAdapter` complete_chat, SSE, and typed events."""
    from orcia_core.ports.llm_streaming_port import (
        LlmEndpointConfig,
        LlmStreamRequest,
        iter_typed_stream_events,
    )
    from orcia_core.testing.cassette_llm import DeterministicCassetteLlmStreamingAdapter

    cassette = DeterministicCassetteLlmStreamingAdapter()
    ep_oai = LlmEndpointConfig(
        provider="OpenAI",
        model_name="gpt-4o",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none",
        protocol_mode="openai_compatible",
        supports_tools=True,
    )
    ep_ant = LlmEndpointConfig(
        provider="Anthropic",
        model_name="claude-3-7-sonnet",
        endpoint_uri="https://api.anthropic.com/v1",
        auth_mode="none",
        protocol_mode="anthropic_messages",
        supports_tools=True,
    )
    out_plain = await cassette.complete_chat(
        LlmStreamRequest(endpoint=ep_oai, messages=({"role": "user", "content": "Hello"},))
    )
    assert out_plain is not None and out_plain.finish_reason == "stop"

    sse_deltas = [
        d
        async for d in cassette.stream_chat_sse(
            LlmStreamRequest(
                endpoint=ep_ant,
                messages=({"role": "user", "content": "[CASSETTE_TOOL_LOOP] Check"},),
                tools=({"name": "direct_tool"},),
            )
        )
    ]
    assert any(d.event == "tool_call_delta" for d in sse_deltas)

    # Also test tool synthesis on second turn & iter_typed_stream_events fallback path
    synth = await cassette.complete_chat(
        LlmStreamRequest(
            endpoint=ep_oai,
            messages=(
                {"role": "user", "content": "[CASSETTE_TOOL_LOOP] Check"},
                {"role": "tool", "tool_call_id": "c1", "name": "direct_tool", "content": "OK"},
            ),
            tools=({"type": "function", "function": {"name": "direct_tool"}},),
        )
    )
    assert synth is not None and "DETERMINISTIC_TOOL_SYNTHESIS" in synth.content

    class _LegacyOnlyPort:
        async def complete_chat(self, _req: LlmStreamRequest) -> None:
            return None

        async def stream_chat_sse(self, _req: LlmStreamRequest) -> AsyncIterator[Any]:
            from orcia_core.ports.llm_streaming_port import LlmStreamDelta

            yield LlmStreamDelta(event="token_delta", delta="hi", accumulated_text="hi")
            yield LlmStreamDelta(event="turn_completed", accumulated_text="hi")

    evs = [
        e
        async for e in iter_typed_stream_events(
            _LegacyOnlyPort(), LlmStreamRequest(endpoint=ep_oai, messages=())
        )
    ]
    assert len(evs) == 2


@pytest.mark.asyncio
async def test_streaming_httpx_404_fallback_retries_timeout_and_budget_speeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover SSE 404 fallback with tools, retryable HTTP/ConnectError, and speed budgets."""
    from orcia_core.orchestration.ai_models_errors import UnsafeLlmEndpointUrlError
    from orcia_core.orchestration.assistant_loop_budgets import (
        AssistantLoopBudgetController,
        AssistantLoopBudgetPolicy,
        resolve_loop_budget_for_speed,
        run_bounded_tool_loop,
    )
    from orcia_core.orchestration.llm_streaming_httpx import HttpxOpenAiCompatibleLlmAdapter
    from orcia_core.ports.llm_streaming_port import (
        Finish,
        LlmEndpointConfig,
        LlmStreamRequest,
        StreamErrorEvent,
    )

    monkeypatch.setenv("ORCIA_LLM_STREAM_RETRY_BASE_S", "bad-float")
    monkeypatch.setenv("ORCIA_LLM_STREAM_IDLE_TIMEOUT_S", "bad-float")

    calls: list[tuple[str, dict[str, Any]]] = []

    def _stream_404_then_ok(req: httpx.Request) -> httpx.Response:
        calls.append((req.url.path, json.loads(req.content.decode("utf-8"))))
        if len(calls) == 1:
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b"not-json\n\ndata: [DONE]\n\n",
        )

    ep = LlmEndpointConfig(
        provider="OpenAI",
        model_name="gpt-4o",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none",
        supports_tools=True,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(_stream_404_then_ok)) as client:
        adapter = HttpxOpenAiCompatibleLlmAdapter(http_client=client)
        evs = [
            e
            async for e in adapter.stream_chat_events(
                LlmStreamRequest(
                    endpoint=ep,
                    messages=({"role": "user", "content": "hi"},),
                    tools=({"type": "function", "function": {"name": "search"}},),
                    tool_choice="required",
                )
            )
        ]
    assert len(calls) == 2 and "tools" in calls[1][1] and calls[1][1]["tool_choice"] == "required"
    assert isinstance(evs[-1], Finish)

    # HTTP 503 retry exhaustion -> StreamErrorEvent
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _r: httpx.Response(503, json={"err": "busy"}))
    ) as client_503:
        adapter_503 = HttpxOpenAiCompatibleLlmAdapter(http_client=client_503, max_stream_retries=1)
        evs_503 = [
            e
            async for e in adapter_503.stream_chat_events(
                LlmStreamRequest(endpoint=ep, messages=({"role": "user", "content": "hi"},))
            )
        ]
    assert isinstance(evs_503[-1], StreamErrorEvent) and evs_503[-1].http_status == 503

    # ConnectError retry exhaustion -> StreamErrorEvent 502
    def _raise_conn(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    async with httpx.AsyncClient(transport=httpx.MockTransport(_raise_conn)) as client_conn:
        adapter_conn = HttpxOpenAiCompatibleLlmAdapter(
            http_client=client_conn, max_stream_retries=1
        )
        evs_conn = [
            e
            async for e in adapter_conn.stream_chat_events(
                LlmStreamRequest(endpoint=ep, messages=({"role": "user", "content": "hi"},))
            )
        ]
    assert isinstance(evs_conn[-1], StreamErrorEvent) and evs_conn[-1].http_status == 502

    # SSRF unsafe URL raises UnsafeLlmEndpointUrlError
    bad_ep = LlmEndpointConfig(
        provider="OpenAI",
        model_name="gpt-4o",
        endpoint_uri="http://169.254.169.254/v1",
        auth_mode="none",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(_stream_404_then_ok)) as client_bad:
        adapter_bad = HttpxOpenAiCompatibleLlmAdapter(http_client=client_bad)
        with pytest.raises(UnsafeLlmEndpointUrlError):
            async for _ in adapter_bad.stream_chat_events(
                LlmStreamRequest(endpoint=bad_ep, messages=({"role": "user", "content": "hi"},))
            ):
                pass

    # Speed budget defaults + None complete_chat outcome
    p3 = resolve_loop_budget_for_speed("SPEED_3_DEEP_AUDIT")
    p2 = resolve_loop_budget_for_speed("SPEED_2_AGENT_TOOLS", max_iterations=6)
    p1 = resolve_loop_budget_for_speed("SPEED_1_FAST")
    assert p3.max_iterations == 12 and p2.max_iterations == 6 and p1.max_iterations == 1
    ctrl = AssistantLoopBudgetController(p1)
    assert ctrl.policy == p1

    class _NonePort:
        async def complete_chat(self, _req: LlmStreamRequest) -> None:
            return None

        async def stream_chat_sse(self, _req: LlmStreamRequest) -> AsyncIterator[Any]:
            if False:
                yield None

    async def _noop_exec(_tc: dict[str, Any]) -> str:
        return "ok"

    res_none = await run_bounded_tool_loop(
        llm_port=_NonePort(),
        endpoint=ep,
        messages=[{"role": "user", "content": "hi"}],
        tools=[],
        tool_executor=_noop_exec,
        policy=AssistantLoopBudgetPolicy(max_iterations=2),
    )
    assert res_none.final_content == ""
    await asyncio.sleep(0)
