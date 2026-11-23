"""Branch-coverage edge tests for streaming HTTP helpers, fallbacks & `BaseHttpxLlmAdapter`."""

from __future__ import annotations

import json

import httpx
import pytest

from orcia_core.orchestration._llm_streaming_http_helpers import (
    build_non_stream_turn_outcome,
    build_openai_fallback_body,
    build_secondary_model_fallback_request,
    should_attempt_openai_404_fallback,
)
from orcia_core.orchestration.ai_models_errors import UnsafeLlmEndpointUrlError
from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
from orcia_core.ports.llm_streaming_port import (
    Finish,
    LlmEndpointConfig,
    LlmStreamRequest,
    StreamErrorEvent,
)


@pytest.mark.asyncio
async def test_http_helpers_and_legacy_plus_agent_fallbacks() -> None:
    ep_same = LlmEndpointConfig(
        provider="anthropic",
        model_name="m1",
        endpoint_uri="https://api.anthropic.com/v1",
        auth_mode="api_key",
        fallback_model_name="m1",
    )
    assert (
        build_secondary_model_fallback_request(LlmStreamRequest(endpoint=ep_same, messages=[]))
        is None
    )
    assert (
        should_attempt_openai_404_fallback(
            allow_legacy_fallback=True,
            status_code=404,
            ep=ep_same,
            target_url="https://api.anthropic.com/v1/messages",
        )
        is None
    )
    oai_fb = build_openai_fallback_body(
        LlmStreamRequest(
            endpoint=LlmEndpointConfig(
                provider="ollama",
                model_name="m",
                endpoint_uri="http://localhost:11434/v1",
                auth_mode="none_local",
                supports_tools=True,
            ),
            messages=[{"role": "user", "content": "hi"}],
            tools=[{"type": "function"}],
            tool_choice="required",
        ),
        stream=True,
    )
    assert oai_fb["tool_choice"] == "required"
    assert build_non_stream_turn_outcome(["not-dict"], [], 0.0) is None
    assert build_non_stream_turn_outcome({}, [], 0.0) is None

    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        body = json.loads(req.content.decode("utf-8"))
        if url.endswith("/v1/chat/completions"):
            return httpx.Response(404, text="not found")
        if url.endswith("/api/chat"):
            if body.get("stream"):
                return httpx.Response(
                    200,
                    content=b'not-json\n{"message":{"content":"ok"}}\n{"type":"message_stop"}\n',
                )
            return httpx.Response(200, json={"message": {"content": "legacy ok"}})
        if ":generateContent" in url or ":streamGenerateContent" in url:
            return httpx.Response(400, text="This model only supports Interactions API.")
        if url.endswith("/v1beta/interactions") and "model" in body:
            return httpx.Response(404, text="Please pass agent field")
        if url.endswith("/v1beta/interactions") and body.get("agent") == "agent-x":
            if body.get("stream"):
                return httpx.Response(
                    200,
                    content=b'data: {"delta":{"type":"text","text":"agent sse"}}\ndata: [DONE]\n',
                )
            return httpx.Response(200, json={"outputs": [{"type": "text", "text": "agent sync"}]})
        return httpx.Response(500, text="fail")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = HttpxMultiProviderLlmStreamingAdapter(http_client=client, max_stream_retries=1)
        leg_req = LlmStreamRequest(
            endpoint=LlmEndpointConfig(
                provider="ollama",
                model_name="llama3",
                endpoint_uri="http://localhost:11434/v1",
                auth_mode="none_local",
            ),
            messages=[{"role": "user", "content": "hi"}],
        )
        out_leg = await adapter.complete_chat(leg_req)
        assert out_leg is not None and out_leg.content == "legacy ok"
        ev_leg = [e async for e in adapter.stream_chat_events(leg_req)]
        assert any(isinstance(e, Finish) and e.accumulated_text == "ok" for e in ev_leg)

        ag_req = LlmStreamRequest(
            endpoint=LlmEndpointConfig(
                provider="google",
                model_name="agent-x",
                endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
                auth_mode="api_key",
                api_key="k",  # pragma: allowlist secret
                protocol_mode="gemini_native",
            ),
            messages=[{"role": "user", "content": "hi"}],
        )
        out_ag = await adapter.complete_chat(ag_req)
        assert out_ag is not None and out_ag.content == "agent sync"
        ev_ag = [e async for e in adapter.stream_chat_events(ag_req)]
        assert any(isinstance(e, Finish) and e.accumulated_text == "agent sse" for e in ev_ag)

        bad_ep = LlmEndpointConfig(
            provider="openai",
            model_name="m",
            endpoint_uri="http://169.254.169.254/v1",
            auth_mode="none_local",
        )
        with pytest.raises(UnsafeLlmEndpointUrlError):
            await adapter.complete_chat(LlmStreamRequest(endpoint=bad_ep, messages=[]))
        with pytest.raises(UnsafeLlmEndpointUrlError):
            _ = [
                e
                async for e in adapter.stream_chat_events(
                    LlmStreamRequest(endpoint=bad_ep, messages=[])
                )
            ]


@pytest.mark.asyncio
async def test_base_httpx_retry_connect_error_and_timeout_branches() -> None:
    oai_ep = LlmEndpointConfig(
        provider="openai",
        model_name="m",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="api_key",
        api_key="k",  # pragma: allowlist secret
    )
    req = LlmStreamRequest(endpoint=oai_ep, messages=[{"role": "user", "content": "hi"}])

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _r: httpx.Response(502, text="bad gateway"))
    ) as err_client:
        err_adapter = HttpxMultiProviderLlmStreamingAdapter(
            http_client=err_client, max_stream_retries=1
        )
        assert await err_adapter.complete_chat(req) is None
        ev_502 = [e async for e in err_adapter.stream_chat_events(req)]
        assert isinstance(ev_502[-1], StreamErrorEvent) and ev_502[-1].http_status == 502

    def exc_handler(r: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=r)

    async with httpx.AsyncClient(transport=httpx.MockTransport(exc_handler)) as exc_client:
        exc_adapter = HttpxMultiProviderLlmStreamingAdapter(
            http_client=exc_client, max_stream_retries=1
        )
        assert await exc_adapter.complete_chat(req) is None
        ev_exc = [e async for e in exc_adapter.stream_chat_events(req)]
        assert isinstance(ev_exc[-1], StreamErrorEvent) and ev_exc[-1].http_status == 502

    def timeout_handler(_r: httpx.Request) -> httpx.Response:
        raise TimeoutError("idle")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as t_client:
        t_adapter = HttpxMultiProviderLlmStreamingAdapter(
            http_client=t_client, max_stream_retries=0
        )
        ev_to = [e async for e in t_adapter.stream_chat_events(req)]
        assert isinstance(ev_to[-1], StreamErrorEvent) and ev_to[-1].http_status == 504
