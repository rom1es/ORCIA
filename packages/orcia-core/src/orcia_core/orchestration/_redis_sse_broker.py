"""Redis Pub/Sub SSE Broadcast Adapter (`SseBroadcastPort`, `AD-4`, `BLOCKING-05`).

Bridges cross-process SSE events between `apps/worker` (`trigger-dispatcher`) and
`apps/api` (`/api/v1/events/stream`) over Redis Pub/Sub `channel:workspace:{ws_id}`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.presence_and_sse import (
    InMemorySseBrokerAdapter,
    SseBroadcastPort,
    SseEventEnvelope,
)
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.core.orchestration.redis_sse")


def serialize_sse_envelope(env: SseEventEnvelope) -> str:
    """Serialize an `SseEventEnvelope` into canonical JSON for Redis Pub/Sub."""
    return json.dumps(
        {
            "event_id": env.event_id,
            "event_name": env.event_name,
            "channel": env.channel,
            "workspace_id": env.workspace_id,
            "run_id": env.run_id,
            "step_execution_id": env.step_execution_id,
            "payload": env.payload,
            "published_at_iso": env.published_at_iso,
            "dispatch_latency_ms": env.dispatch_latency_ms,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def deserialize_sse_envelope(raw: str | bytes) -> SseEventEnvelope | None:
    """Deserialize a Redis Pub/Sub payload back into `SseEventEnvelope`."""
    try:
        text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        return SseEventEnvelope(
            event_id=str(data["event_id"]),
            event_name=str(data["event_name"]),
            channel=str(data["channel"]),
            workspace_id=str(data["workspace_id"]),
            run_id=str(data["run_id"]),
            step_execution_id=str(data["step_execution_id"]),
            payload=dict(data.get("payload") or {}),
            published_at_iso=str(data["published_at_iso"]),
            dispatch_latency_ms=float(data.get("dispatch_latency_ms", 1.0)),
        )
    except Exception as exc:
        logger.warning("redis_sse_deserialize_failed", error_type=type(exc).__name__)
        return None


class RedisSseBrokerAdapter(SseBroadcastPort):
    """Cross-process `SseBroadcastPort` backed by Redis Pub/Sub with local fan-out."""

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._local = InMemorySseBrokerAdapter()
        self._seen_local_ids: deque[str] = deque(maxlen=512)
        self._listener_task: asyncio.Task[None] | None = None
        self._pubsub: Any | None = None

    def set_redis_client(self, redis_client: Any | None) -> None:
        """Bind or update the underlying async Redis client."""
        self._redis = redis_client

    def _build_envelope(
        self,
        *,
        workspace_id: str,
        event_name: str,
        run_id: str,
        step_execution_id: str,
        payload: dict[str, Any],
    ) -> SseEventEnvelope:
        t0 = time.perf_counter()
        channel = f"channel:workspace:{workspace_id}"
        now_iso = datetime.now(UTC).isoformat()
        latency_ms = round(max(0.5, (time.perf_counter() - t0) * 1000.0), 3)
        return SseEventEnvelope(
            event_id=new_uuid7_str(),
            event_name=event_name,
            channel=channel,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            payload=dict(payload),
            published_at_iso=now_iso,
            dispatch_latency_ms=latency_ms,
        )

    def _dispatch_local(self, env: SseEventEnvelope) -> None:
        if env.event_id in self._seen_local_ids:
            return
        self._seen_local_ids.append(env.event_id)
        with self._local._mutex:
            self._local._events.append(env)
            targets = [
                cb for ws, cb in self._local._subscribers if ws is None or ws == env.workspace_id
            ]
        for cb in targets:
            try:
                cb(env)
            except Exception as exc:
                logger.warning("redis_sse_local_subscriber_failed", error=str(exc))

    async def _publish_to_redis(self, env: SseEventEnvelope) -> None:
        if self._redis is None:
            return
        raw = serialize_sse_envelope(env)
        recent_key = f"sse:recent:{env.workspace_id}"
        try:
            pub_res = self._redis.publish(env.channel, raw)
            if asyncio.iscoroutine(pub_res) or hasattr(pub_res, "__await__"):
                await pub_res
            lpush_res = self._redis.lpush(recent_key, raw)
            if asyncio.iscoroutine(lpush_res) or hasattr(lpush_res, "__await__"):
                await lpush_res
            ltrim_res = self._redis.ltrim(recent_key, 0, 49)
            if asyncio.iscoroutine(ltrim_res) or hasattr(ltrim_res, "__await__"):
                await ltrim_res
            exp_res = self._redis.expire(recent_key, 3600)
            if asyncio.iscoroutine(exp_res) or hasattr(exp_res, "__await__"):
                await exp_res
        except Exception as exc:
            logger.warning(
                "redis_sse_publish_failed",
                channel=env.channel,
                error_type=type(exc).__name__,
            )

    def publish(
        self,
        *,
        workspace_id: str,
        event_name: str,
        run_id: str,
        step_execution_id: str,
        payload: dict[str, Any],
    ) -> SseEventEnvelope:
        """Broadcast locally and schedule async Redis Pub/Sub fan-out."""
        env = self._build_envelope(
            workspace_id=workspace_id,
            event_name=event_name,
            run_id=run_id,
            step_execution_id=step_execution_id,
            payload=payload,
        )
        self._dispatch_local(env)
        if self._redis is not None:
            with contextlib.suppress(RuntimeError):
                loop = asyncio.get_running_loop()
                loop.create_task(self._publish_to_redis(env))
        return env

    async def publish_async(
        self,
        *,
        workspace_id: str,
        event_name: str,
        run_id: str,
        step_execution_id: str,
        payload: dict[str, Any],
    ) -> SseEventEnvelope:
        """Broadcast locally and await Redis Pub/Sub delivery."""
        env = self._build_envelope(
            workspace_id=workspace_id,
            event_name=event_name,
            run_id=run_id,
            step_execution_id=step_execution_id,
            payload=payload,
        )
        self._dispatch_local(env)
        await self._publish_to_redis(env)
        return env

    def list_recent_events(self, workspace_id: str | None = None) -> tuple[SseEventEnvelope, ...]:
        """Return recent local events synchronously."""
        return self._local.list_recent_events(workspace_id=workspace_id)

    async def list_recent_events_async(
        self, workspace_id: str | None = None
    ) -> tuple[SseEventEnvelope, ...]:
        """Return merged local + Redis recent events for `workspace_id`."""
        local_events = list(self._local.list_recent_events(workspace_id=workspace_id))
        if self._redis is None or workspace_id is None:
            return tuple(local_events)
        by_id: dict[str, SseEventEnvelope] = {e.event_id: e for e in local_events}
        try:
            raw_items = await self._redis.lrange(f"sse:recent:{workspace_id}", 0, 49)
            for raw in reversed(raw_items or ()):
                env = deserialize_sse_envelope(raw)
                if env is not None and env.event_id not in by_id:
                    by_id[env.event_id] = env
        except Exception as exc:
            logger.warning("redis_sse_lrange_failed", error_type=type(exc).__name__)
        return tuple(sorted(by_id.values(), key=lambda e: e.published_at_iso))

    def subscribe(
        self,
        listener: Callable[[SseEventEnvelope], object],
        *,
        workspace_id: str | None = None,
    ) -> Callable[[], None]:
        """Register a real-time subscriber callback."""
        return self._local.subscribe(listener, workspace_id=workspace_id)

    async def start_pubsub_listener(self) -> None:
        """Start background Redis `psubscribe('channel:workspace:*')` fan-out loop."""
        redis = self._redis
        if redis is None or self._listener_task is not None:
            return
        if not hasattr(redis, "pubsub"):
            return

        async def _listen_loop() -> None:
            try:
                pubsub = redis.pubsub()
                self._pubsub = pubsub
                await pubsub.psubscribe("channel:workspace:*")
                while True:
                    msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                    if msg and msg.get("data"):
                        env = deserialize_sse_envelope(msg["data"])
                        if env is not None:
                            self._dispatch_local(env)
                    await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("redis_sse_listener_stopped", error_type=type(exc).__name__)

        self._listener_task = asyncio.create_task(_listen_loop())

    async def stop_pubsub_listener(self) -> None:
        """Stop background Redis Pub/Sub listener and close pubsub handle."""
        if self._listener_task is not None:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._listener_task
            self._listener_task = None
        if self._pubsub is not None:
            with contextlib.suppress(Exception):
                await self._pubsub.aclose()
            self._pubsub = None


__all__ = ["RedisSseBrokerAdapter", "deserialize_sse_envelope", "serialize_sse_envelope"]
