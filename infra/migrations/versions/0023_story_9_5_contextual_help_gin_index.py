"""Story 9.5: Hybrid Contextual Help (`HelpArticle` in `catalog_items` + GIN index).

Revision ID: 0023_story_9_5
Revises: 0022_epic_8
Create Date: 2026-10-31 16:40:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_story_9_5"
down_revision: str | None = "0022_epic_8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add `item_type` & `metadata_jsonb` + partial GIN index `idx_catalog_help_routes`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE catalog_items
                ADD COLUMN IF NOT EXISTS item_type VARCHAR(64) NOT NULL DEFAULT 'CATALOG_RESOURCE';
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE catalog_items
                ADD COLUMN IF NOT EXISTS metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_catalog_help_routes
                ON catalog_items USING GIN ((metadata_jsonb->'bound_routes'))
                WHERE item_type = 'HELP_ARTICLE';
            """
        )
    )


def downgrade() -> None:
    """Drop partial GIN index `idx_catalog_help_routes` and Story 9.5 columns on `catalog_items`."""
    op.execute(sa.text("DROP INDEX IF EXISTS idx_catalog_help_routes;"))
    op.execute(sa.text("ALTER TABLE catalog_items DROP COLUMN IF EXISTS metadata_jsonb;"))
    op.execute(sa.text("ALTER TABLE catalog_items DROP COLUMN IF EXISTS item_type;"))
