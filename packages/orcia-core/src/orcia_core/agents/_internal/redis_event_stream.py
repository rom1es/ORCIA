"""Async SSE Event Stream Broker with optional Redis 7.4 Pub/Sub fan-out (`Story 16.2`).

Implements `ReflexiveEventStreamPort` using non-blocking `asyncio.Queue` subscribers plus
optional Redis 7.4 Pub/Sub + 24h history list (`orcia:reflexive:history:{execution_id}`).
Never splits text by spaces; preserves event payloads verbatim.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any, cast

from orcia_core.observability.logging import get_logger
from orcia_core.ports.reflexive_runtime_ports import ReflexiveEventStreamPort, TraceEventKind

logger = get_logger("orcia.agents.redis_event_stream")

_TERMINAL_KINDS: frozenset[str] = frozenset(
    {
        TraceEventKind.LOOP_COMPLETED.value,
        TraceEventKind.LOOP_CANCELLED.value,
    }
)
_PAUSE_KIND: str = TraceEventKind.WRITE_PREVIEW_REQUESTED.value
_REDIS_TTL_SECONDS = 86_400


class ReflexiveEventStreamBroker(ReflexiveEventStreamPort):
    """Non-blocking `AsyncIterator` event broker with optional Redis 7.4 persistence/PubSub."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = (redis_url or "").strip() or None
        self._history_by_execution: dict[str, list[dict[str, Any]]] = {}
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    async def publish_event(self, execution_id: str, event_payload: dict[str, Any]) -> None:
        """Append event to history, notify live `asyncio.Queue` listeners, and publish to Redis."""
        copied = dict(event_payload)
        history = self._history_by_execution.setdefault(execution_id, [])
        history.append(copied)

        queues = list(self._subscribers.get(execution_id, ()))
        for queue in queues:
            queue.put_nowait(copied)

        if self._redis_url is not None:
            await self._publish_to_redis(execution_id, copied)

    async def subscribe_events(self, execution_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield buffered and live `AgentTraceEvent` payloads until terminal/pause boundary."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        listeners = self._subscribers.setdefault(execution_id, set())
        listeners.add(queue)
        seen_ids: set[str] = set()
        try:
            buffered = list(self._history_by_execution.get(execution_id, ()))
            if not buffered and self._redis_url is not None:
                buffered = await self._load_redis_history(execution_id)

            last_idx = len(buffered) - 1
            for idx, item in enumerate(buffered):
                ev_id = str(item.get("event_id") or "")
                if ev_id:
                    seen_ids.add(ev_id)
                yield item
                kind = str(item.get("kind") or "")
                if kind in _TERMINAL_KINDS or (kind == _PAUSE_KIND and idx == last_idx):
                    return

            while True:
                try:
                    live_item = await asyncio.wait_for(queue.get(), timeout=15.0)
                except TimeoutError:
                    break
                ev_id = str(live_item.get("event_id") or "")
                if ev_id and ev_id in seen_ids:
                    continue
                if ev_id:
                    seen_ids.add(ev_id)
                yield live_item
                live_kind = str(live_item.get("kind") or "")
                if live_kind in _TERMINAL_KINDS or live_kind == _PAUSE_KIND:
                    return
        finally:
            listeners.discard(queue)
            if not listeners:
                self._subscribers.pop(execution_id, None)

    def sync_history_from_snapshot(self, execution_id: str, events: list[dict[str, Any]]) -> None:
        """Hydrate in-memory history from a persisted PostgreSQL 18 snapshot after restart."""
        existing = self._history_by_execution.get(execution_id, [])
        if events and len(events) > len(existing):
            self._history_by_execution[execution_id] = [dict(ev) for ev in events]

    async def _publish_to_redis(self, execution_id: str, payload: dict[str, Any]) -> None:
        if self._redis_url is None:
            return
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(self._redis_url, decode_responses=True)
            try:
                encoded = json.dumps(payload, ensure_ascii=False)
                hist_key = f"orcia:reflexive:history:{execution_id}"
                chan_key = f"orcia:reflexive:trace:{execution_id}"
                await client.rpush(hist_key, encoded)
                await client.expire(hist_key, _REDIS_TTL_SECONDS)
                await client.publish(chan_key, encoded)
            finally:
                await client.aclose()
        except Exception as exc:
            logger.warning(
                "reflexive_redis_publish_degraded",
                execution_id=execution_id,
                error_type=type(exc).__name__,
            )

    async def _load_redis_history(self, execution_id: str) -> list[dict[str, Any]]:
        if self._redis_url is None:
            return []
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(self._redis_url, decode_responses=True)
            try:
                hist_key = f"orcia:reflexive:history:{execution_id}"
                raw_items = await client.lrange(hist_key, 0, -1)
                return [
                    cast(
                        dict[str, Any],
                        json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw),
                    )
                    for raw in raw_items
                ]
            finally:
                await client.aclose()
        except Exception as exc:
            logger.warning(
                "reflexive_redis_history_load_degraded",
                execution_id=execution_id,
                error_type=type(exc).__name__,
            )
            return []
