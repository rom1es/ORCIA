"""Shared AI Model Discovery Types & Ollama Tags Parser (`Story 19.2`, `Story 26.6a`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ModelUsageHint = Literal["chat", "embedding", "unknown"]
MAX_PAGINATED_MODELS = 250


@dataclass(frozen=True, slots=True)
class DiscoveredModel:
    """Standardized representation of a discovered model returned by a provider."""

    id: str
    display_name: str | None = None
    description: str | None = None
    usage_hint: ModelUsageHint = "unknown"
    owned_by: str | None = None
    supports_tools: bool = False


def parse_ollama_tags_response(body: dict[str, Any]) -> list[DiscoveredModel]:
    """Parse Ollama `/api/tags` payload into normalized models (`ACTION_ITEM-26.4`)."""
    models: list[DiscoveredModel] = []
    for item in body.get("models", []):
        mname = str(item.get("name") or item.get("model") or "")
        if not mname:
            continue
        models.append(
            DiscoveredModel(
                id=mname, display_name=mname, usage_hint="unknown", supports_tools=False
            )
        )
    return sorted(models, key=lambda m: m.id.lower())


__all__ = [
    "DiscoveredModel",
    "MAX_PAGINATED_MODELS",
    "ModelUsageHint",
    "parse_ollama_tags_response",
]
