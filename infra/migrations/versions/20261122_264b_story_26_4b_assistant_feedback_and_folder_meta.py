"""Story 26.4b — Create `assistant_turn_feedback` and add folder metadata columns.

Revision ID: 20261122_264b
Revises: 20261122_264a
Create Date: 2026-11-22

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
No Mode B studio table (`R2`) and no citation drafts table (`R5`) are created.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261122_264b"
down_revision: str | Sequence[str] | None = "20261122_264a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `assistant_turn_feedback` and extend `assistant_folders` with attachment/tag meta."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS assistant_turn_feedback (
                id UUID PRIMARY KEY,
                turn_id UUID NOT NULL,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                rating VARCHAR(8) NOT NULL
                    CONSTRAINT assistant_turn_feedback_rating_check
                    CHECK (rating IN ('up', 'down')),
                reason_code VARCHAR(64) NULL,
                comment TEXT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_assistant_turn_feedback_turn_user UNIQUE (turn_id, user_id)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_assistant_turn_feedback_workspace_turn
                ON assistant_turn_feedback (workspace_id, turn_id);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_assistant_turn_feedback_turn_id
                ON assistant_turn_feedback (turn_id);
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE assistant_folders
                ADD COLUMN IF NOT EXISTS working_attachments_uris JSONB
                    NOT NULL DEFAULT '[]'::jsonb,
                ADD COLUMN IF NOT EXISTS evidence_tags TEXT[] NOT NULL DEFAULT '{}'::text[];
            """
        )
    )


def downgrade() -> None:
    """Remove `assistant_folders` metadata columns and drop `assistant_turn_feedback`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE assistant_folders
                DROP COLUMN IF EXISTS evidence_tags,
                DROP COLUMN IF EXISTS working_attachments_uris;
            """
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_assistant_turn_feedback_turn_id;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_assistant_turn_feedback_workspace_turn;"))
    op.execute(sa.text("DROP TABLE IF EXISTS assistant_turn_feedback;"))
