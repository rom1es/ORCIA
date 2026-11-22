"""Story 26.5 — Create `assistant_thread_messages` table (`AD-25`, `D4`).

Revision ID: 20261122_265
Revises: 20261122_264b
Create Date: 2026-11-22

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
Stores strictly human-facing `user` and `assistant` turns with UUIDv7 primary keys,
server-verified `citation_map JSONB`, `token_count`, and `(thread_id, created_at)` index.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261122_265"
down_revision: str | Sequence[str] | None = "20261122_264b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `assistant_thread_messages` table and `(thread_id, created_at)` index."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS assistant_thread_messages (
                id UUID PRIMARY KEY,
                thread_id UUID NOT NULL REFERENCES assistant_threads(thread_id) ON DELETE CASCADE,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                turn_id UUID NOT NULL,
                parent_turn_id UUID NULL,
                role VARCHAR(16) NOT NULL
                    CONSTRAINT assistant_thread_messages_role_check
                    CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                citation_map JSONB NOT NULL DEFAULT '{}'::jsonb,
                token_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_assistant_thread_messages_turn_role UNIQUE (turn_id, role)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_assistant_thread_messages_thread_created
                ON assistant_thread_messages (thread_id, created_at);
            """
        )
    )


def downgrade() -> None:
    """Drop `idx_assistant_thread_messages_thread_created` and `assistant_thread_messages`."""
    op.execute(sa.text("DROP INDEX IF EXISTS idx_assistant_thread_messages_thread_created;"))
    op.execute(sa.text("DROP TABLE IF EXISTS assistant_thread_messages;"))
