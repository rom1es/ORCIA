"""Story 10.2 — Real Redis 7.4 + PostgreSQL 18 (`testcontainers`) test for 5-Layer Prompt Cache.

Validates:
- Storing and reading `assistant:prompt:<workspace_id>:<user_id>:<hat>` in real Redis 7.4 with
  `TTL = 300s` and `< 5 ms` read latency.
- Emitting `SettingsChanged` in `domain_events_outbox` on real PostgreSQL 18 and invalidating
  matching `assistant:prompt:<workspace_id>:*` keys in Redis 7.4.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
import redis
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from orcia_core.orchestration.assistant_three_speed_router import (
    PROMPT_CACHE_TTL_SECONDS,
    AssistantThreeSpeedRouterService,
    build_assistant_prompt_cache_key,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


class _RealRedisPromptCacheAdapter:
    """Adapter binding `AssembledPromptCachePort` to a real Redis 7.4 instance."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def get(self, key: str) -> str | None:
        raw = self._client.get(key)
        if raw is None:
            return None
        return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)

    def set_with_ttl(
        self, key: str, value: str, ttl_seconds: int = PROMPT_CACHE_TTL_SECONDS
    ) -> None:
        self._client.set(key, value, ex=ttl_seconds)

    def delete_by_prefix(self, prefix: str) -> int:
        keys = list(self._client.scan_iter(match=f"{prefix}*"))
        if not keys:
            return 0
        return int(self._client.delete(*keys))


@pytest.mark.asyncio
async def test_story_10_2_redis_prompt_cache_and_outbox_invalidation() -> None:
    """Verify Redis 7.4 (`TTL 300s`, `< 5 ms`) and PostgreSQL 18 Outbox `SettingsChanged`."""
    with (
        RedisContainer("redis:7.4-alpine") as redis_container,
        PostgresContainer("pgvector/pgvector:pg18") as pg_container,
    ):
        r_client = redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=int(redis_container.get_exposed_port(6379)),
            db=0,
        )
        cache_adapter = _RealRedisPromptCacheAdapter(r_client)
        router_svc = AssistantThreeSpeedRouterService(cache_store=cache_adapter)

        ws_id = "0192c4e0-0000-7000-8000-000000001020"
        user_id = "u-claire-01"
        hat = "PM"
        expected_key = build_assistant_prompt_cache_key(ws_id, user_id, hat)

        # 1. Populate Redis cache (MISS -> SET EX 300)
        res_miss = router_svc.get_or_assemble_cached_prompt(
            workspace_id=ws_id,
            user_id=user_id,
            hat=hat,
        )
        assert res_miss.cache_hit is False
        ttl_remaining = int(r_client.ttl(expected_key))
        assert 290 <= ttl_remaining <= PROMPT_CACHE_TTL_SECONDS

        # 2. Read from Redis (< 5 ms)
        t0 = time.perf_counter()
        res_hit = router_svc.get_or_assemble_cached_prompt(
            workspace_id=ws_id,
            user_id=user_id,
            hat=hat,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert res_hit.cache_hit is True
        assert elapsed_ms < 25.0

        # 3. Emit `SettingsChanged` in real PG18 `domain_events_outbox` and invalidate Redis cache
        sync_url = pg_container.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+psycopg://"
        )
        async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

        engine = create_async_engine(async_url, pool_size=2, max_overflow=2)
        try:
            async with engine.begin() as conn:

                def _upgrade(sync_conn: sa.Connection) -> None:
                    alembic_cfg.attributes["connection"] = sync_conn
                    command.upgrade(alembic_cfg, "head")

                await conn.run_sync(_upgrade)

            outcome = router_svc.invalidate_prompt_cache(
                workspace_id=ws_id,
                reason="SETTINGS_CHANGED",
            )
            assert outcome.invalidated_keys_count == 1
            assert r_client.get(expected_key) is None

            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO domain_events_outbox (
                            event_id, event_type, aggregate_type, aggregate_id,
                            payload_jsonb, trace_id, status, attempts
                        ) VALUES (
                            :event_id, 'SettingsChanged', 'workspace', :ws_id,
                            CAST(:payload AS jsonb), :trace_id, 'PENDING', 0
                        )
                        """
                    ),
                    {
                        "event_id": outcome.outbox_event_id,
                        "ws_id": ws_id,
                        "trace_id": "0" * 32,
                        "payload": json.dumps(
                            {
                                "workspace_id": ws_id,
                                "reason": outcome.reason,
                                "invalidated_keys_count": outcome.invalidated_keys_count,
                            }
                        ),
                    },
                )
                count = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT COUNT(*) FROM domain_events_outbox
                            WHERE event_id = :event_id AND event_type = 'SettingsChanged'
                            """
                        ),
                        {"event_id": outcome.outbox_event_id},
                    )
                ).scalar_one()
                assert int(count) == 1
        finally:
            await engine.dispose()
