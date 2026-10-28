"""Story 3.4: `human_anchor_signatures` and `human_arbitration_requests` tables (`AD-3`, `AD-18`).

Revision ID: 0015_story_3_4
Revises: 0014_story_3_2e
Create Date: 2026-10-28 23:18:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_story_3_4"
down_revision: str | None = "0014_story_3_2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `human_anchor_signatures` and `human_arbitration_requests` tables (`FR-4`, `FR-5`)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS human_anchor_signatures (
                id UUID PRIMARY KEY,
                signature_key VARCHAR(160) NOT NULL UNIQUE,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                step_execution_id UUID NOT NULL REFERENCES step_executions(id) ON DELETE CASCADE,
                step_key VARCHAR(128) NOT NULL,
                section_key VARCHAR(128) NOT NULL,
                content_text TEXT NOT NULL CHECK (char_length(btrim(content_text)) >= 30),
                content_sha256 CHAR(64) NOT NULL,
                char_length INTEGER NOT NULL CHECK (char_length >= 30),
                authored_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                author_display_name VARCHAR(160) NOT NULL,
                signature_hash VARCHAR(255) NOT NULL,
                signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_human_anchor_signatures_step_section
                ON human_anchor_signatures (step_execution_id, section_key);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_human_anchor_signatures_run_step
                ON human_anchor_signatures (run_id, step_key);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS human_arbitration_requests (
                id UUID PRIMARY KEY,
                arbitration_key VARCHAR(160) NOT NULL UNIQUE,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                step_execution_id UUID NOT NULL REFERENCES step_executions(id) ON DELETE CASCADE,
                step_key VARCHAR(128) NOT NULL,
                tie_break_policy VARCHAR(48) NOT NULL DEFAULT 'PAUSE_AND_ESCALATE'
                    CHECK (tie_break_policy IN (
                        'PAUSE_AND_ESCALATE',
                        'ONTOLOGY_AXIOM_FIRST',
                        'DEFER_AND_CONTINUE_WITH_ASSUMPTION'
                    )),
                status VARCHAR(48) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN (
                        'PENDING',
                        'RESOLVED_BY_HUMAN',
                        'RESOLVED_BY_AXIOM',
                        'DEFERRED_WITH_ASSUMPTION'
                    )),
                question_title VARCHAR(255) NOT NULL,
                context_summary TEXT NOT NULL DEFAULT '',
                options_matrix_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                selected_option_key VARCHAR(128) NULL,
                human_justification TEXT NULL,
                resolved_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                resolved_by_axiom_key VARCHAR(160) NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                resolved_at TIMESTAMPTZ NULL
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_human_arbitration_requests_run_status
                ON human_arbitration_requests (run_id, status, step_key);
            """
        )
    )


def downgrade() -> None:
    """Drop `human_arbitration_requests` and `human_anchor_signatures` tables."""
    op.execute(sa.text("DROP TABLE IF EXISTS human_arbitration_requests;"))
    op.execute(sa.text("DROP TABLE IF EXISTS human_anchor_signatures;"))
