"""Story 26.6a — Add `supports_tools` columns to `workspace_llm_tier_mappings`.

Revision ID: 20261122_266a
Revises: 20261122_265
Create Date: 2026-11-22

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261122_266a"
down_revision: str | Sequence[str] | None = "20261122_265"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add `supports_tools` and `supports_tools_override` to `workspace_llm_tier_mappings`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_llm_tier_mappings
                ADD COLUMN IF NOT EXISTS supports_tools BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS supports_tools_override BOOLEAN NULL;
            """
        )
    )


def downgrade() -> None:
    """Remove `supports_tools_override` and `supports_tools` from `workspace_llm_tier_mappings`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_llm_tier_mappings
                DROP COLUMN IF EXISTS supports_tools_override,
                DROP COLUMN IF EXISTS supports_tools;
            """
        )
    )
