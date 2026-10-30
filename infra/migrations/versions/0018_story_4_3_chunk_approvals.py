"""Story 4.3: `chunk_approvals` table for Chunked Validation & Adaptive Human Gates (`AD-11`).

Revision ID: 0018_story_4_3
Revises: 0017_story_4_1
Create Date: 2026-10-30 08:25:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_story_4_3"
down_revision: str | None = "0017_story_4_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `chunk_approvals` table (`FR-6`, `FR-19`, `AD-11`)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS chunk_approvals (
                id UUID PRIMARY KEY,
                gate_evaluation_id UUID NOT NULL
                    REFERENCES gate_evaluations(id) ON DELETE CASCADE,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                step_execution_id UUID NOT NULL
                    REFERENCES step_executions(id) ON DELETE CASCADE,
                chunk_key VARCHAR(128) NOT NULL,
                section_title VARCHAR(255) NOT NULL,
                section_index INTEGER NOT NULL DEFAULT 0 CHECK (section_index >= 0),
                content_markdown TEXT NOT NULL DEFAULT '',
                word_count INTEGER NOT NULL DEFAULT 0 CHECK (word_count >= 0),
                human_authored_required BOOLEAN NOT NULL DEFAULT FALSE,
                status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'APPROVED', 'CO_EDITED', 'CHALLENGED')),
                reviewer_user_id VARCHAR(128) NULL,
                human_anchor_signature_id UUID NULL
                    REFERENCES human_anchor_signatures(id) ON DELETE SET NULL,
                challenge_reason TEXT NULL,
                reviewed_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_chunk_approvals_gate_chunk
                    UNIQUE (gate_evaluation_id, chunk_key)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_chunk_approvals_gate_status
                ON chunk_approvals (gate_evaluation_id, status);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_chunk_approvals_run_step
                ON chunk_approvals (run_id, step_execution_id);
            """
        )
    )


def downgrade() -> None:
    """Drop `chunk_approvals` table."""
    op.execute(sa.text("DROP TABLE IF EXISTS chunk_approvals;"))
