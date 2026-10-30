"""Story 4.4 (`DEC-ACC-01`): Expand + Backfill `request_url` on `permission_broker_tickets`.

Revision ID: 0019_story_4_4_expand
Revises: 0018_story_4_3
Create Date: 2026-10-30 08:47:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_story_4_4_expand"
down_revision: str | None = "0018_story_4_3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Expand `permission_broker_tickets.request_url` and backfill from `jira_request_url`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                ADD COLUMN IF NOT EXISTS request_url TEXT;
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE permission_broker_tickets
               SET request_url = jira_request_url
             WHERE request_url IS NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                ALTER COLUMN request_url SET NOT NULL;
            """
        )
    )


def downgrade() -> None:
    """Drop expanded `request_url` column from `permission_broker_tickets`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                DROP COLUMN IF EXISTS request_url;
            """
        )
    )
