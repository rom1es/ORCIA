"""Redis cache helpers for contextual help (`help:route:<route>:<pack>:<lang>`)."""

from __future__ import annotations

import inspect
import json
from typing import Any

from orcia_core.catalog.contextual_help_loader import (
    dict_to_help_article,
    serialize_redis_help_payload,
)
from orcia_core.catalog.contextual_help_models import (
    HelpArticleCatalogItem,
    HelpArticleLayer,
    build_help_redis_cache_key,
    normalize_help_pack,
)
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.catalog.contextual_help_redis")


def invalidate_help_redis_keys_sync(
    redis_client: Any | None, article: HelpArticleCatalogItem
) -> None:
    """Best-effort sync Redis invalidation for all routes bound to `article`."""
    if redis_client is None:
        return
    pack = normalize_help_pack(article.pack_name or "core")
    for rt in article.bound_routes:
        rkey = build_help_redis_cache_key(rt, pack, article.lang)
        try:
            res = redis_client.delete(rkey)
            if inspect.isawaitable(res) and hasattr(res, "close"):
                res.close()
        except Exception as exc:
            logger.warning("help_redis_delete_sync_failed", key=rkey, error=str(exc))


async def invalidate_help_redis_keys_async(
    redis_client: Any | None, article: HelpArticleCatalogItem
) -> None:
    """Async Redis invalidation for all routes bound to `article`."""
    if redis_client is None:
        return
    pack = normalize_help_pack(article.pack_name or "core")
    for rt in article.bound_routes:
        rkey = build_help_redis_cache_key(rt, pack, article.lang)
        try:
            res = redis_client.delete(rkey)
            if inspect.isawaitable(res):
                await res
        except Exception as exc:
            logger.warning("help_redis_delete_async_failed", key=rkey, error=str(exc))


async def get_cached_help_article_async(
    redis_client: Any | None, cache_key: str
) -> tuple[HelpArticleCatalogItem, tuple[HelpArticleLayer, ...]] | None:
    """Fetch a cached contextual help entry from Redis if present."""
    if redis_client is None:
        return None
    try:
        raw_res = redis_client.get(cache_key)
        raw = await raw_res if inspect.isawaitable(raw_res) else raw_res
        if not raw:
            return None
        text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        cached_obj = json.loads(text)
        cached_art = dict_to_help_article(cached_obj["article"])
        layers = tuple(cached_obj.get("merged_layers") or (cached_art.layer,))
        return cached_art, layers
    except Exception as exc:
        logger.warning("help_redis_get_failed", key=cache_key, error=str(exc))
        return None


async def set_cached_help_article_async(
    redis_client: Any | None,
    cache_key: str,
    article: HelpArticleCatalogItem,
    merged_layers: tuple[HelpArticleLayer, ...],
) -> None:
    """Store a resolved contextual help entry in Redis with 300s TTL."""
    if redis_client is None:
        return
    try:
        payload = serialize_redis_help_payload(article, merged_layers)
        set_res = redis_client.set(cache_key, payload, ex=300)
        if inspect.isawaitable(set_res):
            await set_res
    except Exception as exc:
        logger.warning("help_redis_set_failed", key=cache_key, error=str(exc))
