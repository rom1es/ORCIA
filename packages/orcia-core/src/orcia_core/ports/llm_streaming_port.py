"""Hexagonal `LlmStreamingPort` contract (pure Python Protocol, zero SDK imports)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

LlmStreamEventType = Literal[
    "thinking_delta",
    "token_delta",
    "tool_call_delta",
    "usage",
    "turn_completed",
    "stream_error",
]


@dataclass(frozen=True, slots=True)
class LlmEndpointConfig:
    """Resolved provider endpoint configuration for a streaming or chat turn."""

    provider: str
    model_name: str
    endpoint_uri: str
    auth_mode: str
    tier: str = "medium"
    api_key: str | None = None
    protocol_mode: str = ""
    max_tokens_budget: int = 8192
    supports_tools: bool = False
    fallback_model_name: str | None = None


@dataclass(frozen=True, slots=True)
class LlmStreamRequest:
    """Provider-agnostic chat/streaming request passed to `LlmStreamingPort`."""

    endpoint: LlmEndpointConfig
    messages: Sequence[dict[str, Any]]
    tools: Sequence[dict[str, Any]] = ()
    tool_choice: str | dict[str, Any] | None = None
    stream: bool = True
    include_thoughts: bool = True
    inter_chunk_timeout_s: float | None = None


@dataclass(frozen=True, slots=True)
class ContentDelta:
    """Typed incremental content token delta."""

    delta: str
    accumulated_text: str = ""


@dataclass(frozen=True, slots=True)
class ReasoningDelta:
    """Typed incremental reasoning/thinking delta."""

    delta: str
    thinking_text: str = ""
    elapsed_ms: float = 0.0
    step_code: str = "NODE_5_SINGLE_STREAM_LLM"


@dataclass(frozen=True, slots=True)
class ToolCallDelta:
    """Typed incremental native tool call delta fragment."""

    index: int = 0
    tool_call_id: str = ""
    name: str = ""
    arguments_delta: str = ""


@dataclass(frozen=True, slots=True)
class Usage:
    """Typed token usage event emitted by provider or estimator."""

    input_tokens: int = 0
    output_tokens: int = 0
    usage_source: str = "estimated"


@dataclass(frozen=True, slots=True)
class Finish:
    """Typed terminal completion event carrying reassembled tool calls and finish reason."""

    finish_reason: str = "stop"
    accumulated_text: str = ""
    thinking_text: str = ""
    tool_calls: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    usage_source: str = "estimated"


@dataclass(frozen=True, slots=True)
class StreamErrorEvent:
    """Typed terminal stream error event."""

    error_message: str
    error_code: str = "ERR_INTERNAL_SERVER_ERROR"
    http_status: int = 502


LlmTypedStreamEvent = (
    ContentDelta | ReasoningDelta | ToolCallDelta | Usage | Finish | StreamErrorEvent
)


@dataclass(frozen=True, slots=True)
class LlmStreamDelta:
    """Normalized SSE delta emitted by `LlmStreamingPort.stream_chat_sse`."""

    event: LlmStreamEventType
    delta: str = ""
    accumulated_text: str = ""
    thinking_text: str = ""
    elapsed_ms: float = 0.0
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    usage_source: str = "estimated"
    error_message: str = ""
    error_code: str = ""
    http_status: int = 0
    step_code: str = "NODE_5_SINGLE_STREAM_LLM"
    tool_call_index: int = 0
    tool_call_id: str = ""
    tool_name: str = ""
    arguments_delta: str = ""
    tool_calls: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    finish_reason: str = ""


@dataclass(frozen=True, slots=True)
class LlmChatTurnOutcome:
    """Normalized non-streaming chat completion outcome."""

    content: str
    thinking_text: str
    latency_ms: float
    tool_calls: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    input_tokens: int = 0
    output_tokens: int = 0
    usage_source: str = "estimated"
    finish_reason: str = "stop"


def delta_to_typed_event(delta: LlmStreamDelta) -> LlmTypedStreamEvent:
    """Convert a legacy `LlmStreamDelta` into its typed `LlmTypedStreamEvent` variant."""
    if delta.event == "thinking_delta":
        return ReasoningDelta(
            delta=delta.delta,
            thinking_text=delta.thinking_text,
            elapsed_ms=delta.elapsed_ms,
            step_code=delta.step_code,
        )
    if delta.event == "token_delta":
        return ContentDelta(delta=delta.delta, accumulated_text=delta.accumulated_text)
    if delta.event == "tool_call_delta":
        return ToolCallDelta(
            index=delta.tool_call_index,
            tool_call_id=delta.tool_call_id,
            name=delta.tool_name,
            arguments_delta=delta.arguments_delta,
        )
    if delta.event == "usage":
        return Usage(
            input_tokens=delta.input_tokens,
            output_tokens=delta.output_tokens,
            usage_source=delta.usage_source,
        )
    if delta.event == "stream_error":
        return StreamErrorEvent(
            error_message=delta.error_message,
            error_code=delta.error_code or "ERR_INTERNAL_SERVER_ERROR",
            http_status=delta.http_status or 502,
        )
    return Finish(
        finish_reason=delta.finish_reason or ("tool_calls" if delta.tool_calls else "stop"),
        accumulated_text=delta.accumulated_text,
        thinking_text=delta.thinking_text,
        tool_calls=delta.tool_calls,
        latency_ms=delta.latency_ms,
        input_tokens=delta.input_tokens,
        output_tokens=delta.output_tokens,
        usage_source=delta.usage_source,
    )


def typed_event_to_delta(event: LlmTypedStreamEvent) -> LlmStreamDelta:
    """Convert a typed `LlmTypedStreamEvent` into an `LlmStreamDelta`."""
    if isinstance(event, ReasoningDelta):
        return LlmStreamDelta(
            event="thinking_delta",
            delta=event.delta,
            thinking_text=event.thinking_text,
            elapsed_ms=event.elapsed_ms,
            step_code=event.step_code,
        )
    if isinstance(event, ContentDelta):
        return LlmStreamDelta(
            event="token_delta",
            delta=event.delta,
            accumulated_text=event.accumulated_text,
        )
    if isinstance(event, ToolCallDelta):
        return LlmStreamDelta(
            event="tool_call_delta",
            tool_call_index=event.index,
            tool_call_id=event.tool_call_id,
            tool_name=event.name,
            arguments_delta=event.arguments_delta,
        )
    if isinstance(event, Usage):
        return LlmStreamDelta(
            event="usage",
            input_tokens=event.input_tokens,
            output_tokens=event.output_tokens,
            usage_source=event.usage_source,
        )
    if isinstance(event, StreamErrorEvent):
        return LlmStreamDelta(
            event="stream_error",
            error_message=event.error_message,
            error_code=event.error_code,
            http_status=event.http_status,
        )
    return LlmStreamDelta(
        event="turn_completed",
        accumulated_text=event.accumulated_text,
        thinking_text=event.thinking_text,
        latency_ms=event.latency_ms,
        input_tokens=event.input_tokens,
        output_tokens=event.output_tokens,
        usage_source=event.usage_source,
        tool_calls=event.tool_calls,
        finish_reason=event.finish_reason,
    )


@runtime_checkable
class LlmStreamingPort(Protocol):
    """Hexagonal port for multi-provider async chat and SSE text/reasoning/tool streaming."""

    async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
        """Execute a non-streaming chat completion request."""
        ...

    def stream_chat_sse(self, request: LlmStreamRequest) -> AsyncIterator[LlmStreamDelta]:
        """Stream normalized `LlmStreamDelta` events asynchronously."""
        ...


async def iter_typed_stream_events(
    port: LlmStreamingPort,
    request: LlmStreamRequest,
) -> AsyncIterator[LlmTypedStreamEvent]:
    """Iterate typed `LlmTypedStreamEvent` items from any `LlmStreamingPort` implementation."""
    stream_fn = getattr(port, "stream_chat_events", None)
    if callable(stream_fn):
        async for ev in stream_fn(request):
            yield ev
        return
    async for delta in port.stream_chat_sse(request):
        yield delta_to_typed_event(delta)


__all__ = [
    "ContentDelta",
    "Finish",
    "LlmChatTurnOutcome",
    "LlmEndpointConfig",
    "LlmStreamDelta",
    "LlmStreamEventType",
    "LlmStreamRequest",
    "LlmStreamingPort",
    "LlmTypedStreamEvent",
    "ReasoningDelta",
    "StreamErrorEvent",
    "ToolCallDelta",
    "Usage",
    "delta_to_typed_event",
    "iter_typed_stream_events",
    "typed_event_to_delta",
]
