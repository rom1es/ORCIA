"""Story 9.5 — Hybrid Contextual Help (`HelpArticle` in `catalog_items` + `cas/<sha256>`)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from orcia_core.catalog._contextual_help_pg_ops import (
    publish_hot_version_async_op,
    publish_hot_version_sync_op,
    resolve_for_route_async_op,
    rollback_to_previous_version_async_op,
)
from orcia_core.catalog._internal.sql_contextual_help import seed_help_articles_to_pg18_sql
from orcia_core.catalog.contextual_help_loader import (
    load_git_help_articles,
    parse_declarative_help_markdown,
)
from orcia_core.catalog.contextual_help_models import (
    HELP_ITEM_TYPE,
    LAYER_PRECEDENCE,
    ContextualHelpResolutionResult,
    HelpArticleCatalogItem,
    HelpArticleLayer,
    HelpLanguageCode,
    build_help_redis_cache_key,
    is_version_strictly_newer,
    normalize_help_pack,
    normalize_help_route,
)
from orcia_core.catalog.contextual_help_redis import (
    invalidate_help_redis_keys_async,
    invalidate_help_redis_keys_sync,
)
from orcia_core.catalog.contextual_help_resolver import (
    build_assistant_prefill,
    collect_matching_articles,
    merge_matched_layers,
    resolve_overview_fallback,
)
from orcia_core.catalog.errors import ResourceNotFoundError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

BASE_CONTEXTUAL_HELP_ROUTES: tuple[str, ...] = (
    "/cockpit",
    "/assistant",
    "/inbox",
    "/spaces",
    "/workspaces",
    "/processes",
    "/gates",
    "/agents",
    "/catalog",
    "/finops",
    "/activity",
    "/ontology",
    "/organization",
    "/profile",
    "/settings",
    "/showcase",
    "/wizards",
    "/help",
)

__all__ = [
    "BASE_CONTEXTUAL_HELP_ROUTES",
    "HELP_ITEM_TYPE",
    "LAYER_PRECEDENCE",
    "ContextualHelpResolutionResult",
    "ContextualHelpResolutionService",
    "HelpArticleCatalogItem",
    "HelpArticleLayer",
    "HelpLanguageCode",
    "build_help_redis_cache_key",
    "is_version_strictly_newer",
    "normalize_help_pack",
    "normalize_help_route",
    "parse_declarative_help_markdown",
]


class ContextualHelpResolutionService:
    """Service managing Git-seeded `HELP_ARTICLE` items, CAS blobs, Redis cache, and Rollback."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        redis_client: Any | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        self._articles_by_id: dict[str, HelpArticleCatalogItem] = {}
        self._cas_blobs: dict[str, str] = {}
        self._redis_cache: dict[str, HelpArticleCatalogItem] = {}
        self._history_by_id: dict[str, list[HelpArticleCatalogItem]] = {}
        self._redis_client = redis_client
        self._engine = engine
        root = repo_root or self._detect_repo_root()
        if root is not None:
            self.seed_from_git_directories(root)

    def _invalidate_redis_keys(self, article: HelpArticleCatalogItem) -> None:
        self._redis_cache.clear()
        invalidate_help_redis_keys_sync(self._redis_client, article)

    async def _invalidate_redis_keys_async(self, article: HelpArticleCatalogItem) -> None:
        self._redis_cache.clear()
        await invalidate_help_redis_keys_async(self._redis_client, article)

    @staticmethod
    def _detect_repo_root() -> Path | None:
        curr = Path(__file__).resolve()
        for parent in curr.parents:
            if (parent / "docs" / "help").exists():
                return parent
        return None

    def seed_from_git_directories(self, repo_root: Path) -> int:
        """Idempotently load `docs/help/{fr,en}/*.md` and `packs/*/help/`."""
        seeded_count = 0
        for article in load_git_help_articles(repo_root):
            if self.upsert_seeded_article(article):
                seeded_count += 1
        return seeded_count

    async def ensure_seeded_in_postgres18_async(self) -> int:
        """Idempotently seed Git `HELP_ARTICLE` records into PostgreSQL 18 `catalog_items`."""
        if self._engine is None or not self._articles_by_id:
            return 0
        return await seed_help_articles_to_pg18_sql(self._engine, self._articles_by_id.values())

    def upsert_seeded_article(self, article: HelpArticleCatalogItem) -> bool:
        """Upsert a Git-seeded `HELP_ARTICLE` without ever overwriting a newer `@v(N+1)` version."""
        existing = self._articles_by_id.get(article.resource_id)
        if existing is not None and is_version_strictly_newer(existing.version, article.version):
            return False
        self._cas_blobs[article.cas_key] = article.markdown_body
        self._articles_by_id[article.resource_id] = article
        self._redis_cache.clear()
        return True

    def publish_hot_version(
        self,
        *,
        resource_id: str,
        new_version: str,
        new_title: str,
        new_summary_what_for: str,
        new_markdown_body: str,
        layer: HelpArticleLayer | None = None,
        is_autonomous_generated: bool = False,
        autonomous_run_id: str | None = None,
        contract_label: str | None = None,
        trigger_label: str | None = None,
    ) -> HelpArticleCatalogItem:
        """Publish a hot `@v(N+1)` help article in `cas/<sha256>` and preserve `@v(N-1)`."""
        return publish_hot_version_sync_op(
            self,
            resource_id=resource_id,
            new_version=new_version,
            new_title=new_title,
            new_summary_what_for=new_summary_what_for,
            new_markdown_body=new_markdown_body,
            layer=layer,
            is_autonomous_generated=is_autonomous_generated,
            autonomous_run_id=autonomous_run_id,
            contract_label=contract_label,
            trigger_label=trigger_label,
        )

    def rollback_to_previous_version(self, resource_id: str) -> HelpArticleCatalogItem:
        """Execute a 1-click Rollback restoring `@v(N-1)` and flushing the Redis help cache."""
        history = self._history_by_id.get(resource_id, [])
        if not history:
            raise ResourceNotFoundError(
                detail_code="ERR_HELP_ARTICLE_PREVIOUS_VERSION_NOT_FOUND",
                detail_params={"resource_id": resource_id},
            )
        restored = history.pop()
        self._articles_by_id[resource_id] = restored
        self._invalidate_redis_keys(restored)
        return restored

    def _to_resolution_result(
        self,
        *,
        route: str,
        pack: str,
        lang: HelpLanguageCode,
        cache_key: str,
        cache_hit: bool,
        merged_layers: tuple[HelpArticleLayer, ...],
        article: HelpArticleCatalogItem,
    ) -> ContextualHelpResolutionResult:
        has_rb = bool(self._history_by_id.get(article.resource_id) or article.previous_version)
        return ContextualHelpResolutionResult(
            route=route,
            pack=pack,
            lang=lang,
            redis_cache_key=cache_key,
            cache_hit=cache_hit,
            merged_layers=merged_layers,
            active_article=article,
            rollback_available=has_rb,
            ask_assistant_prefill=build_assistant_prefill(route, article.title, lang),
            is_autonomous_generated=article.is_autonomous_generated,
            run_id=article.autonomous_run_id,
            contract_label=article.contract_label,
            trigger_label=article.trigger_label,
            previous_version_available=has_rb,
        )

    def resolve_for_route(
        self,
        *,
        route: str,
        pack: str = "core",
        lang: HelpLanguageCode = "fr",
    ) -> ContextualHelpResolutionResult:
        """Resolve contextual help in `< 10 ms` using Redis cache and 4-layer merge (`AD-14`)."""
        cache_key = build_help_redis_cache_key(route, pack, lang)
        cached = self._redis_cache.get(cache_key)
        matching_layers = collect_matching_articles(
            route=route, pack=pack, lang=lang, articles=self._articles_by_id
        )
        merged_layer_names = tuple(a.layer for a in matching_layers)
        if cached is not None:
            return self._to_resolution_result(
                route=route,
                pack=pack,
                lang=lang,
                cache_key=cache_key,
                cache_hit=True,
                merged_layers=merged_layer_names or (cached.layer,),
                article=cached,
            )
        if not matching_layers:
            matching_layers = [
                resolve_overview_fallback(self._articles_by_id, route=route, lang=lang)
            ]
        resolved_article, merged_layer_names = merge_matched_layers(matching_layers)
        self._redis_cache[cache_key] = resolved_article
        return self._to_resolution_result(
            route=route,
            pack=pack,
            lang=lang,
            cache_key=cache_key,
            cache_hit=False,
            merged_layers=merged_layer_names,
            article=resolved_article,
        )

    async def publish_hot_version_async(
        self,
        *,
        resource_id: str,
        new_version: str,
        new_title: str,
        new_summary_what_for: str,
        new_markdown_body: str,
        layer: HelpArticleLayer | None = None,
        is_autonomous_generated: bool = False,
        autonomous_run_id: str | None = None,
        contract_label: str | None = None,
        trigger_label: str | None = None,
    ) -> HelpArticleCatalogItem:
        return await publish_hot_version_async_op(
            self,
            resource_id=resource_id,
            new_version=new_version,
            new_title=new_title,
            new_summary_what_for=new_summary_what_for,
            new_markdown_body=new_markdown_body,
            layer=layer,
            is_autonomous_generated=is_autonomous_generated,
            autonomous_run_id=autonomous_run_id,
            contract_label=contract_label,
            trigger_label=trigger_label,
        )

    async def rollback_to_previous_version_async(self, resource_id: str) -> HelpArticleCatalogItem:
        return await rollback_to_previous_version_async_op(self, resource_id)

    async def resolve_for_route_async(
        self,
        *,
        route: str,
        pack: str = "core",
        lang: HelpLanguageCode = "fr",
    ) -> ContextualHelpResolutionResult:
        return cast(
            ContextualHelpResolutionResult,
            await resolve_for_route_async_op(self, route=route, pack=pack, lang=lang),
        )
