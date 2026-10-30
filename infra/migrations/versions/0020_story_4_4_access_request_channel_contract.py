"""Story 4.4 (`DEC-ACC-01`): Contract legacy `jira_request_url` on `permission_broker_tickets`.

Revision ID: 0020_story_4_4_contract
Revises: 0019_story_4_4_expand
Create Date: 2026-10-30 08:48:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_story_4_4_contract"
down_revision: str | None = "0019_story_4_4_expand"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Contract legacy `jira_request_url` column after `request_url` backfill (`DEC-ACC-01`)."""
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                DROP COLUMN IF EXISTS jira_request_url;
            """
        )
    )


def downgrade() -> None:
    """Restore and backfill `jira_request_url` from `request_url`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                ADD COLUMN IF NOT EXISTS jira_request_url TEXT;
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE permission_broker_tickets
               SET jira_request_url = request_url
             WHERE jira_request_url IS NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                ALTER COLUMN jira_request_url SET NOT NULL;
            """
        )
    )
