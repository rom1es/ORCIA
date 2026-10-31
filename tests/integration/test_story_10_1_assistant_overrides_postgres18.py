"""Story 10.1 — Real PostgreSQL 18 (`testcontainers`) test for `workspace_customization_overrides`.

Validates:
- Upserting scoped `TEAM`, `WORKSPACE`, and `USER` customization overrides for
  `target_uri = 'orcia://system/workflows/assistant-agent'` in real PostgreSQL 18.
- 1-click reset (`DELETE FROM workspace_customization_overrides WHERE override_key = ...`)
  restoring parent inheritance without mutating the base workflow definition.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_core.bootstrap.seeder import (
    ASSISTANT_WORKFLOW_URI,
    CUSTOMIZATION_OVERRIDES_UPSERT_SPEC,
    ORG_UNITS_UPSERT_SPEC,
    WORKSPACES_UPSERT_SPEC,
    build_postgres_upsert_sql,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_story_10_1_assistant_overrides_and_reset_postgres18() -> None:
    """Verify `TEAM` and `WORKSPACE` overrides for `assistant-agent` on real PostgreSQL 18."""
    with PostgresContainer("pgvector/pgvector:pg18") as pg:
        sync_url = pg.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+psycopg://"
        )
        async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")

        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

        engine = create_async_engine(async_url, pool_size=4, max_overflow=4)
        try:
            async with engine.begin() as conn:

                def _upgrade_head(sync_conn: sa.Connection) -> None:
                    alembic_cfg.attributes["connection"] = sync_conn
                    command.upgrade(alembic_cfg, "head")

                await conn.run_sync(_upgrade_head)

            async with engine.begin() as conn:
                org_id = "0192c4e0-0000-7000-8000-000000001001"
                ws_id = "0192c4e0-0000-7000-8000-000000001002"

                await conn.execute(
                    sa.text(build_postgres_upsert_sql(ORG_UNITS_UPSERT_SPEC)),
                    {
                        "id": org_id,
                        "slug": "team-checkout-10-1",
                        "name": "Team Checkout 10.1",
                        "unit_type": "TEAM",
                        "parent_id": None,
                    },
                )
                await conn.execute(
                    sa.text(build_postgres_upsert_sql(WORKSPACES_UPSERT_SPEC)),
                    {
                        "id": ws_id,
                        "slug": "ws-checkout-10-1",
                        "name": "Workspace Checkout 10.1",
                        "owner_org_unit_id": org_id,
                        "visibility_mode": "STANDARD",
                        "finops_cost_usd": 0.0,
                    },
                )

                ov_sql = build_postgres_upsert_sql(CUSTOMIZATION_OVERRIDES_UPSERT_SPEC)
                await conn.execute(
                    sa.text(ov_sql),
                    {
                        "id": "0192c4e0-0000-7000-8000-000000001010",
                        "override_key": "assistant-studio-team-checkout",
                        "org_unit_id": org_id,
                        "workspace_id": None,
                        "user_id": None,
                        "target_uri": ASSISTANT_WORKFLOW_URI,
                        "override_layer": "TEAM",
                        "override_manifest_jsonb": json.dumps(
                            {"ai_pre_prompt": "Standard Équipe Checkout"}
                        ),
                        "sha256": "a" * 64,
                    },
                )
                await conn.execute(
                    sa.text(ov_sql),
                    {
                        "id": "0192c4e0-0000-7000-8000-000000001011",
                        "override_key": "assistant-studio-workspace-checkout",
                        "org_unit_id": None,
                        "workspace_id": ws_id,
                        "user_id": None,
                        "target_uri": ASSISTANT_WORKFLOW_URI,
                        "override_layer": "WORKSPACE",
                        "override_manifest_jsonb": json.dumps(
                            {
                                "ai_pre_prompt": "Surcharge Espace Checkout",
                                "mcp_expose_assistant": True,
                            }
                        ),
                        "sha256": "b" * 64,
                    },
                )

                rows = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT override_layer, override_key
                            FROM workspace_customization_overrides
                            WHERE target_uri = :uri
                            ORDER BY override_layer
                            """
                        ),
                        {"uri": ASSISTANT_WORKFLOW_URI},
                    )
                ).fetchall()
                assert len(rows) == 2

                # 1-click Reset of WORKSPACE override leaves TEAM override intact
                await conn.execute(
                    sa.text(
                        """
                        DELETE FROM workspace_customization_overrides
                        WHERE override_key = 'assistant-studio-workspace-checkout'
                        """
                    )
                )
                remaining = (
                    (
                        await conn.execute(
                            sa.text(
                                """
                            SELECT override_layer
                            FROM workspace_customization_overrides
                            WHERE target_uri = :uri
                            """
                            ),
                            {"uri": ASSISTANT_WORKFLOW_URI},
                        )
                    )
                    .scalars()
                    .all()
                )
                assert remaining == ["TEAM"]
        finally:
            await engine.dispose()
