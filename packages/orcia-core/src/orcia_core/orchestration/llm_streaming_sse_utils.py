"""SSE delta serialization & structured error logging helpers (`Story 26.2`)."""

from __future__ import annotations

import time
from typing import Any

import httpx

from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig, LlmStreamDelta

logger = get_logger("orcia.assistant.llm")


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
    if delta.event == "stream_error":
        return {"event": "stream_error", "data": {"message": delta.error_message}}
    return {
        "event": "turn_completed",
        "data": {
            "response_text": delta.accumulated_text,
            "thinking_text": delta.thinking_text,
            "latency_ms": delta.latency_ms,
            "input_tokens": delta.input_tokens,
            "output_tokens": delta.output_tokens,
            "usage_source": delta.usage_source,
        },
    }


__all__ = ["delta_to_sse_dict", "log_provider_error"]
