"""Story 26.4a — Branch Coverage Tests for RedisThreadTurnLock and SetupSnapshotCache."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from orcia_core.bootstrap.setup_snapshot_cache import (
    DEFAULT_PLATFORM_SETUP_SNAPSHOT_TTL_S,
    get_valid_platform_setup_snapshot_async,
    invalidate_platform_setup_snapshot_async,
    resolve_platform_setup_snapshot_ttl_seconds,
    set_cached_platform_setup_snapshot_async,
)
from orcia_core.orchestration.errors import ThreadTurnLockHeldError
from orcia_core.orchestration.redis_thread_lock import (
    RedisThreadTurnLock,
    _decode_redis_str,
    _extract_holder_user_id,
)


def test_redis_thread_lock_sync_and_helper_branches() -> None:
    """Cover sync fallback contention, token checks, and helper decoding paths."""
    assert _decode_redis_str(None) == ""
    assert _decode_redis_str(b"alice:tok1") == "alice:tok1"
    assert _extract_holder_user_id("plain-user") == "plain-user"

    lock = RedisThreadTurnLock()
    key, tok = lock.acquire_sync(thread_id="thr-1", user_id="u-a", ttl_seconds=60)
    assert key == "lock:thread:thr-1"
    with pytest.raises(ThreadTurnLockHeldError):
        lock.acquire_sync(thread_id="thr-1", user_id="u-b", ttl_seconds=60)
    assert lock.release_sync(thread_id="thr-missing", user_id="u-a") is False
    assert lock.release_sync(thread_id="thr-1", user_id="u-b") is False
    assert lock.release_sync(thread_id="thr-1", user_id="u-a", token="wrong") is False
    assert lock.release_sync(thread_id="thr-1", user_id="u-a", token=tok) is True

    lock.set_redis_client(object())
    with pytest.raises(RuntimeError):
        lock.acquire_sync(thread_id="thr-1", user_id="u-a")
    with pytest.raises(RuntimeError):
        lock.release_sync(thread_id="thr-1", user_id="u-a")


@pytest.mark.asyncio
async def test_redis_thread_lock_async_contention_and_no_redis_fallback() -> None:
    """Cover async no-Redis fallback, owner refresh, and lost-race contention paths."""
    lock = RedisThreadTurnLock()
    _, tok = await lock.acquire_async(thread_id="thr-no-redis", user_id="u-a")
    assert await lock.release_async(thread_id="thr-no-redis", user_id="u-a", token=tok) is True

    class _ContendedRedis:
        def __init__(self, *, eval_result: int, latest_get: bytes | None) -> None:
            self.eval_result = eval_result
            self.latest_get = latest_get
            self.calls = 0

        async def set(self, key: str, value: str, *, nx: bool, ex: int) -> bool:
            _ = (key, value, nx, ex)
            return False

        async def get(self, key: str) -> bytes | None:
            _ = key
            self.calls += 1
            if self.calls == 1:
                return b"u-a:old-tok"
            return self.latest_get

        async def eval(self, script: str, numkeys: int, *args: Any) -> int:
            _ = (script, numkeys, args)
            return self.eval_result

    refresh_lock = RedisThreadTurnLock(_ContendedRedis(eval_result=1, latest_get=None))
    _, refreshed_tok = await refresh_lock.acquire_async(thread_id="thr-2", user_id="u-a")
    assert refreshed_tok

    lost_race_lock = RedisThreadTurnLock(_ContendedRedis(eval_result=0, latest_get=b"u-c:tok3"))
    with pytest.raises(ThreadTurnLockHeldError):
        await lost_race_lock.acquire_async(thread_id="thr-2", user_id="u-a")


@pytest.mark.asyncio
async def test_setup_snapshot_cache_error_and_none_state_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover invalid TTL env, None app_state, and resilient Redis error logging branches."""
    monkeypatch.setenv("ORCIA_PLATFORM_SETUP_SNAPSHOT_TTL_S", "not-a-float")
    assert resolve_platform_setup_snapshot_ttl_seconds() == DEFAULT_PLATFORM_SETUP_SNAPSHOT_TTL_S

    assert await get_valid_platform_setup_snapshot_async(None) is None
    await set_cached_platform_setup_snapshot_async(None, object())
    ver_no_redis = await invalidate_platform_setup_snapshot_async(None, redis_client=None)
    assert ver_no_redis

    class _FailingRedis:
        async def get(self, key: str) -> bytes | None:
            _ = key
            raise ConnectionError("redis get down")

        async def set(self, key: str, value: str, *, ex: int | None = None) -> bool:
            _ = (key, value, ex)
            raise ConnectionError("redis set down")

    state = SimpleNamespace(platform_setup_snapshot=None)
    snap = SimpleNamespace(llm_tiers=[{"tier": "medium"}])
    await set_cached_platform_setup_snapshot_async(state, snap, redis_client=_FailingRedis())
    assert (
        await get_valid_platform_setup_snapshot_async(state, redis_client=_FailingRedis()) is snap
    )
    ver = await invalidate_platform_setup_snapshot_async(state, redis_client=_FailingRedis())
    assert ver and state.platform_setup_snapshot is None


@pytest.mark.asyncio
async def test_assistant_outbox_emitter_factory_and_error_branches() -> None:
    """Cover AssistantOutboxEmitter coerce_optional_uuid, factory, and enqueue error resilience."""
    from orcia_core.orchestration.assistant_outbox_emitter import (
        AssistantOutboxEmitter,
        coerce_optional_uuid,
    )

    assert coerce_optional_uuid(None) is None
    assert AssistantOutboxEmitter.from_uow_or_engine() is None
    assert AssistantOutboxEmitter.from_uow_or_engine(engine=object()) is not None  # type: ignore[arg-type]

    no_repo_emitter = AssistantOutboxEmitter(outbox_repo=None)
    assert (
        await no_repo_emitter.emit_settings_changed(
            workspace_id=None, setting_key="k", actor_id="u", trace_id="0" * 32
        )
        is None
    )

    class _BoomOutboxRepo:
        async def enqueue_event(self, event: Any) -> None:
            _ = event
            raise RuntimeError("db temporarily unreachable")

    boom_emitter = AssistantOutboxEmitter(outbox_repo=_BoomOutboxRepo())  # type: ignore[arg-type]
    assert (
        await boom_emitter.emit_settings_changed(
            workspace_id=None, setting_key="k", actor_id="u", trace_id="0" * 32
        )
        is None
    )
