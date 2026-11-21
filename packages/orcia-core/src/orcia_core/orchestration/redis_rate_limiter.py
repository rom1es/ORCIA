"""Redis 7.4 Sliding-Window Rate Limiter & Per-User Concurrency Semaphore (`AD-25`, `H-23`)."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

from orcia_core.ports.assistant_turn_stream_port import AssistantRateLimiterPort


def _decode_val(raw: Any) -> str:
    return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)


def resolve_rate_limit_settings() -> tuple[int, int, int]:
    """Read `(max_requests, window_seconds, max_concurrent_per_user)` dynamically from env."""
    try:
        max_req = max(1, int(os.environ.get("ORCIA_ASSISTANT_RATE_LIMIT_MAX", "60").strip()))
    except ValueError:
        max_req = 60
    try:
        window_s = max(1, int(os.environ.get("ORCIA_ASSISTANT_RATE_LIMIT_WINDOW_S", "60").strip()))
    except ValueError:
        window_s = 60
    try:
        max_conc = max(
            1, int(os.environ.get("ORCIA_ASSISTANT_MAX_CONCURRENT_TURNS_PER_USER", "8").strip())
        )
    except ValueError:
        max_conc = 8
    return max_req, window_s, max_conc


class RedisAssistantRateLimiter(AssistantRateLimiterPort):
    """Redis sliding-window rate limiter + per-user concurrency semaphore with local fallback."""

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client
        self._local_windows: dict[tuple[str, str], list[float]] = {}
        self._local_slots: dict[str, dict[str, float]] = {}

    def set_redis_client(self, redis_client: Any | None) -> None:
        """Bind or replace the async Redis client."""
        self._redis = redis_client

    async def check_and_record_turn_rate(
        self,
        user_id: str,
        workspace_id: str,
        *,
        window_seconds: int,
        max_requests: int,
    ) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - float(window_seconds)
        if self._redis is None:
            bucket = self._local_windows.setdefault((workspace_id, user_id), [])
            bucket[:] = [ts for ts in bucket if ts > cutoff]
            if len(bucket) >= max_requests:
                retry_after = max(1, int(bucket[0] + window_seconds - now) + 1)
                return False, retry_after
            bucket.append(now)
            return True, 0

        key = f"orcia:assistant:ratelimit:{workspace_id}:{user_id}"
        await self._redis.zremrangebyscore(key, "-inf", cutoff)
        current_count = int(await self._redis.zcard(key))
        if current_count >= max_requests:
            oldest = await self._redis.zrange(key, 0, 0, withscores=True)
            retry_after = (
                max(1, int(float(oldest[0][1]) + window_seconds - now) + 1)
                if oldest
                else window_seconds
            )
            return False, retry_after
        member = f"{now:.6f}:{uuid.uuid4().hex[:8]}"
        await self._redis.zadd(key, {member: now})
        await self._redis.expire(key, max(1, window_seconds))
        return True, 0

    async def acquire_concurrency_slot(
        self,
        user_id: str,
        *,
        limit: int,
        ttl_seconds: int = 180,
    ) -> str | None:
        now = time.time()
        expires_at = now + float(ttl_seconds)
        lease_token = uuid.uuid4().hex
        if self._redis is None:
            slots = self._local_slots.setdefault(user_id, {})
            expired = [tok for tok, exp in slots.items() if exp <= now]
            for tok in expired:
                slots.pop(tok, None)
            if len(slots) >= limit:
                return None
            slots[lease_token] = expires_at
            return lease_token

        key = f"orcia:assistant:concurrency:{user_id}"
        raw_slots = await self._redis.hgetall(key)
        expired_tokens: list[str] = []
        active_count = 0
        for raw_tok, raw_exp in (raw_slots or {}).items():
            tok = _decode_val(raw_tok)
            try:
                exp_ts = float(_decode_val(raw_exp))
            except ValueError:
                exp_ts = 0.0
            if exp_ts <= now:
                expired_tokens.append(tok)
            else:
                active_count += 1
        if expired_tokens:
            await self._redis.hdel(key, *expired_tokens)
        if active_count >= limit:
            return None
        await self._redis.hset(key, lease_token, f"{expires_at:.3f}")
        await self._redis.expire(key, max(1, ttl_seconds))
        return lease_token

    async def release_concurrency_slot(self, user_id: str, lease_token: str) -> None:
        if not lease_token:
            return
        if self._redis is None:
            slots = self._local_slots.get(user_id)
            if slots is not None:
                slots.pop(lease_token, None)
            return
        key = f"orcia:assistant:concurrency:{user_id}"
        await self._redis.hdel(key, lease_token)


__all__ = ["RedisAssistantRateLimiter", "resolve_rate_limit_settings"]
