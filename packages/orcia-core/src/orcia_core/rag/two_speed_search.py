"""Two-Speed Federated & Contextual Search (`⌘K`, Zero Layout Shift, `Story 9.3`, `24.3`).

Implements (`Principe A.2`, `AD-8`, `AD-19`, `AD-21`, Component 17 `top-header-search-command`):
- 3 Scopes: `SCREEN`, `WORKSPACE`, `ALL_WORKSPACES`
- 7 Families: `FOLDERS_DISCUSSIONS` .. `HELP_ACTIONS`
- Speed 1 (`As-You-Type`, `< 30 ms`, `0 $` LLM calls)
- Speed 2 (`Pause 450 ms`, `>= 3` words or `force_semantic=True`): cached `300 s` in Redis `7.4`
  using deterministic keys isolated by `(user_id, role, workspace_id, scope, route, locale)`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag._speed2_redis_cache import (
    SPEED2_REDIS_TTL_SECONDS,
    get_speed2_cached_async,
    get_speed2_cached_sync,
    set_speed2_cached_async,
    set_speed2_cached_sync,
)
from orcia_core.rag.indexer_and_rrf import cosine_similarity

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

SEMANTIC_BADGE_FR: str = "✨ Passage proche"


def normalize_search_query(query: str) -> str:
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
    clean_locale = (locale or "fr").strip().lower() or "fr"
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


DEFAULT_SEARCH_CANDIDATES: tuple[FederatedSearchCandidate, ...] = (
    FederatedSearchCandidate(
        item_id="cand-folder-arch-1",
        family="FOLDERS_DISCUSSIONS",
        title="Dossier Architecture Paiement & Rapprochement",
        snippet="Synthèse des discussions d'architecture avec citations [S1] et [G1].",
        workspace_id="GLOBAL",
        screen_route="/cockpit",
        deep_link_uri="/assistant?folder=cand-folder-arch-1#focus-cand-folder-arch-1",
    ),
    FederatedSearchCandidate(
        item_id="cand-proc-spec-1",
        family="PROCESSES_EXECUTIONS",
        title="Processus sdlc/ticket-to-tech-spec",
        snippet="Génération gouvernée de spécification technique depuis un ticket Jira.",
        workspace_id="GLOBAL",
        screen_route="/processes",
        deep_link_uri="/processes?wf=ticket-to-tech-spec#focus-cand-proc-spec-1",
    ),
    FederatedSearchCandidate(
        item_id="cand-help-cockpit-1",
        family="HELP_ACTIONS",
        title="Guide d'aide : Arbitrer un Tie-Break ou ouvrir l'atelier Fokus",
        snippet="Comment trancher en 1 clic sur le Cockpit ou acquérir le verrou Redis.",
        workspace_id="GLOBAL",
        screen_route="/cockpit",
        deep_link_uri="help://cockpit/overview",
    ),
    FederatedSearchCandidate(
        item_id="cand-agents-catalog-1",
        family="AGENTS_SKILLS",
        title="Catalogue des Agents spécialisés & Compétences métiers",
        snippet="Créer, qualifier et exécuter des agents et compétences (skills) gouvernés.",
        workspace_id="GLOBAL",
        screen_route="/agents",
        deep_link_uri="/agents",
    ),
)


class TwoSpeedFederatedSearchService:
    """Service executing Speed 1 lexical (`0 $`) + Speed 2 semantic (`halfvec(1024)` + RRF)."""

    def __init__(
        self,
        *,
        candidates: Sequence[FederatedSearchCandidate] = (),
        embedding_port: EmbeddingPort | None = None,
        redis_client: Any | None = None,
    ) -> None:
        self._candidates: list[FederatedSearchCandidate] = list(candidates)
        self._redis_client: Any | None = redis_client
        # Used strictly when `redis_client is None` (pure unit tests without Redis container).
        self._unit_test_local_cache: dict[str, tuple[FederatedSearchHit, ...]] = {}
        self._embedding_port: EmbeddingPort | None = embedding_port

    def set_redis_client(self, redis_client: Any | None) -> None:
        """Attach the shared Composition Root Redis 7.4 client."""
        self._redis_client = redis_client
        if redis_client is not None:
            self._unit_test_local_cache.clear()

    def register_candidate(self, candidate: FederatedSearchCandidate) -> None:
        self._candidates.append(candidate)

    def _prepare_authorized_and_speed1(
        self,
        *,
        query: str,
        scope: SearchScopeMode,
        active_workspace_id: str,
        active_screen_route: str,
        user_role: str,
        extra_candidates: Sequence[FederatedSearchCandidate],
    ) -> tuple[
        str,
        list[str],
        list[FederatedSearchCandidate],
        list[FederatedSearchHit],
        set[str],
    ]:
        norm_q = normalize_search_query(query)
        words = [w for w in norm_q.split(" ") if w]

        merged_candidates: list[FederatedSearchCandidate] = list(self._candidates)
        seen_ids = {c.item_id for c in merged_candidates}
        for cand in extra_candidates:
            if cand.item_id not in seen_ids:
                merged_candidates.append(cand)
                seen_ids.add(cand.item_id)

        clean_ws = active_workspace_id.strip()
        is_global_or_empty_ws = not clean_ws or clean_ws in ("scope-global", "GLOBAL")
        authorized: list[FederatedSearchCandidate] = []
        for cand in merged_candidates:
            if user_role not in cand.allowed_roles:
                continue
            cand_matches_ws = cand.workspace_id in (clean_ws, "GLOBAL")
            if scope == "SCREEN" and (
                (not is_global_or_empty_ws and not cand_matches_ws)
                or cand.screen_route != active_screen_route
            ):
                continue
            if scope == "WORKSPACE" and not is_global_or_empty_ws and not cand_matches_ws:
                continue
            authorized.append(cand)

        speed1_hits: list[FederatedSearchHit] = []
        speed1_ids: set[str] = set()
        for cand in authorized:
            haystack = f"{cand.title} {cand.snippet}".lower()
            matched_tokens = sum(1 for w in words if w in haystack)
            if not words or matched_tokens == len(words) or (norm_q and norm_q in haystack):
                score = 1.0 + (0.1 * matched_tokens)
                speed1_ids.add(cand.item_id)
                speed1_hits.append(
                    FederatedSearchHit(
                        item_id=cand.item_id,
                        family=cand.family,
                        title=cand.title,
                        snippet=cand.snippet,
                        workspace_id=cand.workspace_id,
                        screen_route=cand.screen_route,
                        deep_link_uri=cand.deep_link_uri,
                        speed_tier=1,
                        locked_top=True,
                        score=round(score, 4),
                        badge=None,
                        highlight_duration_ms=2000,
                        opens_contextual_help_column=(cand.family == "HELP_ACTIONS"),
                    )
                )

        return norm_q, words, authorized, speed1_hits, speed1_ids

    @staticmethod
    def _compute_speed2_hits(
        *,
        authorized: list[FederatedSearchCandidate],
        speed1_ids: set[str],
        query_embedding: tuple[float, ...],
    ) -> tuple[FederatedSearchHit, ...]:
        speed2_candidates: list[FederatedSearchHit] = []
        for cand in authorized:
            if cand.item_id in speed1_ids:
                continue
            if cand.embedding is not None:
                sim = max(0.01, (cosine_similarity(query_embedding, cand.embedding) + 1.0) / 2.0)
            else:
                sim = 0.5
            speed2_candidates.append(
                FederatedSearchHit(
                    item_id=cand.item_id,
                    family=cand.family,
                    title=cand.title,
                    snippet=cand.snippet,
                    workspace_id=cand.workspace_id,
                    screen_route=cand.screen_route,
                    deep_link_uri=cand.deep_link_uri,
                    speed_tier=2,
                    locked_top=False,
                    score=round(sim, 4),
                    badge=SEMANTIC_BADGE_FR,
                    highlight_duration_ms=2000,
                    opens_contextual_help_column=(cand.family == "HELP_ACTIONS"),
                )
            )
        speed2_candidates.sort(key=lambda item: -item.score)
        return tuple(speed2_candidates)

    def execute_search(
        self,
        *,
        query: str,
        scope: SearchScopeMode = "WORKSPACE",
        active_workspace_id: str = "scope-global",
        active_screen_route: str = "/cockpit",
        user_id: str = "anonymous",
        user_role: str = "CONTRIBUTOR",
        locale: str = "fr",
        include_speed2: bool = True,
        force_semantic: bool = False,
        query_embedding: tuple[float, ...] | None = None,
        extra_candidates: Sequence[FederatedSearchCandidate] = (),
    ) -> TwoSpeedSearchReport:
        """Execute Speed 1 + Speed 2 synchronously (Redis sync or unit-test fallback)."""
        norm_q, words, authorized, speed1_hits, speed1_ids = self._prepare_authorized_and_speed1(
            query=query,
            scope=scope,
            active_workspace_id=active_workspace_id,
            active_screen_route=active_screen_route,
            user_role=user_role,
            extra_candidates=extra_candidates,
        )
        should_run_speed2 = include_speed2 and (len(words) >= 3 or force_semantic) and bool(norm_q)
        if not should_run_speed2:
            return TwoSpeedSearchReport(
                query=query,
                scope=scope,
                hits=tuple(speed1_hits),
                speed1_llm_cost_usd=0.0,
                speed2_executed=False,
                speed2_cache_hit=False,
                speed2_redis_key=None,
                speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
            )

        redis_key = build_speed2_redis_cache_key(
            active_workspace_id,
            norm_q,
            user_id=user_id,
            user_role=user_role,
            scope=scope,
            active_screen_route=active_screen_route,
            locale=locale,
        )
        cached_speed2 = (
            get_speed2_cached_sync(self._redis_client, redis_key, FederatedSearchHit)
            if self._redis_client is not None
            else self._unit_test_local_cache.get(redis_key)
        )
        if cached_speed2 is not None:
            appended = [h for h in cached_speed2 if h.item_id not in speed1_ids]
            return TwoSpeedSearchReport(
                query=query,
                scope=scope,
                hits=tuple([*speed1_hits, *appended]),
                speed1_llm_cost_usd=0.0,
                speed2_executed=True,
                speed2_cache_hit=True,
                speed2_redis_key=redis_key,
                speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
            )

        if query_embedding is None:
            return TwoSpeedSearchReport(
                query=query,
                scope=scope,
                hits=tuple(speed1_hits),
                speed1_llm_cost_usd=0.0,
                speed2_executed=False,
                speed2_cache_hit=False,
                speed2_redis_key=None,
                speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
            )

        speed2_tuple = self._compute_speed2_hits(
            authorized=authorized, speed1_ids=speed1_ids, query_embedding=query_embedding
        )
        if self._redis_client is not None:
            set_speed2_cached_sync(
                self._redis_client,
                redis_key,
                speed2_tuple,
                ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
            )
        else:
            self._unit_test_local_cache[redis_key] = speed2_tuple

        return TwoSpeedSearchReport(
            query=query,
            scope=scope,
            hits=tuple([*speed1_hits, *speed2_tuple]),
            speed1_llm_cost_usd=0.0,
            speed2_executed=True,
            speed2_cache_hit=False,
            speed2_redis_key=redis_key,
            speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
        )

    async def execute_search_async(
        self,
        *,
        query: str,
        scope: SearchScopeMode = "WORKSPACE",
        active_workspace_id: str = "scope-global",
        active_screen_route: str = "/cockpit",
        user_id: str = "anonymous",
        user_role: str = "CONTRIBUTOR",
        locale: str = "fr",
        include_speed2: bool = True,
        force_semantic: bool = False,
        query_embedding: tuple[float, ...] | None = None,
        extra_candidates: Sequence[FederatedSearchCandidate] = (),
    ) -> TwoSpeedSearchReport:
        """Execute Speed 1 + Speed 2 with async Redis 7.4 (`TTL 300s`)."""
        norm_q, words, authorized, speed1_hits, speed1_ids = self._prepare_authorized_and_speed1(
            query=query,
            scope=scope,
            active_workspace_id=active_workspace_id,
            active_screen_route=active_screen_route,
            user_role=user_role,
            extra_candidates=extra_candidates,
        )
        should_run_speed2 = include_speed2 and (len(words) >= 3 or force_semantic) and bool(norm_q)
        if not should_run_speed2:
            return TwoSpeedSearchReport(
                query=query,
                scope=scope,
                hits=tuple(speed1_hits),
                speed1_llm_cost_usd=0.0,
                speed2_executed=False,
                speed2_cache_hit=False,
                speed2_redis_key=None,
                speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
            )

        redis_key = build_speed2_redis_cache_key(
            active_workspace_id,
            norm_q,
            user_id=user_id,
            user_role=user_role,
            scope=scope,
            active_screen_route=active_screen_route,
            locale=locale,
        )
        cached_speed2 = (
            await get_speed2_cached_async(self._redis_client, redis_key, FederatedSearchHit)
            if self._redis_client is not None
            else self._unit_test_local_cache.get(redis_key)
        )
        if cached_speed2 is not None:
            appended = [h for h in cached_speed2 if h.item_id not in speed1_ids]
            return TwoSpeedSearchReport(
                query=query,
                scope=scope,
                hits=tuple([*speed1_hits, *appended]),
                speed1_llm_cost_usd=0.0,
                speed2_executed=True,
                speed2_cache_hit=True,
                speed2_redis_key=redis_key,
                speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
            )

        if query_embedding is None:
            return TwoSpeedSearchReport(
                query=query,
                scope=scope,
                hits=tuple(speed1_hits),
                speed1_llm_cost_usd=0.0,
                speed2_executed=False,
                speed2_cache_hit=False,
                speed2_redis_key=None,
                speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
            )

        speed2_tuple = self._compute_speed2_hits(
            authorized=authorized, speed1_ids=speed1_ids, query_embedding=query_embedding
        )
        if self._redis_client is not None:
            await set_speed2_cached_async(
                self._redis_client,
                redis_key,
                speed2_tuple,
                ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
            )
        else:
            self._unit_test_local_cache[redis_key] = speed2_tuple

        return TwoSpeedSearchReport(
            query=query,
            scope=scope,
            hits=tuple([*speed1_hits, *speed2_tuple]),
            speed1_llm_cost_usd=0.0,
            speed2_executed=True,
            speed2_cache_hit=False,
            speed2_redis_key=redis_key,
            speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
        )
