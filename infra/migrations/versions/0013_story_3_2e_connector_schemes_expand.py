"""Story 3.2e (Expand): `connector_schemes` table, idempotent seed & NOT VALID / VALIDATED FKs.

Revision ID: 0013_story_3_2e
Revises: 0012_story_3_2c
Create Date: 2026-10-28 10:30:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_story_3_2e"
down_revision: str | None = "0012_story_3_2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `connector_schemes`, seed schemes idempotently, and attach validated FKs."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS connector_schemes (
                id UUID PRIMARY KEY,
                scheme VARCHAR(32) NOT NULL UNIQUE,
                display_name VARCHAR(128) NOT NULL,
                pack_name VARCHAR(128) NOT NULL DEFAULT 'orcia-core',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO connector_schemes (id, scheme, display_name, pack_name, is_active)
            VALUES
                (
                    '0192c4e0-0000-7000-8000-00000000c001',
                    'orcia', 'ORCIA Native URI', 'orcia-core', TRUE
                ),
                (
                    '0192c4e0-0000-7000-8000-00000000c002',
                    'db', 'Relational Database Connector', 'orcia-core', TRUE
                ),
                (
                    '0192c4e0-0000-7000-8000-00000000c003',
                    'mcp', 'Model Context Protocol Connector', 'orcia-core', TRUE
                ),
                (
                    '0192c4e0-0000-7000-8000-00000000c004',
                    'git', 'Git Repository Connector', 'orcia-pack-sdlc', TRUE
                ),
                (
                    '0192c4e0-0000-7000-8000-00000000c005',
                    'jira', 'Jira Issue Tracker Connector', 'orcia-pack-sdlc', TRUE
                ),
                (
                    '0192c4e0-0000-7000-8000-00000000c006',
                    'confluence', 'Confluence Wiki Connector', 'orcia-pack-sdlc', TRUE
                ),
                (
                    '0192c4e0-0000-7000-8000-00000000c007',
                    'nexus', 'Nexus Artifact Repository Connector', 'orcia-pack-sdlc', TRUE
                )
            ON CONFLICT (scheme) DO UPDATE
            SET display_name = EXCLUDED.display_name,
                pack_name = EXCLUDED.pack_name,
                is_active = EXCLUDED.is_active;
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                ADD CONSTRAINT fk_workspace_datasources_scheme
                FOREIGN KEY (scheme) REFERENCES connector_schemes(scheme)
                ON DELETE RESTRICT NOT VALID;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                VALIDATE CONSTRAINT fk_workspace_datasources_scheme;
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE user_passthrough_credentials
                ADD CONSTRAINT fk_user_passthrough_credentials_scheme
                FOREIGN KEY (connector_scheme) REFERENCES connector_schemes(scheme)
                ON DELETE RESTRICT NOT VALID;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE user_passthrough_credentials
                VALIDATE CONSTRAINT fk_user_passthrough_credentials_scheme;
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_policies
                ADD CONSTRAINT fk_permission_broker_policies_scheme
                FOREIGN KEY (connector_scheme) REFERENCES connector_schemes(scheme)
                ON DELETE RESTRICT NOT VALID;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_policies
                VALIDATE CONSTRAINT fk_permission_broker_policies_scheme;
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                ADD CONSTRAINT fk_permission_broker_tickets_scheme
                FOREIGN KEY (connector_scheme) REFERENCES connector_schemes(scheme)
                ON DELETE RESTRICT NOT VALID;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                VALIDATE CONSTRAINT fk_permission_broker_tickets_scheme;
            """
        )
    )


def downgrade() -> None:
    """Drop FKs on the 4 scheme columns and drop `connector_schemes` table."""
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_tickets
                DROP CONSTRAINT IF EXISTS fk_permission_broker_tickets_scheme;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE permission_broker_policies
                DROP CONSTRAINT IF EXISTS fk_permission_broker_policies_scheme;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE user_passthrough_credentials
                DROP CONSTRAINT IF EXISTS fk_user_passthrough_credentials_scheme;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                DROP CONSTRAINT IF EXISTS fk_workspace_datasources_scheme;
            """
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS connector_schemes;"))
