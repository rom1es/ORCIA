"""Base HTTPX Async Streaming & Non-Streaming Client with SSRF Guard (`Story 26.2`, `26.6a`)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable

import httpx

from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration._llm_streaming_fallbacks import (
    maybe_resolve_stream_switch,
    parse_sse_json_line,
    post_chat_with_protocol_fallbacks,
)
from orcia_core.orchestration._llm_streaming_http_helpers import (
    build_effective_request_parts,
    build_non_stream_turn_outcome,
    build_secondary_model_fallback_request,
    build_stream_terminal_events,
)
from orcia_core.orchestration.ai_models_errors import UnsafeLlmEndpointUrlError
from orcia_core.orchestration.ai_models_pinned_http import prepare_pinned_http_request
from orcia_core.orchestration.llm_provider_parsing import extract_stream_chunk_deltas
from orcia_core.orchestration.llm_streaming_sse_utils import (
    emit_chunk_deltas,
    iter_lines_with_idle_timeout,
    log_provider_error,
    resolve_inter_chunk_timeout_s,
    resolve_stream_retry_base_delay_s,
    stream_error_code_for_status,
)
from orcia_core.orchestration.llm_tool_dialects import ToolCallAccumulator
from orcia_core.orchestration.llm_usage_telemetry import extract_usage_tokens_from_payload
from orcia_core.ports.llm_streaming_port import (
    LlmChatTurnOutcome,
    LlmEndpointConfig,
    LlmStreamDelta,
    LlmStreamingPort,
    LlmStreamRequest,
    LlmTypedStreamEvent,
    StreamErrorEvent,
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
        """Execute async non-streaming chat completion with DNS pinning & fallbacks."""
        ep = request.endpoint
        target_url, headers, body, msgs = build_effective_request_parts(request, stream=False)
        t0 = time.perf_counter()
        try:
            resp = await post_chat_with_protocol_fallbacks(
                self._client,
                request,
                target_url=target_url,
                headers=headers,
                body=body,
                allow_legacy_fallback=self._allow_legacy_fallback,
            )
            if (
                resp.status_code not in (200, 401, 403)
                and (fb_req := build_secondary_model_fallback_request(request)) is not None
            ):
                _logger.warning(
                    "llm_primary_model_failed_falling_back_to_secondary",
                    primary_model=ep.model_name,
                    fallback_model=fb_req.endpoint.model_name,
                    status_code=resp.status_code,
                )
                return await self.complete_chat(fb_req)
            resp.raise_for_status()
            return build_non_stream_turn_outcome(resp.json(), msgs, t0)
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
        """Stream typed events with Gemini Interactions auto-switch & secondary fallback."""
        ep = request.endpoint
        use_url, use_headers, use_body, msgs = build_effective_request_parts(request, stream=True)
        t0 = time.perf_counter()
        acc_content: list[str] = []
        acc_thinking: list[str] = []
        tool_acc = ToolCallAccumulator()
        in_think, saw_usage, obs_in_tok, obs_out_tok = False, False, 0, 0
        idle_timeout_s = resolve_inter_chunk_timeout_s(
            request.inter_chunk_timeout_s or self._inter_chunk_timeout_s
        )
        base_delay_s = resolve_stream_retry_base_delay_s()
        emitted_any_byte, switched_to_agent, attempt = False, False, 0

        while True:
            try:
                p_url, p_headers, ext = await prepare_pinned_http_request(
                    self._client, use_url, use_headers
                )
                async with self._client.stream(
                    "POST", p_url, json=use_body, headers=p_headers, extensions=ext
                ) as resp:
                    if not emitted_any_byte and resp.status_code in (400, 404):
                        switched = await maybe_resolve_stream_switch(
                            request,
                            resp,
                            use_url=use_url,
                            use_headers=use_headers,
                            allow_legacy_fallback=self._allow_legacy_fallback,
                            switched_to_agent=switched_to_agent,
                        )
                        if switched is not None:
                            use_url, use_headers, use_body, switched_to_agent = switched
                            continue
                    resp.raise_for_status()
                    async for raw_line in iter_lines_with_idle_timeout(
                        resp.aiter_lines(), idle_timeout_s=idle_timeout_s
                    ):
                        emitted_any_byte = True
                        parsed = parse_sse_json_line(raw_line)
                        if parsed == "skip":
                            continue
                        if parsed == "done":
                            break
                        if (u_tok := extract_usage_tokens_from_payload(parsed)) is not None:
                            saw_usage = True
                            obs_in_tok = u_tok[0] if u_tok[0] > 0 else obs_in_tok
                            obs_out_tok = u_tok[1] if u_tok[1] > 0 else obs_out_tok
                        c_delta, r_delta = extract_stream_chunk_deltas(parsed)
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
                        for tc_delta in tool_acc.process_chunk(parsed):
                            yield tc_delta
                        if parsed.get("type") == "message_stop":
                            break
                usage_ev, finish_ev = build_stream_terminal_events(
                    msgs=msgs,
                    resp_txt="".join(acc_content),
                    think_txt="".join(acc_thinking),
                    final_tcs=tool_acc.finalize_tool_calls(),
                    finish_reason=tool_acc.finish_reason or "",
                    obs_in_tok=obs_in_tok,
                    obs_out_tok=obs_out_tok,
                    saw_usage=saw_usage,
                    t0=t0,
                )
                yield usage_ev
                yield finish_ev
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
                    and status not in (200, 401, 403)
                    and (fb_req := build_secondary_model_fallback_request(request)) is not None
                ):
                    _logger.warning(
                        "llm_primary_model_failed_falling_back_to_secondary",
                        primary_model=ep.model_name,
                        fallback_model=fb_req.endpoint.model_name,
                        status_code=status,
                    )
                    async for ev in self.stream_chat_events(fb_req):
                        yield ev
                    return
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
                    attempt += 1
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
                    attempt += 1
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
