"""Asynchronous connection tester for chat and embedding AI models (`AD-24.3`, `Story 26.1`)."""

from __future__ import annotations

import time
from typing import Literal

import httpx

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.ai_models_connection_helpers import (
    AiModelConnectionTestSuccess,
    build_chat_connection_probe,
    raise_for_chat_http_status,
)
from orcia_core.orchestration.ai_models_crypto import validate_safe_llm_endpoint_url
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
    build_legacy_local_chat_url as _build_legacy_local_chat_url,
)
from orcia_core.orchestration.ai_models_urls import is_anthropic_provider as _is_anthropic
from orcia_core.orchestration.ai_models_urls import is_gemini_native_provider as _is_gemini_native
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
    target_url, headers, body = build_chat_connection_probe(
        endpoint_uri=endpoint_uri,
        protocol_mode=protocol_mode,
        model_name=model_name,
        api_key=api_key,
        provider_slug=provider_slug,
    )
    t0 = time.perf_counter()
    try:
        p_url, p_headers, ext = await prepare_pinned_http_request(
            http_client, target_url, headers, instance=instance
        )
        resp = await http_client.post(
            p_url, json=body, headers=p_headers, timeout=timeout_seconds, extensions=ext
        )
        if (
            resp.status_code == 404
            and protocol_mode == "openai_compatible"
            and not _is_anthropic(endpoint_uri, provider_slug)
            and not _is_gemini_native(endpoint_uri, provider_slug)
        ):
            fallback_url = _build_legacy_local_chat_url(endpoint_uri)
            if fallback_url != target_url:
                fb_url, fb_headers, fb_ext = await prepare_pinned_http_request(
                    http_client, fallback_url, headers, instance=instance
                )
                resp = await http_client.post(
                    fb_url,
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "ping"}],
                        "stream": False,
                    },
                    headers=fb_headers,
                    timeout=timeout_seconds,
                    extensions=fb_ext,
                )
        latency_ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))
    except httpx.TimeoutException as exc:
        logger.warning("llm_connection_test_timeout", endpoint=target_url, model=model_name)
        raise ModelConnectionTimeoutError(
            detail_override=f"Timeout while connecting to '{target_url}'.",
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
            detail_override=f"Network error while connecting to '{target_url}'.",
            instance=instance,
        ) from exc

    if resp.status_code != 200:
        raise_for_chat_http_status(
            status_code=resp.status_code,
            response_text=resp.text,
            api_key=api_key,
            target_url=target_url,
            model_name=model_name,
            latency_ms=latency_ms,
            instance=instance,
        )
    p_label = provider_slug or "provider"
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
    assert_embedding_usage_supported(provider_slug=provider_slug or "", protocol_mode=protocol_mode)
    validate_safe_llm_endpoint_url(endpoint_uri, instance=instance)
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
                detail_override=f"Timeout on embedding endpoint: {err_msg}",
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
            detail_override="Timeout on embedding endpoint.", instance=instance
        ) from exc
    except httpx.NetworkError as exc:
        raise ModelConnectionNetworkError(
            detail_override="Network error on embedding endpoint.", instance=instance
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


test_ai_model_endpoint_connection.__test__ = False  # type: ignore[attr-defined]

__all__ = ["AiModelConnectionTestSuccess", "test_ai_model_endpoint_connection"]
