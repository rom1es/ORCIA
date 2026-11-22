"""Distributed Redis 7.4 Thread Turn Lock (`SET NX EX` + Lua release, `AD-4`, `H-09`)."""

from __future__ import annotations

import time
import uuid
from typing import Any

from orcia_core.orchestration.errors import ThreadTurnLockHeldError
from orcia_core.ports.assistant_turn_stream_port import ThreadTurnLockPort

_RELEASE_LUA = """
local current = redis.call('GET', KEYS[1])
if not current then
    return 0
end
if ARGV[2] ~= '' then
    if current == ARGV[1] .. ':' .. ARGV[2] then
        return redis.call('DEL', KEYS[1])
    end
    return 0
end
if current == ARGV[1] or string.sub(current, 1, string.len(ARGV[1]) + 1) == ARGV[1] .. ':' then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

_REFRESH_IF_OWNER_LUA = """
local current = redis.call('GET', KEYS[1])
if not current then
    return redis.call('SET', KEYS[1], ARGV[2], 'EX', tonumber(ARGV[3]), 'NX') and 1 or 0
end
if current == ARGV[1] or string.sub(current, 1, string.len(ARGV[1]) + 1) == ARGV[1] .. ':' then
    redis.call('SET', KEYS[1], ARGV[2], 'EX', tonumber(ARGV[3]))
    return 1
end
return 0
"""


def _decode_redis_str(raw: Any) -> str:
    if raw is None:
        return ""
    return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)


def _extract_holder_user_id(raw_value: str) -> str:
    if ":" in raw_value:
        return raw_value.split(":", 1)[0]
    return raw_value


class RedisThreadTurnLock(ThreadTurnLockPort):
    """Atomic Redis `SET lock:thread:<thread_id> <user_id>:<token> NX EX <ttl>` turn lock."""

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._local_entries: dict[str, tuple[str, str, float]] = {}

    def set_redis_client(self, redis_client: Any | None) -> None:
        """Bind or replace the async Redis client from the Composition Root."""
        self._redis = redis_client

    @staticmethod
    def build_key(thread_id: str) -> str:
        """Return canonical Redis turn lock key `lock:thread:<thread_id>` (`AD-4`)."""
        return f"lock:thread:{thread_id}"

    def acquire_sync(
        self, *, thread_id: str, user_id: str, ttl_seconds: int = 60
    ) -> tuple[str, str]:
        """Acquire turn lock synchronously when Redis is unconfigured (unit-test fallback)."""
        if self._redis is not None:
            raise RuntimeError(
                "RedisThreadTurnLock.acquire_sync cannot run with an async Redis client; "
                "await acquire_async() instead."
            )
        key = self.build_key(thread_id)
        now = time.monotonic()
        existing = self._local_entries.get(thread_id)
        if existing is not None and existing[2] > now and existing[0] != user_id:
            raise ThreadTurnLockHeldError(
                detail_override=(
                    f"Verrou de tour Redis actif sur {key} (détenu par '{existing[0]}')."
                )
            )
        token = uuid.uuid4().hex
        self._local_entries[thread_id] = (user_id, token, now + float(ttl_seconds))
        return key, token

    def release_sync(self, *, thread_id: str, user_id: str, token: str | None = None) -> bool:
        """Release turn lock synchronously when Redis is unconfigured (unit-test fallback)."""
        if self._redis is not None:
            raise RuntimeError(
                "RedisThreadTurnLock.release_sync cannot run with an async Redis client; "
                "await release_async() instead."
            )
        existing = self._local_entries.get(thread_id)
        if existing is None or existing[0] != user_id:
            return False
        if token is not None and existing[1] != token:
            return False
        del self._local_entries[thread_id]
        return True

    async def acquire_async(
        self, *, thread_id: str, user_id: str, ttl_seconds: int = 60
    ) -> tuple[str, str]:
        """Acquire `lock:thread:<thread_id>` via Redis `SET NX EX`, raising 409 on peer hold."""
        if self._redis is None:
            return self.acquire_sync(thread_id=thread_id, user_id=user_id, ttl_seconds=ttl_seconds)
        key = self.build_key(thread_id)
        token = uuid.uuid4().hex
        lock_value = f"{user_id}:{token}"
        acquired = await self._redis.set(key, lock_value, nx=True, ex=ttl_seconds)
        if acquired:
            return key, token

        current_raw = _decode_redis_str(await self._redis.get(key))
        holder = _extract_holder_user_id(current_raw)
        if holder and holder != user_id:
            raise ThreadTurnLockHeldError(
                detail_override=(f"Verrou de tour Redis actif sur {key} (détenu par '{holder}').")
            )
        refreshed = await self._redis.eval(
            _REFRESH_IF_OWNER_LUA, 1, key, user_id, lock_value, str(int(ttl_seconds))
        )
        if int(refreshed or 0) == 1:
            return key, token

        latest_holder = _extract_holder_user_id(_decode_redis_str(await self._redis.get(key)))
        raise ThreadTurnLockHeldError(
            detail_override=(
                f"Verrou de tour Redis actif sur {key} (détenu par '{latest_holder or 'peer'}')."
            )
        )

    async def release_async(
        self, *, thread_id: str, user_id: str, token: str | None = None
    ) -> bool:
        """Atomically release `lock:thread:<thread_id>` via Lua if owned by `user_id`/`token`."""
        if self._redis is None:
            return self.release_sync(thread_id=thread_id, user_id=user_id, token=token)
        key = self.build_key(thread_id)
        deleted = await self._redis.eval(_RELEASE_LUA, 1, key, user_id, token or "")
        return int(deleted or 0) == 1


__all__ = ["RedisThreadTurnLock"]
