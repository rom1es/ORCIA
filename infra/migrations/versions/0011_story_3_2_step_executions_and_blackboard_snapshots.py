"""Story 3.2: step_executions & append-only blackboard_snapshots with PostgreSQL trigger.

Revision ID: 0011_story_3_2
Revises: 0010_story_3_1
Create Date: 2026-10-27 10:15:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
- `blackboard_snapshots` is strictly append-only (`BEFORE UPDATE OR DELETE RAISE EXCEPTION`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_story_3_2"
down_revision: str | None = "0010_story_3_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `step_executions` and append-only `blackboard_snapshots` tables (AD-2, NFR-SEC-3)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS step_executions (
                id UUID PRIMARY KEY,
                step_execution_key VARCHAR(160) NOT NULL UNIQUE,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                step_key VARCHAR(128) NOT NULL,
                step_index INTEGER NOT NULL CHECK (step_index >= 0),
                step_type VARCHAR(32) NOT NULL DEFAULT 'AGENT'
                    CHECK (step_type IN (
                        'AGENT', 'SKILL', 'SUB_WORKFLOW', 'POST_ACTION_VERIFICATION'
                    )),
                execution_mode VARCHAR(32) NOT NULL DEFAULT 'INTERACTIVE_COACHING'
                    CHECK (execution_mode IN (
                        'INTERACTIVE_COACHING', 'BACKGROUND_FAST_PATH', 'AUTONOMOUS_CONTRACT'
                    )),
                status VARCHAR(48) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN (
                        'PENDING',
                        'WAITING_FOR_HUMAN_ANCHOR',
                        'EXECUTING_AGENT',
                        'WAITING_FOR_HUMAN_ARBITRATION',
                        'EVALUATING_GATES',
                        'WAITING_FOR_HUMAN_GATE',
                        'COMMITTED',
                        'CHALLENGED_REWIND',
                        'FAILED'
                    )),
                attempt_count INTEGER NOT NULL DEFAULT 0
                    CHECK (attempt_count >= 0 AND attempt_count <= 10),
                max_agent_retries INTEGER NOT NULL DEFAULT 3
                    CHECK (max_agent_retries >= 1 AND max_agent_retries <= 10),
                draft_artifact_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                draft_cas_key VARCHAR(255) NULL,
                step_memlog_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                hydrated_input_uris_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                child_run_id UUID NULL REFERENCES workflow_runs(id) ON DELETE SET NULL,
                committed_snapshot_id UUID NULL,
                cost_usd NUMERIC(12, 4) NOT NULL DEFAULT 0.0000,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_step_executions_run_step
                ON step_executions (run_id, step_index, status);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS blackboard_snapshots (
                id UUID PRIMARY KEY,
                snapshot_key VARCHAR(160) NOT NULL UNIQUE,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE RESTRICT,
                step_execution_id UUID NOT NULL REFERENCES step_executions(id) ON DELETE RESTRICT,
                parent_snapshot_id UUID NULL REFERENCES blackboard_snapshots(id) ON DELETE RESTRICT,
                step_key VARCHAR(128) NOT NULL,
                branch_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (branch_status IN ('ACTIVE', 'SUPERSEDED')),
                artifact_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                artifact_cas_key VARCHAR(255) NOT NULL,
                artifact_sha256 CHAR(64) NOT NULL,
                memlog_summary_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                superseded_snapshot_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_blackboard_snapshots_run_branch
                ON blackboard_snapshots (run_id, branch_status, step_key);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION prevent_blackboard_snapshot_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION
                    'ERR_BLACKBOARD_APPEND_ONLY_VIOLATION: '
                    'blackboard_snapshots is strictly append-only (% forbidden on snapshot id=%)',
                    TG_OP, OLD.id;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
    )
    op.execute(
        sa.text(
            "DROP TRIGGER IF EXISTS trg_blackboard_snapshots_append_only ON blackboard_snapshots;"
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_blackboard_snapshots_append_only
                BEFORE UPDATE OR DELETE ON blackboard_snapshots
                FOR EACH ROW
                EXECUTE FUNCTION prevent_blackboard_snapshot_mutation();
            """
        )
    )


def downgrade() -> None:
    """Drop `blackboard_snapshots` and `step_executions` tables."""
    op.execute(sa.text("DROP TABLE IF EXISTS blackboard_snapshots;"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_blackboard_snapshot_mutation();"))
    op.execute(sa.text("DROP TABLE IF EXISTS step_executions;"))
