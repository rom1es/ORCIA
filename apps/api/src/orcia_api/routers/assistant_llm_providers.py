"""Agnostic Async LLM Provider Adapters, DNS-Pinned SSRF Guard & True SSE Parser (`AD-15`)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from orcia_api.routers._assistant_llm_provider_parsing import (
    ProviderChatTurnResponse,
    ResolvedLiveLlmEndpoint,
    build_provider_headers,
    build_provider_request_body,
    extract_stream_chunk_deltas,
    make_thinking_evt,
    parse_non_stream_json,
)
from orcia_api.routers._assistant_usage_telemetry import (
    extract_usage_tokens_from_payload,
    resolve_usage_with_fallback,
)
from orcia_api.routers.assistant_llm_gemini_adapter import (
    _separate_think_tags as _separate_think_tags,
)
from orcia_api.routers.assistant_llm_gemini_adapter import is_google_gemini_native_provider
from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration.ai_models_pinned_http import prepare_pinned_http_request
from orcia_core.orchestration.ai_models_urls import (
    build_legacy_local_chat_url as build_legacy_local_chat_url,
)
from orcia_core.orchestration.ai_models_urls import is_anthropic_provider as is_anthropic_provider
from orcia_core.orchestration.ai_models_urls import (
    normalize_chat_completions_url as normalize_chat_completions_url,
)
from orcia_core.orchestration.ssrf_guard import is_safe_llm_endpoint_url

extract_thinking_and_clean_content = _separate_think_tags
_extract_stream_chunk_deltas = extract_stream_chunk_deltas
_parse_non_stream_json = parse_non_stream_json
logger = get_logger("orcia.assistant.llm")


def _log_provider_error(
    event: str, exc: Exception, ep: ResolvedLiveLlmEndpoint, target_url: str, t0: float
) -> None:
    kw: dict[str, Any] = {
        "endpoint": target_url,
        "model": ep.model_name,
        "provider": ep.provider,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "error_type": type(exc).__name__,
        "error": scrub_sensitive_text(str(exc)),
    }
    if isinstance(exc, httpx.HTTPStatusError):
        kw["status_code"] = exc.response.status_code
    logger.warning(event, **kw)


async def invoke_provider_chat_async(
    http_client: httpx.AsyncClient,
    *,
    ep: ResolvedLiveLlmEndpoint,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> ProviderChatTurnResponse | None:
    """Execute an async chat completion call with DNS pinning and legacy 404 fallback."""
    target_url = normalize_chat_completions_url(
        ep.endpoint_uri, ep.provider, model_name=ep.model_name, stream=False
    )
    headers = build_provider_headers(ep, target_url)
    body = build_provider_request_body(
        ep=ep, target_url=target_url, messages=messages, stream=False, tools=tools
    )
    t0 = time.perf_counter()
    try:
        p_url, p_headers, ext = await prepare_pinned_http_request(http_client, target_url, headers)
        resp = await http_client.post(p_url, json=body, headers=p_headers, extensions=ext)
        if (
            resp.status_code == 404
            and not is_anthropic_provider(target_url, ep.provider)
            and not is_google_gemini_native_provider(target_url, ep.provider)
        ):
            fallback_url = build_legacy_local_chat_url(ep.endpoint_uri)
            if fallback_url != target_url:
                fb_url, fb_headers, fb_ext = await prepare_pinned_http_request(
                    http_client, fallback_url, headers
                )
                resp = await http_client.post(
                    fb_url,
                    json={"model": ep.model_name, "messages": messages, "stream": False},
                    headers=fb_headers,
                    extensions=fb_ext,
                )
        resp.raise_for_status()
        data = resp.json()
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if not isinstance(data, dict):
            return None
        clean_content, thinking_text, tool_calls = parse_non_stream_json(data)
        if not clean_content and not tool_calls:
            return None
        obs = extract_usage_tokens_from_payload(data)
        in_tok, out_tok, u_src = resolve_usage_with_fallback(
            messages=messages,
            reply_text=f"{clean_content}\n{thinking_text}",
            observed_input_tokens=obs[0] if obs else 0,
            observed_output_tokens=obs[1] if obs else 0,
            saw_provider_usage=obs is not None,
        )
        return ProviderChatTurnResponse(
            clean_content, thinking_text, elapsed_ms, tool_calls, in_tok, out_tok, u_src
        )
    except httpx.HTTPStatusError as exc:
        _log_provider_error("llm_provider_http_status_error", exc, ep, target_url, t0)
        return None
    except Exception as exc:
        _log_provider_error("llm_provider_invocation_failed", exc, ep, target_url, t0)
        return None


async def stream_provider_chat_sse_async(
    http_client: httpx.AsyncClient,
    *,
    ep: ResolvedLiveLlmEndpoint,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """True async HTTP SSE streaming (`resp.aiter_lines()`) with DNS pinning."""
    target_url = normalize_chat_completions_url(
        ep.endpoint_uri, ep.provider, model_name=ep.model_name, stream=True
    )
    headers = build_provider_headers(ep, target_url)
    body = build_provider_request_body(
        ep=ep, target_url=target_url, messages=messages, stream=True, tools=tools
    )
    t0 = time.perf_counter()
    acc_content: list[str] = []
    acc_thinking: list[str] = []
    in_think = False
    saw_usage, obs_in_tok, obs_out_tok = False, 0, 0
    try:
        p_url, p_headers, ext = await prepare_pinned_http_request(http_client, target_url, headers)
        async with http_client.stream(
            "POST", p_url, json=body, headers=p_headers, extensions=ext
        ) as resp:
            resp.raise_for_status()
            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if not line or line.startswith((":", "event:")):
                    continue
                payload_str = line[5:].strip() if line.startswith("data:") else line
                if payload_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(payload_str)
                except json.JSONDecodeError:
                    continue
                if not isinstance(chunk, dict):
                    continue
                if (u_tok := extract_usage_tokens_from_payload(chunk)) is not None:
                    saw_usage = True
                    obs_in_tok = u_tok[0] if u_tok[0] > 0 else obs_in_tok
                    obs_out_tok = u_tok[1] if u_tok[1] > 0 else obs_out_tok
                c_delta, r_delta = extract_stream_chunk_deltas(chunk)
                if r_delta:
                    acc_thinking.append(r_delta)
                    yield make_thinking_evt(r_delta, acc_thinking, t0)
                if c_delta:
                    if "<think>" in c_delta:
                        in_think, c_delta = True, c_delta.replace("<think>", "")
                    if in_think:
                        if "</think>" in c_delta:
                            t_part, _, rest = c_delta.partition("</think>")
                            if t_part:
                                acc_thinking.append(t_part)
                            in_think, c_delta = False, rest
                        else:
                            acc_thinking.append(c_delta)
                            yield make_thinking_evt(c_delta, acc_thinking, t0)
                            continue
                    if c_delta:
                        acc_content.append(c_delta)
                        yield {
                            "event": "token_delta",
                            "data": {"delta": c_delta, "accumulated_text": "".join(acc_content)},
                        }
        resp_txt, think_txt = "".join(acc_content), "".join(acc_thinking)
        in_tok, out_tok, u_src = resolve_usage_with_fallback(
            messages=messages,
            reply_text=f"{resp_txt}\n{think_txt}",
            observed_input_tokens=obs_in_tok,
            observed_output_tokens=obs_out_tok,
            saw_provider_usage=saw_usage,
        )
        yield {
            "event": "turn_completed",
            "data": {
                "response_text": resp_txt,
                "thinking_text": think_txt,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "usage_source": u_src,
            },
        }
    except httpx.HTTPStatusError as exc:
        _log_provider_error("llm_provider_stream_http_status_error", exc, ep, target_url, t0)
    except Exception as exc:
        _log_provider_error("llm_provider_stream_failed", exc, ep, target_url, t0)


__all__ = [
    "ProviderChatTurnResponse",
    "ResolvedLiveLlmEndpoint",
    "build_legacy_local_chat_url",
    "build_provider_headers",
    "build_provider_request_body",
    "extract_thinking_and_clean_content",
    "invoke_provider_chat_async",
    "is_anthropic_provider",
    "is_safe_llm_endpoint_url",
    "normalize_chat_completions_url",
    "stream_provider_chat_sse_async",
]
