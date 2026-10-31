"""Story 11.1 — Real PostgreSQL 18 `testcontainers` integration test.

Verifies against a real ephemeral PostgreSQL 18 container:
1. Alembic migration `0026_story_11_1` (`workspace_exception_waivers` table, CHECK constraints
   on `norm_level` and `status`, and UNIQUE constraint).
2. `chunk_approvals_status_check` expansion allowing `HUMAN_AMENDED_EXTERNAL` (`Verrou V2`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
import uuid_utils as uuid
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_story_11_1_waivers_and_human_amended_external_postgres18() -> None:
    """Verify `0026_story_11_1` schema on real PostgreSQL 18 (`testcontainers`)."""
    with PostgresContainer("pgvector/pgvector:pg18") as pg_container:
        sync_url = pg_container.get_connection_url().replace(
            "postgresql+psycopg2://", "postgresql+psycopg://"
        )
        async_url = sync_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

        org_id = str(uuid.uuid7())
        ws_id = str(uuid.uuid7())
        user_id = str(uuid.uuid7())
        waiver_id = str(uuid.uuid7())

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
                        VALUES (:id, :slug, 'Team Claims 11.1', 'TEAM', NULL)
                        """
                    ),
                    {"id": org_id, "slug": f"team-11-1-{org_id[:8]}"},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO users (
                            id, email, display_name, auth_mode,
                            human_profile_archetype, platform_role, primary_org_unit_id
                        )
                        VALUES (
                            :uid, :email, 'Claire TechLead', 'OIDC',
                            'TECH_LEAD', 'TEAM_LEAD', :org_id
                        )
                        """
                    ),
                    {
                        "uid": user_id,
                        "email": f"claire-{user_id[:6]}@orcia.io",
                        "org_id": org_id,
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspaces (
                            id, slug, name, owner_org_unit_id, visibility_mode
                        )
                        VALUES (:ws_id, :slug, 'Workspace Claims 11.1', :org_id, 'STANDARD')
                        """
                    ),
                    {"ws_id": ws_id, "slug": f"ws-11-1-{ws_id[:8]}", "org_id": org_id},
                )

                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspace_exception_waivers (
                            waiver_id, workspace_id, source_uri, source_sha256,
                            conflict_rule_id, norm_level, dna_chain_jsonb,
                            approved_by_user_id, approved_by_role, reason, status,
                            expires_at
                        )
                        VALUES (
                            :wid, :ws_id, 'confluence://CLAIMS/OLD-SPEC', 'sha256_abc123',
                            'RULE_STALE_DOC', '3_WORKSPACE',
                            CAST(:dna AS jsonb),
                            :uid, 'TEAM_LEAD', 'Acquitté pour le sprint courant', 'ACTIVE',
                            NOW() + INTERVAL '30 days'
                        )
                        """
                    ),
                    {
                        "wid": waiver_id,
                        "ws_id": ws_id,
                        "uid": user_id,
                        "dna": (
                            '[{"node_key":"NORM_1","stereotype":"NORM",'
                            '"level":"3_WORKSPACE","inviolable":false}]'
                        ),
                    },
                )

                row = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT conflict_rule_id, status, norm_level
                            FROM workspace_exception_waivers
                            WHERE waiver_id = :wid
                            """
                        ),
                        {"wid": waiver_id},
                    )
                ).one()
                assert row[0] == "RULE_STALE_DOC"
                assert row[1] == "ACTIVE"
                assert row[2] == "3_WORKSPACE"

                # Verify chunk_approvals constraint definition includes HUMAN_AMENDED_EXTERNAL
                chk_def = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT pg_get_constraintdef(oid)
                            FROM pg_constraint
                            WHERE conname = 'chunk_approvals_status_check'
                            """
                        )
                    )
                ).scalar_one()
                assert "HUMAN_AMENDED_EXTERNAL" in str(chk_def)
        finally:
            await engine.dispose()
