"""Provider-Specific Async Model Discovery Dialects (`Story 19.2`, `Story 26.1`)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._ai_models_discovery_common import (
    MAX_PAGINATED_MODELS,
    DiscoveredModel,
    ModelUsageHint,
    parse_ollama_tags_response,
)
from orcia_core.orchestration.ai_models_capabilities import detect_discovered_model_supports_tools
from orcia_core.orchestration.ai_models_errors import (
    ModelDiscoveryAuthFailedError,
    ModelDiscoveryEndpointNotFoundError,
    ModelDiscoveryNetworkError,
)
from orcia_core.orchestration.ai_models_pinned_http import prepare_pinned_http_request
from orcia_core.orchestration.ai_models_urls import is_gemini_interactions_only_model

logger = get_logger(__name__)


async def discover_gemini_native(
    *,
    http_client: httpx.AsyncClient,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
    instance: str,
) -> list[DiscoveredModel]:
    """Discover Gemini Native models with pagination."""
    models_url = f"{base_url}/models" if "/v1beta" in base_url else f"{base_url}/v1beta/models"
    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["x-goog-api-key"] = api_key
    ranked_models: list[tuple[int, DiscoveredModel]] = []
    page_token: str | None = None

    while True:
        params: dict[str, str] = {"pageToken": page_token} if page_token else {}
        try:
            p_url, p_headers, ext = await prepare_pinned_http_request(
                http_client, models_url, headers, instance=instance
            )
            res = await http_client.get(
                p_url, headers=p_headers, params=params, timeout=timeout_seconds, extensions=ext
            )
        except httpx.TimeoutException as exc:
            logger.warning(
                "model_discovery_gemini_timeout", endpoint=urlparse(base_url).netloc, error=str(exc)
            )
            raise ModelDiscoveryNetworkError(
                detail_override="Timeout while discovering Google Gemini models.",
                instance=instance,
            ) from exc
        except httpx.RequestError as exc:
            logger.warning(
                "model_discovery_gemini_network_error",
                endpoint=urlparse(base_url).netloc,
                error=str(exc),
            )
            raise ModelDiscoveryNetworkError(
                detail_override=f"Network error discovering Google Gemini models: {exc}.",
                instance=instance,
            ) from exc

        if res.status_code in (401, 403):
            raise ModelDiscoveryAuthFailedError(instance=instance)
        if res.status_code == 404:
            raise ModelDiscoveryEndpointNotFoundError(instance=instance)
        if res.status_code >= 400:
            raise ModelDiscoveryNetworkError(
                detail_override=f"Google Gemini returned HTTP {res.status_code}.",
                instance=instance,
            )

        data: dict[str, Any] = res.json()
        for m in data.get("models", []):
            raw_name = str(m.get("name") or "")
            if not raw_name:
                continue
            model_id = raw_name[len("models/") :] if raw_name.startswith("models/") else raw_name
            methods = list(m.get("supportedGenerationMethods") or [])
            is_embed = "embedContent" in methods or "batchEmbedContents" in methods
            is_chat = "generateContent" in methods or "createInteraction" in methods
            hint: ModelUsageHint = (
                "embedding"
                if (is_embed and not is_chat)
                else ("chat" if (is_chat and not is_embed) else "unknown")
            )
            is_standard_chat = ("generateContent" in methods) and not (
                is_gemini_interactions_only_model(model_id)
            )
            rank = (
                0
                if (hint == "chat" and is_standard_chat)
                else (1 if hint in ("chat", "embedding") else 2)
            )
            ranked_models.append(
                (
                    rank,
                    DiscoveredModel(
                        id=model_id,
                        display_name=m.get("displayName") or model_id,
                        description=m.get("description"),
                        usage_hint=hint,
                    ),
                )
            )
        page_token = data.get("nextPageToken")
        if not page_token or len(ranked_models) >= MAX_PAGINATED_MODELS:
            break
    return [m for _, m in sorted(ranked_models, key=lambda item: (item[0], item[1].id.lower()))]


async def discover_anthropic_messages(
    *,
    http_client: httpx.AsyncClient,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
    instance: str,
) -> list[DiscoveredModel]:
    """Discover Anthropic Messages chat models."""
    models_url = f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"
    headers: dict[str, str] = {"Accept": "application/json", "anthropic-version": "2023-06-01"}
    if api_key:
        headers["x-api-key"] = api_key
    try:
        p_url, p_headers, ext = await prepare_pinned_http_request(
            http_client, models_url, headers, instance=instance
        )
        res = await http_client.get(
            p_url, headers=p_headers, timeout=timeout_seconds, extensions=ext
        )
    except httpx.TimeoutException as exc:
        logger.warning(
            "model_discovery_anthropic_timeout", endpoint=urlparse(base_url).netloc, error=str(exc)
        )
        raise ModelDiscoveryNetworkError(
            detail_override="Timeout while discovering Anthropic models.",
            instance=instance,
        ) from exc
    except httpx.RequestError as exc:
        logger.warning(
            "model_discovery_anthropic_network_error",
            endpoint=urlparse(base_url).netloc,
            error=str(exc),
        )
        raise ModelDiscoveryNetworkError(
            detail_override=f"Network error discovering Anthropic models: {exc}.",
            instance=instance,
        ) from exc

    if res.status_code in (401, 403):
        raise ModelDiscoveryAuthFailedError(instance=instance)
    if res.status_code == 404:
        raise ModelDiscoveryEndpointNotFoundError(instance=instance)
    if res.status_code >= 400:
        raise ModelDiscoveryNetworkError(
            detail_override=f"Anthropic returned HTTP {res.status_code}.",
            instance=instance,
        )

    items = res.json().get("data", [])
    models = [
        DiscoveredModel(
            id=str(item.get("id") or ""),
            display_name=item.get("display_name") or str(item.get("id") or ""),
            usage_hint="chat",
            supports_tools=detect_discovered_model_supports_tools(
                item,
                protocol_mode="anthropic_messages",
                endpoint_uri=base_url,
                provider_slug="anthropic",
                usage_hint="chat",
                model_id=str(item.get("id") or ""),
            ),
        )
        for item in items
        if str(item.get("id") or "")
    ]
    return sorted(models, key=lambda m: m.id.lower())


async def discover_openai_compatible(
    *,
    http_client: httpx.AsyncClient,
    base_url: str,
    provider_slug: str | None,
    api_key: str | None,
    timeout_seconds: float,
    instance: str,
) -> list[DiscoveredModel]:
    """Discover OpenAI-compatible or local `/api/tags` models."""
    if base_url.endswith("/v1"):
        models_url = f"{base_url}/models"
        tags_url = f"{base_url[:-3].rstrip('/')}/api/tags"
    else:
        models_url = f"{base_url}/v1/models"
        tags_url = f"{base_url}/api/tags"

    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        p_url, p_headers, ext = await prepare_pinned_http_request(
            http_client, models_url, headers, instance=instance
        )
        res = await http_client.get(
            p_url, headers=p_headers, timeout=timeout_seconds, extensions=ext
        )
    except httpx.TimeoutException as exc:
        logger.warning(
            "model_discovery_openai_timeout", endpoint=urlparse(base_url).netloc, error=str(exc)
        )
        raise ModelDiscoveryNetworkError(
            detail_override="Timeout while discovering OpenAI-compatible models.",
            instance=instance,
        ) from exc
    except httpx.RequestError as exc:
        logger.warning(
            "model_discovery_openai_network_error",
            endpoint=urlparse(base_url).netloc,
            error=str(exc),
        )
        raise ModelDiscoveryNetworkError(
            detail_override=f"Network error discovering models: {exc}.",
            instance=instance,
        ) from exc

    if res.status_code == 404:
        p_slug = (provider_slug or "").lower()
        is_local_tags_candidate = (
            "ollama" in p_slug or "11434" in base_url or "localhost" in base_url
        )
        if is_local_tags_candidate:
            try:
                t_url, t_headers, t_ext = await prepare_pinned_http_request(
                    http_client, tags_url, {"Accept": "application/json"}, instance=instance
                )
                tags_res = await http_client.get(
                    t_url, headers=t_headers, timeout=timeout_seconds, extensions=t_ext
                )
                if tags_res.status_code == 200:
                    return parse_ollama_tags_response(tags_res.json())
            except Exception as exc:
                logger.warning("model_discovery_tags_fallback_failed", error=str(exc))
        raise ModelDiscoveryEndpointNotFoundError(instance=instance)

    if res.status_code in (401, 403):
        raise ModelDiscoveryAuthFailedError(instance=instance)
    if res.status_code >= 400:
        raise ModelDiscoveryNetworkError(
            detail_override=f"Provider returned HTTP {res.status_code}.",
            instance=instance,
        )

    body: dict[str, Any] = res.json()
    if isinstance(body.get("data"), list):
        models = [
            DiscoveredModel(
                id=str(item.get("id") or ""),
                display_name=str(item.get("id") or ""),
                owned_by=item.get("owned_by"),
                usage_hint="unknown",
                supports_tools=detect_discovered_model_supports_tools(
                    item,
                    protocol_mode="openai_compatible",
                    endpoint_uri=base_url,
                    provider_slug=provider_slug,
                    usage_hint="unknown",
                    model_id=str(item.get("id") or ""),
                ),
            )
            for item in body["data"]
            if str(item.get("id") or "")
        ]
        return sorted(models, key=lambda m: m.id.lower())
    if isinstance(body.get("models"), list):
        return parse_ollama_tags_response(body)
    return []


__all__ = [
    "DiscoveredModel",
    "MAX_PAGINATED_MODELS",
    "ModelUsageHint",
    "discover_anthropic_messages",
    "discover_gemini_native",
    "discover_openai_compatible",
    "parse_ollama_tags_response",
]
