"""Story 26.7 — Add `execution_profile` to `reflexive_execution_sessions` (`AD-25`).

Revision ID: 20261122_267
Revises: 20261122_266a
Create Date: 2026-11-22 15:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261122_267"
down_revision: str | None = "20261122_266a"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Add `execution_profile` (`PROCESS | ASSISTANT`) column, check constraint, and index."""
    op.execute(
        sa.text(
            """
            ALTER TABLE reflexive_execution_sessions
                ADD COLUMN IF NOT EXISTS execution_profile VARCHAR(24) NOT NULL DEFAULT 'PROCESS'
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'ck_reflexive_exec_sessions_profile'
                ) THEN
                    ALTER TABLE reflexive_execution_sessions
                        ADD CONSTRAINT ck_reflexive_exec_sessions_profile
                        CHECK (execution_profile IN ('PROCESS', 'ASSISTANT'));
                END IF;
            END $$
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_reflexive_exec_sessions_profile_ws
                ON reflexive_execution_sessions (execution_profile, workspace_id, updated_at DESC)
            """
        )
    )


def downgrade() -> None:
    """Drop `execution_profile` index, constraint, and column."""
    op.execute(sa.text("DROP INDEX IF EXISTS ix_reflexive_exec_sessions_profile_ws"))
    op.execute(
        sa.text(
            """
            ALTER TABLE reflexive_execution_sessions
                DROP CONSTRAINT IF EXISTS ck_reflexive_exec_sessions_profile
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE reflexive_execution_sessions
                DROP COLUMN IF EXISTS execution_profile
            """
        )
    )
