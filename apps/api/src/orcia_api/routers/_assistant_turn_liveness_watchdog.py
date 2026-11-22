"""Liveness Watchdog & Cross-Worker Stop Pub/Sub Listener (`Story 26.3`)."""

from __future__ import annotations

import asyncio
import contextlib

from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry


async def watch_liveness_and_stop(
    registry: RedisAssistantTurnRegistry,
    *,
    turn_id: str,
    liveness_ttl_s: int,
    producer_task: asyncio.Task[None],
) -> None:
    """Refresh turn liveness TTL and cancel `producer_task` on cross-worker Redis stop."""
    beat_s = min(1.0, max(0.2, liveness_ttl_s / 3.0))
    pubsub = None
    redis_cli = getattr(registry, "_redis", None)
    if redis_cli is not None:
        with contextlib.suppress(Exception):
            pubsub = redis_cli.pubsub()
            await pubsub.subscribe(registry.stop_channel(turn_id))
    try:
        while not producer_task.done():
            await registry.refresh_liveness(turn_id, ttl_seconds=liveness_ttl_s)
            if await registry.is_stop_requested(turn_id) is not None:
                producer_task.cancel()
                return
            if pubsub is not None:
                with contextlib.suppress(Exception):
                    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=beat_s)
                    if msg is not None:
                        producer_task.cancel()
                        return
                    continue
            await asyncio.sleep(beat_s)
    except asyncio.CancelledError:
        return
    finally:
        if pubsub is not None:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(registry.stop_channel(turn_id))
                await pubsub.aclose()
