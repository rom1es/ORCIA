"""Pure asynchronous connection tester for chat and embedding AI models (`AD-24.3`, `Story 19.3`).

Executes minimal non-blocking HTTP requests:
- Chat: `max_tokens=1` inference call according to protocol mode (`openai_compatible`,
  `anthropic_messages`, `gemini_native`), validating API key and model existence.
- Embedding: short test text via `EmbeddingPort` HTTPX adapter with strict 1024-dimension check.
Measures real roundtrip latency (`time.perf_counter()`) with zero hardcoded/mock latencies.
Translates provider errors to domain errors inheriting from `OrciaDomainError`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.ai_models_crypto import validate_safe_llm_endpoint_url
from orcia_core.orchestration.ai_models_errors import (
    ModelConnectionAuthFailedError,
    ModelConnectionNetworkError,
    ModelConnectionNotFoundError,
    ModelConnectionRateLimitedError,
    ModelConnectionTimeoutError,
    ModelConnectionUpstreamError,
)
from orcia_core.orchestration.ai_models_records import LlmProtocolMode
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag.adapters.embedding_httpx import (
    HttpxGeminiNativeEmbeddingAdapter,
    HttpxOpenAiCompatibleEmbeddingAdapter,
    assert_embedding_usage_supported,
)
from orcia_core.rag.errors import (
    EmbeddingDimensionMismatchError,
    EmbeddingGenerationFailedError,
    EmbeddingProviderUnsupportedError,
)

logger = get_logger(__name__)

DEFAULT_TEST_TIMEOUT_SECONDS: float = 15.0


@dataclass(frozen=True, slots=True)
class AiModelConnectionTestSuccess:
    """Successful outcome of a real connectivity test."""

    latency_ms: int
    message_fr: str
    message_en: str


def _clean_error_snippet(text: str, secret_key: str | None) -> str:
    snippet = text[:250].strip()
    if secret_key:
        snippet = snippet.replace(secret_key, "[REDACTED]")
    return snippet


def _is_anthropic(endpoint_uri: str, provider_slug: str | None = None) -> bool:
    u = endpoint_uri.strip().lower().rstrip("/")
    p = (provider_slug or "").strip().lower()
    return (
        u.endswith("/messages")
        or "anthropic.com" in u
        or ("anthropic" in p and not u.endswith("/chat/completions"))
    )


def _is_gemini_native(endpoint_uri: str, provider_slug: str | None = None) -> bool:
    u = endpoint_uri.strip().lower().rstrip("/")
    p = (provider_slug or "").strip().lower()
    if "googleapis.com" in u:
        return "/v1beta/openai" not in u
    return "gemini" in p and "native" in p


def _normalize_chat_url(
    endpoint_uri: str,
    protocol_mode: LlmProtocolMode,
    model_name: str,
    provider_slug: str | None = None,
) -> str:
    base = endpoint_uri.strip().rstrip("/")
    if protocol_mode == "anthropic_messages" or _is_anthropic(base, provider_slug):
        if base.endswith("/messages"):
            return base
        return f"{base}/messages" if base.endswith("/v1") else f"{base}/v1/messages"

    if protocol_mode == "gemini_native" or _is_gemini_native(base, provider_slug):
        model_part = model_name if model_name.startswith("models/") else f"models/{model_name}"
        if ":generateContent" in base:
            return base
        if "/v1beta" in base:
            return f"{base}/{model_part}:generateContent"
        return f"{base}/v1beta/{model_part}:generateContent"

    if base.endswith(("/chat/completions", "/api/chat", "/messages")):
        return base
    if base.endswith(("/v1beta/openai", "/openai", "/v1")):
        return f"{base}/chat/completions"
    if base.endswith("/api"):
        return f"{base[:-4].rstrip('/')}/v1/chat/completions"
    return f"{base}/v1/chat/completions"


def _build_legacy_local_chat_url(endpoint_uri: str) -> str:
    clean = endpoint_uri.strip().rstrip("/")
    for suffix in ("/v1/chat/completions", "/chat/completions", "/v1", "/api/chat", "/api"):
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)].rstrip("/")
            break
    return f"{clean}/api/chat"


async def _test_chat_connection(
    *,
    http_client: httpx.AsyncClient,
    endpoint_uri: str,
    protocol_mode: LlmProtocolMode,
    model_name: str,
    api_key: str | None,
    provider_slug: str | None,
    timeout_seconds: float,
    instance: str,
) -> AiModelConnectionTestSuccess:
    target_url = _normalize_chat_url(endpoint_uri, protocol_mode, model_name, provider_slug)
    headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
    body: dict[str, Any]

    if protocol_mode == "anthropic_messages" or _is_anthropic(endpoint_uri, provider_slug):
        headers["anthropic-version"] = "2023-06-01"
        if api_key:
            headers["x-api-key"] = api_key
        body = {
            "model": model_name,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
    elif protocol_mode == "gemini_native" or _is_gemini_native(endpoint_uri, provider_slug):
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

    t0 = time.perf_counter()
    try:
        resp = await http_client.post(
            target_url,
            json=body,
            headers=headers,
            timeout=timeout_seconds,
        )
        if (
            resp.status_code == 404
            and protocol_mode == "openai_compatible"
            and not _is_anthropic(endpoint_uri, provider_slug)
            and not _is_gemini_native(endpoint_uri, provider_slug)
        ):
            fallback_url = _build_legacy_local_chat_url(endpoint_uri)
            if fallback_url != target_url:
                resp = await http_client.post(
                    fallback_url,
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "ping"}],
                        "stream": False,
                    },
                    headers=headers,
                    timeout=timeout_seconds,
                )
        latency_ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))
    except httpx.TimeoutException as exc:
        logger.warning("llm_connection_test_timeout", endpoint=target_url, model=model_name)
        raise ModelConnectionTimeoutError(
            detail_override=(
                f"Délai d'attente dépassé lors de la connexion à '{target_url}' (timeout)."
            ),
            instance=instance,
        ) from exc
    except httpx.NetworkError as exc:
        logger.warning(
            "llm_connection_test_network_error",
            endpoint=target_url,
            model=model_name,
            error_type=type(exc).__name__,
        )
        raise ModelConnectionNetworkError(
            detail_override=f"Erreur réseau lors de la tentative de connexion à '{target_url}'.",
            instance=instance,
        ) from exc

    if resp.status_code in (401, 403):
        snippet = _clean_error_snippet(resp.text, api_key)
        logger.warning(
            "llm_connection_test_auth_failed",
            endpoint=target_url,
            status_code=resp.status_code,
            latency_ms=latency_ms,
        )
        raise ModelConnectionAuthFailedError(
            detail_override=(
                f"Authentification refusée par le fournisseur ({resp.status_code}): {snippet}"
            ),
            instance=instance,
            latency_ms=latency_ms,
        )

    if resp.status_code == 404:
        snippet = _clean_error_snippet(resp.text, api_key)
        logger.warning("llm_connection_test_not_found", endpoint=target_url, latency_ms=latency_ms)
        raise ModelConnectionNotFoundError(
            detail_override=(
                f"Modèle '{model_name}' ou endpoint introuvable sur {target_url} "
                f"(HTTP 404): {snippet}"
            ),
            instance=instance,
            latency_ms=latency_ms,
        )

    if resp.status_code == 429:
        snippet = _clean_error_snippet(resp.text, api_key)
        logger.warning(
            "llm_connection_test_rate_limited", endpoint=target_url, latency_ms=latency_ms
        )
        raise ModelConnectionRateLimitedError(
            detail_override=(
                f"Quota ou limite de débit dépassée sur {target_url} (HTTP 429): {snippet}"
            ),
            instance=instance,
            latency_ms=latency_ms,
        )

    if resp.status_code != 200:
        snippet = _clean_error_snippet(resp.text, api_key)
        logger.warning(
            "llm_connection_test_upstream_error",
            endpoint=target_url,
            status_code=resp.status_code,
            latency_ms=latency_ms,
        )
        raise ModelConnectionUpstreamError(
            detail_override=(
                f"Le fournisseur a retourné une erreur HTTP {resp.status_code}: {snippet}"
            ),
            instance=instance,
            latency_ms=latency_ms,
        )

    p_label = provider_slug or "fournisseur"
    return AiModelConnectionTestSuccess(
        latency_ms=latency_ms,
        message_fr=(
            f"✅ Connexion réussie au modèle « {model_name} » ({p_label}) sur {endpoint_uri} — "
            f"Réponse reçue en {latency_ms} ms."
        ),
        message_en=(
            f"✅ Successfully connected to model '{model_name}' ({p_label}) at {endpoint_uri} — "
            f"Response received in {latency_ms} ms."
        ),
    )


async def _test_embedding_connection(
    *,
    http_client: httpx.AsyncClient,
    endpoint_uri: str,
    protocol_mode: LlmProtocolMode,
    model_name: str,
    api_key: str | None,
    provider_slug: str | None,
    timeout_seconds: float,
    instance: str,
) -> AiModelConnectionTestSuccess:
    assert_embedding_usage_supported(
        provider_slug=provider_slug or "",
        protocol_mode=protocol_mode,
    )

    adapter: EmbeddingPort
    if protocol_mode == "gemini_native" or _is_gemini_native(endpoint_uri, provider_slug):
        adapter = HttpxGeminiNativeEmbeddingAdapter(
            http_client=http_client,
            endpoint_uri=endpoint_uri,
            model_name=model_name,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
    else:
        adapter = HttpxOpenAiCompatibleEmbeddingAdapter(
            http_client=http_client,
            endpoint_uri=endpoint_uri,
            model_name=model_name,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    t0 = time.perf_counter()
    try:
        await adapter.embed(["orcia connection test"])
        latency_ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))
    except (EmbeddingDimensionMismatchError, EmbeddingProviderUnsupportedError):
        raise
    except EmbeddingGenerationFailedError as exc:
        latency_ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))
        err_msg = str(exc)
        if "HTTP 401" in err_msg or "HTTP 403" in err_msg:
            raise ModelConnectionAuthFailedError(
                detail_override=err_msg, instance=instance, latency_ms=latency_ms
            ) from exc
        if "HTTP 404" in err_msg:
            raise ModelConnectionNotFoundError(
                detail_override=err_msg, instance=instance, latency_ms=latency_ms
            ) from exc
        if "HTTP 429" in err_msg:
            raise ModelConnectionRateLimitedError(
                detail_override=err_msg, instance=instance, latency_ms=latency_ms
            ) from exc
        if isinstance(exc.__cause__, httpx.TimeoutException) or "Timeout" in err_msg:
            raise ModelConnectionTimeoutError(
                detail_override=(
                    f"Délai d'attente dépassé (timeout) sur l'endpoint d'embeddings : {err_msg}"
                ),
                instance=instance,
                latency_ms=latency_ms,
            ) from exc
        if "Network error" in err_msg:
            raise ModelConnectionNetworkError(detail_override=err_msg, instance=instance) from exc
        raise ModelConnectionUpstreamError(
            detail_override=err_msg, instance=instance, latency_ms=latency_ms
        ) from exc
    except httpx.TimeoutException as exc:
        raise ModelConnectionTimeoutError(
            detail_override="Délai d'attente dépassé (timeout) sur l'endpoint d'embeddings.",
            instance=instance,
        ) from exc
    except httpx.NetworkError as exc:
        raise ModelConnectionNetworkError(
            detail_override="Erreur réseau lors de l'appel à l'endpoint d'embeddings.",
            instance=instance,
        ) from exc

    return AiModelConnectionTestSuccess(
        latency_ms=latency_ms,
        message_fr=(
            f"✅ Connexion réussie au modèle d'embedding « {model_name} » "
            f"(dimension 1024 validée) — Réponse en {latency_ms} ms."
        ),
        message_en=(
            f"✅ Successfully connected to embedding model '{model_name}' "
            f"(1024-dim validated) — Response in {latency_ms} ms."
        ),
    )


async def test_ai_model_endpoint_connection(
    *,
    http_client: httpx.AsyncClient,
    endpoint_uri: str,
    protocol_mode: LlmProtocolMode,
    model_name: str,
    usage: Literal["chat", "embedding"] = "chat",
    api_key: str | None = None,
    provider_slug: str | None = None,
    timeout_seconds: float = DEFAULT_TEST_TIMEOUT_SECONDS,
    instance: str = "/api/v1/settings/ai-models/test",
) -> AiModelConnectionTestSuccess:
    """Execute real minimal non-blocking connection test for chat or embedding models."""
    cleaned_uri = endpoint_uri.strip().rstrip("/")
    validate_safe_llm_endpoint_url(cleaned_uri, instance=instance)

    if usage == "embedding":
        return await _test_embedding_connection(
            http_client=http_client,
            endpoint_uri=cleaned_uri,
            protocol_mode=protocol_mode,
            model_name=model_name.strip(),
            api_key=api_key,
            provider_slug=provider_slug,
            timeout_seconds=timeout_seconds,
            instance=instance,
        )

    return await _test_chat_connection(
        http_client=http_client,
        endpoint_uri=cleaned_uri,
        protocol_mode=protocol_mode,
        model_name=model_name.strip(),
        api_key=api_key,
        provider_slug=provider_slug,
        timeout_seconds=timeout_seconds,
        instance=instance,
    )


# Prevent pytest from collecting this function as a test
test_ai_model_endpoint_connection.__test__ = False  # type: ignore[attr-defined]


__all__ = [
    "AiModelConnectionTestSuccess",
    "test_ai_model_endpoint_connection",
]
