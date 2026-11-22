"""Zero-Token Native Tool-Calling Capability Discovery & Defaults (`D5 + R7`, `AD-24.8`)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from orcia_core.orchestration.ai_models_urls import (
    is_anthropic_provider,
    is_gemini_native_provider,
)


def is_non_v1_ollama_endpoint(endpoint_uri: str, provider_slug: str | None = None) -> bool:
    """Return True for native Ollama endpoints not targeting `/v1` OpenAI compatibility."""
    u = (endpoint_uri or "").strip().lower().rstrip("/")
    p = (provider_slug or "").strip().lower()
    path = urlparse(u).path.lower().rstrip("/")
    if path.endswith("/v1") or "/v1/" in path:
        return False
    return "ollama" in p or ":11434" in u or path.endswith(("/api/chat", "/api/tags", "/api"))


def infer_default_supports_tools(
    *,
    endpoint_uri: str,
    protocol_mode: str = "openai_compatible",
    provider_slug: str | None = None,
    usage: str = "chat",
    model_name: str = "",
) -> bool:
    """Infer deterministic 0-token `supports_tools` default (`D5 + R7`, `ACTION_ITEM-26.4`)."""
    if usage == "embedding":
        return False
    if protocol_mode == "gemini_native" or is_gemini_native_provider(endpoint_uri, provider_slug):
        return False
    if is_non_v1_ollama_endpoint(endpoint_uri, provider_slug):
        return False
    m_low = (model_name or "").strip().lower()
    if any(tok in m_low for tok in ("embed", "bge-", "e5-large", "nomic-embed", "mxbai-embed")):
        return False
    if protocol_mode == "anthropic_messages" or is_anthropic_provider(endpoint_uri, provider_slug):
        return True
    return True


def detect_discovered_model_supports_tools(
    raw_item: dict[str, Any],
    *,
    protocol_mode: str,
    endpoint_uri: str,
    provider_slug: str | None,
    usage_hint: str = "unknown",
    model_id: str = "",
) -> bool:
    """Inspect 0-token provider metadata for `supports_tools`, honoring `ACTION_ITEM-26.4`."""
    if usage_hint == "embedding":
        return False
    if protocol_mode == "gemini_native" or is_gemini_native_provider(endpoint_uri, provider_slug):
        return False
    if is_non_v1_ollama_endpoint(endpoint_uri, provider_slug):
        return False

    explicit = raw_item.get("supports_tools")
    if isinstance(explicit, bool):
        return explicit
    caps = raw_item.get("capabilities")
    if isinstance(caps, dict):
        for key in ("tools", "tool_calling", "function_calling"):
            if isinstance(caps.get(key), bool):
                return bool(caps[key])
    features = raw_item.get("supported_features")
    if isinstance(features, list):
        norm = {str(f).strip().lower() for f in features}
        if "tools" in norm or "tool_calling" in norm or "function_calling" in norm:
            return True
    return infer_default_supports_tools(
        endpoint_uri=endpoint_uri,
        protocol_mode=protocol_mode,
        provider_slug=provider_slug,
        usage="chat",
        model_name=model_id,
    )


__all__ = [
    "detect_discovered_model_supports_tools",
    "infer_default_supports_tools",
    "is_non_v1_ollama_endpoint",
]
