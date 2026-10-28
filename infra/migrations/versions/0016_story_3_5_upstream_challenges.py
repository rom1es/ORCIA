"""Story 3.5: `upstream_challenges` table for Inter-Step Challenge & Replay (`FR-7`, `AD-7`).

Revision ID: 0016_story_3_5
Revises: 0015_story_3_4
Create Date: 2026-10-28 23:39:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_story_3_5"
down_revision: str | None = "0015_story_3_4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `upstream_challenges` table (`FR-7`, `FR-16`, `AD-7`, `UX-DR7`)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS upstream_challenges (
                id UUID PRIMARY KEY,
                challenge_key VARCHAR(160) NOT NULL UNIQUE,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                challenger_step_key VARCHAR(128) NOT NULL,
                target_upstream_step_key VARCHAR(128) NOT NULL,
                challenged_section_key VARCHAR(128) NOT NULL,
                challenge_reason TEXT NOT NULL CHECK (char_length(btrim(challenge_reason)) >= 10),
                target_profile_archetype VARCHAR(48) NOT NULL DEFAULT 'PM_PO',
                translated_summary TEXT NOT NULL,
                invalidated_steps_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                invalidated_sections_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                invalidated_axioms_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                status VARCHAR(48) NOT NULL DEFAULT 'OPEN'
                    CHECK (status IN ('OPEN', 'RESOLVED_REVISED', 'REPLAYED')),
                created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                outbox_event_id UUID NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                resolved_at TIMESTAMPTZ NULL
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_upstream_challenges_run_target
                ON upstream_challenges (run_id, target_upstream_step_key, status);
            """
        )
    )


def downgrade() -> None:
    """Drop `upstream_challenges` table."""
    op.execute(sa.text("DROP TABLE IF EXISTS upstream_challenges;"))
