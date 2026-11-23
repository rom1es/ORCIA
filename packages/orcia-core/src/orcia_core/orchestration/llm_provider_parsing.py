"""Agnostic Provider Request/Response Parsing Helpers (`AD-15`, `Story 26.2`, `Story 26.6a`)."""

from __future__ import annotations

import time
from typing import Any

from orcia_core.orchestration.ai_models_urls import (
    is_anthropic_provider,
    is_gemini_interactions_url,
)
from orcia_core.orchestration.llm_gemini_dialect import (
    build_anthropic_native_request_body,
    build_gemini_native_headers,
    build_gemini_native_request_body,
    extract_gemini_stream_chunk_deltas,
    is_google_gemini_native_provider,
    parse_gemini_native_response,
    separate_think_tags,
)
from orcia_core.orchestration.llm_gemini_interactions import (
    build_gemini_interactions_request_body,
    extract_gemini_interactions_stream_deltas,
    parse_gemini_interactions_response,
)
from orcia_core.orchestration.llm_tool_dialects import (
    format_messages_for_dialect,
    parse_json_arguments,
)
from orcia_core.ports.llm_streaming_port import LlmChatTurnOutcome, LlmEndpointConfig

ResolvedLiveLlmEndpoint = LlmEndpointConfig
ProviderChatTurnResponse = LlmChatTurnOutcome
extract_thinking_and_clean_content = separate_think_tags


def build_provider_headers(ep: LlmEndpointConfig, target_url: str) -> dict[str, str]:
    """Construct HTTP headers for OpenAI-compatible, Anthropic Messages, Gemini Native, or Azure."""
    if is_gemini_interactions_url(target_url) or is_google_gemini_native_provider(
        target_url, ep.provider
    ):
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
    ep: LlmEndpointConfig,
    target_url: str,
    messages: list[dict[str, Any]],
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    include_thoughts: bool = True,
) -> dict[str, Any]:
    """Build JSON payload for Gemini Interactions/Native, Anthropic, or OpenAI-compatible."""
    if is_gemini_interactions_url(target_url):
        return build_gemini_interactions_request_body(
            ep.model_name, messages, stream=stream, tools=tools
        )
    if is_google_gemini_native_provider(target_url, ep.provider):
        return build_gemini_native_request_body(
            messages, include_thoughts=include_thoughts, tools=tools
        )
    if is_anthropic_provider(target_url, ep.provider):
        return build_anthropic_native_request_body(
            ep.model_name, messages, stream=stream, tools=tools, tool_choice=tool_choice
        )
    formatted_msgs = format_messages_for_dialect(messages, dialect="openai_compatible")
    payload: dict[str, Any] = {
        "model": ep.model_name,
        "messages": formatted_msgs,
        "stream": stream,
    }
    if stream:
        payload["stream_options"] = {"include_usage": True}
    if tools:
        payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
    return payload


def parse_non_stream_outcome(
    data: dict[str, Any],
) -> tuple[str, str, tuple[dict[str, Any], ...], str]:
    """Extract `(clean_content, thinking_text, tool_calls, finish_reason)` from provider JSON."""
    if isinstance(data.get("candidates"), list):
        clean, think, t_calls = parse_gemini_native_response(data)
        c0 = (
            data["candidates"][0]
            if data["candidates"] and isinstance(data["candidates"][0], dict)
            else {}
        )
        return clean, think, t_calls, str(c0.get("finishReason") or "stop")
    if "candidates" not in data and (
        any(k in data for k in ("outputs", "steps", "interaction", "output_text"))
        or data.get("object") == "interaction"
    ):
        clean, think, t_calls = parse_gemini_interactions_response(data)
        return clean, think, t_calls, "tool_calls" if t_calls else "stop"
    if isinstance(data.get("content"), list):
        blocks = [b for b in data["content"] if isinstance(b, dict)]
        texts = "".join(str(b.get("text") or "") for b in blocks if b.get("type") == "text")
        thinks = "\n".join(
            str(b.get("thinking") or "") for b in blocks if b.get("type") == "thinking"
        )
        t_calls = tuple(
            {
                "id": str(b.get("id") or f"toolu_{idx + 1}"),
                "name": str(b.get("name") or ""),
                "arguments": parse_json_arguments(b.get("input")),
            }
            for idx, b in enumerate(blocks)
            if b.get("type") == "tool_use"
        )
        clean, think = separate_think_tags(texts, thinks)
        stop_reason = str(data.get("stop_reason") or ("tool_use" if t_calls else "stop"))
        return clean, think, t_calls, stop_reason

    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        c0 = choices[0]
        msg = c0.get("message")
        if isinstance(msg, dict):
            raw_r = str(
                msg.get("reasoning_content") or msg.get("reasoning") or msg.get("thinking") or ""
            )
            tools = tuple(
                {
                    "id": str(tc.get("id") or f"call_{idx + 1}"),
                    "name": str((tc.get("function") or {}).get("name") or tc.get("name") or ""),
                    "arguments": parse_json_arguments((tc.get("function") or {}).get("arguments")),
                }
                for idx, tc in enumerate(msg.get("tool_calls") or ())
                if isinstance(tc, dict)
            )
            clean, think = separate_think_tags(str(msg.get("content") or ""), raw_r)
            fr = str(c0.get("finish_reason") or ("tool_calls" if tools else "stop"))
            return clean, think, tools, fr

    msg_obj = data.get("message")
    if isinstance(msg_obj, dict):
        raw_r = str(
            msg_obj.get("reasoning_content")
            or msg_obj.get("thinking")
            or msg_obj.get("reasoning")
            or ""
        )
        clean, think = separate_think_tags(str(msg_obj.get("content") or ""), raw_r)
        return clean, think, (), str(data.get("done_reason") or "stop")
    return "", "", (), "stop"


def parse_non_stream_json(data: dict[str, Any]) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    """Extract `(clean_content, thinking_text, tool_calls)` from provider JSON."""
    clean, think, t_calls, _ = parse_non_stream_outcome(data)
    return clean, think, t_calls


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
    if "delta" in chunk or str(chunk.get("event_type") or "").startswith(
        ("content.", "step.", "interaction.")
    ):
        return extract_gemini_interactions_stream_deltas(chunk)
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
