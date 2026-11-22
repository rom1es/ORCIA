"""Redis 7.4 Tool Idempotency Store (`idem:{turn_id}:{iteration}:{tool_call_id}`, `Story 26.6b`)."""

from __future__ import annotations

import json
from typing import Any

from orcia_core.ports.assistant_tool_executor_port import ToolIdempotencyStorePort


def build_tool_idempotency_key(
    *,
    turn_id: str,
    iteration: int,
    tool_call_id: str,
    workspace_id: str = "",
    user_id: str = "",
) -> str:
    """Return canonical idempotency key `idem:{ws}:{user}:{turn_id}:{iteration}:{tool_call_id}`."""
    ws_part = (workspace_id or "global").strip() or "global"
    user_part = (user_id or "anon").strip() or "anon"
    return f"idem:{ws_part}:{user_part}:{turn_id}:{int(iteration)}:{tool_call_id}"


class RedisToolIdempotencyStore(ToolIdempotencyStorePort):
    """Redis 7.4 backed idempotency store with local dict fallback when Redis is absent."""

    def __init__(self, redis_client: Any | None = None, *, ttl_seconds: int = 1800) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds
        self._local_cache: dict[str, str] = {}

    def set_redis_client(self, redis_client: Any | None) -> None:
        """Attach or replace async Redis client from Composition Root."""
        self._redis = redis_client

    async def get_cached_result(self, key: str) -> dict[str, Any] | None:
        """Fetch previously serialized tool result for `key` if present."""
        if self._redis is None:
            raw = self._local_cache.get(key)
        else:
            raw_bytes = await self._redis.get(f"orcia:assistant:{key}")
            raw = (
                raw_bytes.decode("utf-8", errors="replace")
                if isinstance(raw_bytes, (bytes, bytearray))
                else raw_bytes
            )
        if not raw:
            return None
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else None

    async def save_result(
        self, key: str, payload: dict[str, Any], *, ttl_seconds: int | None = None
    ) -> None:
        """Persist serialized tool result under `key` with bounded TTL."""
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if self._redis is None:
            self._local_cache[key] = encoded
            return
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        await self._redis.set(f"orcia:assistant:{key}", encoded, ex=ttl)


__all__ = ["RedisToolIdempotencyStore", "build_tool_idempotency_key"]
