"""Story 26.4a — TDD Unit & AST Guard Tests: Redis Locks, Outbox, R6 Removal, TTL & Zero DDL."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_prompt_cache_machinery_and_forged_outbox_id_deleted() -> None:
    """Verify R6: InMemoryPromptCacheStore, AssembledPromptCachePort & forged outbox ID deleted."""
    cache_helper = (
        REPO_ROOT
        / "packages/orcia-core/src/orcia_core/orchestration/_assistant_three_speed_cache.py"
    )
    assert not cache_helper.exists(), "_assistant_three_speed_cache.py must be deleted (R6)"

    models_mod = importlib.import_module("orcia_core.orchestration.assistant_three_speed_models")
    router_mod = importlib.import_module("orcia_core.orchestration.assistant_three_speed_router")
    for forbidden in ("InMemoryPromptCacheStore", "AssembledPromptCachePort"):
        assert not hasattr(models_mod, forbidden), f"{forbidden} still in three_speed_models"
        assert not hasattr(router_mod, forbidden), f"{forbidden} still in three_speed_router"

    router_src = (
        REPO_ROOT
        / "packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py"
    ).read_text(encoding="utf-8")
    assert "outbox_event_id=new_uuid7_str()" not in router_src
    assert "outbox_event_id=" not in router_src


def test_in_memory_thread_lock_only_in_fakes_and_redis_lock_wired() -> None:
    """Verify _turn_locks RAM dicts are gone, InMemory* lock is in fakes/, and Redis lock wired."""
    from tests.unit.fakes.in_memory_thread_lock import InMemoryThreadTurnLock

    from orcia_core.orchestration.redis_thread_lock import RedisThreadTurnLock
    from orcia_core.ports.assistant_turn_stream_port import ThreadTurnLockPort

    assert isinstance(InMemoryThreadTurnLock(), ThreadTurnLockPort)
    assert isinstance(RedisThreadTurnLock(), ThreadTurnLockPort)

    for rel in (
        "packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py",
        "packages/orcia-core/src/orcia_core/orchestration/_assistant_folders_sync.py",
        "packages/orcia-core/src/orcia_core/orchestration/_assistant_folders_models.py",
    ):
        txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "_turn_locks" not in txt, f"_turn_locks RAM dict still in {rel}"
        assert "_ActiveTurnLockEntry" not in txt, f"_ActiveTurnLockEntry still in {rel}"

    orch_dir = REPO_ROOT / "packages/orcia-core/src/orcia_core/orchestration"
    for py_file in orch_dir.rglob("*.py"):
        if not py_file.name.startswith(("assistant_", "_assistant_", "redis_")):
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith("InMemory"):
                raise AssertionError(f"InMemory* class {node.name} found in {py_file}")

    portal_src = (
        REPO_ROOT / "apps/api/src/orcia_api/dependencies/portal_and_assistant.py"
    ).read_text(encoding="utf-8")
    assert "redis_client" in portal_src
    assert "set_redis_client" in portal_src


def test_zero_runtime_ddl_and_zero_ephemeral_httpx_clients_and_file_size_cap() -> None:
    """Verify H-32: zero runtime DDL, zero ephemeral httpx.AsyncClient(), and <= 300 L cap."""
    checked_paths = (
        "packages/orcia-core/src/orcia_core/orchestration/llm_endpoint_resolver.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_queries.py",
        "packages/orcia-core/src/orcia_core/orchestration/redis_thread_lock.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_outbox_emitter.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_models.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_steps.py",
        "packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py",
        "packages/orcia-core/src/orcia_core/orchestration/_assistant_folders_sync.py",
        "packages/orcia-core/src/orcia_core/orchestration/_assistant_folders_async_ops.py",
        "packages/orcia-core/src/orcia_core/bootstrap/setup_snapshot_cache.py",
        "apps/api/src/orcia_api/dependencies/portal_and_assistant.py",
        "apps/api/src/orcia_api/dependencies/_rag_availability_guards.py",
        "apps/api/src/orcia_api/routers/assistant_llm_resolver.py",
        "apps/api/src/orcia_api/routers/ai_models_hub.py",
        "apps/api/src/orcia_api/routers/_ai_models_helpers.py",
        "apps/api/src/orcia_api/routers/_ai_models_test_and_reindex_routes.py",
        "apps/api/src/orcia_api/routers/_ai_models_reindex_helpers.py",
        "apps/api/src/orcia_api/routers/_bootstrap_llm_routes.py",
        "apps/api/src/orcia_api/routers/_bootstrap_setup_state.py",
        "apps/api/src/orcia_api/routers/assistant_turns.py",
        "apps/api/src/orcia_api/routers/_assistant_turn_controls_routes.py",
        "apps/api/src/orcia_api/routers/assistant_workspace_governance.py",
        "apps/api/src/orcia_api/routers/_assistant_turn_producer.py",
        "apps/api/src/orcia_api/routers/_assistant_turn_producer_helpers.py",
    )
    for rel in checked_paths:
        p = REPO_ROOT / rel
        assert p.exists(), f"Missing expected Story 26.4a file: {rel}"
        lines = p.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 300, f"{rel} has {len(lines)} lines (> 300 L limit)"

    runtime_no_ddl_paths = (
        "packages/orcia-core/src/orcia_core/orchestration/llm_endpoint_resolver.py",
        "packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_queries.py",
        "apps/api/src/orcia_api/dependencies/_rag_availability_guards.py",
        "apps/api/src/orcia_api/routers/assistant_llm_resolver.py",
        "apps/api/src/orcia_api/routers/ai_models_hub.py",
        "apps/api/src/orcia_api/routers/_ai_models_helpers.py",
        "apps/api/src/orcia_api/routers/_ai_models_test_and_reindex_routes.py",
        "apps/api/src/orcia_api/routers/_ai_models_reindex_helpers.py",
    )
    for rel in runtime_no_ddl_paths:
        txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "ensure_ai_model_mappings_schema_on_postgres18" not in txt, (
            f"Runtime DDL helper still referenced in {rel}"
        )
        for ddl_kw in ("CREATE TABLE", "ALTER TABLE", "CREATE INDEX", "CREATE UNIQUE INDEX"):
            assert ddl_kw not in txt, f"Runtime DDL {ddl_kw} found in {rel}"

    no_ephemeral_http_paths = (
        "apps/api/src/orcia_api/dependencies/_rag_availability_guards.py",
        "apps/api/src/orcia_api/routers/_ai_models_helpers.py",
        "apps/api/src/orcia_api/routers/_bootstrap_llm_routes.py",
    )
    for rel in no_ephemeral_http_paths:
        txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "httpx.AsyncClient(" not in txt, f"Ephemeral httpx.AsyncClient() found in {rel}"


@pytest.mark.asyncio
async def test_platform_setup_snapshot_ttl_and_redis_version_invalidation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify H-35: bounded snapshot TTL and immediate Redis version invalidation."""
    from orcia_core.bootstrap.setup_snapshot_cache import (
        get_valid_platform_setup_snapshot_async,
        invalidate_platform_setup_snapshot_async,
        set_cached_platform_setup_snapshot_async,
    )

    class _FakeAsyncRedis:
        def __init__(self) -> None:
            self.store: dict[str, bytes] = {}

        async def get(self, key: str) -> bytes | None:
            return self.store.get(key)

        async def set(self, key: str, value: str, *, ex: int | None = None) -> bool:
            _ = ex
            self.store[key] = value.encode("utf-8")
            return True

    fake_redis = _FakeAsyncRedis()
    state_w1 = SimpleNamespace(platform_setup_snapshot=None)
    state_w2 = SimpleNamespace(platform_setup_snapshot=None)
    snap_v1 = SimpleNamespace(llm_tiers=[{"tier": "medium", "primaryModel": "m-v1"}])

    now = [100.0]
    monkeypatch.setattr("orcia_core.bootstrap.setup_snapshot_cache.time.monotonic", lambda: now[0])
    monkeypatch.setenv("ORCIA_PLATFORM_SETUP_SNAPSHOT_TTL_S", "30")

    await set_cached_platform_setup_snapshot_async(state_w1, snap_v1, redis_client=fake_redis)
    ver = await fake_redis.get("orcia:platform_setup_snapshot:version")
    assert ver is not None
    await set_cached_platform_setup_snapshot_async(
        state_w2, snap_v1, redis_client=fake_redis, version=ver.decode("utf-8")
    )

    assert (
        await get_valid_platform_setup_snapshot_async(state_w1, redis_client=fake_redis) is snap_v1
    )
    assert (
        await get_valid_platform_setup_snapshot_async(state_w2, redis_client=fake_redis) is snap_v1
    )

    # AI Hub mutation on Worker 1 invalidates Redis version -> Worker 2 sees None immediately
    await invalidate_platform_setup_snapshot_async(state_w1, redis_client=fake_redis)
    assert await get_valid_platform_setup_snapshot_async(state_w1, redis_client=fake_redis) is None
    assert await get_valid_platform_setup_snapshot_async(state_w2, redis_client=fake_redis) is None

    # Bounded TTL expiration even without external invalidation
    snap_v2 = SimpleNamespace(llm_tiers=[{"tier": "medium", "primaryModel": "m-v2"}])
    await set_cached_platform_setup_snapshot_async(state_w1, snap_v2, redis_client=fake_redis)
    assert (
        await get_valid_platform_setup_snapshot_async(state_w1, redis_client=fake_redis) is snap_v2
    )
    now[0] += 31.0
    assert await get_valid_platform_setup_snapshot_async(state_w1, redis_client=fake_redis) is None


@pytest.mark.asyncio
async def test_assistant_outbox_emitter_enqueues_real_domain_events() -> None:
    """Verify H-22: harness lifecycle events emit through Outbox repository contract."""
    from orcia_core.orchestration.assistant_outbox_emitter import AssistantOutboxEmitter

    enqueued: list[Any] = []

    class _FakeOutboxRepo:
        async def enqueue_event(self, event: Any) -> None:
            enqueued.append(event)

    emitter = AssistantOutboxEmitter(outbox_repo=_FakeOutboxRepo())  # type: ignore[arg-type]
    ws_uuid = "0195f000-0000-7000-8000-000000000301"
    await emitter.emit_turn_started(
        turn_id="turn-01",
        workspace_id=ws_uuid,
        user_id="user-01",
        speed_mode="SPEED_1_FAST",
        trace_id="0" * 32,
    )
    await emitter.emit_turn_completed(
        turn_id="turn-01",
        workspace_id=ws_uuid,
        user_id="user-01",
        speed_mode="SPEED_1_FAST",
        input_tokens=12,
        output_tokens=24,
        trace_id="0" * 32,
    )
    await emitter.emit_turn_stopped(
        turn_id="turn-02",
        workspace_id="non-uuid-slug",
        user_id="user-01",
        stopped_by_user_id="user-01",
        trace_id="0" * 32,
    )
    await emitter.emit_turn_failed(
        turn_id="turn-03",
        workspace_id=ws_uuid,
        user_id="user-01",
        error_code="ERR_INTERNAL_SERVER_ERROR",
        trace_id="0" * 32,
    )
    await emitter.emit_settings_changed(
        workspace_id=ws_uuid,
        setting_key="assistant.mode_a.workspace",
        actor_id="user-01",
        trace_id="0" * 32,
    )
    assert [e.event_type for e in enqueued] == [
        "AssistantTurnStarted",
        "AssistantTurnCompleted",
        "AssistantTurnStopped",
        "AssistantTurnFailed",
        "SettingsChanged",
    ]
    assert enqueued[0].workspace_id == ws_uuid
    assert enqueued[2].workspace_id is None
