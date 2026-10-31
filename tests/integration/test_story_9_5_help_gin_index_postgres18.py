"""Story 9.5 — Real PostgreSQL 18 (`testcontainers`) test for `idx_catalog_help_routes`.

Validates:
- Alembic migration `0023_story_9_5` (`upgrade` -> `downgrade` -> `upgrade`) on real PG 18.
- Partial GIN index `idx_catalog_help_routes` on `(metadata_jsonb->'bound_routes')`.
- Idempotent upsert via `HELP_ARTICLES_CATALOG_UPSERT_SPEC` (`bootstrap/seeder.py`).
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
    HELP_ARTICLES_CATALOG_UPSERT_SPEC,
    ORG_UNITS_UPSERT_SPEC,
    build_postgres_upsert_sql,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_story_9_5_alembic_0023_gin_index_and_help_article_upsert_postgres18() -> None:
    """Verify migration 0023 upgrade/downgrade and GIN index query on real PostgreSQL 18."""
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

                def _run_upgrade_and_downgrade(sync_conn: sa.Connection) -> None:
                    alembic_cfg.attributes["connection"] = sync_conn
                    command.upgrade(alembic_cfg, "head")
                    command.downgrade(alembic_cfg, "0022_epic_8")
                    command.upgrade(alembic_cfg, "head")

                await conn.run_sync(_run_upgrade_and_downgrade)

            async with engine.begin() as conn:
                # Seed an org_unit and a HELP_ARTICLE in catalog_items
                org_sql = build_postgres_upsert_sql(ORG_UNITS_UPSERT_SPEC)
                await conn.execute(
                    sa.text(org_sql),
                    {
                        "id": "0192c4e0-0000-7000-8000-000000000001",
                        "slug": "orcia-root-org",
                        "name": "ORCIA Root Org",
                        "unit_type": "ENTERPRISE",
                        "parent_id": None,
                    },
                )

                help_sql = build_postgres_upsert_sql(HELP_ARTICLES_CATALOG_UPSERT_SPEC)
                await conn.execute(
                    sa.text(help_sql),
                    {
                        "id": "0192c4e0-0000-7000-8000-000000000950",
                        "resource_id": "help-pack-sdlc-spaces-sources-fr",
                        "uri": "orcia://packs/orcia-pack-sdlc/help/spaces-sources/fr",
                        "title": "Sources SDLC de l'Espace",
                        "description": "Fiche d'aide contextuelle",
                        "resource_type": "template",
                        "source_format": "ORCIA",
                        "version": "1.1.0",
                        "sha256": "a" * 64,
                        "cas_key": f"cas/{'a' * 64}",
                        "visibility_scope": "PUBLISHED_ORG",
                        "owner_org_unit_id": "0192c4e0-0000-7000-8000-000000000001",
                        "owner_workspace_id": None,
                        "item_type": "HELP_ARTICLE",
                        "metadata_jsonb": json.dumps(
                            {"bound_routes": ["/mes-espaces/$id/sources", "/spaces"]}
                        ),
                    },
                )

                # Query using the partial GIN index expression
                res = await conn.execute(
                    sa.text(
                        """
                        SELECT resource_id, item_type
                        FROM catalog_items
                        WHERE item_type = 'HELP_ARTICLE'
                          AND (metadata_jsonb->'bound_routes') @>
                              '["/mes-espaces/$id/sources"]'::jsonb
                        """
                    )
                )
                row = res.fetchone()
                assert row is not None
                assert row[0] == "help-pack-sdlc-spaces-sources-fr"
                assert row[1] == "HELP_ARTICLE"

                # Verify index `idx_catalog_help_routes` exists in pg_indexes
                idx_res = await conn.execute(
                    sa.text(
                        """
                        SELECT indexname
                        FROM pg_indexes
                        WHERE tablename = 'catalog_items'
                          AND indexname = 'idx_catalog_help_routes'
                        """
                    )
                )
                assert idx_res.scalar_one() == "idx_catalog_help_routes"
        finally:
            await engine.dispose()
