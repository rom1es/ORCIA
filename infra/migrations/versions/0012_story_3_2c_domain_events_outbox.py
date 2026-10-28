"""Story 3.2c: Transactional Outbox table `domain_events_outbox` (`ARCH-M6`, `Q2: 2A`, `C3`).

Revision ID: 0012_story_3_2c
Revises: 0011_story_3_2
Create Date: 2026-10-28 08:30:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_story_3_2c"
down_revision: str | None = "0011_story_3_2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `domain_events_outbox` table and partial index on `status = 'PENDING'` (`AD-19`)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS domain_events_outbox (
                event_id UUID PRIMARY KEY,
                event_type VARCHAR(96) NOT NULL
                    CHECK (event_type IN (
                        'StepCompleted',
                        'ArtifactProduced',
                        'GateEvaluated',
                        'RunTerminated',
                        'HumanArbitrationRequested'
                    )),
                aggregate_type VARCHAR(96) NOT NULL,
                aggregate_id VARCHAR(128) NOT NULL,
                run_id UUID NULL REFERENCES workflow_runs(id) ON DELETE SET NULL,
                workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE SET NULL,
                payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                trace_id VARCHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'PUBLISHED', 'FAILED')),
                attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                published_at TIMESTAMPTZ NULL
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_domain_events_outbox_pending
                ON domain_events_outbox (created_at ASC, event_id ASC)
                WHERE status = 'PENDING';
            """
        )
    )


def downgrade() -> None:
    """Drop `domain_events_outbox` table and partial index."""
    op.execute(sa.text("DROP INDEX IF EXISTS idx_domain_events_outbox_pending;"))
    op.execute(sa.text("DROP TABLE IF EXISTS domain_events_outbox;"))
