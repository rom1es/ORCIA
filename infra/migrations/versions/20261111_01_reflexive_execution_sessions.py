"""0029 / 20261111_01 — Stateless Reflexive Execution Sessions (`Story 16.2`, `CAP-160`).

Revision ID: 20261111_01
Revises: 20261108_0910
Create Date: 2026-11-11 14:50:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_01"
down_revision: str | None = "20261108_0910"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create `reflexive_execution_sessions` table and status/TTL indexes (raw SQL, UUIDv7 PK)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS reflexive_execution_sessions (
                id UUID PRIMARY KEY,
                execution_id VARCHAR(128) NOT NULL UNIQUE,
                workspace_id VARCHAR(128),
                actor_slug VARCHAR(128) NOT NULL,
                orchestration_mode VARCHAR(32) NOT NULL DEFAULT 'non_deterministic',
                effort_level VARCHAR(16) NOT NULL DEFAULT 'standard',
                status VARCHAR(32) NOT NULL DEFAULT 'RUNNING',
                snapshot_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_reflexive_exec_sessions_ws_status_updated
                ON reflexive_execution_sessions (workspace_id, status, updated_at DESC)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_reflexive_exec_sessions_expires_at
                ON reflexive_execution_sessions (expires_at)
            """
        )
    )


def downgrade() -> None:
    """Drop `reflexive_execution_sessions` indexes and table."""
    op.execute(sa.text("DROP INDEX IF EXISTS ix_reflexive_exec_sessions_expires_at"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_reflexive_exec_sessions_ws_status_updated"))
    op.execute(sa.text("DROP TABLE IF EXISTS reflexive_execution_sessions"))
