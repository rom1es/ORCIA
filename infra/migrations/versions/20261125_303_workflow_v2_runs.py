"""Story 30.3 — Persist `workflow_v2_runs` in PostgreSQL 18 (`UX30-06`, `CAP-140`, `CAP-160`).

Revision ID: 20261125_303
Revises: 20261122_267
Create Date: 2026-11-25 23:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261125_303"
down_revision: str | None = "20261122_267"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create `workflow_v2_runs` table and workspace/status index (raw SQL, UUIDv7 PK)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS workflow_v2_runs (
                id UUID PRIMARY KEY,
                run_id VARCHAR(128) NOT NULL UNIQUE,
                workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                workflow_id VARCHAR(128) NOT NULL,
                workflow_slug VARCHAR(128) NOT NULL,
                workflow_title VARCHAR(255) NOT NULL DEFAULT '',
                actor_slug VARCHAR(128) NOT NULL DEFAULT '',
                status VARCHAR(48) NOT NULL DEFAULT 'RUNNING',
                reflexive_execution_id VARCHAR(128) NULL,
                state_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_workflow_v2_runs_ws_status_updated
                ON workflow_v2_runs (workspace_id, status, updated_at DESC)
            """
        )
    )


def downgrade() -> None:
    """Drop `workflow_v2_runs` index and table."""
    op.execute(sa.text("DROP INDEX IF EXISTS ix_workflow_v2_runs_ws_status_updated"))
    op.execute(sa.text("DROP TABLE IF EXISTS workflow_v2_runs"))
