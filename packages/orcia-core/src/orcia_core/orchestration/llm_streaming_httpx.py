"""HTTPX pure async streaming adapters for `LlmStreamingPort` (`AD-15`, `CAP-076`, `D5 + R7`)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from orcia_core.orchestration.ai_models_urls import is_anthropic_provider
from orcia_core.orchestration.llm_gemini_dialect import is_google_gemini_native_provider
from orcia_core.orchestration.llm_streaming_base_httpx import (
    BaseHttpxLlmAdapter,
    LogErrorFn,
)
from orcia_core.orchestration.llm_streaming_sse_utils import (
    delta_to_sse_dict as delta_to_sse_dict,
)
from orcia_core.orchestration.llm_streaming_sse_utils import (
    log_provider_error as log_provider_error,
)
from orcia_core.ports.llm_streaming_port import (
    LlmChatTurnOutcome,
    LlmEndpointConfig,
    LlmStreamDelta,
    LlmStreamingPort,
    LlmStreamRequest,
)


class HttpxOpenAiCompatibleLlmAdapter(BaseHttpxLlmAdapter):
    """OpenAI-compatible / Azure / vLLM / Ollama `/v1` + `/api/chat` fallback adapter."""

    def __init__(
        self, *, http_client: httpx.AsyncClient, log_error_fn: LogErrorFn = log_provider_error
    ) -> None:
        super().__init__(
            http_client=http_client, allow_legacy_fallback=True, log_error_fn=log_error_fn
        )


class HttpxAnthropicLlmAdapter(BaseHttpxLlmAdapter):
    """Anthropic `/v1/messages` streaming & non-streaming adapter."""

    def __init__(
        self, *, http_client: httpx.AsyncClient, log_error_fn: LogErrorFn = log_provider_error
    ) -> None:
        super().__init__(
            http_client=http_client, allow_legacy_fallback=False, log_error_fn=log_error_fn
        )


class HttpxGeminiNativeLlmAdapter(BaseHttpxLlmAdapter):
    """Google Gemini Native `/v1beta` (`CAP-076`) streaming & non-streaming adapter."""

    def __init__(
        self, *, http_client: httpx.AsyncClient, log_error_fn: LogErrorFn = log_provider_error
    ) -> None:
        super().__init__(
            http_client=http_client, allow_legacy_fallback=False, log_error_fn=log_error_fn
        )


class HttpxMultiProviderLlmStreamingAdapter(LlmStreamingPort):
    """Multi-dialect `LlmStreamingPort` dispatcher across all 3 HTTPX adapters."""

    def __init__(
        self, *, http_client: httpx.AsyncClient, log_error_fn: LogErrorFn = log_provider_error
    ) -> None:
        self._openai = HttpxOpenAiCompatibleLlmAdapter(
            http_client=http_client, log_error_fn=log_error_fn
        )
        self._anthropic = HttpxAnthropicLlmAdapter(
            http_client=http_client, log_error_fn=log_error_fn
        )
        self._gemini = HttpxGeminiNativeLlmAdapter(
            http_client=http_client, log_error_fn=log_error_fn
        )

    def _select(self, ep: LlmEndpointConfig) -> LlmStreamingPort:
        if ep.protocol_mode == "gemini_native" or is_google_gemini_native_provider(
            ep.endpoint_uri, ep.provider
        ):
            return self._gemini
        if ep.protocol_mode == "anthropic_messages" or is_anthropic_provider(
            ep.endpoint_uri, ep.provider
        ):
            return self._anthropic
        return self._openai

    async def complete_chat(self, request: LlmStreamRequest) -> LlmChatTurnOutcome | None:
        return await self._select(request.endpoint).complete_chat(request)

    def stream_chat_sse(self, request: LlmStreamRequest) -> AsyncIterator[LlmStreamDelta]:
        return self._select(request.endpoint).stream_chat_sse(request)


__all__ = [
    "HttpxAnthropicLlmAdapter",
    "HttpxGeminiNativeLlmAdapter",
    "HttpxMultiProviderLlmStreamingAdapter",
    "HttpxOpenAiCompatibleLlmAdapter",
    "delta_to_sse_dict",
    "log_provider_error",
]
