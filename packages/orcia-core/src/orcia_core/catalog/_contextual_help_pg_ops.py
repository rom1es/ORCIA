"""Async resolution and mutation helpers for `ContextualHelpResolutionService` (`Story 9.5`)."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from orcia_core.catalog._internal.sql_contextual_help import (
    list_pg_help_articles_sql,
    publish_hot_help_article_sql,
    rollback_help_article_sql,
)
from orcia_core.catalog.contextual_help_loader import (
    dict_to_help_article,
    parse_declarative_help_markdown,
)
from orcia_core.catalog.contextual_help_models import (
    HelpArticleCatalogItem,
    HelpArticleLayer,
    HelpLanguageCode,
    build_help_redis_cache_key,
    normalize_help_pack,
)
from orcia_core.catalog.contextual_help_redis import (
    get_cached_help_article_async,
    set_cached_help_article_async,
)
from orcia_core.catalog.contextual_help_resolver import (
    collect_matching_articles,
    merge_matched_layers,
    resolve_overview_fallback,
)
from orcia_core.catalog.errors import ResourceNotFoundError

if TYPE_CHECKING:
    from orcia_core.catalog.contextual_help import ContextualHelpResolutionService


def publish_hot_version_sync_op(
    service: ContextualHelpResolutionService,
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
    existing = service._articles_by_id.get(resource_id)
    if existing is None:
        raise ResourceNotFoundError(
            detail_code="ERR_HELP_ARTICLE_ID_NOT_FOUND_DETAIL",
            detail_params={"resource_id": resource_id},
        )
    service._history_by_id.setdefault(resource_id, []).append(existing)
    digest = hashlib.sha256(new_markdown_body.encode("utf-8")).hexdigest()
    cas_key = f"cas/{digest}"
    service._cas_blobs[cas_key] = new_markdown_body
    parsed_update = parse_declarative_help_markdown(new_markdown_body)
    updated = HelpArticleCatalogItem(
        resource_id=existing.resource_id,
        uri=existing.uri,
        title=new_title,
        version=new_version,
        lang=existing.lang,
        layer=layer if layer is not None else existing.layer,
        pack_name=existing.pack_name,
        bound_routes=existing.bound_routes,
        summary_what_for=new_summary_what_for,
        step_by_step_items=(parsed_update.step_by_step_items or existing.step_by_step_items),
        key_terms_items=parsed_update.key_terms_items or existing.key_terms_items,
        faq_items=parsed_update.faq_items or existing.faq_items,
        cas_key=cas_key,
        sha256=digest,
        markdown_body=new_markdown_body,
        previous_version=existing.version,
        previous_cas_key=existing.cas_key,
        is_autonomous_generated=is_autonomous_generated,
        autonomous_run_id=autonomous_run_id,
        contract_label=contract_label,
        trigger_label=trigger_label,
        real_example_text=parsed_update.real_example_text or existing.real_example_text,
        common_pitfalls_items=(
            parsed_update.common_pitfalls_items or existing.common_pitfalls_items
        ),
    )
    service._articles_by_id[resource_id] = updated
    service._invalidate_redis_keys(updated)
    return updated


async def publish_hot_version_async_op(
    service: ContextualHelpResolutionService,
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
    """Async publish `@v(N+1)` synced across PG18 `catalog_items`, memory, and Redis."""
    if service._engine is not None:
        pg_dict = await publish_hot_help_article_sql(
            service._engine,
            resource_id=resource_id,
            new_version=new_version,
            new_title=new_title,
            new_summary_what_for=new_summary_what_for,
            new_markdown_body=new_markdown_body,
            layer=layer,
        )
        if pg_dict is not None:
            art = dict_to_help_article(pg_dict)
            service._articles_by_id[resource_id] = art
            await service._invalidate_redis_keys_async(art)
            return art
    updated = service.publish_hot_version(
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
    await service._invalidate_redis_keys_async(updated)
    return updated


async def rollback_to_previous_version_async_op(
    service: ContextualHelpResolutionService, resource_id: str
) -> HelpArticleCatalogItem:
    """Async 1-click Rollback restoring `@v(N-1)` in PG18 & flushing Redis."""
    if service._engine is not None:
        pg_dict = await rollback_help_article_sql(service._engine, resource_id=resource_id)
        if pg_dict is not None:
            restored = dict_to_help_article(pg_dict)
            service._articles_by_id[resource_id] = restored
            await service._invalidate_redis_keys_async(restored)
            return restored
    restored = service.rollback_to_previous_version(resource_id)
    await service._invalidate_redis_keys_async(restored)
    return restored


async def resolve_for_route_async_op(
    service: ContextualHelpResolutionService,
    *,
    route: str,
    pack: str = "core",
    lang: HelpLanguageCode = "fr",
) -> Any:
    """Resolve contextual help using Redis cache + PG18 `catalog_items` with lazy seed."""
    norm_pack = normalize_help_pack(pack)
    cache_key = build_help_redis_cache_key(route, norm_pack, lang)
    cached_hit = await get_cached_help_article_async(service._redis_client, cache_key)
    if cached_hit is not None:
        cached_art, layers = cached_hit
        return service._to_resolution_result(
            route=route,
            pack=norm_pack,
            lang=lang,
            cache_key=cache_key,
            cache_hit=True,
            merged_layers=layers,
            article=cached_art,
        )

    if service._engine is not None:
        pg_rows = await list_pg_help_articles_sql(service._engine, lang=lang)
        if not pg_rows and service._articles_by_id:
            seeded = await service.ensure_seeded_in_postgres18_async()
            if seeded > 0:
                pg_rows = await list_pg_help_articles_sql(service._engine, lang=lang)
        pool = dict(service._articles_by_id)
        for row in pg_rows:
            pg_art = dict_to_help_article(row)
            pool[pg_art.resource_id] = pg_art
        matching = collect_matching_articles(route=route, pack=norm_pack, lang=lang, articles=pool)
        if not matching:
            matching = [resolve_overview_fallback(pool, route=route, lang=lang)]
        resolved, merged_layers = merge_matched_layers(matching)
        await set_cached_help_article_async(
            service._redis_client, cache_key, resolved, merged_layers
        )
        return service._to_resolution_result(
            route=route,
            pack=norm_pack,
            lang=lang,
            cache_key=cache_key,
            cache_hit=False,
            merged_layers=merged_layers,
            article=resolved,
        )

    res = service.resolve_for_route(route=route, pack=norm_pack, lang=lang)
    await set_cached_help_article_async(
        service._redis_client, cache_key, res.active_article, res.merged_layers
    )
    return res
