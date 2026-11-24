"""Asynchronous connection tester for chat and embedding AI models (`AD-24.3`, `Story 26.1`)."""

from __future__ import annotations

import time
from typing import Literal

import httpx

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.ai_models_capabilities import infer_default_supports_tools
from orcia_core.orchestration.ai_models_connection_helpers import (
    AiModelConnectionTestSuccess,
    build_chat_connection_probe,
    maybe_retry_gemini_interactions_probe,
    post_pinned_probe,
    raise_for_chat_http_status,
    raise_for_embedding_connection_error,
)
from orcia_core.orchestration.ai_models_crypto import validate_safe_llm_endpoint_url
from orcia_core.orchestration.ai_models_errors import (
    ModelConnectionNetworkError,
    ModelConnectionTimeoutError,
)
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
    fallback_model_name: str | None = None,
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
        resp = await post_pinned_probe(
            http_client, target_url, headers, body, timeout_seconds, instance
        )
        if (
            resp.status_code == 404
            and protocol_mode == "openai_compatible"
            and not _is_anthropic(endpoint_uri, provider_slug)
            and not _is_gemini_native(endpoint_uri, provider_slug)
        ):
            fallback_url = _build_legacy_local_chat_url(endpoint_uri)
            if fallback_url != target_url:
                resp = await post_pinned_probe(
                    http_client,
                    fallback_url,
                    headers,
                    {
                        "model": model_name,
                        "messages": [{"role": "user", "content": "ping"}],
                        "stream": False,
                    },
                    timeout_seconds,
                    instance,
                )
        elif protocol_mode == "gemini_native" or _is_gemini_native(endpoint_uri, provider_slug):
            target_url, resp = await maybe_retry_gemini_interactions_probe(
                http_client,
                resp,
                endpoint_uri=endpoint_uri,
                target_url=target_url,
                headers=headers,
                model_name=model_name,
                timeout_seconds=timeout_seconds,
                instance=instance,
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

    if resp.status_code not in (200, 401, 403):
        fb_model = (fallback_model_name or "").strip()
        if fb_model and fb_model != model_name.strip():
            logger.warning(
                "llm_connection_test_falling_back_to_secondary",
                primary_model=model_name,
                fallback_model=fb_model,
                status_code=resp.status_code,
            )
            fb_outcome = await _test_chat_connection(
                http_client=http_client,
                endpoint_uri=endpoint_uri,
                protocol_mode=protocol_mode,
                model_name=fb_model,
                api_key=api_key,
                provider_slug=provider_slug,
                timeout_seconds=timeout_seconds,
                instance=instance,
                fallback_model_name=None,
            )
            from orcia_core.orchestration._agents_skills_locales import (
                AI_MODEL_CONNECTION_MSG_LOCALES,
            )

            ms = fb_outcome.latency_ms
            return AiModelConnectionTestSuccess(
                latency_ms=ms,
                message_fr=AI_MODEL_CONNECTION_MSG_LOCALES["fr"]["fallback_ok"].format(
                    fb_model=fb_model, ms=ms
                ),
                message_en=AI_MODEL_CONNECTION_MSG_LOCALES["en"]["fallback_ok"].format(
                    fb_model=fb_model, ms=ms
                ),
                supports_tools=fb_outcome.supports_tools,
            )

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
    detected_tools = infer_default_supports_tools(
        endpoint_uri=endpoint_uri,
        protocol_mode=protocol_mode,
        provider_slug=provider_slug,
        usage="chat",
        model_name=model_name,
    )
    from orcia_core.orchestration._agents_skills_locales import AI_MODEL_CONNECTION_MSG_LOCALES

    return AiModelConnectionTestSuccess(
        latency_ms=latency_ms,
        message_fr=AI_MODEL_CONNECTION_MSG_LOCALES["fr"]["chat_ok"].format(
            model_name=model_name, p_label=p_label, endpoint_uri=endpoint_uri, latency_ms=latency_ms
        ),
        message_en=AI_MODEL_CONNECTION_MSG_LOCALES["en"]["chat_ok"].format(
            model_name=model_name, p_label=p_label, endpoint_uri=endpoint_uri, latency_ms=latency_ms
        ),
        supports_tools=detected_tools,
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
    adapter_cls = (
        HttpxGeminiNativeEmbeddingAdapter
        if (protocol_mode == "gemini_native" or _is_gemini_native(endpoint_uri, provider_slug))
        else HttpxOpenAiCompatibleEmbeddingAdapter
    )
    adapter = adapter_cls(
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
        raise_for_embedding_connection_error(exc, instance=instance, latency_ms=latency_ms)
    except httpx.TimeoutException as exc:
        raise ModelConnectionTimeoutError(
            detail_override="Timeout on embedding endpoint.", instance=instance
        ) from exc
    except httpx.NetworkError as exc:
        raise ModelConnectionNetworkError(
            detail_override="Network error on embedding endpoint.", instance=instance
        ) from exc

    from orcia_core.orchestration._agents_skills_locales import AI_MODEL_CONNECTION_MSG_LOCALES

    return AiModelConnectionTestSuccess(
        latency_ms=latency_ms,
        message_fr=AI_MODEL_CONNECTION_MSG_LOCALES["fr"]["embed_ok"].format(
            model_name=model_name, latency_ms=latency_ms
        ),
        message_en=AI_MODEL_CONNECTION_MSG_LOCALES["en"]["embed_ok"].format(
            model_name=model_name, latency_ms=latency_ms
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
    fallback_model_name: str | None = None,
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
        fallback_model_name=fallback_model_name,
    )


test_ai_model_endpoint_connection.__test__ = False  # type: ignore[attr-defined]

__all__ = ["AiModelConnectionTestSuccess", "test_ai_model_endpoint_connection"]
