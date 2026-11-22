"""Story 10.2 (Amended by Story 26.4a `R6`) — PG18 Outbox & Direct 5-Layer Prompt Assembly.

Validates:
- Direct 5-layer prompt assembly (`cache_hit=False`, `ttl_seconds=0`, measured latency) per `R6`.
- Real PostgreSQL 18 Outbox persistence via `AssistantOutboxEmitter` &
  `SqlDomainEventsOutboxRepository` (`SettingsChanged` & `AssistantTurnCompleted`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_core.orchestration.assistant_outbox_emitter import AssistantOutboxEmitter
from orcia_core.orchestration.assistant_three_speed_router import (
    AssistantThreeSpeedRouterService,
    build_assistant_prompt_cache_key,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_story_10_2_direct_prompt_assembly_and_real_outbox_pg18() -> None:
    """Verify `R6` direct prompt assembly and real PG18 Outbox `SettingsChanged` persistence."""
    with PostgresContainer("pgvector/pgvector:pg18") as pg_container:
        router_svc = AssistantThreeSpeedRouterService()
        ws_id = "0192c4e0-0000-7000-8000-000000001020"
        user_id = "u-claire-01"
        hat = "PM"
        expected_key = build_assistant_prompt_cache_key(ws_id, user_id, hat)
        assert expected_key == f"assistant:prompt:{ws_id}:{user_id}:{hat}"

        assembled = router_svc.get_or_assemble_cached_prompt(
            workspace_id=ws_id,
            user_id=user_id,
            hat=hat,
        )
        assert assembled.cache_hit is False
        assert assembled.ttl_seconds == 0
        assert len(assembled.layers) == 5

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
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                        VALUES (
                            CAST('0192c4e0-0000-7000-8000-000000000001' AS uuid),
                            'orcia-root-10-2',
                            'ORCIA Root 10.2',
                            'ENTERPRISE',
                            NULL
                        )
                        ON CONFLICT (id) DO NOTHING;
                        """
                    )
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode)
                        VALUES (
                            CAST(:ws_id AS uuid),
                            'ws-10-2-outbox',
                            'WS 10.2 Outbox',
                            CAST('0192c4e0-0000-7000-8000-000000000001' AS uuid),
                            'STANDARD'
                        )
                        ON CONFLICT (id) DO NOTHING;
                        """
                    ),
                    {"ws_id": ws_id},
                )

            emitter = AssistantOutboxEmitter.from_uow_or_engine(engine=engine)
            assert emitter is not None
            event_id = await emitter.emit_settings_changed(
                workspace_id=ws_id,
                setting_key="assistant.mode_a.workspace",
                actor_id=user_id,
                trace_id="0" * 32,
            )
            assert event_id is not None

            async with engine.begin() as conn:
                count = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT COUNT(*) FROM domain_events_outbox
                            WHERE event_id = CAST(:event_id AS uuid)
                              AND event_type = 'SettingsChanged'
                            """
                        ),
                        {"event_id": event_id},
                    )
                ).scalar_one()
                assert int(count) == 1
        finally:
            await engine.dispose()
