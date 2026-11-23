"""Internal HTTPX Request & Fallback Builders for `BaseHttpxLlmAdapter` (`Story 26.6a`)."""

from __future__ import annotations

import dataclasses
import time
from typing import Any

from orcia_core.orchestration.ai_models_urls import (
    build_gemini_interactions_url,
    build_legacy_local_chat_url,
    is_anthropic_provider,
    normalize_chat_completions_url,
)
from orcia_core.orchestration.llm_gemini_dialect import is_google_gemini_native_provider
from orcia_core.orchestration.llm_gemini_interactions import (
    build_gemini_interactions_request_body,
)
from orcia_core.orchestration.llm_provider_parsing import (
    build_provider_headers,
    build_provider_request_body,
    parse_non_stream_outcome,
)
from orcia_core.orchestration.llm_tool_dialects import format_messages_for_dialect
from orcia_core.orchestration.llm_usage_telemetry import (
    extract_usage_tokens_from_payload,
    resolve_usage_with_fallback,
)
from orcia_core.ports.llm_streaming_port import (
    Finish,
    LlmChatTurnOutcome,
    LlmEndpointConfig,
    LlmStreamRequest,
    Usage,
)


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


def build_gemini_interactions_fallback_request(
    request: LlmStreamRequest,
    *,
    stream: bool,
    use_agent_field: bool = False,
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Build `(url, headers, body)` targeting Google Gemini `/v1beta/interactions`."""
    ep = request.endpoint
    url = build_gemini_interactions_url(ep.endpoint_uri)
    headers = build_provider_headers(ep, url)
    tools = list(request.tools) if (ep.supports_tools and request.tools) else None
    body = build_gemini_interactions_request_body(
        ep.model_name,
        list(request.messages),
        stream=stream,
        tools=tools,
        use_agent_field=use_agent_field,
    )
    return url, headers, body


def build_secondary_model_fallback_request(request: LlmStreamRequest) -> LlmStreamRequest | None:
    """Return a copy of `request` targeting `fallback_model_name` (non-recursive), or `None`."""
    fb = (request.endpoint.fallback_model_name or "").strip()
    if not fb or fb == request.endpoint.model_name.strip():
        return None
    fb_ep = dataclasses.replace(request.endpoint, model_name=fb, fallback_model_name=None)
    return dataclasses.replace(request, endpoint=fb_ep)


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


def build_non_stream_turn_outcome(
    data: Any,
    msgs: list[dict[str, Any]],
    t0: float,
) -> LlmChatTurnOutcome | None:
    """Parse provider JSON response into `LlmChatTurnOutcome` with usage fallback."""
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    if not isinstance(data, dict):
        return None
    clean_content, thinking_text, tool_calls, finish_reason = parse_non_stream_outcome(data)
    if not clean_content and not tool_calls:
        return None
    obs = extract_usage_tokens_from_payload(data)
    in_tok, out_tok, u_src = resolve_usage_with_fallback(
        messages=msgs,
        reply_text=f"{clean_content}\n{thinking_text}",
        observed_input_tokens=obs[0] if obs else 0,
        observed_output_tokens=obs[1] if obs else 0,
        saw_provider_usage=obs is not None,
    )
    return LlmChatTurnOutcome(
        content=clean_content,
        thinking_text=thinking_text,
        latency_ms=elapsed_ms,
        tool_calls=tool_calls,
        input_tokens=in_tok,
        output_tokens=out_tok,
        usage_source=u_src,
        finish_reason=finish_reason,
    )


def build_stream_terminal_events(
    *,
    msgs: list[dict[str, Any]],
    resp_txt: str,
    think_txt: str,
    final_tcs: tuple[dict[str, Any], ...],
    finish_reason: str,
    obs_in_tok: int,
    obs_out_tok: int,
    saw_usage: bool,
    t0: float,
) -> tuple[Usage, Finish]:
    """Build final `(Usage, Finish)` typed stream events."""
    in_tok, out_tok, u_src = resolve_usage_with_fallback(
        messages=msgs,
        reply_text=f"{resp_txt}\n{think_txt}",
        observed_input_tokens=obs_in_tok,
        observed_output_tokens=obs_out_tok,
        saw_provider_usage=saw_usage,
    )
    usage_ev = Usage(input_tokens=in_tok, output_tokens=out_tok, usage_source=u_src)
    finish_ev = Finish(
        finish_reason=finish_reason or ("tool_calls" if final_tcs else "stop"),
        accumulated_text=resp_txt,
        thinking_text=think_txt,
        tool_calls=final_tcs,
        latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
        input_tokens=in_tok,
        output_tokens=out_tok,
        usage_source=u_src,
    )
    return usage_ev, finish_ev


__all__ = [
    "build_effective_request_parts",
    "build_gemini_interactions_fallback_request",
    "build_non_stream_turn_outcome",
    "build_openai_fallback_body",
    "build_secondary_model_fallback_request",
    "build_stream_terminal_events",
    "should_attempt_openai_404_fallback",
]
