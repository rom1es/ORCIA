"""Domain models & route normalization for Hybrid Contextual Help (`Story 9.5`, `REM-19`)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HelpArticleLayer = Literal["BASE", "PACK", "WORKSPACE", "USER"]
HelpLanguageCode = Literal["fr", "en"]

HELP_ITEM_TYPE: str = "HELP_ARTICLE"
LAYER_PRECEDENCE: dict[HelpArticleLayer, int] = {
    "BASE": 1,
    "PACK": 2,
    "WORKSPACE": 3,
    "USER": 4,
}


@dataclass(frozen=True, slots=True)
class HelpArticleCatalogItem:
    """Domain representation of a `HELP_ARTICLE` stored in `catalog_items` + `cas/<sha256>`."""

    resource_id: str
    uri: str
    title: str
    version: str
    lang: HelpLanguageCode
    layer: HelpArticleLayer
    pack_name: str | None
    bound_routes: tuple[str, ...]
    summary_what_for: str
    step_by_step_items: tuple[str, ...]
    key_terms_items: tuple[str, ...]
    faq_items: tuple[str, ...]
    cas_key: str
    sha256: str
    markdown_body: str
    item_type: str = HELP_ITEM_TYPE
    previous_version: str | None = None
    previous_cas_key: str | None = None
    is_autonomous_generated: bool = False
    autonomous_run_id: str | None = None
    contract_label: str | None = None
    trigger_label: str | None = None
    real_example_text: str | None = None
    common_pitfalls_items: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextualHelpResolutionResult:
    """Resolved contextual help payload returned by `GET /api/v1/help/resolve` (`< 10 ms`)."""

    route: str
    pack: str
    lang: HelpLanguageCode
    redis_cache_key: str
    cache_hit: bool
    merged_layers: tuple[HelpArticleLayer, ...]
    active_article: HelpArticleCatalogItem
    rollback_available: bool
    ask_assistant_prefill: str
    is_autonomous_generated: bool = False
    run_id: str | None = None
    contract_label: str | None = None
    trigger_label: str | None = None
    previous_version_available: bool = False


def normalize_help_pack(pack: str) -> str:
    """Normalize legacy `orcia-core` pack identifier onto canonical `core`."""
    cleaned = pack.strip()
    if not cleaned or cleaned == "orcia-core":
        return "core"
    return cleaned


def normalize_help_route(route: str) -> tuple[str, tuple[str, ...]]:
    """Return normalized route plus ordered canonical candidate routes for matching."""
    raw = (route or "").split("?", 1)[0].split("#", 1)[0].strip()
    if not raw or raw == "/":
        return "/", ("/", "/cockpit")
    cleaned = raw.rstrip("/") if len(raw) > 1 else raw
    candidates: list[str] = [cleaned]
    if cleaned.startswith("/workspaces/") and cleaned.endswith("/sources"):
        candidates.extend(["/workspaces/$wsId/sources", "/workspaces", "/mes-espaces/$id/sources"])
    elif cleaned.startswith("/workspaces/"):
        candidates.extend(["/workspaces/$wsId", "/workspaces"])
    elif cleaned.startswith("/mes-espaces/") and cleaned.endswith("/sources"):
        candidates.extend(["/mes-espaces/$id/sources", "/workspaces"])
    elif cleaned.startswith("/processes/studio/"):
        candidates.extend(["/processes/studio/$workflowId", "/processes"])
    elif cleaned.startswith("/processes/vsm/"):
        candidates.extend(["/processes/vsm/$vsmId", "/processes"])
    elif cleaned.startswith("/settings/"):
        candidates.append("/settings")
    elif cleaned.startswith("/spaces/"):
        candidates.append("/spaces")
    return cleaned, tuple(dict.fromkeys(candidates))


def build_help_redis_cache_key(route: str, pack: str, lang: str) -> str:
    """Build the canonical Redis cache key `help:route:<route>:<pack>:<lang>` (`Story 9.5`)."""
    norm_route = route.strip() or "/cockpit"
    norm_pack = normalize_help_pack(pack)
    norm_lang = lang.strip().lower() or "fr"
    return f"help:route:{norm_route}:{norm_pack}:{norm_lang}"


def _parse_version_tuple(version_str: str) -> tuple[int, ...]:
    cleaned = version_str.strip().lstrip("v@")
    parts: list[int] = []
    for token in cleaned.split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0, 0, 0)


def is_version_strictly_newer(candidate_version: str, baseline_version: str) -> bool:
    """Return True if `candidate_version` (`@v(N+1)`) is strictly newer than `baseline_version`."""
    return _parse_version_tuple(candidate_version) > _parse_version_tuple(baseline_version)
