"""Pure asynchronous AI model discovery client (`Story 19.2`, `AD-24.2`, `Story 26.1`)."""

from __future__ import annotations

import httpx

from orcia_core.orchestration.ai_models_crypto import validate_safe_llm_endpoint_url
from orcia_core.orchestration.ai_models_discovery_dialects import (
    MAX_PAGINATED_MODELS,
    DiscoveredModel,
    ModelUsageHint,
    discover_anthropic_messages,
    discover_gemini_native,
    discover_openai_compatible,
)
from orcia_core.orchestration.ai_models_records import LlmProtocolMode

DEFAULT_DISCOVERY_TIMEOUT_SECONDS = 5.0


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
        return await discover_gemini_native(
            http_client=http_client,
            base_url=cleaned_uri,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            instance=instance,
        )
    if protocol_mode == "anthropic_messages":
        return await discover_anthropic_messages(
            http_client=http_client,
            base_url=cleaned_uri,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            instance=instance,
        )
    return await discover_openai_compatible(
        http_client=http_client,
        base_url=cleaned_uri,
        provider_slug=provider_slug,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        instance=instance,
    )


__all__ = [
    "DEFAULT_DISCOVERY_TIMEOUT_SECONDS",
    "DiscoveredModel",
    "MAX_PAGINATED_MODELS",
    "ModelUsageHint",
    "discover_models_from_provider",
]
