"""Story 5.1: task_notifications, step_executions claim & resource_leases (`AD-4`, `DEC-CONC-01`).

Revision ID: 0021_story_5_1
Revises: 0020_story_4_4_contract
Create Date: 2026-10-30 13:25:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_story_5_1"
down_revision: str | None = "0020_story_4_4_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `task_notifications`, `resource_leases` and add claim columns to `step_executions`."""
    op.execute(
        sa.text(
            """
            ALTER TABLE step_executions
                ADD COLUMN IF NOT EXISTS claimed_by_user_id UUID NULL,
                ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ NULL;
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS task_notifications (
                id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                target_team_id UUID NULL REFERENCES org_units(id) ON DELETE SET NULL,
                target_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                step_execution_id UUID NOT NULL REFERENCES step_executions(id) ON DELETE CASCADE,
                step_key VARCHAR(128) NOT NULL,
                notification_type VARCHAR(64) NOT NULL
                    CHECK (notification_type IN (
                        'HUMAN_GATE',
                        'HUMAN_ARBITRATION',
                        'HUMAN_ANCHOR',
                        'UPSTREAM_CHALLENGE',
                        'PERMISSION_ALERT',
                        'STALE_WARNING',
                        'AUTONOMOUS_ESCALATION',
                        'POST_HOC_AUDIT_SAMPLE'
                    )),
                scope_kind VARCHAR(32) NOT NULL DEFAULT 'TEAM'
                    CHECK (scope_kind IN ('PERSONAL', 'TEAM')),
                title VARCHAR(255) NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                status VARCHAR(32) NOT NULL DEFAULT 'OPEN'
                    CHECK (status IN ('OPEN', 'CLAIMED', 'RESOLVED')),
                claimed_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                claimed_by_display_name VARCHAR(160) NULL,
                claimed_at TIMESTAMPTZ NULL,
                lock_expires_at TIMESTAMPTZ NULL,
                source_event_id UUID NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_task_notifications_ws_status
                ON task_notifications (workspace_id, status, scope_kind, created_at DESC);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_task_notifications_step_exec
                ON task_notifications (step_execution_id);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS resource_leases (
                id UUID PRIMARY KEY,
                resource_uri VARCHAR(512) NOT NULL UNIQUE,
                resource_class VARCHAR(64) NOT NULL DEFAULT 'DEFAULT',
                holder_run_id UUID NOT NULL,
                holder_root_run_id UUID NOT NULL,
                holder_parent_run_id UUID NULL,
                holder_step_execution_id UUID NOT NULL,
                fencing_token BIGINT NOT NULL CHECK (fencing_token > 0),
                acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_resource_leases_holder_run
                ON resource_leases (holder_run_id, holder_root_run_id);
            """
        )
    )


def downgrade() -> None:
    """Drop `resource_leases`, `task_notifications` and claim columns on `step_executions`."""
    op.execute(sa.text("DROP INDEX IF EXISTS idx_resource_leases_holder_run;"))
    op.execute(sa.text("DROP TABLE IF EXISTS resource_leases;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_task_notifications_step_exec;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_task_notifications_ws_status;"))
    op.execute(sa.text("DROP TABLE IF EXISTS task_notifications;"))
    op.execute(
        sa.text(
            """
            ALTER TABLE step_executions
                DROP COLUMN IF EXISTS claimed_at,
                DROP COLUMN IF EXISTS claimed_by_user_id;
            """
        )
    )
