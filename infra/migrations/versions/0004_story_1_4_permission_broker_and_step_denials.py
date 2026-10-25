"""Story 1.4 Passthrough / Service Principal Execution & AI Permission Broker connected to Jira.

Revision ID: 0004_story_1_4
Revises: 0003_story_1_3
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0004_story_1_4"
down_revision: str | None = "0003_story_1_3"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE permission_broker_policies (
        id UUID PRIMARY KEY,
        policy_key VARCHAR(128) NOT NULL UNIQUE,
        uri_pattern TEXT NOT NULL UNIQUE,
        connector_scheme VARCHAR(32) NOT NULL CHECK (
            connector_scheme IN ('git', 'jira', 'confluence', 'db', 'nexus', 'mcp')
        ),
        required_role VARCHAR(128) NOT NULL,
        approver_team VARCHAR(128) NOT NULL,
        request_url_template TEXT NOT NULL,
        sla_hours INTEGER NOT NULL CHECK (sla_hours > 0),
        procedure_markdown TEXT NOT NULL DEFAULT '',
        service_principal_allowed BOOLEAN NOT NULL DEFAULT FALSE,
        approved_by_admin_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        human_anchor_author_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        human_anchor_signature TEXT NULL,
        freshness_ttl_days INTEGER NOT NULL DEFAULT 90 CHECK (freshness_ttl_days > 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_permission_broker_policies_scheme "
        "ON permission_broker_policies(connector_scheme);"
    ),
    """
    CREATE TABLE permission_broker_tickets (
        id UUID PRIMARY KEY,
        ticket_key VARCHAR(128) NOT NULL UNIQUE,
        workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        requester_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        policy_id UUID NOT NULL REFERENCES permission_broker_policies(id) ON DELETE RESTRICT,
        step_key VARCHAR(128) NOT NULL,
        step_number INTEGER NOT NULL DEFAULT 1 CHECK (step_number > 0),
        step_state VARCHAR(64) NOT NULL DEFAULT 'PERMISSION_DENIED_STEP' CHECK (
            step_state IN ('PERMISSION_DENIED_STEP', 'PAUSED', 'REPLAYED', 'GRANTED')
        ),
        status VARCHAR(64) NOT NULL DEFAULT 'WAITING_FOR_PERMISSION' CHECK (
            status IN ('WAITING_FOR_PERMISSION', 'PAUSED', 'REPLAYED', 'GRANTED')
        ),
        target_uri TEXT NOT NULL,
        connector_scheme VARCHAR(32) NOT NULL CHECK (
            connector_scheme IN ('git', 'jira', 'confluence', 'db', 'nexus', 'mcp')
        ),
        execution_identity VARCHAR(32) NOT NULL DEFAULT 'passthrough' CHECK (
            execution_identity IN ('passthrough', 'service_principal')
        ),
        upstream_http_status INTEGER NOT NULL DEFAULT 403 CHECK (
            upstream_http_status IN (401, 403)
        ),
        required_role VARCHAR(128) NOT NULL,
        approver_team VARCHAR(128) NOT NULL,
        sla_hours INTEGER NOT NULL CHECK (sla_hours > 0),
        jira_request_url TEXT NOT NULL,
        permission_broker_hint TEXT NOT NULL,
        procedure_markdown TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_permission_broker_tickets_workspace_id "
        "ON permission_broker_tickets(workspace_id);"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_permission_broker_tickets_status "
        "ON permission_broker_tickets(status);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS permission_broker_tickets;",
    "DROP TABLE IF EXISTS permission_broker_policies;",
)


def upgrade() -> None:
    """Create Story 1.4 Permission Broker policies and step denial tickets tables."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 1.4 Permission Broker policies and step denial tickets tables."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
