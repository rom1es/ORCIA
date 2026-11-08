"""Agnostic Async LLM Provider Adapters, SSRF Guard & True SSE Parser (`AD-15`, `AD-19`)."""

from __future__ import annotations

import ipaddress
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from orcia_api.routers.assistant_llm_gemini_adapter import (
    _separate_think_tags as _separate_think_tags,
)
from orcia_api.routers.assistant_llm_gemini_adapter import (
    build_gemini_native_headers,
    build_gemini_native_request_body,
    build_gemini_native_url,
    extract_gemini_stream_chunk_deltas,
    is_google_gemini_native_provider,
    parse_gemini_native_response,
)
from orcia_core.observability.logging import get_logger

extract_thinking_and_clean_content = _separate_think_tags

logger = get_logger("orcia.assistant.llm")

_BLOCKED_HOSTS: frozenset[str] = frozenset({"169.254.169.254", "100.100.100.200", "metadata.google.internal", "metadata.goog", "metadata.azure.com", "instance-data", "example.com", "api.example.com", "mock-llm", "api.anthropic.local", "api.openai.local", "api.google.local", "api.mistral.local"})  # fmt: skip  # noqa: E501


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


def is_safe_llm_endpoint_url(url: str) -> bool:
    """Validate `url` against Cloud Metadata SSRF while permitting `.local`/`.internal`."""
    raw = (url or "").strip()
    if not raw:
        return False
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").strip().lower().rstrip(".")
    if not host or host in _BLOCKED_HOSTS or host.endswith((".example.com", ".google.internal")):
        return False
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_link_local or ip.is_unspecified or ip.is_multicast:
            return False
    except ValueError:
        pass
    return True


def is_anthropic_provider(endpoint_uri: str, provider: str = "") -> bool:
    """Return True if the endpoint targets Anthropic Messages API (`/v1/messages`)."""
    u, p = endpoint_uri.strip().lower().rstrip("/"), provider.strip().lower()
    return (
        u.endswith("/messages")
        or "anthropic.com" in u
        or ("anthropic" in p and not u.endswith("/chat/completions"))
    )


def normalize_chat_completions_url(
    endpoint_uri: str,
    provider: str = "",
    *,
    model_name: str = "gemini-argon",
    stream: bool = False,
) -> str:
    """Normalize provider base URL to its canonical chat/messages/generateContent endpoint."""
    base = endpoint_uri.strip().rstrip("/")
    if is_anthropic_provider(base, provider):
        if base.endswith("/messages"):
            return base
        return f"{base}/messages" if base.endswith("/v1") else f"{base}/v1/messages"
    if is_google_gemini_native_provider(base, provider):
        return build_gemini_native_url(base, model_name, stream=stream)
    if base.endswith(("/chat/completions", "/api/chat", "/messages")):
        return base
    if base.endswith(("/v1beta/openai", "/openai", "/v1")):
        return f"{base}/chat/completions"
    if base.endswith("/api"):
        return f"{base[:-4].rstrip('/')}/v1/chat/completions"
    return f"{base}/v1/chat/completions"


def build_legacy_local_chat_url(endpoint_uri: str) -> str:
    """Build fallback `/api/chat` URL for legacy local servers returning 404 on `/v1/chat`."""
    clean = endpoint_uri.strip().rstrip("/")
    for suffix in ("/v1/chat/completions", "/chat/completions", "/v1", "/api/chat", "/api"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)].rstrip("/")
            break
    return f"{clean}/api/chat"


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
        sys_blocks = [str(m.get("content") or "") for m in messages if m.get("role") == "system"]
        conv_msgs = [
            {
                "role": "assistant" if m.get("role") == "assistant" else "user",
                "content": str(m.get("content") or ""),
            }
            for m in messages
            if m.get("role") != "system"
        ]
        body: dict[str, Any] = {
            "model": ep.model_name,
            "max_tokens": 4096,
            "messages": conv_msgs or [{"role": "user", "content": "Hello"}],
            "stream": stream,
        }
        if sys_blocks:
            body["system"] = "\n\n".join(sys_blocks)
        if tools:
            body["tools"] = [
                {
                    "name": t.get("function", {}).get("name", "tool"),
                    "description": t.get("function", {}).get("description", ""),
                    "input_schema": t.get("function", {}).get("parameters", {"type": "object"}),
                }
                for t in tools
                if isinstance(t, dict)
            ]
        return body
    payload: dict[str, Any] = {"model": ep.model_name, "messages": messages, "stream": stream}
    if tools:
        payload["tools"] = tools
    return payload


def _parse_non_stream_json(data: dict[str, Any]) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    """Extract `(clean_content, thinking_text, tool_calls)` from provider JSON."""
    if isinstance(data.get("candidates"), list):
        return parse_gemini_native_response(data)
    if isinstance(data.get("content"), list):
        blocks = [b for b in data["content"] if isinstance(b, dict)]
        texts = "".join(str(b.get("text") or "") for b in blocks if b.get("type") == "text")
        thinks = "\n".join(str(b.get("thinking") or "") for b in blocks if b.get("type") == "thinking")  # fmt: skip  # noqa: E501
        t_calls = tuple(
            {"id": str(b.get("id") or "call_1"), "name": str(b.get("name") or ""), "arguments": b.get("input") or {}}  # noqa: E501
            for b in blocks if b.get("type") == "tool_use"
        )  # fmt: skip
        clean, think = extract_thinking_and_clean_content(texts, thinks)
        return clean, think, t_calls

    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        msg = choices[0].get("message")
        if isinstance(msg, dict):
            raw_r = str(msg.get("reasoning_content") or msg.get("reasoning") or msg.get("thinking") or "")  # fmt: skip  # noqa: E501
            tools = tuple(
                {"id": str(tc.get("id") or "call_1"), "name": str((tc.get("function") or {}).get("name") or tc.get("name") or ""), "arguments": (tc.get("function") or {}).get("arguments") or {}}  # noqa: E501
                for tc in (msg.get("tool_calls") or []) if isinstance(tc, dict)
            )  # fmt: skip
            clean, think = extract_thinking_and_clean_content(str(msg.get("content") or ""), raw_r)
            return clean, think, tools

    msg_obj = data.get("message")
    if isinstance(msg_obj, dict):
        raw_r = str(msg_obj.get("reasoning_content") or msg_obj.get("thinking") or msg_obj.get("reasoning") or "")  # fmt: skip  # noqa: E501
        clean, think = extract_thinking_and_clean_content(str(msg_obj.get("content") or ""), raw_r)
        return clean, think, ()
    return "", "", ()


def _log_provider_error(
    event: str, exc: Exception, ep: ResolvedLiveLlmEndpoint, target_url: str, t0: float
) -> None:
    kw: dict[str, Any] = {"endpoint": target_url, "model": ep.model_name, "provider": ep.provider, "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2), "error_type": type(exc).__name__}  # fmt: skip  # noqa: E501
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
    """Execute an async chat completion call with structured logging and legacy 404 fallback."""
    target_url = normalize_chat_completions_url(
        ep.endpoint_uri, ep.provider, model_name=ep.model_name, stream=False
    )
    headers = build_provider_headers(ep, target_url)
    body = build_provider_request_body(
        ep=ep, target_url=target_url, messages=messages, stream=False, tools=tools
    )
    t0 = time.perf_counter()
    try:
        resp = await http_client.post(target_url, json=body, headers=headers)
        if (
            resp.status_code == 404
            and not is_anthropic_provider(target_url, ep.provider)
            and not is_google_gemini_native_provider(target_url, ep.provider)
        ):
            fallback_url = build_legacy_local_chat_url(ep.endpoint_uri)
            if fallback_url != target_url:
                resp = await http_client.post(
                    fallback_url,
                    json={"model": ep.model_name, "messages": messages, "stream": False},
                    headers=headers,
                )
        resp.raise_for_status()
        data = resp.json()
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if not isinstance(data, dict):
            return None
        clean_content, thinking_text, tool_calls = _parse_non_stream_json(data)
        if not clean_content and not tool_calls:
            return None
        return ProviderChatTurnResponse(clean_content, thinking_text, elapsed_ms, tool_calls)
    except httpx.HTTPStatusError as exc:
        _log_provider_error("llm_provider_http_status_error", exc, ep, target_url, t0)
        return None
    except Exception as exc:
        _log_provider_error("llm_provider_invocation_failed", exc, ep, target_url, t0)
        return None


def _extract_stream_chunk_deltas(chunk: dict[str, Any]) -> tuple[str, str]:
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
        return str(msg.get("content") or ""), str(msg.get("thinking") or msg.get("reasoning_content") or "")  # fmt: skip  # noqa: E501
    return "", ""


def _make_thinking_evt(delta: str, acc: list[str], t0: float) -> dict[str, Any]:
    return {
        "event": "thinking_delta",
        "data": {
            "step_code": "NODE_5_SINGLE_STREAM_LLM",
            "delta": delta,
            "thinking_text": "".join(acc),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        },
    }


async def stream_provider_chat_sse_async(
    http_client: httpx.AsyncClient,
    *,
    ep: ResolvedLiveLlmEndpoint,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """True async HTTP SSE streaming (`resp.aiter_lines()`) preserving `\n` and code indentation."""
    target_url = normalize_chat_completions_url(
        ep.endpoint_uri, ep.provider, model_name=ep.model_name, stream=True
    )
    headers = build_provider_headers(ep, target_url)
    body = build_provider_request_body(
        ep=ep, target_url=target_url, messages=messages, stream=True, tools=tools
    )
    t0 = time.perf_counter()
    acc_content, acc_thinking, in_think = [], [], False
    try:
        async with http_client.stream("POST", target_url, json=body, headers=headers) as resp:
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
                c_delta, r_delta = _extract_stream_chunk_deltas(chunk)
                if r_delta:
                    acc_thinking.append(r_delta)
                    yield _make_thinking_evt(r_delta, acc_thinking, t0)
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
                            yield _make_thinking_evt(c_delta, acc_thinking, t0)
                            continue
                    if c_delta:
                        acc_content.append(c_delta)
                        yield {
                            "event": "token_delta",
                            "data": {"delta": c_delta, "accumulated_text": "".join(acc_content)},
                        }
        yield {
            "event": "turn_completed",
            "data": {
                "response_text": "".join(acc_content),
                "thinking_text": "".join(acc_thinking),
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            },
        }
    except httpx.HTTPStatusError as exc:
        _log_provider_error("llm_provider_stream_http_status_error", exc, ep, target_url, t0)
    except Exception as exc:
        _log_provider_error("llm_provider_stream_failed", exc, ep, target_url, t0)
