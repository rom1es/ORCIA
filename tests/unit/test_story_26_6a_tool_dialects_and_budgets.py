"""Story 26.6a — TDD Unit Tests: Native Tool Dialects, supports_tools, 422 Guard & Loop Budgets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_llm_streaming_port_typed_events_and_zero_sdk_imports() -> None:
    """`LlmStreamingPort` exposes typed events with zero framework/SDK imports (`AD-19`)."""
    from orcia_core.ports.llm_streaming_port import (
        ContentDelta,
        Finish,
        LlmEndpointConfig,
        LlmStreamingPort,
        LlmStreamRequest,
        ReasoningDelta,
        ToolCallDelta,
        Usage,
    )

    port_src = (
        REPO_ROOT / "packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("httpx", "fastapi", "sqlalchemy", "litellm", "redis", "dbos", "dramatiq"):
        assert forbidden not in port_src

    assert ContentDelta(delta="hi", accumulated_text="hi").delta == "hi"
    assert ReasoningDelta(delta="think").delta == "think"
    assert (
        ToolCallDelta(index=0, tool_call_id="c1", name="search", arguments_delta="{}").name
        == "search"
    )
    assert Usage(input_tokens=10, output_tokens=5, usage_source="provider").output_tokens == 5
    assert (
        Finish(finish_reason="tool_calls", tool_calls=({"id": "c1"},)).finish_reason == "tool_calls"
    )

    ep = LlmEndpointConfig(
        provider="OpenAI",
        model_name="gpt-4o",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="api_key",
        supports_tools=True,
    )
    req = LlmStreamRequest(
        endpoint=ep,
        messages=({"role": "user", "content": "hi"},),
        tools=({"type": "function", "function": {"name": "search"}},),
        tool_choice="auto",
    )
    assert req.endpoint.supports_tools is True
    assert req.tool_choice == "auto"
    assert LlmStreamingPort is not None


@pytest.mark.asyncio
async def test_openai_compatible_streamed_and_non_streamed_tool_calls_and_404_fallback() -> None:
    """OpenAI-compatible dialect parses streamed/non-streamed tool calls and keeps tools on 404."""
    from orcia_core.orchestration.llm_streaming_httpx import HttpxOpenAiCompatibleLlmAdapter
    from orcia_core.orchestration.llm_tool_dialects import (
        format_messages_for_dialect,
        format_tool_result_message,
    )
    from orcia_core.ports.llm_streaming_port import (
        ContentDelta,
        Finish,
        LlmEndpointConfig,
        LlmStreamRequest,
        ReasoningDelta,
        ToolCallDelta,
        Usage,
    )

    tool_schema = [
        {
            "type": "function",
            "function": {
                "name": "query_workspace_knowledge_and_glossary",
                "description": "Search KB",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
        }
    ]
    sse_payload = (
        b'data: {"choices":[{"delta":{"reasoning_content":"Checking KB... "}}]}\n\n'
        b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_oai_1",'
        b'"type":"function","function":{"name":"query_workspace_knowledge_and_glossary",'
        b'"arguments":"{\\"que"}}]}}]}\n\n'
        b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"function":'
        b'{"arguments":"ry\\": \\"DORA\\"}"}}]},"finish_reason":null}]}\n\n'
        b'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}],'
        b'"usage":{"prompt_tokens":42,"completion_tokens":18}}\n\n'
        b"data: [DONE]\n\n"
    )
    seen_bodies: list[dict[str, Any]] = []

    def _stream_handler(req: httpx.Request) -> httpx.Response:
        seen_bodies.append(json.loads(req.content.decode("utf-8")))
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, content=sse_payload
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_stream_handler)) as client:
        adapter = HttpxOpenAiCompatibleLlmAdapter(http_client=client)
        ep = LlmEndpointConfig(
            provider="OpenAI",
            model_name="gpt-4o",
            endpoint_uri="https://api.openai.com/v1",
            auth_mode="api_key",
            api_key="sk-test",  # pragma: allowlist secret
            supports_tools=True,
        )
        events = [
            ev
            async for ev in adapter.stream_chat_events(
                LlmStreamRequest(
                    endpoint=ep,
                    messages=({"role": "user", "content": "Check DORA"},),
                    tools=tuple(tool_schema),
                    tool_choice="auto",
                )
            )
        ]

    assert seen_bodies[0]["tools"] == tool_schema
    assert seen_bodies[0]["tool_choice"] == "auto"
    assert any(isinstance(e, ReasoningDelta) for e in events)
    assert sum(1 for e in events if isinstance(e, ToolCallDelta)) == 2
    assert any(
        isinstance(e, Usage) and e.input_tokens == 42 and e.output_tokens == 18 for e in events
    )
    finish = events[-1]
    assert isinstance(finish, Finish)
    assert finish.finish_reason == "tool_calls"
    assert len(finish.tool_calls) == 1
    assert finish.tool_calls[0]["id"] == "call_oai_1"
    assert finish.tool_calls[0]["name"] == "query_workspace_knowledge_and_glossary"
    assert finish.tool_calls[0]["arguments"] == {"query": "DORA"}

    # Tool-result formatting for OpenAI
    formatted_msgs = format_messages_for_dialect(
        [
            {"role": "user", "content": "Check DORA"},
            {"role": "assistant", "content": "", "tool_calls": list(finish.tool_calls)},
            format_tool_result_message(
                tool_call_id="call_oai_1",
                name="query_workspace_knowledge_and_glossary",
                content="DORA Article 6 applies.",
            ),
        ],
        dialect="openai_compatible",
    )
    assert formatted_msgs[1]["tool_calls"][0]["function"]["name"] == (
        "query_workspace_knowledge_and_glossary"
    )
    assert formatted_msgs[2]["role"] == "tool"
    assert formatted_msgs[2]["tool_call_id"] == "call_oai_1"

    # Non-streamed 404 fallback MUST preserve `tools` and `tool_choice`
    fallback_bodies: list[tuple[str, dict[str, Any]]] = []

    def _fallback_404_handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode("utf-8"))
        fallback_bodies.append((req.url.path, body))
        if req.url.path == "/v1/chat/completions":
            return httpx.Response(404, text="Not Found")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_fb_1",
                                    "type": "function",
                                    "function": {
                                        "name": "query_workspace_knowledge_and_glossary",
                                        "arguments": '{"query": "fallback"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_fallback_404_handler)) as client:
        adapter = HttpxOpenAiCompatibleLlmAdapter(http_client=client)
        ep_fb = LlmEndpointConfig(
            provider="vLLM",
            model_name="qwen2.5-coder",
            endpoint_uri="https://vllm.enterprise.internal/v1",
            auth_mode="none",
            supports_tools=True,
        )
        outcome = await adapter.complete_chat(
            LlmStreamRequest(
                endpoint=ep_fb,
                messages=({"role": "user", "content": "hi"},),
                tools=tuple(tool_schema),
                tool_choice="required",
                stream=False,
            )
        )
    assert len(fallback_bodies) == 2
    assert fallback_bodies[1][1].get("tools") == tool_schema
    assert fallback_bodies[1][1].get("tool_choice") == "required"
    assert outcome is not None
    assert outcome.finish_reason == "tool_calls"
    assert outcome.tool_calls[0]["arguments"] == {"query": "fallback"}
    assert ContentDelta(delta="a").delta == "a"


@pytest.mark.asyncio
async def test_anthropic_streamed_and_non_streamed_tool_calls_and_tool_result_blocks() -> None:
    """Anthropic dialect parses `tool_use`/`input_json_delta` and formats `tool_result` blocks."""
    from orcia_core.orchestration.llm_streaming_httpx import HttpxAnthropicLlmAdapter
    from orcia_core.orchestration.llm_tool_dialects import (
        format_messages_for_dialect,
        format_tool_result_message,
    )
    from orcia_core.ports.llm_streaming_port import (
        Finish,
        LlmEndpointConfig,
        LlmStreamRequest,
        ReasoningDelta,
        ToolCallDelta,
        Usage,
    )

    ant_sse = (
        b'data: {"type":"message_start","message":{"usage":{"input_tokens":55}}}\n\n'
        b'data: {"type":"content_block_start","index":0,"content_block":{"type":"thinking"}}\n\n'
        b'data: {"type":"content_block_delta","index":0,'
        b'"delta":{"type":"thinking_delta","thinking":"Inspecting..."}}\n\n'
        b'data: {"type":"content_block_start","index":1,'
        b'"content_block":{"type":"tool_use","id":"toolu_01",'
        b'"name":"query_workspace_knowledge_and_glossary"}}\n\n'
        b'data: {"type":"content_block_delta","index":1,'
        b'"delta":{"type":"input_json_delta","partial_json":"{\\"query\\": \\"SE"}}\n\n'
        b'data: {"type":"content_block_delta","index":1,'
        b'"delta":{"type":"input_json_delta","partial_json":"PA\\"}"}}\n\n'
        b'data: {"type":"content_block_stop","index":1}\n\n'
        b'data: {"type":"message_delta","delta":{"stop_reason":"tool_use"},'
        b'"usage":{"output_tokens":24}}\n\n'
        b'data: {"type":"message_stop"}\n\n'
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _r: httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=ant_sse
            )
        )
    ) as client:
        adapter = HttpxAnthropicLlmAdapter(http_client=client)
        ep = LlmEndpointConfig(
            provider="Anthropic",
            model_name="claude-3-7-sonnet",
            endpoint_uri="https://api.anthropic.com/v1",
            auth_mode="api_key",
            api_key="sk-ant",  # pragma: allowlist secret
            protocol_mode="anthropic_messages",
            supports_tools=True,
        )
        events = [
            ev
            async for ev in adapter.stream_chat_events(
                LlmStreamRequest(
                    endpoint=ep,
                    messages=({"role": "user", "content": "Check SEPA"},),
                    tools=(
                        {
                            "type": "function",
                            "function": {
                                "name": "query_workspace_knowledge_and_glossary",
                                "parameters": {"type": "object"},
                            },
                        },
                    ),
                )
            )
        ]

    assert any(isinstance(e, ReasoningDelta) and "Inspecting" in e.thinking_text for e in events)
    assert any(isinstance(e, ToolCallDelta) and e.tool_call_id == "toolu_01" for e in events)
    assert any(
        isinstance(e, Usage) and e.input_tokens == 55 and e.output_tokens == 24 for e in events
    )
    finish = events[-1]
    assert isinstance(finish, Finish)
    assert finish.finish_reason == "tool_use"
    assert finish.tool_calls == (
        {
            "id": "toolu_01",
            "name": "query_workspace_knowledge_and_glossary",
            "arguments": {"query": "SEPA"},
        },
    )

    ant_msgs = format_messages_for_dialect(
        [
            {"role": "user", "content": "Check SEPA"},
            {"role": "assistant", "content": "", "tool_calls": list(finish.tool_calls)},
            format_tool_result_message(
                tool_call_id="toolu_01",
                name="query_workspace_knowledge_and_glossary",
                content="SEPA instant verified.",
            ),
        ],
        dialect="anthropic_messages",
    )
    assert ant_msgs[1]["role"] == "assistant"
    assert ant_msgs[1]["content"][0]["type"] == "tool_use"
    assert ant_msgs[2]["role"] == "user"
    assert ant_msgs[2]["content"][0] == {
        "type": "tool_result",
        "tool_use_id": "toolu_01",
        "content": "SEPA instant verified.",
    }


@pytest.mark.asyncio
async def test_supports_tools_false_never_sends_tools_and_gemini_native_ollama_default_false() -> (
    None
):
    """`supports_tools=false` omits `tools`; Gemini REST & non-/v1 Ollama default false."""
    from orcia_core.orchestration.ai_models_capabilities import infer_default_supports_tools
    from orcia_core.orchestration.ai_models_discovery import discover_models_from_provider
    from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
    from orcia_core.ports.llm_streaming_port import LlmEndpointConfig, LlmStreamRequest

    assert (
        infer_default_supports_tools(
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            protocol_mode="gemini_native",
            provider_slug="google",
        )
        is False
    )
    assert (
        infer_default_supports_tools(
            endpoint_uri="http://localhost:11434",
            protocol_mode="openai_compatible",
            provider_slug="ollama",
        )
        is False
    )
    assert (
        infer_default_supports_tools(
            endpoint_uri="http://localhost:11434/v1",
            protocol_mode="openai_compatible",
            provider_slug="ollama",
        )
        is True
    )

    # Discovery defaults for Gemini Native and Ollama /api/tags
    def _disc_handler(req: httpx.Request) -> httpx.Response:
        if "generativelanguage.googleapis.com" in str(req.url):
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "name": "models/gemini-2.5-flash",
                            "supportedGenerationMethods": ["generateContent"],
                        }
                    ]
                },
            )
        if req.url.path == "/v1/models":
            return httpx.Response(404)
        return httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(_disc_handler)) as client:
        gem_models = await discover_models_from_provider(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            protocol_mode="gemini_native",
            api_key="AIza-test",  # pragma: allowlist secret
        )
        ollama_native_models = await discover_models_from_provider(
            http_client=client,
            endpoint_uri="http://localhost:11434",
            protocol_mode="openai_compatible",
            provider_slug="ollama",
        )
    assert gem_models[0].supports_tools is False
    assert ollama_native_models[0].supports_tools is False

    # Outgoing LLM payload NEVER contains `tools` when `supports_tools=False`
    sent_bodies: list[dict[str, Any]] = []

    def _capture_handler(req: httpx.Request) -> httpx.Response:
        sent_bodies.append(json.loads(req.content.decode("utf-8")))
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "Gemini text ok"}]}}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_capture_handler)) as client:
        multi = HttpxMultiProviderLlmStreamingAdapter(http_client=client)
        ep_gem = LlmEndpointConfig(
            provider="Google Gemini",
            model_name="gemini-2.5-flash",
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            auth_mode="api_key",
            api_key="AIza-test",  # pragma: allowlist secret
            protocol_mode="gemini_native",
            supports_tools=False,
        )
        out = await multi.complete_chat(
            LlmStreamRequest(
                endpoint=ep_gem,
                messages=({"role": "user", "content": "hi"},),
                tools=({"type": "function", "function": {"name": "search"}},),
                tool_choice="auto",
                stream=False,
            )
        )
    assert out is not None and out.content == "Gemini text ok"
    assert "tools" not in sent_bodies[0]
    assert "tool_choice" not in sent_bodies[0]


def test_api_rejects_speed_2_and_3_with_422_err_model_tools_unsupported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """API returns HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED (RFC 9457) when supports_tools=false."""
    from orcia_api.dependencies import get_ai_models_hub_service
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(tmp_path / "missing.env"))
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    with TestClient(app) as client:
        # Trigger lazy hub init or access via app.state
        r_list = client.get("/api/v1/settings/ai-models/mappings")
        assert r_list.status_code == 200
        hub = app.state.ai_models_hub_service
        assert get_ai_models_hub_service is not None
        rec = hub.create_mapping(
            scope_level="GLOBAL",
            scope_id="0195f000-0000-7000-8000-000000000000",
            display_name="Gemini Native",
            inference_tier="medium",
            provider_slug="google",
            model_family="Gemini",
            model_name="gemini-2.5-flash",
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            auth_mode="none_local",
            protocol_mode="gemini_native",
            usage="chat",
        )
        assert rec.supports_tools is False

        r_s2 = client.post(
            "/api/v1/assistant/turns",
            params={"persona_key": "marc"},
            json={
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                "user_prompt": "Run tool search",
                "requested_speed": "SPEED_2_AGENT_TOOLS",
            },
        )
        assert r_s2.status_code == 422
        body = r_s2.json()
        assert body["error_code"] == "ERR_MODEL_TOOLS_UNSUPPORTED"
        assert "trace_id" in body

        r_s3 = client.post(
            "/api/v1/assistant/three-speed/stream",
            params={"persona_key": "marc"},
            json={
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                "user_prompt": "Deep audit",
                "requested_speed": "SPEED_3_DEEP_AUDIT",
            },
        )
        assert r_s3.status_code == 422
        assert r_s3.json()["error_code"] == "ERR_MODEL_TOOLS_UNSUPPORTED"


@pytest.mark.asyncio
async def test_loop_budgets_iterations_tokens_wall_clock_and_cassettes() -> None:
    """Loop budget controller enforces iterations, tokens, wall-clock, synthesis & cassettes."""
    from orcia_core.orchestration.assistant_loop_budgets import (
        AssistantLoopBudgetPolicy,
        run_bounded_tool_loop,
    )
    from orcia_core.orchestration.assistant_turn_errors import TurnBudgetExceededError
    from orcia_core.ports.llm_streaming_port import LlmEndpointConfig
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

    async def _exec_tool(tc: dict[str, Any]) -> str:
        return f"Tool {tc['name']} verified: {tc['arguments']}"

    # 1. Cassette multi-step OpenAI-compatible + forced synthesis at iteration limit
    res_oai = await run_bounded_tool_loop(
        llm_port=cassette,
        endpoint=ep_oai,
        messages=[{"role": "user", "content": "[CASSETTE_TOOL_LOOP] Check SLA"}],
        tools=[
            {
                "type": "function",
                "function": {"name": "search_kb", "parameters": {"type": "object"}},
            }
        ],
        tool_executor=_exec_tool,
        policy=AssistantLoopBudgetPolicy(
            max_iterations=2,
            max_total_tokens=5000,
            max_wall_clock_seconds=10.0,
            force_synthesis_on_limit=True,
        ),
    )
    assert res_oai.final_content
    assert res_oai.iterations_used <= 2

    # 2. Cassette Anthropic tool loop completes cleanly
    res_ant = await run_bounded_tool_loop(
        llm_port=cassette,
        endpoint=ep_ant,
        messages=[{"role": "user", "content": "[CASSETTE_TOOL_LOOP] Check DORA"}],
        tools=[
            {
                "type": "function",
                "function": {"name": "search_kb", "parameters": {"type": "object"}},
            }
        ],
        tool_executor=_exec_tool,
        policy=AssistantLoopBudgetPolicy(
            max_iterations=3,
            max_total_tokens=5000,
            max_wall_clock_seconds=10.0,
            force_synthesis_on_limit=False,
        ),
    )
    assert res_ant.final_content
    assert len(res_ant.executed_tool_calls) >= 1

    # 3. Token budget exhaustion raises TurnBudgetExceededError when force_synthesis_on_limit=False
    with pytest.raises(TurnBudgetExceededError) as exc_tok:
        await run_bounded_tool_loop(
            llm_port=cassette,
            endpoint=ep_oai,
            messages=[{"role": "user", "content": "[CASSETTE_MULTI_STEP_LOOP] Loop forever"}],
            tools=[
                {
                    "type": "function",
                    "function": {"name": "search_kb", "parameters": {"type": "object"}},
                }
            ],
            tool_executor=_exec_tool,
            policy=AssistantLoopBudgetPolicy(
                max_iterations=5,
                max_total_tokens=1,
                max_wall_clock_seconds=10.0,
                force_synthesis_on_limit=False,
            ),
        )
    assert exc_tok.value.error_code == "ERR_ASSISTANT_TURN_BUDGET_EXCEEDED"

    # 4. Wall-clock budget exhaustion with deterministic fake clock
    ticks = iter([0.0, 0.5, 12.0])
    with pytest.raises(TurnBudgetExceededError) as exc_wc:
        await run_bounded_tool_loop(
            llm_port=cassette,
            endpoint=ep_oai,
            messages=[{"role": "user", "content": "[CASSETTE_MULTI_STEP_LOOP] Slow loop"}],
            tools=[
                {
                    "type": "function",
                    "function": {"name": "search_kb", "parameters": {"type": "object"}},
                }
            ],
            tool_executor=_exec_tool,
            policy=AssistantLoopBudgetPolicy(
                max_iterations=5,
                max_total_tokens=10000,
                max_wall_clock_seconds=5.0,
                force_synthesis_on_limit=False,
            ),
            clock_fn=lambda: next(ticks, 15.0),
        )
    assert exc_wc.value.error_code == "ERR_ASSISTANT_TURN_BUDGET_EXCEEDED"
