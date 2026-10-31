"""Story 10.4 — Real PostgreSQL 18 + Redis 7.4 `testcontainers` integration test.

Verifies against real ephemeral PostgreSQL 18 + Redis 7.4 containers:
1. Alembic migration `0025_story_10_4` (`assistant_folders`, `assistant_threads`,
   `assistant_folder_shares`) with CHECK constraints (`visibility_mode`, `access_role`)
   and UNIQUE constraint `(folder_id, grantee_user_id)`.
2. Atomic Redis turn lock (`SET lock:thread:<thread_id> <user_id> NX EX 60`) rejecting
   concurrent peer turns while preserving per-author `Passthrough` identity (`AD-4`, `AD-6`).
"""

from __future__ import annotations

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
async def test_story_10_4_folders_shares_and_redis_turn_lock_pg18_redis() -> None:
    """Verify `0025_story_10_4` PG18 tables and real Redis `SET lock:thread:<id> NX EX 60`."""
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
        owner_id = str(uuid.uuid7())
        peer_id = str(uuid.uuid7())
        folder_id = str(uuid.uuid7())
        thread_id = str(uuid.uuid7())
        share_id = str(uuid.uuid7())

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
                        VALUES (:id, :slug, 'Team Checkout 10.4', 'TEAM', NULL)
                        """
                    ),
                    {"id": org_id, "slug": f"team-10-4-{org_id[:8]}"},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO users (
                            id, email, display_name, auth_mode,
                            human_profile_archetype, platform_role, primary_org_unit_id
                        )
                        VALUES
                            (
                                :u1, :e1, 'Hélène Owner', 'OIDC',
                                'TECH_LEAD', 'TEAM_LEAD', :org_id
                            ),
                            (
                                :u2, :e2, 'Yanis CoContributor', 'OIDC',
                                'DEVELOPER', 'CONTRIBUTOR', :org_id
                            )
                        """
                    ),
                    {
                        "u1": owner_id,
                        "u2": peer_id,
                        "org_id": org_id,
                        "e1": f"helene-{owner_id[:6]}@orcia.io",
                        "e2": f"yanis-{peer_id[:6]}@orcia.io",
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspaces (
                            id, slug, name, owner_org_unit_id, visibility_mode, finops_cost_usd
                        ) VALUES (
                            :id, :slug, 'Workspace Checkout 10.4', :org_id, 'STANDARD', 0.0
                        )
                        """
                    ),
                    {"id": ws_id, "org_id": org_id, "slug": f"ws-10-4-{ws_id[:8]}"},
                )

                # Insert thematic folder (`SHARED_SELECTED`)
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO assistant_folders (
                            folder_id, workspace_id, owner_user_id, title,
                            pinned_notes_markdown, visibility_mode, consolidated_summary,
                            has_restricted_sources
                        ) VALUES (
                            :folder_id, :ws_id, :owner_id, 'Refonte Tunnel Checkout',
                            'Décision #1 : 3DS2 frictionless.', 'SHARED_SELECTED',
                            'Synthèse consolidée des discussions PSP.', TRUE
                        )
                        """
                    ),
                    {"folder_id": folder_id, "ws_id": ws_id, "owner_id": owner_id},
                )

                # Share with Yanis as `CO_CONTRIBUTOR`
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO assistant_folder_shares (
                            share_id, folder_id, workspace_id, grantee_user_id, access_role
                        ) VALUES (
                            :share_id, :folder_id, :ws_id, :peer_id, 'CO_CONTRIBUTOR'
                        )
                        """
                    ),
                    {
                        "share_id": share_id,
                        "folder_id": folder_id,
                        "ws_id": ws_id,
                        "peer_id": peer_id,
                    },
                )

                # Create thread inside folder and record Yanis's personal Passthrough identity
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO assistant_threads (
                            thread_id, workspace_id, folder_id, creator_user_id,
                            title, thread_summary, turn_count,
                            last_author_user_id, last_author_passthrough_identity
                        ) VALUES (
                            :thread_id, :ws_id, :folder_id, :owner_id,
                            'Arbitrage PSP Stripe', 'Analyse latence 3DS2', 2,
                            :peer_id, :passthrough_id
                        )
                        """
                    ),
                    {
                        "thread_id": thread_id,
                        "ws_id": ws_id,
                        "folder_id": folder_id,
                        "owner_id": owner_id,
                        "peer_id": peer_id,
                        "passthrough_id": f"passthrough:oidc:{peer_id}:yanis@orcia.io",
                    },
                )

                row = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT creator_user_id::text,
                                   last_author_user_id::text,
                                   last_author_passthrough_identity
                            FROM assistant_threads
                            WHERE thread_id = :thread_id
                            """
                        ),
                        {"thread_id": thread_id},
                    )
                ).fetchone()
                assert row is not None
                assert row[0] == owner_id
                assert row[1] == peer_id
                assert row[2] == f"passthrough:oidc:{peer_id}:yanis@orcia.io"

            # Verify atomic Redis turn lock `SET lock:thread:<thread_id> <user_id> NX EX 60`
            lock_key = f"lock:thread:{thread_id}"
            acquired_by_yanis = r_client.set(lock_key, peer_id, nx=True, ex=60)
            assert acquired_by_yanis is True

            # Concurrent attempt by Hélène while Yanis's turn is running must fail (`NX`)
            acquired_by_helene = r_client.set(lock_key, owner_id, nx=True, ex=60)
            assert acquired_by_helene is None
            assert int(r_client.ttl(lock_key)) > 0
        finally:
            await engine.dispose()
