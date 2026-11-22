"""SSE delta serialization & structured error logging helpers (`Story 26.2`, `Story 26.6a`)."""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig, LlmStreamDelta

logger = get_logger("orcia.assistant.llm")


def resolve_stream_retry_base_delay_s() -> float:
    """Resolve exponential backoff base delay from `ORCIA_LLM_STREAM_RETRY_BASE_S`."""
    try:
        return max(0.005, float(os.environ.get("ORCIA_LLM_STREAM_RETRY_BASE_S", "0.25").strip()))
    except ValueError:
        return 0.25


def resolve_inter_chunk_timeout_s(explicit: float | None = None) -> float:
    """Resolve inter-chunk idle timeout from request/adapter or env (default 30s)."""
    if explicit is not None and explicit > 0:
        return float(explicit)
    try:
        return max(0.02, float(os.environ.get("ORCIA_LLM_STREAM_IDLE_TIMEOUT_S", "30.0").strip()))
    except ValueError:
        return 30.0


async def iter_lines_with_idle_timeout(
    lines_iter: AsyncIterator[str], *, idle_timeout_s: float
) -> AsyncIterator[str]:
    """Yield lines from `lines_iter`, raising `TimeoutError` after `idle_timeout_s`."""
    raw_iter = lines_iter.__aiter__()
    while True:
        try:
            yield await asyncio.wait_for(raw_iter.__anext__(), timeout=idle_timeout_s)
        except StopAsyncIteration:
            return


def stream_error_code_for_status(status_code: int) -> str:
    """Map an HTTP status code from a streaming LLM upstream to a canonical ORCIA error code."""
    if status_code == 429:
        return "ERR_RATE_LIMITED"
    if status_code in (502, 503):
        return "ERR_TRANSIENT_INFRA_ERROR"
    if status_code == 504:
        return "ERR_UPSTREAM_TIMEOUT"
    return "ERR_INTERNAL_SERVER_ERROR"


def log_provider_error(
    event: str, exc: Exception, ep: LlmEndpointConfig, target_url: str, t0: float
) -> None:
    """Emit structured provider error log with redacted error details."""
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


def delta_to_sse_dict(delta: LlmStreamDelta) -> dict[str, Any]:
    """Convert normalized `LlmStreamDelta` to legacy SSE payload dict."""
    if delta.event == "thinking_delta":
        return {
            "event": "thinking_delta",
            "data": {
                "step_code": delta.step_code,
                "delta": delta.delta,
                "thinking_text": delta.thinking_text,
                "elapsed_ms": delta.elapsed_ms,
            },
        }
    if delta.event == "token_delta":
        return {
            "event": "token_delta",
            "data": {"delta": delta.delta, "accumulated_text": delta.accumulated_text},
        }
    if delta.event == "tool_call_delta":
        return {
            "event": "tool_call_delta",
            "data": {
                "index": delta.tool_call_index,
                "tool_call_id": delta.tool_call_id,
                "name": delta.tool_name,
                "arguments_delta": delta.arguments_delta,
            },
        }
    if delta.event == "usage":
        return {
            "event": "usage",
            "data": {
                "input_tokens": delta.input_tokens,
                "output_tokens": delta.output_tokens,
                "usage_source": delta.usage_source,
            },
        }
    if delta.event == "stream_error":
        payload: dict[str, Any] = {"message": delta.error_message}
        if delta.error_code:
            payload["error_code"] = delta.error_code
        if delta.http_status:
            payload["status"] = delta.http_status
        return {"event": "stream_error", "data": payload}
    completed_data: dict[str, Any] = {
        "response_text": delta.accumulated_text,
        "thinking_text": delta.thinking_text,
        "latency_ms": delta.latency_ms,
        "input_tokens": delta.input_tokens,
        "output_tokens": delta.output_tokens,
        "usage_source": delta.usage_source,
    }
    if delta.finish_reason:
        completed_data["finish_reason"] = delta.finish_reason
    if delta.tool_calls:
        completed_data["tool_calls"] = list(delta.tool_calls)
    return {"event": "turn_completed", "data": completed_data}


def emit_chunk_deltas(
    c_delta: str,
    r_delta: str,
    *,
    acc_content: list[str],
    acc_thinking: list[str],
    in_think: bool,
    t0: float,
) -> tuple[bool, list[LlmStreamDelta]]:
    """Convert raw content/reasoning chunk strings into normalized `LlmStreamDelta` items."""
    out: list[LlmStreamDelta] = []
    if r_delta:
        acc_thinking.append(r_delta)
        out.append(
            LlmStreamDelta(
                event="thinking_delta",
                delta=r_delta,
                thinking_text="".join(acc_thinking),
                elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
            )
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
                out.append(
                    LlmStreamDelta(
                        event="thinking_delta",
                        delta=c_delta,
                        thinking_text="".join(acc_thinking),
                        elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                    )
                )
                return in_think, out
        if c_delta:
            acc_content.append(c_delta)
            out.append(
                LlmStreamDelta(
                    event="token_delta",
                    delta=c_delta,
                    accumulated_text="".join(acc_content),
                )
            )
    return in_think, out


__all__ = [
    "delta_to_sse_dict",
    "emit_chunk_deltas",
    "iter_lines_with_idle_timeout",
    "log_provider_error",
    "resolve_inter_chunk_timeout_s",
    "resolve_stream_retry_base_delay_s",
    "stream_error_code_for_status",
]
