"""Two-Speed Federated & Contextual Search (`Cmd+K`, Zero Layout Shift, `Story 9.3`, `24.3`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag._speed2_redis_cache import (
    SPEED2_REDIS_TTL_SECONDS,
    get_speed2_cached_async,
    get_speed2_cached_sync,
    set_speed2_cached_async,
    set_speed2_cached_sync,
)
from orcia_core.rag._two_speed_search_helpers import (
    compute_speed2_semantic_hits,
    prepare_authorized_and_speed1_hits,
)
from orcia_core.rag._two_speed_search_models import (
    DEFAULT_SEARCH_CANDIDATES,
    SEVEN_SEARCH_FAMILIES,
    FederatedSearchCandidate,
    FederatedSearchHit,
    SearchFamilyKey,
    SearchScopeMode,
    TwoSpeedSearchReport,
    build_speed2_redis_cache_key,
    normalize_search_query,
)

__all__ = [
    "DEFAULT_SEARCH_CANDIDATES",
    "SEVEN_SEARCH_FAMILIES",
    "FederatedSearchCandidate",
    "FederatedSearchHit",
    "SearchFamilyKey",
    "SearchScopeMode",
    "TwoSpeedFederatedSearchService",
    "TwoSpeedSearchReport",
    "build_speed2_redis_cache_key",
    "normalize_search_query",
]


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

    @staticmethod
    def _empty_speed2_report(
        query: str, scope: SearchScopeMode, speed1_hits: Sequence[FederatedSearchHit]
    ) -> TwoSpeedSearchReport:
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
        norm_q, words, authorized, speed1_hits, speed1_ids = prepare_authorized_and_speed1_hits(
            candidates=self._candidates,
            query=query,
            scope=scope,
            active_workspace_id=active_workspace_id,
            active_screen_route=active_screen_route,
            user_role=user_role,
            extra_candidates=extra_candidates,
        )
        should_run_speed2 = include_speed2 and (len(words) >= 3 or force_semantic) and bool(norm_q)
        if not should_run_speed2:
            return self._empty_speed2_report(query, scope, speed1_hits)

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
            return self._empty_speed2_report(query, scope, speed1_hits)

        speed2_tuple = compute_speed2_semantic_hits(
            authorized=authorized,
            speed1_ids=speed1_ids,
            query_embedding=query_embedding,
            locale=locale,
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
        norm_q, words, authorized, speed1_hits, speed1_ids = prepare_authorized_and_speed1_hits(
            candidates=self._candidates,
            query=query,
            scope=scope,
            active_workspace_id=active_workspace_id,
            active_screen_route=active_screen_route,
            user_role=user_role,
            extra_candidates=extra_candidates,
        )
        should_run_speed2 = include_speed2 and (len(words) >= 3 or force_semantic) and bool(norm_q)
        if not should_run_speed2:
            return self._empty_speed2_report(query, scope, speed1_hits)

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
            return self._empty_speed2_report(query, scope, speed1_hits)

        speed2_tuple = compute_speed2_semantic_hits(
            authorized=authorized,
            speed1_ids=speed1_ids,
            query_embedding=query_embedding,
            locale=locale,
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
