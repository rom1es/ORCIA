"""Epic 7 review: add FK `workspaces(id) ON DELETE CASCADE` on `autonomy_contracts` (`MINOR-02`).

Revision ID: 20261117_0705
Revises: 20261117_0704
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261117_0705"
down_revision: str | Sequence[str] | None = "20261117_0704"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Purge orphan `autonomy_contracts` rows and enforce FK `workspaces(id)`."""
    op.execute(
        sa.text(
            """
            DELETE FROM autonomy_contracts
            WHERE workspace_id NOT IN (SELECT id FROM workspaces);
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
                    WHERE conname = 'fk_autonomy_contracts_workspace'
                      AND conrelid = 'autonomy_contracts'::regclass
                ) THEN
                    ALTER TABLE autonomy_contracts
                        ADD CONSTRAINT fk_autonomy_contracts_workspace
                        FOREIGN KEY (workspace_id)
                        REFERENCES workspaces(id)
                        ON DELETE CASCADE;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    """Drop FK constraint `fk_autonomy_contracts_workspace` from `autonomy_contracts`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE autonomy_contracts
                DROP CONSTRAINT IF EXISTS fk_autonomy_contracts_workspace;
            """
        )
    )
