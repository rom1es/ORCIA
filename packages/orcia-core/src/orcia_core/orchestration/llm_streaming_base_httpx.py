"""Base HTTPX Async Streaming & Non-Streaming Client with SSRF Guard (`Story 26.2`, `26.6a`)."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable

import httpx

from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration._llm_streaming_http_helpers import (
    build_effective_request_parts,
    build_openai_fallback_body,
    should_attempt_openai_404_fallback,
)
from orcia_core.orchestration.ai_models_errors import UnsafeLlmEndpointUrlError
from orcia_core.orchestration.ai_models_pinned_http import prepare_pinned_http_request
from orcia_core.orchestration.llm_provider_parsing import (
    extract_stream_chunk_deltas,
    parse_non_stream_outcome,
)
from orcia_core.orchestration.llm_streaming_sse_utils import (
    emit_chunk_deltas,
    iter_lines_with_idle_timeout,
    log_provider_error,
    resolve_inter_chunk_timeout_s,
    resolve_stream_retry_base_delay_s,
    stream_error_code_for_status,
)
from orcia_core.orchestration.llm_tool_dialects import ToolCallAccumulator
from orcia_core.orchestration.llm_usage_telemetry import (
    extract_usage_tokens_from_payload,
    resolve_usage_with_fallback,
)
from orcia_core.ports.llm_streaming_port import (
    Finish,
    LlmChatTurnOutcome,
    LlmEndpointConfig,
    LlmStreamDelta,
    LlmStreamingPort,
    LlmStreamRequest,
    LlmTypedStreamEvent,
    StreamErrorEvent,
    Usage,
    delta_to_typed_event,
    typed_event_to_delta,
)

LogErrorFn = Callable[[str, Exception, LlmEndpointConfig, str, float], None]
_RETRYABLE_STREAM_STATUSES = frozenset({429, 502, 503})
_logger = get_logger("orcia.assistant.llm")


class BaseHttpxLlmAdapter(LlmStreamingPort):
    """Shared async HTTPX chat & SSE streaming adapter with DNS-pinned SSRF protection."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        allow_legacy_fallback: bool,
        log_error_fn: LogErrorFn = log_provider_error,
        inter_chunk_timeout_s: float | None = None,
        max_stream_retries: int = 2,
    ) -> None:
        self._client = http_client
        self._allow_legacy_fallback = allow_legacy_fallback
        self._log_error = log_error_fn
        self._inter_chunk_timeout_s = inter_chunk_timeout_s
        self._max_stream_retries = max(0, max_stream_retries)

    async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
        """Execute async non-streaming chat completion with DNS pinning."""
        ep = request.endpoint
        target_url, headers, body, msgs = build_effective_request_parts(request, stream=False)
        t0 = time.perf_counter()
        try:
            p_url, p_headers, ext = await prepare_pinned_http_request(
                self._client, target_url, headers
            )
            resp = await self._client.post(p_url, json=body, headers=p_headers, extensions=ext)
            fallback_url = should_attempt_openai_404_fallback(
                allow_legacy_fallback=self._allow_legacy_fallback,
                status_code=resp.status_code,
                ep=ep,
                target_url=target_url,
            )
            if fallback_url is not None:
                fb_url, fb_hdrs, fb_ext = await prepare_pinned_http_request(
                    self._client, fallback_url, headers
                )
                resp = await self._client.post(
                    fb_url,
                    json=build_openai_fallback_body(request, stream=False),
                    headers=fb_hdrs,
                    extensions=fb_ext,
                )
            resp.raise_for_status()
            data = resp.json()
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
        except UnsafeLlmEndpointUrlError:
            raise
        except httpx.HTTPStatusError as exc:
            self._log_error("llm_provider_http_status_error", exc, ep, target_url, t0)
            return None
        except Exception as exc:
            self._log_error("llm_provider_invocation_failed", exc, ep, target_url, t0)
            return None

    async def stream_chat_events(
        self, request: LlmStreamRequest
    ) -> AsyncIterator[LlmTypedStreamEvent]:
        """Stream typed `ContentDelta | ReasoningDelta | ToolCallDelta | Usage | Finish` events."""
        ep = request.endpoint
        target_url, headers, body, msgs = build_effective_request_parts(request, stream=True)
        t0 = time.perf_counter()
        acc_content: list[str] = []
        acc_thinking: list[str] = []
        tool_acc = ToolCallAccumulator()
        in_think = False
        saw_usage, obs_in_tok, obs_out_tok = False, 0, 0
        idle_timeout_s = resolve_inter_chunk_timeout_s(
            request.inter_chunk_timeout_s or self._inter_chunk_timeout_s
        )
        base_delay_s = resolve_stream_retry_base_delay_s()
        emitted_any_byte = False
        use_url, use_body = target_url, body

        for attempt in range(self._max_stream_retries + 1):
            try:
                p_url, p_headers, ext = await prepare_pinned_http_request(
                    self._client, use_url, headers
                )
                async with self._client.stream(
                    "POST", p_url, json=use_body, headers=p_headers, extensions=ext
                ) as resp:
                    if resp.status_code == 404 and not emitted_any_byte:
                        fb = should_attempt_openai_404_fallback(
                            allow_legacy_fallback=self._allow_legacy_fallback,
                            status_code=404,
                            ep=ep,
                            target_url=use_url,
                        )
                        if fb is not None:
                            use_url = fb
                            use_body = build_openai_fallback_body(request, stream=True)
                            continue
                    resp.raise_for_status()
                    async for raw_line in iter_lines_with_idle_timeout(
                        resp.aiter_lines(), idle_timeout_s=idle_timeout_s
                    ):
                        emitted_any_byte = True
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
                        in_think, out_deltas = emit_chunk_deltas(
                            c_delta,
                            r_delta,
                            acc_content=acc_content,
                            acc_thinking=acc_thinking,
                            in_think=in_think,
                            t0=t0,
                        )
                        for delta_item in out_deltas:
                            yield delta_to_typed_event(delta_item)
                        for tc_delta in tool_acc.process_chunk(chunk):
                            yield tc_delta
                        if chunk.get("type") == "message_stop":
                            break
                resp_txt, think_txt = "".join(acc_content), "".join(acc_thinking)
                final_tcs = tool_acc.finalize_tool_calls()
                in_tok, out_tok, u_src = resolve_usage_with_fallback(
                    messages=msgs,
                    reply_text=f"{resp_txt}\n{think_txt}",
                    observed_input_tokens=obs_in_tok,
                    observed_output_tokens=obs_out_tok,
                    saw_provider_usage=saw_usage,
                )
                yield Usage(input_tokens=in_tok, output_tokens=out_tok, usage_source=u_src)
                f_reason = tool_acc.finish_reason or ("tool_calls" if final_tcs else "stop")
                yield Finish(
                    finish_reason=f_reason,
                    accumulated_text=resp_txt,
                    thinking_text=think_txt,
                    tool_calls=final_tcs,
                    latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    usage_source=u_src,
                )
                return
            except UnsafeLlmEndpointUrlError:
                raise
            except TimeoutError as exc:
                self._log_error("llm_provider_stream_idle_timeout", exc, ep, use_url, t0)
                yield StreamErrorEvent(
                    error_message=scrub_sensitive_text(
                        f"Stream idle timeout after {idle_timeout_s:.1f}s ({ep.model_name})."
                    ),
                    error_code="ERR_UPSTREAM_TIMEOUT",
                    http_status=504,
                )
                return
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if (
                    not emitted_any_byte
                    and status in _RETRYABLE_STREAM_STATUSES
                    and attempt < self._max_stream_retries
                ):
                    delay = base_delay_s * (2**attempt)
                    _logger.warning(
                        "llm_provider_stream_retry",
                        attempt=attempt + 1,
                        status_code=status,
                        delay_s=delay,
                        model=ep.model_name,
                    )
                    await asyncio.sleep(delay)
                    continue
                self._log_error("llm_provider_stream_http_status_error", exc, ep, use_url, t0)
                yield StreamErrorEvent(
                    error_message=scrub_sensitive_text(
                        f"Provider HTTP {status} ({ep.model_name})."
                    ),
                    error_code=stream_error_code_for_status(status),
                    http_status=status,
                )
                return
            except Exception as exc:
                if (
                    not emitted_any_byte
                    and isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout))
                    and attempt < self._max_stream_retries
                ):
                    await asyncio.sleep(base_delay_s * (2**attempt))
                    continue
                self._log_error("llm_provider_stream_failed", exc, ep, use_url, t0)
                yield StreamErrorEvent(
                    error_message=scrub_sensitive_text(
                        f"Provider stream failed ({type(exc).__name__}): {exc}"
                    ),
                    error_code="ERR_INTERNAL_SERVER_ERROR",
                    http_status=502,
                )
                return

    async def stream_chat_sse(self, request: LlmStreamRequest) -> AsyncIterator[LlmStreamDelta]:
        """Stream true async HTTP SSE deltas (`resp.aiter_lines()`) with DNS pinning."""
        async for event in self.stream_chat_events(request):
            yield typed_event_to_delta(event)
