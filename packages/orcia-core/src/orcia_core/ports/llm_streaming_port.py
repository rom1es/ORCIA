"""Hexagonal `LlmStreamingPort` contract (pure Python Protocol, zero SDK imports)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

LlmStreamEventType = Literal["thinking_delta", "token_delta", "turn_completed", "stream_error"]


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


@dataclass(frozen=True, slots=True)
class LlmStreamRequest:
    """Provider-agnostic chat/streaming request passed to `LlmStreamingPort`."""

    endpoint: LlmEndpointConfig
    messages: Sequence[dict[str, Any]]
    tools: Sequence[dict[str, Any]] = ()
    stream: bool = True
    include_thoughts: bool = True
    inter_chunk_timeout_s: float | None = None


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


@runtime_checkable
class LlmStreamingPort(Protocol):
    """Hexagonal port for multi-provider async chat and SSE text/reasoning streaming."""

    async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
        """Execute a non-streaming chat completion request."""
        ...

    def stream_chat_sse(self, request: LlmStreamRequest) -> AsyncIterator[LlmStreamDelta]:
        """Stream normalized `LlmStreamDelta` events asynchronously."""
        ...


__all__ = [
    "LlmChatTurnOutcome",
    "LlmEndpointConfig",
    "LlmStreamDelta",
    "LlmStreamEventType",
    "LlmStreamRequest",
    "LlmStreamingPort",
]
