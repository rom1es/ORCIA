"""Internal HTTPX Request & Fallback Builders for `BaseHttpxLlmAdapter` (`Story 26.6a`)."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration.ai_models_urls import (
    build_legacy_local_chat_url,
    is_anthropic_provider,
    normalize_chat_completions_url,
)
from orcia_core.orchestration.llm_gemini_dialect import is_google_gemini_native_provider
from orcia_core.orchestration.llm_provider_parsing import (
    build_provider_headers,
    build_provider_request_body,
)
from orcia_core.orchestration.llm_tool_dialects import format_messages_for_dialect
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig, LlmStreamRequest


def build_effective_request_parts(
    request: LlmStreamRequest,
    *,
    stream: bool,
) -> tuple[str, dict[str, str], dict[str, Any], list[dict[str, Any]]]:
    """Build target URL, headers, and JSON body enforcing `ep.supports_tools` (`D5`)."""
    ep = request.endpoint
    msgs = list(request.messages)
    tools = list(request.tools) if (ep.supports_tools and request.tools) else None
    tool_choice = request.tool_choice if tools else None
    target_url = normalize_chat_completions_url(
        ep.endpoint_uri,
        ep.provider,
        protocol_mode=ep.protocol_mode,
        model_name=ep.model_name,
        stream=stream,
    )
    headers = build_provider_headers(ep, target_url)
    body = build_provider_request_body(
        ep=ep,
        target_url=target_url,
        messages=msgs,
        stream=stream,
        tools=tools,
        tool_choice=tool_choice,
        include_thoughts=request.include_thoughts,
    )
    return target_url, headers, body, msgs


def should_attempt_openai_404_fallback(
    *,
    allow_legacy_fallback: bool,
    status_code: int,
    ep: LlmEndpointConfig,
    target_url: str,
) -> str | None:
    """Return distinct fallback URL when OpenAI-compatible 404 legacy fallback applies."""
    if not allow_legacy_fallback or status_code != 404:
        return None
    if is_anthropic_provider(target_url, ep.provider) or is_google_gemini_native_provider(
        target_url, ep.provider
    ):
        return None
    fallback_url = build_legacy_local_chat_url(ep.endpoint_uri)
    return fallback_url if fallback_url != target_url else None


def build_openai_fallback_body(
    request: LlmStreamRequest,
    *,
    stream: bool,
) -> dict[str, Any]:
    """Build 404 fallback JSON payload preserving `tools` and `tool_choice` (`H-04`, `D5`)."""
    ep = request.endpoint
    formatted = format_messages_for_dialect(list(request.messages), dialect="openai_compatible")
    body: dict[str, Any] = {
        "model": ep.model_name,
        "messages": formatted,
        "stream": stream,
    }
    if ep.supports_tools and request.tools:
        body["tools"] = list(request.tools)
        if request.tool_choice is not None:
            body["tool_choice"] = request.tool_choice
    return body


__all__ = [
    "build_effective_request_parts",
    "build_openai_fallback_body",
    "should_attempt_openai_404_fallback",
]
