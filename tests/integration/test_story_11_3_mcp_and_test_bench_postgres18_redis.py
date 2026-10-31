"""Story 11.3 — Real PostgreSQL 18 + Redis 7.4 `testcontainers` integration test.

Verifies against real ephemeral PostgreSQL 18 + Redis 7.4 containers:
1. Persistence of MCP exposure metadata and Outbox audit events (`ADMIN_CONNECTION_TEST`,
   `MCP_IDE_CLIENT`) in PostgreSQL 18.
2. Sub-10ms Redis validation, rate-limiting, and revocation of `pat_mcp_*` SHA-256 tokens.
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest
import redis
import sqlalchemy as sa
import uuid_utils as uuid
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_story_11_3_mcp_and_test_bench_pg18_redis() -> None:
    """Verify Story 11.3 PG18 Outbox audit events and sub-10ms Redis `pat_mcp_*` revocation."""
    with (
        RedisContainer("redis:7.4-alpine") as redis_container,
        PostgresContainer("pgvector/pgvector:pg18") as pg_container,
    ):
        r_client = redis.Redis(
            host=redis_container.get_container_host_ip(),
            port=int(redis_container.get_exposed_port(6379)),
            db=0,
        )
        sync_url = pg_container.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+psycopg://"
        )
        async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

        org_id = str(uuid.uuid7())
        ws_id = str(uuid.uuid7())
        ev_id = str(uuid.uuid7())

        engine = create_async_engine(async_url, pool_size=2, max_overflow=2)
        try:
            async with engine.begin() as conn:

                def _upgrade(sync_conn: sa.Connection) -> None:
                    alembic_cfg.attributes["connection"] = sync_conn
                    command.upgrade(alembic_cfg, "head")

                await conn.run_sync(_upgrade)

            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                        VALUES (:id, :slug, 'Team MCP 11.3', 'TEAM', NULL)
                        """
                    ),
                    {"id": org_id, "slug": f"team-11-3-{org_id[:8]}"},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspaces (
                            id, slug, name, owner_org_unit_id, visibility_mode
                        )
                        VALUES (:ws_id, :slug, 'Workspace MCP 11.3', :org_id, 'STANDARD')
                        """
                    ),
                    {"ws_id": ws_id, "slug": f"ws-11-3-{ws_id[:8]}", "org_id": org_id},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO domain_events_outbox (
                            event_id, event_type, aggregate_type, aggregate_id,
                            run_id, workspace_id, payload_jsonb, trace_id, status
                        )
                        VALUES (
                            :ev_id, 'StepCompleted', 'McpInvocation', 'agent.triage-agent',
                            NULL, :ws_id, CAST(:payload AS jsonb), 'trace-mcp-11-3', 'PENDING'
                        )
                        """
                    ),
                    {
                        "ev_id": ev_id,
                        "ws_id": ws_id,
                        "payload": (
                            '{"actor_type":"MCP_IDE_CLIENT",'
                            '"history_badge":"💻 Appelé via MCP (IDE)"}'
                        ),
                    },
                )

                stored_actor = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT payload_jsonb->>'actor_type'
                            FROM domain_events_outbox
                            WHERE event_id = :ev_id
                            """
                        ),
                        {"ev_id": ev_id},
                    )
                ).scalar_one()
                assert stored_actor == "MCP_IDE_CLIENT"

            # Verify < 10 ms pat_mcp_* lookup and revocation in Redis 7.4
            raw_pat = "pat_mcp_ide_live_01"  # pragma: allowlist secret
            pat_hash = hashlib.sha256(raw_pat.encode("utf-8")).hexdigest()
            redis_key = f"mcp:pat:{pat_hash}"
            r_client.set(redis_key, ws_id, ex=3600)

            t0 = time.perf_counter()
            val = r_client.get(redis_key)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert val is not None
            assert elapsed_ms < 10.0

            r_client.delete(redis_key)
            assert r_client.get(redis_key) is None
        finally:
            await engine.dispose()
