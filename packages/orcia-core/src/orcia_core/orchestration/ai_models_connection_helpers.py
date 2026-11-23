"""Connection Test Helpers & Status Normalization (`Story 19.3`, `Story 26.1`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn

import httpx

from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration.ai_models_errors import (
    ModelConnectionAuthFailedError,
    ModelConnectionNetworkError,
    ModelConnectionNotFoundError,
    ModelConnectionRateLimitedError,
    ModelConnectionTimeoutError,
    ModelConnectionUpstreamError,
)
from orcia_core.orchestration.ai_models_pinned_http import prepare_pinned_http_request
from orcia_core.orchestration.ai_models_records import LlmProtocolMode
from orcia_core.orchestration.ai_models_urls import (
    build_gemini_interactions_url,
    is_anthropic_provider,
    is_gemini_interactions_url,
    is_gemini_native_provider,
    normalize_chat_completions_url,
)
from orcia_core.orchestration.llm_gemini_interactions import (
    build_gemini_interactions_probe_body,
    is_gemini_interactions_agent_field_required_error,
    is_gemini_interactions_api_required_error,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AiModelConnectionTestSuccess:
    """Successful outcome of a real connectivity test."""

    latency_ms: int
    message_fr: str
    message_en: str
    supports_tools: bool = False


def clean_error_snippet(text: str, secret_key: str | None) -> str:
    """Truncate upstream error snippet and redact credentials."""
    snippet = text[:250].strip()
    if secret_key:
        snippet = snippet.replace(secret_key, "[REDACTED]")
    return scrub_sensitive_text(snippet)


def build_chat_connection_probe(
    *,
    endpoint_uri: str,
    protocol_mode: LlmProtocolMode,
    model_name: str,
    api_key: str | None,
    provider_slug: str | None,
) -> tuple[str, dict[str, str], dict[str, Any]]:
    """Build normalized URL, headers, and minimal `max_tokens=1` payload."""
    target_url = normalize_chat_completions_url(
        endpoint_uri,
        provider_slug=provider_slug or "",
        protocol_mode=protocol_mode,
        model_name=model_name,
    )
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    body: dict[str, Any]
    if protocol_mode == "anthropic_messages" or is_anthropic_provider(endpoint_uri, provider_slug):
        headers["anthropic-version"] = "2023-06-01"
        if api_key:
            headers["x-api-key"] = api_key
        body = {
            "model": model_name,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
    elif protocol_mode == "gemini_native" or is_gemini_native_provider(endpoint_uri, provider_slug):
        if api_key:
            headers["x-goog-api-key"] = api_key
        if is_gemini_interactions_url(target_url):
            body = build_gemini_interactions_probe_body(model_name)
        else:
            body = {
                "contents": [{"parts": [{"text": "ping"}]}],
                "generationConfig": {"maxOutputTokens": 1},
            }
    else:
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        body = {
            "model": model_name,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "stream": False,
        }
    return target_url, headers, body


def raise_for_chat_http_status(
    *,
    status_code: int,
    response_text: str,
    api_key: str | None,
    target_url: str,
    model_name: str,
    latency_ms: int,
    instance: str,
) -> None:
    """Translate non-200 provider responses into scrubbed RFC 9457 domain errors."""
    snippet = clean_error_snippet(response_text, api_key)
    if status_code in (401, 403):
        logger.warning(
            "llm_connection_test_auth_failed",
            endpoint=target_url,
            status_code=status_code,
            latency_ms=latency_ms,
        )
        raise ModelConnectionAuthFailedError(
            detail_override=(f"Authentication rejected by provider ({status_code}): {snippet}"),
            instance=instance,
            latency_ms=latency_ms,
        )
    if status_code == 404:
        logger.warning("llm_connection_test_not_found", endpoint=target_url, latency_ms=latency_ms)
        raise ModelConnectionNotFoundError(
            detail_override=(
                f"Model '{model_name}' or endpoint not found at {target_url} (HTTP 404): {snippet}"
            ),
            instance=instance,
            latency_ms=latency_ms,
        )
    if status_code == 429:
        logger.warning(
            "llm_connection_test_rate_limited", endpoint=target_url, latency_ms=latency_ms
        )
        raise ModelConnectionRateLimitedError(
            detail_override=f"Quota or rate limit exceeded at {target_url} (HTTP 429): {snippet}",
            instance=instance,
            latency_ms=latency_ms,
        )
    logger.warning(
        "llm_connection_test_upstream_error",
        endpoint=target_url,
        status_code=status_code,
        latency_ms=latency_ms,
    )
    raise ModelConnectionUpstreamError(
        detail_override=f"Provider returned HTTP {status_code}: {snippet}",
        instance=instance,
        latency_ms=latency_ms,
    )


async def post_pinned_probe(
    http_client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout_seconds: float,
    instance: str,
) -> httpx.Response:
    """Execute pinned HTTPX POST probe with SSRF protection."""
    p_url, p_headers, ext = await prepare_pinned_http_request(
        http_client, url, headers, instance=instance
    )
    return await http_client.post(
        p_url, json=body, headers=p_headers, timeout=timeout_seconds, extensions=ext
    )


async def maybe_retry_gemini_interactions_probe(
    http_client: httpx.AsyncClient,
    resp: httpx.Response,
    *,
    endpoint_uri: str,
    target_url: str,
    headers: dict[str, str],
    model_name: str,
    timeout_seconds: float,
    instance: str,
) -> tuple[str, httpx.Response]:
    """Retry Gemini connection probe on `/interactions` (`model` then `agent`) if required."""
    if not is_gemini_interactions_url(target_url) and is_gemini_interactions_api_required_error(
        resp.status_code, resp.text
    ):
        target_url = build_gemini_interactions_url(endpoint_uri)
        resp = await post_pinned_probe(
            http_client,
            target_url,
            headers,
            build_gemini_interactions_probe_body(model_name, use_agent_field=False),
            timeout_seconds,
            instance,
        )
    if is_gemini_interactions_url(target_url) and is_gemini_interactions_agent_field_required_error(
        resp.status_code, resp.text
    ):
        resp = await post_pinned_probe(
            http_client,
            target_url,
            headers,
            build_gemini_interactions_probe_body(model_name, use_agent_field=True),
            timeout_seconds,
            instance,
        )
    return target_url, resp


def raise_for_embedding_connection_error(
    exc: Exception, *, instance: str, latency_ms: int
) -> NoReturn:
    """Translate `EmbeddingGenerationFailedError` into a localized RFC 9457 error."""
    err_msg = str(exc)
    for tokens, err_cls in (
        (("HTTP 401", "HTTP 403"), ModelConnectionAuthFailedError),
        (("HTTP 404",), ModelConnectionNotFoundError),
        (("HTTP 429",), ModelConnectionRateLimitedError),
    ):
        if any(t in err_msg for t in tokens):
            raise err_cls(
                detail_override=err_msg, instance=instance, latency_ms=latency_ms
            ) from exc
    if isinstance(exc.__cause__, httpx.TimeoutException) or "Timeout" in err_msg:
        raise ModelConnectionTimeoutError(
            detail_override=f"Timeout on embedding endpoint: {err_msg}",
            instance=instance,
            latency_ms=latency_ms,
        ) from exc
    if "Network error" in err_msg:
        raise ModelConnectionNetworkError(detail_override=err_msg, instance=instance) from exc
    raise ModelConnectionUpstreamError(
        detail_override=err_msg, instance=instance, latency_ms=latency_ms
    ) from exc


__all__ = [
    "AiModelConnectionTestSuccess",
    "build_chat_connection_probe",
    "clean_error_snippet",
    "maybe_retry_gemini_interactions_probe",
    "post_pinned_probe",
    "raise_for_chat_http_status",
    "raise_for_embedding_connection_error",
]
