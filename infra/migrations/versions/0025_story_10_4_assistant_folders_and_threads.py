"""Story 10.4: Create `assistant_folders`, `assistant_threads` & `assistant_folder_shares`.

Revision ID: 0025_story_10_4
Revises: 0024_story_10_2
Create Date: 2026-10-31 17:45:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_story_10_4"
down_revision: str | None = "0024_story_10_2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `assistant_folders`, `assistant_threads`, and `assistant_folder_shares` tables."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS assistant_folders (
                folder_id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                pinned_notes_markdown TEXT NOT NULL DEFAULT '',
                visibility_mode VARCHAR(32) NOT NULL DEFAULT 'PRIVATE'
                    CONSTRAINT assistant_folders_visibility_mode_check
                    CHECK (visibility_mode IN ('PRIVATE', 'SHARED_SELECTED', 'WORKSPACE_OPEN')),
                consolidated_summary TEXT NOT NULL DEFAULT '',
                has_restricted_sources BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_assistant_folders_workspace_id
                ON assistant_folders (workspace_id, updated_at DESC)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS assistant_threads (
                thread_id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                folder_id UUID REFERENCES assistant_folders(folder_id) ON DELETE SET NULL,
                creator_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                thread_summary TEXT NOT NULL DEFAULT '',
                turn_count INTEGER NOT NULL DEFAULT 0,
                last_author_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                last_author_passthrough_identity VARCHAR(255),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_assistant_threads_folder_id
                ON assistant_threads (folder_id, updated_at DESC)
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS assistant_folder_shares (
                share_id UUID PRIMARY KEY,
                folder_id UUID NOT NULL REFERENCES assistant_folders(folder_id) ON DELETE CASCADE,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                grantee_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                access_role VARCHAR(32) NOT NULL DEFAULT 'READ_ONLY'
                    CONSTRAINT assistant_folder_shares_access_role_check
                    CHECK (access_role IN ('READ_ONLY', 'CO_CONTRIBUTOR')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_assistant_folder_share_grantee
                    UNIQUE (folder_id, grantee_user_id)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_assistant_folder_shares_workspace_grantee
                ON assistant_folder_shares (workspace_id, grantee_user_id)
            """
        )
    )


def downgrade() -> None:
    """Drop `assistant_folder_shares`, `assistant_threads`, and `assistant_folders` tables."""
    op.execute(sa.text("DROP TABLE IF EXISTS assistant_folder_shares"))
    op.execute(sa.text("DROP TABLE IF EXISTS assistant_threads"))
    op.execute(sa.text("DROP TABLE IF EXISTS assistant_folders"))
