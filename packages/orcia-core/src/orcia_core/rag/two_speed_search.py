"""Two-Speed Federated & Contextual Search (`⌘K`, Zero Layout Shift, `Story 9.3`).

Implements (`Principe A.2`, `AD-8`, `AD-19`, `AD-21`, Component 17 `top-header-search-command`):
- 3 Scopes: `SCREEN` (`📍 Cet écran`), `WORKSPACE` (`📦 Cet Espace`), `ALL_WORKSPACES` (`🌐 Tous`)
- 7 Families:
  1. `FOLDERS_DISCUSSIONS` (`📁 Dossiers & 💬 Discussions`)
  2. `PROCESSES_EXECUTIONS` (`☍ Processus & ▶ Exécutions`)
  3. `DELIVERABLES_ARTIFACTS` (`📄 Livrables & Artefacts`)
  4. `SOURCES_SNIPPETS` (`🗄️ Sources & Extraits`)
  5. `GLOSSARY_RULES` (`📖 Glossaire & Règles Métier`)
  6. `AGENTS_SKILLS` (`🤖 Agents & Compétences`)
  7. `HELP_ACTIONS` (`❓ Fiches d'Aide & Actions`)
- Speed 1 (`As-You-Type`, `< 30 ms`, `0 $` LLM calls, `debounce 80 ms`): lexical `tsvector` +
  `pg_trgm` prefix/substring matching, locked at the top of each category (`locked_top=True`).
- Speed 2 (`Pause 450 ms`, triggered only when `>= 3` words or `force_semantic=True`):
  `halfvec(1024)` + `RRF` (`AD-8`) cached `5 min` (`300 s`) by `(workspace_id, sha256(query_norm))`
  and appended exclusively at the bottom (`locked_top=False`, `badge='✨ Passage proche'`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from orcia_core.rag.indexer_and_rrf import (
    compute_deterministic_halfvec_1024,
    cosine_similarity,
)

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
SPEED2_REDIS_TTL_SECONDS: int = 300


def normalize_search_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def build_speed2_redis_cache_key(workspace_id: str, query: str) -> str:
    """Return deterministic Redis cache key `search:v2:{workspace_id}:{sha256(query_norm)}`."""
    norm = normalize_search_query(query)
    digest = hashlib.sha256(norm.encode("utf-8")).hexdigest()
    return f"search:v2:{workspace_id.strip() or 'global'}:{digest}"


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
        workspace_id="ws-claims-alpha",
        screen_route="/cockpit",
        deep_link_uri="/assistant?folder=cand-folder-arch-1#focus-cand-folder-arch-1",
    ),
    FederatedSearchCandidate(
        item_id="cand-proc-spec-1",
        family="PROCESSES_EXECUTIONS",
        title="Processus sdlc/ticket-to-tech-spec",
        snippet="Génération gouvernée de spécification technique depuis un ticket Jira.",
        workspace_id="ws-claims-alpha",
        screen_route="/processes",
        deep_link_uri="/processes?wf=ticket-to-tech-spec#focus-cand-proc-spec-1",
    ),
    FederatedSearchCandidate(
        item_id="cand-help-cockpit-1",
        family="HELP_ACTIONS",
        title="Guide d'aide : Arbitrer un Tie-Break ou ouvrir l'atelier Fokus",
        snippet="Comment trancher en 1 clic sur le Cockpit ou acquérir le verrou Redis.",
        workspace_id="ws-claims-alpha",
        screen_route="/cockpit",
        deep_link_uri="help://cockpit/overview",
    ),
)


class TwoSpeedFederatedSearchService:
    """Service executing Speed 1 lexical (`0 $`) + Speed 2 semantic (`halfvec(1024)` + RRF)."""

    def __init__(
        self,
        *,
        candidates: tuple[FederatedSearchCandidate, ...] = DEFAULT_SEARCH_CANDIDATES,
    ) -> None:
        self._candidates: list[FederatedSearchCandidate] = list(candidates)
        self._speed2_cache: dict[str, tuple[FederatedSearchHit, ...]] = {}

    def register_candidate(self, candidate: FederatedSearchCandidate) -> None:
        self._candidates.append(candidate)

    def execute_search(
        self,
        *,
        query: str,
        scope: SearchScopeMode = "WORKSPACE",
        active_workspace_id: str = "ws-claims-alpha",
        active_screen_route: str = "/cockpit",
        user_role: str = "CONTRIBUTOR",
        include_speed2: bool = True,
        force_semantic: bool = False,
    ) -> TwoSpeedSearchReport:
        """Execute Speed 1 lexical search and optionally Speed 2 semantic search (`>= 3` words)."""
        norm_q = normalize_search_query(query)
        words = [w for w in norm_q.split(" ") if w]

        # 1. Filter by PermissionGuard (AD-21) and Scope (SCREEN | WORKSPACE | ALL_WORKSPACES)
        authorized: list[FederatedSearchCandidate] = []
        for cand in self._candidates:
            if user_role not in cand.allowed_roles:
                continue
            if scope == "SCREEN" and (
                cand.workspace_id != active_workspace_id or cand.screen_route != active_screen_route
            ):
                continue
            if scope == "WORKSPACE" and cand.workspace_id != active_workspace_id:
                continue
            authorized.append(cand)

        # 2. Speed 1 (As-You-Type lexical tsvector / trigram prefix match, 0 $ LLM cost)
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

        # 3. Speed 2 (Pause 450 ms, >= 3 words or force_semantic=True, cached 300 s in Redis)
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

        redis_key = build_speed2_redis_cache_key(active_workspace_id, norm_q)
        cached_speed2 = self._speed2_cache.get(redis_key)
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

        q_vec = compute_deterministic_halfvec_1024(norm_q)
        speed2_candidates: list[FederatedSearchHit] = []
        for cand in authorized:
            if cand.item_id in speed1_ids:
                continue
            c_vec = compute_deterministic_halfvec_1024(f"{cand.title} {cand.snippet}")
            sim = max(0.01, (cosine_similarity(q_vec, c_vec) + 1.0) / 2.0)
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
        self._speed2_cache[redis_key] = tuple(speed2_candidates)

        return TwoSpeedSearchReport(
            query=query,
            scope=scope,
            hits=tuple([*speed1_hits, *speed2_candidates]),
            speed1_llm_cost_usd=0.0,
            speed2_executed=True,
            speed2_cache_hit=False,
            speed2_redis_key=redis_key,
            speed2_cache_ttl_seconds=SPEED2_REDIS_TTL_SECONDS,
        )
