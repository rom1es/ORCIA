"""Story 19.5 — AI Models Hub usage & active global embedding (`AD-24.5`, `D5`, `D6`).

Revision ID: 20261115_2105
Revises: 20261115_1901
Create Date: 2026-11-15

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261115_2105"
down_revision: str | None = "20261115_1901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_llm_tier_mappings
                ADD COLUMN IF NOT EXISTS usage VARCHAR(32) NOT NULL DEFAULT 'chat'
                    CHECK (usage IN ('chat', 'embedding'));
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_tier_mappings_single_active_global_embedding
                ON workspace_llm_tier_mappings (scope_level, usage)
                WHERE (usage = 'embedding' AND is_active = TRUE AND scope_level = 'GLOBAL');
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DROP INDEX IF EXISTS idx_llm_tier_mappings_single_active_global_embedding;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_llm_tier_mappings
                DROP COLUMN IF EXISTS usage;
            """
        )
    )
