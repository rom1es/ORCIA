"""Redis 7.4 Speed-2 semantic search cache helpers (`TTL 300s`, `Story 24.3`).

Pure helper supporting both `redis.asyncio.Redis` and sync `redis.Redis` clients
without introducing hard SDK dependencies in `orcia_core` domain types (`AD-19`).
"""

from __future__ import annotations

import inspect
import json
from dataclasses import asdict
from typing import Any, Literal, cast

from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.core.rag.speed2_redis_cache")

SPEED2_REDIS_TTL_SECONDS: int = 300


def serialize_speed2_hits(hits: tuple[Any, ...]) -> str:
    """Serialize `FederatedSearchHit` tuples into compact JSON for Redis storage."""
    return json.dumps([asdict(hit) for hit in hits], ensure_ascii=False)


def deserialize_speed2_hits(raw: Any, hit_factory: type[Any]) -> tuple[Any, ...] | None:
    """Deserialize JSON payload from Redis into `FederatedSearchHit` tuple."""
    if not raw:
        return None
    text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        return None
    items: list[Any] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        tier_val = 2 if int(entry.get("speed_tier", 2)) == 2 else 1
        items.append(
            hit_factory(
                item_id=str(entry["item_id"]),
                family=entry["family"],
                title=str(entry["title"]),
                snippet=str(entry["snippet"]),
                workspace_id=str(entry["workspace_id"]),
                screen_route=str(entry["screen_route"]),
                deep_link_uri=str(entry["deep_link_uri"]),
                speed_tier=cast(Literal[1, 2], tier_val),
                locked_top=bool(entry.get("locked_top", False)),
                score=float(entry.get("score", 0.5)),
                badge=entry.get("badge"),
                highlight_duration_ms=int(entry.get("highlight_duration_ms", 2000)),
                opens_contextual_help_column=bool(entry.get("opens_contextual_help_column", False)),
            )
        )
    return tuple(items)


def get_speed2_cached_sync(
    redis_client: Any | None,
    cache_key: str,
    hit_factory: type[Any],
) -> tuple[Any, ...] | None:
    """Best-effort sync Redis GET for Speed 2 cache (skips awaitable async clients cleanly)."""
    if redis_client is None:
        return None
    try:
        res = redis_client.get(cache_key)
        if inspect.isawaitable(res):
            if hasattr(res, "close"):
                res.close()
            return None
        return deserialize_speed2_hits(res, hit_factory)
    except Exception as exc:
        logger.warning("speed2_redis_get_sync_failed", key=cache_key, error=str(exc))
        return None


def set_speed2_cached_sync(
    redis_client: Any | None,
    cache_key: str,
    hits: tuple[Any, ...],
    *,
    ttl_seconds: int = SPEED2_REDIS_TTL_SECONDS,
) -> None:
    """Best-effort sync Redis SETEX (`300s`) for Speed 2 cache."""
    if redis_client is None:
        return
    try:
        payload = serialize_speed2_hits(hits)
        res = redis_client.set(cache_key, payload, ex=ttl_seconds)
        if inspect.isawaitable(res) and hasattr(res, "close"):
            res.close()
    except Exception as exc:
        logger.warning("speed2_redis_set_sync_failed", key=cache_key, error=str(exc))


async def get_speed2_cached_async(
    redis_client: Any | None,
    cache_key: str,
    hit_factory: type[Any],
) -> tuple[Any, ...] | None:
    """Async Redis GET for Speed 2 semantic search cache (`TTL 300s`)."""
    if redis_client is None:
        return None
    try:
        res = redis_client.get(cache_key)
        raw = await res if inspect.isawaitable(res) else res
        return deserialize_speed2_hits(raw, hit_factory)
    except Exception as exc:
        logger.warning("speed2_redis_get_async_failed", key=cache_key, error=str(exc))
        return None


async def set_speed2_cached_async(
    redis_client: Any | None,
    cache_key: str,
    hits: tuple[Any, ...],
    *,
    ttl_seconds: int = SPEED2_REDIS_TTL_SECONDS,
) -> None:
    """Async Redis SET (`ex=300`) for Speed 2 semantic search cache."""
    if redis_client is None:
        return
    try:
        payload = serialize_speed2_hits(hits)
        res = redis_client.set(cache_key, payload, ex=ttl_seconds)
        if inspect.isawaitable(res):
            await res
    except Exception as exc:
        logger.warning("speed2_redis_set_async_failed", key=cache_key, error=str(exc))
