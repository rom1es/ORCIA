"""Story 24.1 — Persist Jira staged actions (`jira_staged_actions`) & MCP proposals in PG18.

Revision ID: 20261120_2401
Revises: 20261117_2003
Create Date: 2026-11-20

Pure raw SQL Expand migration (`op.execute(sa.text(...))`), zero ORM imports, UUIDv7 PKs,
and reversible `downgrade()`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_2401"
down_revision: str | Sequence[str] | None = "20261117_2003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `jira_staged_actions`, `mcp_governed_proposals` and index `vsm_definitions_v2`."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS jira_staged_actions (
                id UUID PRIMARY KEY,
                workspace_id VARCHAR(128) NOT NULL,
                run_id VARCHAR(128) NOT NULL,
                step_execution_id VARCHAR(128) NOT NULL,
                project_alias VARCHAR(128) NOT NULL,
                project_key VARCHAR(64) NOT NULL,
                action_type VARCHAR(32) NOT NULL
                    CHECK (
                        action_type IN (
                            'create_issue',
                            'update_issue',
                            'add_comment',
                            'transition_issue'
                        )
                    ),
                issue_key VARCHAR(64) NULL,
                summary VARCHAR(512) NOT NULL,
                target_transition VARCHAR(128) NULL,
                payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                status VARCHAR(32) NOT NULL DEFAULT 'STAGED'
                    CHECK (status IN ('STAGED', 'EXECUTED')),
                idempotency_key VARCHAR(512) NOT NULL UNIQUE,
                provenance_run_lock_uri VARCHAR(256) NULL,
                provenance_run_lock_sha256 VARCHAR(128) NULL,
                external_key VARCHAR(64) NULL,
                replayed_from_cache BOOLEAN NOT NULL DEFAULT FALSE,
                staged_by VARCHAR(128) NULL,
                approved_by VARCHAR(128) NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_jira_staged_actions_ws_created
                ON jira_staged_actions (workspace_id, created_at ASC, id ASC);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_jira_staged_actions_run_step
                ON jira_staged_actions (run_id, step_execution_id, created_at ASC);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_jira_staged_actions_status
                ON jira_staged_actions (status);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS mcp_governed_proposals (
                id UUID PRIMARY KEY,
                workspace_id VARCHAR(128) NOT NULL,
                run_id VARCHAR(128) NOT NULL DEFAULT 'run-default',
                section_key VARCHAR(128) NOT NULL,
                content_markdown TEXT NOT NULL,
                ide_client VARCHAR(64) NOT NULL DEFAULT 'vscode',
                execution_identity VARCHAR(32) NOT NULL DEFAULT 'passthrough',
                status VARCHAR(32) NOT NULL DEFAULT 'PROPOSED'
                    CHECK (status IN ('PROPOSED', 'ACCEPTED', 'REJECTED')),
                proposed_by VARCHAR(128) NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_mcp_governed_proposals_ws_run
                ON mcp_governed_proposals (workspace_id, run_id, created_at DESC, id DESC);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_vsm_definitions_v2_pack_id
                ON vsm_definitions_v2 (pack_id, updated_at ASC);
            """
        )
    )


def downgrade() -> None:
    """Drop indexes and tables introduced in Story 24.1."""
    op.execute(sa.text("DROP INDEX IF EXISTS ix_vsm_definitions_v2_pack_id;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_mcp_governed_proposals_ws_run;"))
    op.execute(sa.text("DROP TABLE IF EXISTS mcp_governed_proposals;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_jira_staged_actions_status;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_jira_staged_actions_run_step;"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_jira_staged_actions_ws_created;"))
    op.execute(sa.text("DROP TABLE IF EXISTS jira_staged_actions;"))
