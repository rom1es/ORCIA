"""Connection Test Helpers & Status Normalization (`Story 19.3`, `Story 26.1`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orcia_core.observability.logging import get_logger, scrub_sensitive_text
from orcia_core.orchestration.ai_models_errors import (
    ModelConnectionAuthFailedError,
    ModelConnectionNotFoundError,
    ModelConnectionRateLimitedError,
    ModelConnectionUpstreamError,
)
from orcia_core.orchestration.ai_models_records import LlmProtocolMode
from orcia_core.orchestration.ai_models_urls import (
    is_anthropic_provider,
    is_gemini_native_provider,
    normalize_chat_completions_url,
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


__all__ = [
    "AiModelConnectionTestSuccess",
    "build_chat_connection_probe",
    "clean_error_snippet",
    "raise_for_chat_http_status",
]
