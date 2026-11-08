"""Unit & Integration tests for Google Gemini (`gemini-argon`) Mode B Native & Mode A Bridge."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from orcia_api.main import app
from orcia_api.routers.assistant_llm_gemini_adapter import (
    build_gemini_native_headers,
    build_gemini_native_url,
    evaluate_welcome_llm_connection_test,
    extract_gemini_stream_chunk_deltas,
    is_google_gemini_native_provider,
    parse_gemini_native_response,
)
from orcia_api.routers.assistant_llm_providers import (
    ResolvedLiveLlmEndpoint,
    build_provider_headers,
    build_provider_request_body,
    invoke_provider_chat_async,
    normalize_chat_completions_url,
    stream_provider_chat_sse_async,
)
from orcia_api.schemas import bootstrap as bs


def test_google_gemini_mode_a_openai_bridge_url_normalization_and_bearer_headers() -> None:
    """Mode A (`/v1beta/openai`): verify URL normalization without double `/v1` & Bearer header."""
    mode_a_url = normalize_chat_completions_url(
        "https://generativelanguage.googleapis.com/v1beta/openai", "google"
    )
    assert mode_a_url == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert "/v1beta/openai/v1/" not in mode_a_url
    assert (
        is_google_gemini_native_provider(
            "https://generativelanguage.googleapis.com/v1beta/openai", "google"
        )
        is False
    )

    ep_mode_a = ResolvedLiveLlmEndpoint(
        provider="Google Gemini",
        model_name="gemini-argon",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta/openai",
        auth_mode="api_key",
        api_key="AIzaSy-test-openai-bridge-key",  # pragma: allowlist secret
    )
    headers = build_provider_headers(ep_mode_a, mode_a_url)
    assert headers["Authorization"] == "Bearer AIzaSy-test-openai-bridge-key"
    assert "x-goog-api-key" not in headers

    body = build_provider_request_body(
        ep=ep_mode_a,
        target_url=mode_a_url,
        messages=[
            {"role": "system", "content": "Sys"},
            {"role": "user", "content": "Hello Argon"},
        ],
        stream=True,
    )
    assert body["model"] == "gemini-argon"
    assert body["stream"] is True
    assert len(body["messages"]) == 2


def test_google_gemini_mode_b_native_url_headers_and_request_body_for_gemini_argon() -> None:
    """Mode B (`/v1beta`): verify `:generateContent`, `x-goog-api-key` & `thinkingConfig`."""
    assert (
        is_google_gemini_native_provider(
            "https://generativelanguage.googleapis.com/v1beta", "google"
        )
        is True
    )
    assert (
        build_gemini_native_url(
            "https://generativelanguage.googleapis.com/v1beta", "gemini-argon", stream=False
        )
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-argon:generateContent"
    )
    assert (
        build_gemini_native_url(
            "https://generativelanguage.googleapis.com", "models/gemini-argon", stream=True
        )
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-argon:streamGenerateContent?alt=sse"
    )

    ep_mode_b = ResolvedLiveLlmEndpoint(
        provider="Google Gemini",
        model_name="gemini-argon",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="api_key",
        api_key="AIzaSy-native-gemini-key",  # pragma: allowlist secret
    )
    target_non_stream = normalize_chat_completions_url(
        ep_mode_b.endpoint_uri,
        ep_mode_b.provider,
        model_name=ep_mode_b.model_name,
        stream=False,
    )
    target_stream = normalize_chat_completions_url(
        ep_mode_b.endpoint_uri,
        ep_mode_b.provider,
        model_name=ep_mode_b.model_name,
        stream=True,
    )
    assert (
        target_non_stream
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-argon:generateContent"
    )
    assert (
        target_stream
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-argon:streamGenerateContent?alt=sse"
    )

    headers = build_provider_headers(ep_mode_b, target_non_stream)
    assert headers == {
        "Content-Type": "application/json",
        "x-goog-api-key": "AIzaSy-native-gemini-key",
    }
    assert build_gemini_native_headers("AIzaSy-key")["x-goog-api-key"] == "AIzaSy-key"

    body = build_provider_request_body(
        ep=ep_mode_b,
        target_url=target_non_stream,
        messages=[
            {"role": "system", "content": "Constitution Layer 1"},
            {"role": "user", "content": "Question 1"},
            {"role": "assistant", "content": "Answer 1"},
            {"role": "user", "content": "Question 2"},
        ],
        stream=False,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "query_workspace_knowledge_and_glossary",
                    "description": "Search workspace glossary",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
                },
            }
        ],
    )
    assert body["systemInstruction"] == {"parts": [{"text": "Constitution Layer 1"}]}
    assert body["generationConfig"] == {"thinkingConfig": {"includeThoughts": True}}
    assert body["contents"] == [
        {"role": "user", "parts": [{"text": "Question 1"}]},
        {"role": "model", "parts": [{"text": "Answer 1"}]},
        {"role": "user", "parts": [{"text": "Question 2"}]},
    ]
    assert (
        body["tools"][0]["functionDeclarations"][0]["name"]
        == "query_workspace_knowledge_and_glossary"
    )


@pytest.mark.asyncio
async def test_google_gemini_mode_b_non_streaming_and_sse_streaming_thought_separation() -> None:
    """Verify Mode B `:generateContent` & `:streamGenerateContent` separate `thought: True`."""
    expected_final = "Here is the final synthesis for Gemini Argon:\n\n- Point 1\n- Point 2"
    non_stream_payload: dict[str, Any] = {
        "candidates": [
            {
                "content": {
                    "role": "model",
                    "parts": [
                        {
                            "thought": True,
                            "text": "Evaluating DORA ICT third-party risk constraints...",
                        },
                        {"text": expected_final},
                        {
                            "functionCall": {
                                "name": "query_workspace_knowledge_and_glossary",
                                "args": {"query": "DORA"},
                            }
                        },
                    ],
                }
            }
        ]
    }
    clean, think, tool_calls = parse_gemini_native_response(non_stream_payload)
    assert clean == expected_final
    assert think == "Evaluating DORA ICT third-party risk constraints..."
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "query_workspace_knowledge_and_glossary"

    c_d1, r_d1 = extract_gemini_stream_chunk_deltas(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"thought": True, "text": "Step 1: Deep Argon reasoning. "}]
                    }
                }
            ]
        }
    )
    assert c_d1 == "" and r_d1 == "Step 1: Deep Argon reasoning. "

    c_d2, r_d2 = extract_gemini_stream_chunk_deltas(
        {
            "candidates": [
                {"content": {"parts": [{"text": "Final answer line 1\n    indented_code()"}]}}
            ]
        }
    )
    assert c_d2 == "Final answer line 1\n    indented_code()" and r_d2 == ""

    ep_gemini = ResolvedLiveLlmEndpoint(
        provider="Google Gemini",
        model_name="gemini-argon",
        endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
        auth_mode="api_key",
        api_key="AIzaSy-live-key",  # pragma: allowlist secret
    )

    def _non_stream_handler(req: httpx.Request) -> httpx.Response:
        assert (
            str(req.url)
            == "https://generativelanguage.googleapis.com/v1beta/models/gemini-argon:generateContent"
        )
        assert req.headers.get("x-goog-api-key") == "AIzaSy-live-key"
        req_body = json.loads(req.content.decode("utf-8"))
        assert req_body["generationConfig"]["thinkingConfig"]["includeThoughts"] is True
        return httpx.Response(200, json=non_stream_payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(_non_stream_handler)) as client:
        turn_res = await invoke_provider_chat_async(
            client,
            ep=ep_gemini,
            messages=[
                {"role": "system", "content": "System"},
                {"role": "user", "content": "Analyze DORA"},
            ],
        )
        assert turn_res is not None
        assert turn_res.content == expected_final
        assert turn_res.thinking_text == "Evaluating DORA ICT third-party risk constraints..."
        assert turn_res.tool_calls[0]["name"] == "query_workspace_knowledge_and_glossary"

    sse_chunks = [
        'data: {"candidates": [{"content": {"role": "model", '
        '"parts": [{"thought": true, "text": "Thinking phase 1... "}]}}]}',
        'data: {"candidates": [{"content": {"role": "model", '
        '"parts": [{"thought": true, "text": "Thinking phase 2."}]}}]}',
        'data: {"candidates": [{"content": {"role": "model", '
        '"parts": [{"text": "```python\\ndef argon():\\n"}]}}]}',
        'data: {"candidates": [{"content": {"role": "model", '
        '"parts": [{"text": "    return 42\\n```"}]}}]}',
    ]
    sse_raw = "\n\n".join(sse_chunks) + "\n\n"

    def _stream_handler(req: httpx.Request) -> httpx.Response:
        assert (
            str(req.url)
            == "https://generativelanguage.googleapis.com/v1beta/models/gemini-argon:streamGenerateContent?alt=sse"
        )
        assert req.headers.get("x-goog-api-key") == "AIzaSy-live-key"
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=sse_raw.encode("utf-8"),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_stream_handler)) as s_client:
        events = [
            evt
            async for evt in stream_provider_chat_sse_async(
                s_client,
                ep=ep_gemini,
                messages=[{"role": "user", "content": "Write argon()"}],
            )
        ]
        thinking_evts = [e for e in events if e["event"] == "thinking_delta"]
        token_evts = [e for e in events if e["event"] == "token_delta"]
        completed_evt = events[-1]
        assert len(thinking_evts) == 2
        assert thinking_evts[-1]["data"]["thinking_text"] == "Thinking phase 1... Thinking phase 2."
        assert len(token_evts) == 2
        assert completed_evt["event"] == "turn_completed"
        assert (
            completed_evt["data"]["response_text"] == "```python\ndef argon():\n    return 42\n```"
        )
        assert completed_evt["data"]["thinking_text"] == "Thinking phase 1... Thinking phase 2."


def test_welcome_setup_llm_connection_reports_gemini_mode_b_and_mode_a() -> None:
    """Verify `POST /api/v1/bootstrap/welcome-setup/llm-test` reports Mode B vs Mode A."""
    trace_id = "0" * 32
    res_b = evaluate_welcome_llm_connection_test(
        bs.LlmConnectionTestRequest(
            provider_slug="Google Gemini",
            model_name="gemini-argon",
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta",
            auth_mode="api_key",
            api_key="AIzaSy-test-key",  # pragma: allowlist secret
        ),
        trace_id,
    )
    assert res_b.ok is True
    assert "Mode B" in res_b.message_fr
    assert "gemini-argon:generateContent" in res_b.message_fr

    res_a = evaluate_welcome_llm_connection_test(
        bs.LlmConnectionTestRequest(
            provider_slug="Google Gemini",
            model_name="gemini-argon",
            endpoint_uri="https://generativelanguage.googleapis.com/v1beta/openai",
            auth_mode="api_key",
            api_key="AIzaSy-test-key",  # pragma: allowlist secret
        ),
        trace_id,
    )
    assert res_a.ok is True
    assert "Mode A" in res_a.message_fr
    assert "/v1beta/openai/chat/completions" in res_a.message_fr

    with TestClient(app) as client:
        http_res = client.post(
            "/api/v1/bootstrap/welcome-setup/llm-test",
            json={
                "provider_slug": "Google Gemini",
                "model_name": "gemini-argon",
                "endpoint_uri": "https://generativelanguage.googleapis.com/v1beta",
                "auth_mode": "api_key",
                "api_key": "AIzaSy-test-key",  # pragma: allowlist secret
            },
        )
        assert http_res.status_code == 200
        body = http_res.json()
        assert body["ok"] is True
        assert "Mode B" in body["message_fr"]
        assert "gemini-argon" in body["message_fr"]
