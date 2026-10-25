"""Story 1.1 Foundation Extensions: pgvector & append-only trigger function.

Revision ID: 0001_story_1_1
Revises: None
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001_story_1_1"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_APPEND_ONLY_FN_SQL = """
CREATE OR REPLACE FUNCTION orcia_prevent_append_only_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'ERR_APPEND_ONLY_VIOLATION: table % is strictly append-only (operation % forbidden)',
        TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$;
"""

DOWNGRADE_APPEND_ONLY_FN_SQL = """
DROP FUNCTION IF EXISTS orcia_prevent_append_only_mutation();
"""


def upgrade() -> None:
    """Apply foundation database extensions and append-only trigger function."""
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector;"))
    op.execute(sa.text(UPGRADE_APPEND_ONLY_FN_SQL))


def downgrade() -> None:
    """Revert foundation append-only trigger function and vector extension."""
    op.execute(sa.text(DOWNGRADE_APPEND_ONLY_FN_SQL))
    op.execute(sa.text("DROP EXTENSION IF EXISTS vector;"))
