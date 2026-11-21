"""Thin API facade delegating provider calls to `orcia_core` HTTPX adapters (`AD-15`)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx

from orcia_api.routers._assistant_llm_provider_parsing import (
    ProviderChatTurnResponse as ProviderChatTurnResponse,
)
from orcia_api.routers._assistant_llm_provider_parsing import (
    ResolvedLiveLlmEndpoint as ResolvedLiveLlmEndpoint,
)
from orcia_api.routers._assistant_llm_provider_parsing import (
    build_provider_headers as build_provider_headers,
)
from orcia_api.routers._assistant_llm_provider_parsing import (
    build_provider_request_body as build_provider_request_body,
)
from orcia_api.routers._assistant_llm_provider_parsing import (
    extract_stream_chunk_deltas as _extract_stream_chunk_deltas,
)
from orcia_api.routers._assistant_llm_provider_parsing import (
    extract_thinking_and_clean_content as extract_thinking_and_clean_content,
)
from orcia_api.routers._assistant_llm_provider_parsing import (
    parse_non_stream_json as _parse_non_stream_json,
)
from orcia_api.routers.assistant_llm_gemini_adapter import (
    _separate_think_tags as _separate_think_tags,
)
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.ai_models_urls import (
    build_legacy_local_chat_url as build_legacy_local_chat_url,
)
from orcia_core.orchestration.ai_models_urls import (
    is_anthropic_provider as is_anthropic_provider,
)
from orcia_core.orchestration.ai_models_urls import (
    normalize_chat_completions_url as normalize_chat_completions_url,
)
from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
from orcia_core.orchestration.llm_streaming_sse_utils import (
    delta_to_sse_dict,
    log_provider_error,
)
from orcia_core.orchestration.ssrf_guard import is_safe_llm_endpoint_url as is_safe_llm_endpoint_url
from orcia_core.ports.llm_streaming_port import LlmStreamRequest

logger = get_logger("orcia.assistant.llm")


def _log_provider_error(
    event: str, exc: Exception, ep: ResolvedLiveLlmEndpoint, target_url: str, t0: float
) -> None:
    log_provider_error(event, exc, ep, target_url, t0)


async def invoke_provider_chat_async(
    http_client: httpx.AsyncClient,
    *,
    ep: ResolvedLiveLlmEndpoint,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> ProviderChatTurnResponse | None:
    """Delegate non-streaming chat completion to `HttpxMultiProviderLlmStreamingAdapter`."""
    adapter = HttpxMultiProviderLlmStreamingAdapter(
        http_client=http_client,
        log_error_fn=lambda ev, ex, e, u, t0: _log_provider_error(ev, ex, e, u, t0),
    )
    return await adapter.complete_chat(
        LlmStreamRequest(
            endpoint=ep,
            messages=tuple(messages),
            tools=tuple(tools or ()),
        )
    )


async def stream_provider_chat_sse_async(
    http_client: httpx.AsyncClient,
    *,
    ep: ResolvedLiveLlmEndpoint,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Delegate SSE streaming to `HttpxMultiProviderLlmStreamingAdapter`."""
    adapter = HttpxMultiProviderLlmStreamingAdapter(
        http_client=http_client,
        log_error_fn=lambda ev, ex, e, u, t0: _log_provider_error(ev, ex, e, u, t0),
    )
    async for delta in adapter.stream_chat_sse(
        LlmStreamRequest(
            endpoint=ep,
            messages=tuple(messages),
            tools=tuple(tools or ()),
        )
    ):
        yield delta_to_sse_dict(delta)


__all__ = [
    "ProviderChatTurnResponse",
    "ResolvedLiveLlmEndpoint",
    "_extract_stream_chunk_deltas",
    "_log_provider_error",
    "_parse_non_stream_json",
    "_separate_think_tags",
    "build_legacy_local_chat_url",
    "build_provider_headers",
    "build_provider_request_body",
    "extract_thinking_and_clean_content",
    "invoke_provider_chat_async",
    "is_anthropic_provider",
    "is_safe_llm_endpoint_url",
    "logger",
    "normalize_chat_completions_url",
    "stream_provider_chat_sse_async",
]
