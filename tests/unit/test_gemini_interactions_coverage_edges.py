"""Branch-coverage edge tests for Gemini Interactions dialect, URLs, parsing & telemetry."""

from __future__ import annotations

from typing import Any

import pytest

from orcia_core.orchestration.ai_models_urls import (
    build_gemini_interactions_url,
    build_gemini_native_chat_url,
    is_anthropic_provider,
    is_gemini_interactions_url,
)
from orcia_core.orchestration.llm_gemini_interactions import (
    build_gemini_interactions_request_body,
    extract_gemini_interactions_stream_deltas,
    parse_gemini_interactions_response,
)
from orcia_core.orchestration.llm_provider_parsing import (
    build_provider_headers,
    build_provider_request_body,
    extract_stream_chunk_deltas,
    make_thinking_evt,
    parse_non_stream_outcome,
)
from orcia_core.orchestration.llm_usage_telemetry import (
    extract_usage_tokens_from_payload,
    persist_assistant_turn_ledger_entry,
    resolve_usage_with_fallback,
)
from orcia_core.ports.llm_streaming_port import (
    Finish,
    LlmEndpointConfig,
    LlmStreamDelta,
    LlmStreamRequest,
    StreamErrorEvent,
    ToolCallDelta,
    Usage,
    delta_to_typed_event,
    iter_typed_stream_events,
    typed_event_to_delta,
)


def test_interactions_dialect_and_url_helpers_branches() -> None:
    multi = build_gemini_interactions_request_body(
        "models/deep-research-pro",
        [
            {"role": "system", "content": "Be concise"},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ],
        stream=True,
        tools=[
            {"function": {"name": "search", "description": "s", "parameters": {"type": "object"}}}
        ],
        use_agent_field=True,
    )
    assert multi["agent"] == "deep-research-pro"
    assert multi["system_instruction"] == "Be concise"
    assert len(multi["input"]) == 2 and multi["input"][0]["role"] == "user"
    assert multi["tools"][0]["function_declarations"][0]["name"] == "search"

    assert build_gemini_interactions_request_body("m1", [])["input"] == "Hello"

    c, t, tc = parse_gemini_interactions_response(
        {
            "interaction": {
                "outputs": [
                    "ignore",
                    {"type": "thought_summary", "summary": "S1"},
                    {"type": "thought"},
                    {"type": "function_call", "functionCall": {"name": "fn1", "args": {"a": 1}}},
                    {"content": ["bad", {"thought": True, "text": "T2"}, {"text": "Part1"}]},
                    {"parts": [{"thought": True, "text": "T3"}, {"text": "Part2"}]},
                ]
            }
        }
    )
    assert c == "Part1Part2" and "S1" in t and "T2" in t and "T3" in t and tc[0]["name"] == "fn1"
    assert (
        parse_gemini_interactions_response({"output_text": "Direct output"})[0] == "Direct output"
    )

    assert extract_gemini_interactions_stream_deltas({"delta": "bad"}) == ("", "")
    assert extract_gemini_interactions_stream_deltas(
        {"delta": {"type": "thought_summary", "summary": "Sum"}}
    ) == ("", "Sum")
    assert extract_gemini_interactions_stream_deltas({"delta": {"content": "Chunk"}}) == (
        "Chunk",
        "",
    )

    assert is_gemini_interactions_url("https://host/v1beta/interactions?alt=sse") is True
    assert (
        build_gemini_interactions_url("https://host/v1beta/interactions")
        == "https://host/v1beta/interactions"
    )
    assert (
        build_gemini_interactions_url("https://host/v1alpha/models/m:streamGenerateContent")
        == "https://host/v1alpha/interactions"
    )
    assert (
        build_gemini_interactions_url("https://host/v1beta/m:generateContent")
        == "https://host/v1beta/interactions"
    )
    assert (
        build_gemini_interactions_url("https://host/models/m:generateContent")
        == "https://host/v1beta/interactions"
    )
    assert (
        build_gemini_interactions_url("https://host/v1beta/models")
        == "https://host/v1beta/interactions"
    )
    assert (
        build_gemini_interactions_url("https://generativelanguage.googleapis.com")
        == "https://generativelanguage.googleapis.com/v1beta/interactions"
    )

    with pytest.raises(ValueError):
        build_gemini_native_chat_url("https://generativelanguage.googleapis.com", "")
    with pytest.raises(ValueError):
        build_gemini_native_chat_url("https://generativelanguage.googleapis.com", "models/")
    assert build_gemini_native_chat_url(
        "https://generativelanguage.googleapis.com", "gemini-2.5-flash"
    ).endswith("/v1beta/models/gemini-2.5-flash:generateContent")
    assert build_gemini_native_chat_url(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash",
        "gemini-2.5-flash",
    ).endswith(":generateContent")
    assert is_anthropic_provider("https://api.anthropic.com/v1/messages") is True


@pytest.mark.asyncio
async def test_telemetry_provider_parsing_and_ports_branches() -> None:
    assert extract_usage_tokens_from_payload(
        {"interaction": {"usage": {"total_input_tokens": 3, "total_output_tokens": 5}}}
    ) == (3, 5)
    assert extract_usage_tokens_from_payload(
        {"message": {"usage": {"input_tokens": 2, "output_tokens": 4}}}
    ) == (2, 4)
    assert extract_usage_tokens_from_payload(
        {"usageMetadata": {"promptTokenCount": 4, "totalTokenCount": 10}}
    ) == (4, 6)
    assert extract_usage_tokens_from_payload({"prompt_eval_count": 7, "eval_count": 8}) == (7, 8)
    assert extract_usage_tokens_from_payload({}) is None
    assert resolve_usage_with_fallback(prompt_text="abcd", reply_text="abcd") == (1, 1, "estimated")

    class _FakeSink:
        def __init__(self, fail: bool = False) -> None:
            self.fail = fail

        async def record_entry(self, entry: Any) -> str:
            if self.fail:
                raise RuntimeError("boom")
            return str(entry.workspace_id)

    assert (
        await persist_assistant_turn_ledger_entry(
            audit_ledger_sink=_FakeSink(),
            user_id="u1",
            user_email=None,
            user_display_name=None,
            workspace_id="not-a-uuid",
            turn_id="t1",
            model_id="m1",
            input_tokens=1,
            output_tokens=1,
            latency_ms=5.0,
            invoked_targets=("t_a",),
        )
        == "None"
    )
    assert (
        await persist_assistant_turn_ledger_entry(
            audit_ledger_sink=_FakeSink(fail=True),
            user_id="u1",
            user_email=None,
            user_display_name=None,
            workspace_id="00000000-0000-7000-8000-000000000001",
            turn_id="t2",
            model_id="m1",
            input_tokens=1,
            output_tokens=1,
            latency_ms=5.0,
        )
        is None
    )

    ep_az = LlmEndpointConfig(
        provider="azure",
        model_name="gpt",
        endpoint_uri="https://x.openai.azure.com/v1",
        auth_mode="api_key",
        api_key="k",  # pragma: allowlist secret
    )
    assert (
        build_provider_headers(ep_az, "https://x.openai.azure.com/v1/chat/completions")["api-key"]
        == "k"
    )
    ep_ant = LlmEndpointConfig(
        provider="anthropic",
        model_name="claude",
        endpoint_uri="https://api.anthropic.com/v1",
        auth_mode="api_key",
        api_key="k",  # pragma: allowlist secret
    )
    assert (
        build_provider_headers(ep_ant, "https://api.anthropic.com/v1/messages")["x-api-key"] == "k"
    )
    oai_body = build_provider_request_body(
        ep=ep_az,
        target_url="https://x.openai.azure.com/v1/chat/completions",
        messages=[{"role": "user", "content": "hi"}],
        stream=False,
        tools=[{"type": "function", "function": {"name": "t"}}],
        tool_choice="auto",
    )
    assert oai_body["tool_choice"] == "auto"
    assert parse_non_stream_outcome({"object": "interaction", "output_text": "ok"})[0] == "ok"
    assert parse_non_stream_outcome({}) == ("", "", (), "stop")
    assert extract_stream_chunk_deltas({"event_type": "interaction.created"}) == ("", "")
    assert extract_stream_chunk_deltas({"message": {"content": "c", "thinking": "r"}}) == ("c", "r")
    assert extract_stream_chunk_deltas({}) == ("", "")
    assert make_thinking_evt("d", ["d"], 0.0)["event"] == "thinking_delta"

    for ev in (
        ToolCallDelta(index=1, tool_call_id="id1", name="fn", arguments_delta="{}"),
        Usage(input_tokens=2, output_tokens=3, usage_source="provider"),
        StreamErrorEvent(error_message="err", error_code="E", http_status=500),
        Finish(finish_reason="stop", accumulated_text="a"),
    ):
        assert type(delta_to_typed_event(typed_event_to_delta(ev))) is type(ev)

    class _SseOnlyPort:
        async def complete_chat(self, request: LlmStreamRequest) -> None:
            return None

        async def stream_chat_sse(self, request: LlmStreamRequest):
            yield LlmStreamDelta(event="token_delta", delta="hi", accumulated_text="hi")

    req = LlmStreamRequest(endpoint=ep_az, messages=[{"role": "user", "content": "hi"}])
    assert len([e async for e in iter_typed_stream_events(_SseOnlyPort(), req)]) == 1
