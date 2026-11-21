"""Composition Root `Depends` providers for `LlmStreamingPort` (`Story 26.2`, `AD-19`)."""

from __future__ import annotations

import os
from typing import Any, cast

import httpx
from fastapi import Request

from orcia_core.orchestration.llm_streaming_httpx import HttpxMultiProviderLlmStreamingAdapter
from orcia_core.ports.llm_streaming_port import LlmStreamingPort


def is_cassette_llm_enabled() -> bool:
    """Return True when `ORCIA_USE_CASSETTE_LLM` explicitly selects deterministic cassettes."""
    return os.environ.get("ORCIA_USE_CASSETTE_LLM", "").strip().lower() in ("1", "true", "yes")


def get_or_create_async_http_client(request: Request) -> httpx.AsyncClient:
    """Return shared `httpx.AsyncClient` from `request.app.state.http_client`."""
    shared: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    if shared is not None and not getattr(shared, "is_closed", False):
        return shared
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(300.0, connect=10.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    request.app.state.http_client = client
    return client


def _api_log_provider_error(
    event: str, exc: Exception, ep: Any, target_url: str, t0: float
) -> None:
    from orcia_api.routers import assistant_llm_providers

    assistant_llm_providers._log_provider_error(event, exc, ep, target_url, t0)


def get_llm_streaming_port(request: Request) -> LlmStreamingPort:
    """FastAPI `Depends` provider returning `LlmStreamingPort` (Cassette or HTTPX)."""
    explicit = getattr(request.app.state, "llm_streaming_port", None)
    if explicit is not None:
        return cast(LlmStreamingPort, explicit)
    if is_cassette_llm_enabled():
        from orcia_core.testing.cassette_llm import DeterministicCassetteLlmStreamingAdapter

        return DeterministicCassetteLlmStreamingAdapter()
    return HttpxMultiProviderLlmStreamingAdapter(
        http_client=get_or_create_async_http_client(request),
        log_error_fn=_api_log_provider_error,
    )


__all__ = [
    "get_llm_streaming_port",
    "get_or_create_async_http_client",
    "is_cassette_llm_enabled",
]
