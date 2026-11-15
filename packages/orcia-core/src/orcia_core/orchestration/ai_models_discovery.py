"""Pure asynchronous AI model discovery client (`Story 19.2`, `AD-24.2`).

Queries provider metadata endpoints to dynamically list available models with
0 tokens consumed and 0 inference cost.
Supported protocols:
- `openai_compatible`: `GET {base}/v1/models` (OpenAI, Mistral, vLLM, Ollama),
  with fallback to `/api/tags`
- `anthropic_messages`: `GET {base}/v1/models` with `x-api-key` and `anthropic-version`
- `gemini_native`: `GET {base}/v1beta/models` with `x-goog-api-key`, `pageToken` pagination, and
  `generateContent` vs `embedContent` classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

import httpx

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.ai_models_crypto import validate_safe_llm_endpoint_url
from orcia_core.orchestration.ai_models_errors import (
    ModelDiscoveryAuthFailedError,
    ModelDiscoveryEndpointNotFoundError,
    ModelDiscoveryNetworkError,
)
from orcia_core.orchestration.ai_models_records import LlmProtocolMode

logger = get_logger(__name__)

ModelUsageHint = Literal["chat", "embedding", "unknown"]
MAX_PAGINATED_MODELS = 250
DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class DiscoveredModel:
    """Standardized representation of a discovered model returned by a provider."""

    id: str
    display_name: str | None = None
    description: str | None = None
    usage_hint: ModelUsageHint = "unknown"
    owned_by: str | None = None


async def discover_models_from_provider(
    *,
    http_client: httpx.AsyncClient,
    endpoint_uri: str,
    protocol_mode: LlmProtocolMode,
    provider_slug: str | None = None,
    api_key: str | None = None,
    timeout_seconds: float = DEFAULT_DISCOVERY_TIMEOUT_SECONDS,
    instance: str = "/api/v1/settings/ai-models/discover",
) -> list[DiscoveredModel]:
    """Query provider metadata API to list models without consuming any inference tokens."""
    cleaned_uri = endpoint_uri.strip().rstrip("/")
    validate_safe_llm_endpoint_url(cleaned_uri, instance=instance)

    if protocol_mode == "gemini_native":
        return await _discover_gemini_native(
            http_client=http_client,
            base_url=cleaned_uri,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            instance=instance,
        )
    if protocol_mode == "anthropic_messages":
        return await _discover_anthropic_messages(
            http_client=http_client,
            base_url=cleaned_uri,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            instance=instance,
        )
    return await _discover_openai_compatible(
        http_client=http_client,
        base_url=cleaned_uri,
        provider_slug=provider_slug,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        instance=instance,
    )


async def _discover_gemini_native(
    *,
    http_client: httpx.AsyncClient,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
    instance: str,
) -> list[DiscoveredModel]:
    models_url = f"{base_url}/models" if "/v1beta" in base_url else f"{base_url}/v1beta/models"

    headers: dict[str, str] = {
        "Accept": "application/json",
    }
    if api_key:
        headers["x-goog-api-key"] = api_key

    all_models: list[DiscoveredModel] = []
    page_token: str | None = None

    while True:
        params: dict[str, str] = {}
        if page_token:
            params["pageToken"] = page_token

        try:
            res = await http_client.get(
                models_url,
                headers=headers,
                params=params,
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            logger.warning(
                "model_discovery_gemini_timeout",
                endpoint=urlparse(base_url).netloc,
                error=str(exc),
            )
            raise ModelDiscoveryNetworkError(
                detail_override=(
                    "Délai d'attente dépassé lors de la découverte des modèles Google Gemini."
                ),
                instance=instance,
            ) from exc
        except httpx.RequestError as exc:
            logger.warning(
                "model_discovery_gemini_network_error",
                endpoint=urlparse(base_url).netloc,
                error=str(exc),
            )
            raise ModelDiscoveryNetworkError(
                detail_override=(
                    f"Erreur réseau lors de la découverte des modèles Google Gemini : {exc}."
                ),
                instance=instance,
            ) from exc

        if res.status_code in (401, 403):
            raise ModelDiscoveryAuthFailedError(instance=instance)
        if res.status_code == 404:
            raise ModelDiscoveryEndpointNotFoundError(instance=instance)
        if res.status_code >= 400:
            raise ModelDiscoveryNetworkError(
                detail_override=f"Google Gemini a renvoyé le statut HTTP {res.status_code}.",
                instance=instance,
            )

        data: dict[str, Any] = res.json()
        models_list = data.get("models", [])
        for m in models_list:
            raw_name = str(m.get("name") or "")
            if not raw_name:
                continue
            model_id = raw_name[len("models/") :] if raw_name.startswith("models/") else raw_name
            disp = m.get("displayName") or model_id
            desc = m.get("description")
            methods = list(m.get("supportedGenerationMethods") or [])
            is_embed = "embedContent" in methods or "batchEmbedContents" in methods
            is_chat = "generateContent" in methods
            if is_embed and not is_chat:
                hint: ModelUsageHint = "embedding"
            elif is_chat and not is_embed:
                hint = "chat"
            else:
                hint = "unknown"

            all_models.append(
                DiscoveredModel(
                    id=model_id,
                    display_name=disp,
                    description=desc,
                    usage_hint=hint,
                )
            )

        page_token = data.get("nextPageToken")
        if not page_token or len(all_models) >= MAX_PAGINATED_MODELS:
            break

    return sorted(all_models, key=lambda m: m.id.lower())


async def _discover_anthropic_messages(
    *,
    http_client: httpx.AsyncClient,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
    instance: str,
) -> list[DiscoveredModel]:
    models_url = f"{base_url}/models" if base_url.endswith("/v1") else f"{base_url}/v1/models"

    headers: dict[str, str] = {
        "Accept": "application/json",
        "anthropic-version": "2023-06-01",
    }
    if api_key:
        headers["x-api-key"] = api_key

    try:
        res = await http_client.get(models_url, headers=headers, timeout=timeout_seconds)
    except httpx.TimeoutException as exc:
        logger.warning(
            "model_discovery_anthropic_timeout",
            endpoint=urlparse(base_url).netloc,
            error=str(exc),
        )
        raise ModelDiscoveryNetworkError(
            detail_override="Délai d'attente dépassé lors de la découverte des modèles Anthropic.",
            instance=instance,
        ) from exc
    except httpx.RequestError as exc:
        logger.warning(
            "model_discovery_anthropic_network_error",
            endpoint=urlparse(base_url).netloc,
            error=str(exc),
        )
        raise ModelDiscoveryNetworkError(
            detail_override=f"Erreur réseau lors de la découverte des modèles Anthropic : {exc}.",
            instance=instance,
        ) from exc

    if res.status_code in (401, 403):
        raise ModelDiscoveryAuthFailedError(instance=instance)
    if res.status_code == 404:
        raise ModelDiscoveryEndpointNotFoundError(instance=instance)
    if res.status_code >= 400:
        raise ModelDiscoveryNetworkError(
            detail_override=f"Anthropic a renvoyé le statut HTTP {res.status_code}.",
            instance=instance,
        )

    data: dict[str, Any] = res.json()
    items = data.get("data", [])
    models: list[DiscoveredModel] = []
    for item in items:
        mid = str(item.get("id") or "")
        if not mid:
            continue
        disp = item.get("display_name") or mid
        models.append(
            DiscoveredModel(
                id=mid,
                display_name=disp,
                usage_hint="chat",  # Anthropic models are chat/completion only (D6)
            )
        )
    return sorted(models, key=lambda m: m.id.lower())


async def _discover_openai_compatible(
    *,
    http_client: httpx.AsyncClient,
    base_url: str,
    provider_slug: str | None,
    api_key: str | None,
    timeout_seconds: float,
    instance: str,
) -> list[DiscoveredModel]:
    if base_url.endswith("/v1"):
        models_url = f"{base_url}/models"
        ollama_tags_url = f"{base_url[:-3].rstrip('/')}/api/tags"
    else:
        models_url = f"{base_url}/v1/models"
        ollama_tags_url = f"{base_url}/api/tags"

    headers: dict[str, str] = {
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    res: httpx.Response | None = None
    try:
        res = await http_client.get(models_url, headers=headers, timeout=timeout_seconds)
    except httpx.TimeoutException as exc:
        logger.warning(
            "model_discovery_openai_timeout",
            endpoint=urlparse(base_url).netloc,
            error=str(exc),
        )
        raise ModelDiscoveryNetworkError(
            detail_override=(
                "Délai d'attente dépassé lors de la découverte des modèles OpenAI-compatible."
            ),
            instance=instance,
        ) from exc
    except httpx.RequestError as exc:
        logger.warning(
            "model_discovery_openai_network_error",
            endpoint=urlparse(base_url).netloc,
            error=str(exc),
        )
        raise ModelDiscoveryNetworkError(
            detail_override=f"Erreur réseau lors de la découverte des modèles : {exc}.",
            instance=instance,
        ) from exc

    if res.status_code == 404:
        # Check if Ollama /api/tags fallback is viable
        p_slug = (provider_slug or "").lower()
        is_ollama_candidate = "ollama" in p_slug or "11434" in base_url or "localhost" in base_url
        if is_ollama_candidate:
            try:
                tags_res = await http_client.get(
                    ollama_tags_url, headers={"Accept": "application/json"}, timeout=timeout_seconds
                )
                if tags_res.status_code == 200:
                    return _parse_ollama_tags_response(tags_res.json())
            except Exception:  # noqa: S110
                pass
        raise ModelDiscoveryEndpointNotFoundError(instance=instance)

    if res.status_code in (401, 403):
        raise ModelDiscoveryAuthFailedError(instance=instance)
    if res.status_code >= 400:
        raise ModelDiscoveryNetworkError(
            detail_override=f"Le fournisseur a renvoyé le statut HTTP {res.status_code}.",
            instance=instance,
        )

    body: dict[str, Any] = res.json()
    if "data" in body and isinstance(body["data"], list):
        models: list[DiscoveredModel] = []
        for item in body["data"]:
            mid = str(item.get("id") or "")
            if not mid:
                continue
            owned = item.get("owned_by")
            models.append(
                DiscoveredModel(
                    id=mid,
                    display_name=mid,
                    owned_by=owned,
                    usage_hint="unknown",
                )
            )
        return sorted(models, key=lambda m: m.id.lower())

    if "models" in body and isinstance(body["models"], list):
        return _parse_ollama_tags_response(body)

    return []


def _parse_ollama_tags_response(body: dict[str, Any]) -> list[DiscoveredModel]:
    models: list[DiscoveredModel] = []
    for item in body.get("models", []):
        mname = str(item.get("name") or item.get("model") or "")
        if not mname:
            continue
        models.append(
            DiscoveredModel(
                id=mname,
                display_name=mname,
                usage_hint="unknown",
            )
        )
    return sorted(models, key=lambda m: m.id.lower())


__all__ = [
    "DEFAULT_DISCOVERY_TIMEOUT_SECONDS",
    "DiscoveredModel",
    "ModelUsageHint",
    "discover_models_from_provider",
]
