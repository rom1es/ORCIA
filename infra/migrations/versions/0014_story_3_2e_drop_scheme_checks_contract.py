"""Story 3.2e (Contract): Drop hardcoded scheme CHECK constraints on 4 tables (`AD-20`, `AC-E5`).

Revision ID: 0014_story_3_2e
Revises: 0013_story_3_2e
Create Date: 2026-10-28 10:35:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_story_3_2e"
down_revision: str | None = "0013_story_3_2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the 4 hardcoded scheme `CHECK` constraints now governed by `connector_schemes` FK."""
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                DROP CONSTRAINT IF EXISTS workspace_datasources_scheme_check;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE user_passthrough_credentials
                DROP CONSTRAINT IF EXISTS user_passthrough_credentials_connector_scheme_check;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_policies
                DROP CONSTRAINT IF EXISTS permission_broker_policies_connector_scheme_check;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                DROP CONSTRAINT IF EXISTS permission_broker_tickets_connector_scheme_check;
            """
        )
    )


def downgrade() -> None:
    """Restore the 4 scheme `CHECK` constraints in `downgrade()`."""
    op.execute(
        sa.text(
            """
            DELETE FROM permission_broker_tickets
            WHERE connector_scheme NOT IN ('git', 'jira', 'confluence', 'db', 'nexus', 'mcp');
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM permission_broker_policies
            WHERE connector_scheme NOT IN ('git', 'jira', 'confluence', 'db', 'nexus', 'mcp');
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM user_passthrough_credentials
            WHERE connector_scheme NOT IN ('git', 'jira', 'confluence', 'db', 'nexus');
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM workspace_datasources
            WHERE scheme NOT IN ('git', 'jira', 'confluence', 'db', 'nexus');
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                ADD CONSTRAINT workspace_datasources_scheme_check
                CHECK (scheme IN ('git', 'jira', 'confluence', 'db', 'nexus'));
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE user_passthrough_credentials
                ADD CONSTRAINT user_passthrough_credentials_connector_scheme_check
                CHECK (connector_scheme IN ('git', 'jira', 'confluence', 'db', 'nexus'));
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_policies
                ADD CONSTRAINT permission_broker_policies_connector_scheme_check
                CHECK (connector_scheme IN ('git', 'jira', 'confluence', 'db', 'nexus', 'mcp'));
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                ADD CONSTRAINT permission_broker_tickets_connector_scheme_check
                CHECK (connector_scheme IN ('git', 'jira', 'confluence', 'db', 'nexus', 'mcp'));
            """
        )
    )
