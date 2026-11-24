"""Models, cache-key builder & default candidates for `TwoSpeedFederatedSearchService`."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from orcia_core.rag._rag_locales import get_rag_locale_bundle

SearchScopeMode = Literal["SCREEN", "WORKSPACE", "ALL_WORKSPACES"]
SearchFamilyKey = Literal[
    "FOLDERS_DISCUSSIONS",
    "PROCESSES_EXECUTIONS",
    "DELIVERABLES_ARTIFACTS",
    "SOURCES_SNIPPETS",
    "GLOSSARY_RULES",
    "AGENTS_SKILLS",
    "HELP_ACTIONS",
]

SEVEN_SEARCH_FAMILIES: tuple[SearchFamilyKey, ...] = (
    "FOLDERS_DISCUSSIONS",
    "PROCESSES_EXECUTIONS",
    "DELIVERABLES_ARTIFACTS",
    "SOURCES_SNIPPETS",
    "GLOSSARY_RULES",
    "AGENTS_SKILLS",
    "HELP_ACTIONS",
)


def normalize_search_query(query: str) -> str:
    """Normalize search query whitespace and casing."""
    return " ".join(query.strip().lower().split())


def build_speed2_redis_cache_key(
    workspace_id: str,
    query: str,
    *,
    user_id: str = "anonymous",
    user_role: str = "CONTRIBUTOR",
    scope: SearchScopeMode = "WORKSPACE",
    active_screen_route: str = "/spaces",
    locale: str = "fr",
) -> str:
    """Return deterministic multi-tenant Redis cache key (`user/role/ws/scope/route/locale`)."""
    norm = normalize_search_query(query)
    digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    clean_uid = user_id.strip() or "anonymous"
    clean_role = user_role.strip() or "CONTRIBUTOR"
    clean_ws = workspace_id.strip() or "global"
    clean_scope = scope.strip() or "WORKSPACE"
    clean_route = active_screen_route.strip() or "/spaces"
    clean_locale_raw = (locale or "fr").strip().lower().replace("_", "-")
    clean_locale = "en" if clean_locale_raw.split("-", 1)[0] == "en" else "fr"
    return (
        f"search:v2:{clean_uid}:{clean_role}:{clean_ws}:"
        f"{clean_scope}:{clean_route}:{clean_locale}:{digest}"
    )


@dataclass(frozen=True, slots=True)
class FederatedSearchCandidate:
    """Indexed item across one of the 7 federated search families (`AD-8`, `AD-21`)."""

    item_id: str
    family: SearchFamilyKey
    title: str
    snippet: str
    workspace_id: str
    screen_route: str
    deep_link_uri: str
    allowed_roles: tuple[str, ...] = (
        "PLATFORM_ADMIN",
        "BU_DIRECTOR",
        "TEAM_LEAD",
        "CONTRIBUTOR",
        "GATE_REVIEWER",
        "ONTOLOGY_STEWARD_L3",
        "OBSERVER",
    )
    embedding: tuple[float, ...] | None = None


@dataclass(frozen=True, slots=True)
class FederatedSearchHit:
    """Resolved search hit returned by `TwoSpeedFederatedSearchService`."""

    item_id: str
    family: SearchFamilyKey
    title: str
    snippet: str
    workspace_id: str
    screen_route: str
    deep_link_uri: str
    speed_tier: Literal[1, 2]
    locked_top: bool
    score: float
    badge: str | None = None
    highlight_duration_ms: int = 2000
    opens_contextual_help_column: bool = False


@dataclass(frozen=True, slots=True)
class TwoSpeedSearchReport:
    """Aggregated response of 2-speed federated search (`GET /api/v1/search`)."""

    query: str
    scope: SearchScopeMode
    hits: tuple[FederatedSearchHit, ...]
    speed1_llm_cost_usd: float
    speed2_executed: bool
    speed2_cache_hit: bool
    speed2_redis_key: str | None
    speed2_cache_ttl_seconds: int


def build_default_search_candidates(
    locale: str = "fr",
) -> tuple[FederatedSearchCandidate, ...]:
    """Build localized baseline federated search candidates."""
    bundle = get_rag_locale_bundle(locale)
    return (
        FederatedSearchCandidate(
            item_id="cand-folder-arch-1",
            family="FOLDERS_DISCUSSIONS",
            title=bundle.search_cand_folder_title,
            snippet=bundle.search_cand_folder_snippet,
            workspace_id="GLOBAL",
            screen_route="/cockpit",
            deep_link_uri="/assistant?folder=cand-folder-arch-1#focus-cand-folder-arch-1",
        ),
        FederatedSearchCandidate(
            item_id="cand-proc-spec-1",
            family="PROCESSES_EXECUTIONS",
            title=bundle.search_cand_proc_title,
            snippet=bundle.search_cand_proc_snippet,
            workspace_id="GLOBAL",
            screen_route="/processes",
            deep_link_uri="/processes?wf=ticket-to-tech-spec#focus-cand-proc-spec-1",
        ),
        FederatedSearchCandidate(
            item_id="cand-help-cockpit-1",
            family="HELP_ACTIONS",
            title=bundle.search_cand_help_title,
            snippet=bundle.search_cand_help_snippet,
            workspace_id="GLOBAL",
            screen_route="/cockpit",
            deep_link_uri="help://cockpit/overview",
        ),
        FederatedSearchCandidate(
            item_id="cand-agents-catalog-1",
            family="AGENTS_SKILLS",
            title=bundle.search_cand_agents_title,
            snippet=bundle.search_cand_agents_snippet,
            workspace_id="GLOBAL",
            screen_route="/agents",
            deep_link_uri="/agents",
        ),
    )


DEFAULT_SEARCH_CANDIDATES: tuple[FederatedSearchCandidate, ...] = build_default_search_candidates(
    "fr"
)
