"""Agnostic Provider Request/Response Parsing Helpers (`AD-15`, `Story 26.1`)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from orcia_api.routers.assistant_llm_gemini_adapter import (
    _separate_think_tags as extract_thinking_and_clean_content,
)
from orcia_api.routers.assistant_llm_gemini_adapter import (
    build_anthropic_native_request_body,
    build_gemini_native_headers,
    build_gemini_native_request_body,
    extract_gemini_stream_chunk_deltas,
    is_google_gemini_native_provider,
    parse_gemini_native_response,
)
from orcia_core.orchestration.ai_models_urls import is_anthropic_provider


@dataclass(frozen=True, slots=True)
class ResolvedLiveLlmEndpoint:
    """Resolved LLM endpoint configuration for a given cognitive tier."""

    provider: str
    model_name: str
    endpoint_uri: str
    auth_mode: str
    tier: str = "medium"
    api_key: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderChatTurnResponse:
    """Normalized non-streaming response from any LLM provider."""

    content: str
    thinking_text: str
    latency_ms: float
    tool_calls: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    input_tokens: int = 0
    output_tokens: int = 0
    usage_source: str = "estimated"


def build_provider_headers(ep: ResolvedLiveLlmEndpoint, target_url: str) -> dict[str, str]:
    """Construct HTTP headers for OpenAI-compatible, Anthropic Messages, Gemini Native, or Azure."""
    if is_google_gemini_native_provider(target_url, ep.provider):
        return build_gemini_native_headers(ep.api_key)
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if is_anthropic_provider(target_url, ep.provider):
        headers["anthropic-version"] = "2023-06-01"
        if ep.api_key:
            headers["x-api-key"] = ep.api_key
        return headers
    if ep.api_key:
        headers["Authorization"] = f"Bearer {ep.api_key}"
        if "openai.azure.com" in target_url.lower() or "azure" in ep.provider.lower():
            headers["api-key"] = ep.api_key
    return headers


def build_provider_request_body(
    *,
    ep: ResolvedLiveLlmEndpoint,
    target_url: str,
    messages: list[dict[str, Any]],
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build JSON payload for Gemini Native, Anthropic (`/v1/messages`), or OpenAI-compatible."""
    if is_google_gemini_native_provider(target_url, ep.provider):
        return build_gemini_native_request_body(messages, include_thoughts=True, tools=tools)
    if is_anthropic_provider(target_url, ep.provider):
        return build_anthropic_native_request_body(
            ep.model_name, messages, stream=stream, tools=tools
        )
    payload: dict[str, Any] = {"model": ep.model_name, "messages": messages, "stream": stream}
    if stream:
        payload["stream_options"] = {"include_usage": True}
    if tools:
        payload["tools"] = tools
    return payload


def parse_non_stream_json(data: dict[str, Any]) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    """Extract `(clean_content, thinking_text, tool_calls)` from provider JSON."""
    if isinstance(data.get("candidates"), list):
        return parse_gemini_native_response(data)
    if isinstance(data.get("content"), list):
        blocks = [b for b in data["content"] if isinstance(b, dict)]
        texts = "".join(str(b.get("text") or "") for b in blocks if b.get("type") == "text")
        thinks = "\n".join(
            str(b.get("thinking") or "") for b in blocks if b.get("type") == "thinking"
        )
        t_calls = tuple(
            {
                "id": str(b.get("id") or "call_1"),
                "name": str(b.get("name") or ""),
                "arguments": b.get("input") or {},
            }
            for b in blocks
            if b.get("type") == "tool_use"
        )
        clean, think = extract_thinking_and_clean_content(texts, thinks)
        return clean, think, t_calls

    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        msg = choices[0].get("message")
        if isinstance(msg, dict):
            raw_r = str(
                msg.get("reasoning_content") or msg.get("reasoning") or msg.get("thinking") or ""
            )
            tools = tuple(
                {
                    "id": str(tc.get("id") or "call_1"),
                    "name": str((tc.get("function") or {}).get("name") or tc.get("name") or ""),
                    "arguments": (tc.get("function") or {}).get("arguments") or {},
                }
                for tc in (msg.get("tool_calls") or [])
                if isinstance(tc, dict)
            )
            clean, think = extract_thinking_and_clean_content(str(msg.get("content") or ""), raw_r)
            return clean, think, tools

    msg_obj = data.get("message")
    if isinstance(msg_obj, dict):
        raw_r = str(
            msg_obj.get("reasoning_content")
            or msg_obj.get("thinking")
            or msg_obj.get("reasoning")
            or ""
        )
        clean, think = extract_thinking_and_clean_content(str(msg_obj.get("content") or ""), raw_r)
        return clean, think, ()
    return "", "", ()


def extract_stream_chunk_deltas(chunk: dict[str, Any]) -> tuple[str, str]:
    """Return `(content_delta, reasoning_delta)` from a single parsed SSE/NDJSON chunk."""
    if isinstance(chunk.get("candidates"), list):
        return extract_gemini_stream_chunk_deltas(chunk)
    if chunk.get("type") == "content_block_delta" and isinstance(chunk.get("delta"), dict):
        d = chunk["delta"]
        if d.get("type") == "text_delta":
            return str(d.get("text") or ""), ""
        if d.get("type") == "thinking_delta":
            return "", str(d.get("thinking") or "")
    choices = chunk.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        delta = choices[0].get("delta")
        if isinstance(delta, dict):
            r = delta.get("reasoning_content") or delta.get("reasoning") or delta.get("thinking")
            return str(delta.get("content") or ""), str(r or "")
    msg = chunk.get("message")
    if isinstance(msg, dict):
        r_msg = msg.get("thinking") or msg.get("reasoning_content") or ""
        return str(msg.get("content") or ""), str(r_msg)
    return "", ""


def make_thinking_evt(delta: str, acc: list[str], t0: float) -> dict[str, Any]:
    """Build normalized SSE `thinking_delta` payload."""
    return {
        "event": "thinking_delta",
        "data": {
            "step_code": "NODE_5_SINGLE_STREAM_LLM",
            "delta": delta,
            "thinking_text": "".join(acc),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        },
    }
