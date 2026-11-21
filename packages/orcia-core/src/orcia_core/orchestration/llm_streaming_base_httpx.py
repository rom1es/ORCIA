"""Base HTTPX Async Streaming & Non-Streaming Client with DNS-Pinned SSRF Guard (`Story 26.2`)."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Callable

import httpx

from orcia_core.orchestration.ai_models_errors import UnsafeLlmEndpointUrlError
from orcia_core.orchestration.ai_models_pinned_http import prepare_pinned_http_request
from orcia_core.orchestration.ai_models_urls import (
    build_legacy_local_chat_url,
    is_anthropic_provider,
    normalize_chat_completions_url,
)
from orcia_core.orchestration.llm_gemini_dialect import is_google_gemini_native_provider
from orcia_core.orchestration.llm_provider_parsing import (
    build_provider_headers,
    build_provider_request_body,
    extract_stream_chunk_deltas,
    parse_non_stream_json,
)
from orcia_core.orchestration.llm_streaming_sse_utils import log_provider_error
from orcia_core.orchestration.llm_usage_telemetry import (
    extract_usage_tokens_from_payload,
    resolve_usage_with_fallback,
)
from orcia_core.ports.llm_streaming_port import (
    LlmChatTurnOutcome,
    LlmEndpointConfig,
    LlmStreamDelta,
    LlmStreamingPort,
    LlmStreamRequest,
)

LogErrorFn = Callable[[str, Exception, LlmEndpointConfig, str, float], None]


class BaseHttpxLlmAdapter(LlmStreamingPort):
    """Shared async HTTPX chat & SSE streaming adapter with DNS-pinned SSRF protection."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        allow_legacy_fallback: bool,
        log_error_fn: LogErrorFn = log_provider_error,
    ) -> None:
        self._client = http_client
        self._allow_legacy_fallback = allow_legacy_fallback
        self._log_error = log_error_fn

    async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
        """Execute async non-streaming chat completion with DNS pinning."""
        ep = request.endpoint
        msgs = list(request.messages)
        tools = list(request.tools) or None
        target_url = normalize_chat_completions_url(
            ep.endpoint_uri,
            ep.provider,
            protocol_mode=ep.protocol_mode,
            model_name=ep.model_name,
            stream=False,
        )
        headers = build_provider_headers(ep, target_url)
        body = build_provider_request_body(
            ep=ep,
            target_url=target_url,
            messages=msgs,
            stream=False,
            tools=tools,
            include_thoughts=request.include_thoughts,
        )
        t0 = time.perf_counter()
        try:
            p_url, p_headers, ext = await prepare_pinned_http_request(
                self._client, target_url, headers
            )
            resp = await self._client.post(p_url, json=body, headers=p_headers, extensions=ext)
            if (
                self._allow_legacy_fallback
                and resp.status_code == 404
                and not is_anthropic_provider(target_url, ep.provider)
                and not is_google_gemini_native_provider(target_url, ep.provider)
            ):
                fallback_url = build_legacy_local_chat_url(ep.endpoint_uri)
                if fallback_url != target_url:
                    fb_url, fb_hdrs, fb_ext = await prepare_pinned_http_request(
                        self._client, fallback_url, headers
                    )
                    resp = await self._client.post(
                        fb_url,
                        json={"model": ep.model_name, "messages": msgs, "stream": False},
                        headers=fb_hdrs,
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
            )
        except UnsafeLlmEndpointUrlError:
            raise
        except httpx.HTTPStatusError as exc:
            self._log_error("llm_provider_http_status_error", exc, ep, target_url, t0)
            return None
        except Exception as exc:
            self._log_error("llm_provider_invocation_failed", exc, ep, target_url, t0)
            return None

    async def stream_chat_sse(self, request: LlmStreamRequest) -> AsyncIterator[LlmStreamDelta]:
        """Stream true async HTTP SSE deltas (`resp.aiter_lines()`) with DNS pinning."""
        ep = request.endpoint
        msgs = list(request.messages)
        tools = list(request.tools) or None
        target_url = normalize_chat_completions_url(
            ep.endpoint_uri,
            ep.provider,
            protocol_mode=ep.protocol_mode,
            model_name=ep.model_name,
            stream=True,
        )
        headers = build_provider_headers(ep, target_url)
        body = build_provider_request_body(
            ep=ep,
            target_url=target_url,
            messages=msgs,
            stream=True,
            tools=tools,
            include_thoughts=request.include_thoughts,
        )
        t0 = time.perf_counter()
        acc_content: list[str] = []
        acc_thinking: list[str] = []
        in_think = False
        saw_usage, obs_in_tok, obs_out_tok = False, 0, 0
        try:
            p_url, p_headers, ext = await prepare_pinned_http_request(
                self._client, target_url, headers
            )
            async with self._client.stream(
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
                        yield LlmStreamDelta(
                            event="thinking_delta",
                            delta=r_delta,
                            thinking_text="".join(acc_thinking),
                            elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                        )
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
                                yield LlmStreamDelta(
                                    event="thinking_delta",
                                    delta=c_delta,
                                    thinking_text="".join(acc_thinking),
                                    elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                                )
                                continue
                        if c_delta:
                            acc_content.append(c_delta)
                            yield LlmStreamDelta(
                                event="token_delta",
                                delta=c_delta,
                                accumulated_text="".join(acc_content),
                            )
            resp_txt, think_txt = "".join(acc_content), "".join(acc_thinking)
            in_tok, out_tok, u_src = resolve_usage_with_fallback(
                messages=msgs,
                reply_text=f"{resp_txt}\n{think_txt}",
                observed_input_tokens=obs_in_tok,
                observed_output_tokens=obs_out_tok,
                saw_provider_usage=saw_usage,
            )
            yield LlmStreamDelta(
                event="turn_completed",
                accumulated_text=resp_txt,
                thinking_text=think_txt,
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                input_tokens=in_tok,
                output_tokens=out_tok,
                usage_source=u_src,
            )
        except UnsafeLlmEndpointUrlError:
            raise
        except httpx.HTTPStatusError as exc:
            self._log_error("llm_provider_stream_http_status_error", exc, ep, target_url, t0)
        except Exception as exc:
            self._log_error("llm_provider_stream_failed", exc, ep, target_url, t0)
