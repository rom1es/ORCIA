"""Unit tests for Gemini Interactions API auto-switch, fallback model & discovery sorting."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from orcia_core.orchestration.ai_models_connection import test_ai_model_endpoint_connection
from orcia_core.orchestration.ai_models_discovery_dialects import discover_gemini_native
from orcia_core.orchestration.ai_models_errors import ModelConnectionAuthFailedError
from orcia_core.orchestration.llm_endpoint_resolver import extract_tier_endpoint_from_dict
from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
from orcia_core.ports.llm_streaming_port import (
    ContentDelta,
    Finish,
    LlmEndpointConfig,
    LlmStreamRequest,
    ReasoningDelta,
    StreamErrorEvent,
    Usage,
)


@pytest.mark.asyncio
async def test_connection_auto_switches_to_interactions_model_and_agent_variants() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content.decode("utf-8"))
        calls.append((str(req.url), body))
        if ":generateContent" in str(req.url):
            return httpx.Response(400, text="This model only supports Interactions API.")
        if str(req.url).endswith("/v1beta/interactions") and "model" in body:
            return httpx.Response(400, text="Please pass the agent field instead of model.")
        if str(req.url).endswith("/v1beta/interactions") and body.get("agent") == "custom-agent":
            return httpx.Response(200, json={"outputs": [{"type": "text", "text": "pong"}]})
        return httpx.Response(500, text="unexpected")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        res = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            protocol_mode="gemini_native",
            model_name="custom-agent",
            api_key="AIza-test-key",  # pragma: allowlist secret
            provider_slug="google",
        )
    assert res.latency_ms >= 1
    assert len(calls) == 3
    assert ":generateContent" in calls[0][0]
    assert calls[1][0].endswith("/v1beta/interactions") and "model" in calls[1][1]
    assert calls[2][0].endswith("/v1beta/interactions") and calls[2][1]["agent"] == "custom-agent"


@pytest.mark.asyncio
async def test_connection_falls_back_to_secondary_model_but_not_on_401() -> None:
    seen_urls: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen_urls.append(str(req.url))
        if "antigravity-preview-05-2026" in req.content.decode("utf-8"):
            return httpx.Response(404, text="model not found")
        if "gemini-2.5-flash:generateContent" in str(req.url):
            return httpx.Response(200, json={"candidates": []})
        return httpx.Response(401, text="invalid api key")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        ok_res = await test_ai_model_endpoint_connection(
            http_client=client,
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            protocol_mode="gemini_native",
            model_name="antigravity-preview-05-2026",
            fallback_model_name="gemini-2.5-flash",
            api_key="AIza-test-key",  # pragma: allowlist secret
            provider_slug="google",
        )
        assert "gemini-2.5-flash" in ok_res.message_fr
        assert "gemini-2.5-flash" in ok_res.message_en
        assert seen_urls[0].endswith("/v1beta/interactions")
        assert seen_urls[1].endswith("/models/gemini-2.5-flash:generateContent")

        with pytest.raises(ModelConnectionAuthFailedError):
            await test_ai_model_endpoint_connection(
                http_client=client,
                endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
                protocol_mode="gemini_native",
                model_name="bad-key-model",
                fallback_model_name="gemini-2.5-flash",
                api_key="bad-key",  # pragma: allowlist secret
                provider_slug="google",
            )


@pytest.mark.asyncio
async def test_adapter_complete_chat_and_stream_auto_switch_interactions() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        body = json.loads(req.content.decode("utf-8"))
        if ":generateContent" in url or ":streamGenerateContent" in url:
            return httpx.Response(400, text="This model only supports Interactions API.")
        if url.endswith("/v1beta/interactions") and body.get("stream"):
            evts = [
                {"event_type": "interaction.created", "interaction": {"id": "int_1"}},
                {"event_type": "content.delta", "delta": {"type": "thought", "thought": "Plan"}},
                {"event_type": "content.delta", "delta": {"type": "text", "text": "Bonjour "}},
                {"event_type": "step.delta", "delta": {"type": "text", "text": "ORCIA"}},
                {
                    "event_type": "interaction.complete",
                    "interaction": {
                        "outputs": [{"type": "text", "text": "Bonjour ORCIA"}],
                        "usage": {"total_input_tokens": 11, "total_output_tokens": 7},
                    },
                },
            ]
            sse = "\n".join([*(f"data: {json.dumps(e)}" for e in evts), "data: [DONE]"])
            return httpx.Response(
                200, content=sse.encode("utf-8"), headers={"content-type": "text/event-stream"}
            )
        if url.endswith("/v1beta/interactions"):
            return httpx.Response(
                200,
                json={
                    "outputs": [
                        {"type": "thought", "thought": "Deep check"},
                        {"type": "text", "text": "Final answer"},
                    ],
                    "usage": {"total_input_tokens": 9, "total_output_tokens": 4},
                },
            )
        return httpx.Response(500, text="unexpected")

    ep_auto = LlmEndpointConfig(
        provider="google",
        model_name="gemini-special-experimental",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="api_key",
        api_key="AIza-test-key",  # pragma: allowlist secret
        protocol_mode="gemini_native",
    )
    req = LlmStreamRequest(endpoint=ep_auto, messages=[{"role": "user", "content": "Hi"}])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = HttpxMultiProviderLlmStreamingAdapter(http_client=client, max_stream_retries=0)
        sync_out = await adapter.complete_chat(req)
        assert sync_out is not None
        assert sync_out.content == "Final answer"
        assert sync_out.thinking_text == "Deep check"
        assert sync_out.input_tokens == 9 and sync_out.output_tokens == 4

        events = [ev async for ev in adapter.stream_chat_events(req)]
        assert any(isinstance(e, ReasoningDelta) and e.delta == "Plan" for e in events)
        assert [e.delta for e in events if isinstance(e, ContentDelta)] == ["Bonjour ", "ORCIA"]
        usage = next(e for e in events if isinstance(e, Usage))
        assert (usage.input_tokens, usage.output_tokens) == (11, 7)
        finish = next(e for e in events if isinstance(e, Finish))
        assert finish.accumulated_text == "Bonjour ORCIA"


@pytest.mark.asyncio
async def test_adapter_secondary_model_fallback_sync_stream_and_401_guard() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        body = json.loads(req.content.decode("utf-8"))
        if url.endswith("/v1beta/interactions"):
            return httpx.Response(404, text="retired model")
        if "gemini-2.5-flash:streamGenerateContent" in url:
            sse = (
                'data: {"candidates":[{"content":{"parts":[{"text":"Fallback SSE"}]}}]}\n'
                "data: [DONE]\n"
            )
            return httpx.Response(200, content=sse.encode("utf-8"))
        if "gemini-2.5-flash:generateContent" in url:
            return httpx.Response(
                200,
                json={"candidates": [{"content": {"parts": [{"text": "Fallback sync"}]}}]},
            )
        if body.get("model") == "auth-fail":
            return httpx.Response(401, text="unauthorized")
        return httpx.Response(401, text="unauthorized")

    ep = LlmEndpointConfig(
        provider="google",
        model_name="antigravity-preview-05-2026",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="api_key",
        api_key="AIza-test-key",  # pragma: allowlist secret
        protocol_mode="gemini_native",
        fallback_model_name="gemini-2.5-flash",
    )
    req = LlmStreamRequest(endpoint=ep, messages=[{"role": "user", "content": "Hello"}])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = HttpxMultiProviderLlmStreamingAdapter(http_client=client, max_stream_retries=0)
        sync_out = await adapter.complete_chat(req)
        assert sync_out is not None and sync_out.content == "Fallback sync"

        stream_events = [ev async for ev in adapter.stream_chat_events(req)]
        finish = next(e for e in stream_events if isinstance(e, Finish))
        assert finish.accumulated_text == "Fallback SSE"

        auth_req = LlmStreamRequest(
            endpoint=LlmEndpointConfig(
                provider="openai",
                model_name="auth-fail",
                endpoint_uri="https://api.openai.com/v1",
                auth_mode="api_key",
                api_key="bad",  # pragma: allowlist secret
                fallback_model_name="gemini-2.5-flash",
            ),
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert await adapter.complete_chat(auth_req) is None
        err_events = [ev async for ev in adapter.stream_chat_events(auth_req)]
        assert len(err_events) == 1 and isinstance(err_events[0], StreamErrorEvent)
        assert err_events[0].http_status == 401


@pytest.mark.asyncio
async def test_discover_gemini_native_sorts_gemini_chat_first_and_create_interaction() -> None:
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "models/aqa", "supportedGenerationMethods": ["generateAnswer"]},
                    {
                        "name": "models/antigravity-preview-05-2026",
                        "supportedGenerationMethods": ["createInteraction"],
                    },
                    {
                        "name": "models/text-embedding-004",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                    {
                        "name": "models/gemini-2.5-pro",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/gemini-2.5-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        models = await discover_gemini_native(
            http_client=client,
            base_url="https://generativelanguage.googleapis.com/v1beta",
            api_key="AIza-test",  # pragma: allowlist secret
            timeout_seconds=5.0,
            instance="/test",
        )
    assert [m.id for m in models] == [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "antigravity-preview-05-2026",
        "text-embedding-004",
        "aqa",
    ]
    assert models[2].usage_hint == "chat"

    ep = extract_tier_endpoint_from_dict(
        {
            "primaryModel": "antigravity-preview-05-2026",
            "secondaryModel": "gemini-2.5-flash",
            "endpointUrl": "https://generativelanguage.googleapis.com/v1beta",
            "modelFamily": "Google Gemini",
        }
    )
    assert ep is not None and ep.fallback_model_name == "gemini-2.5-flash"
