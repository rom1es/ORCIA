"""Story 3.1 Workflow-as-Code YAML/JSON, Triggers, Workflow Runs (SUB_WORKFLOW <= 3) & Run Lock.

Revision ID: 0010_story_3_1
Revises: 0009_story_2_4
Create Date: 2026-10-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0010_story_3_1"
down_revision: str | None = "0009_story_2_4"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    ALTER TABLE workflow_definitions
        ADD COLUMN IF NOT EXISTS criticality VARCHAR(32) NOT NULL DEFAULT 'STANDARD'
            CHECK (criticality IN ('LOW_NON_CRITICAL', 'STANDARD', 'HIGH_CRITICAL')),
        ADD COLUMN IF NOT EXISTS execution_regime VARCHAR(32) NOT NULL
            DEFAULT 'INTERACTIVE_COACHING'
            CHECK (execution_regime IN (
                'INTERACTIVE_COACHING', 'BACKGROUND_FAST_PATH', 'AUTONOMOUS_CONTRACT'
            )),
        ADD COLUMN IF NOT EXISTS tie_break_policy VARCHAR(48) NOT NULL
            DEFAULT 'PAUSE_AND_ESCALATE'
            CHECK (tie_break_policy IN (
                'ONTOLOGY_AXIOM_FIRST',
                'DEFER_AND_CONTINUE_WITH_ASSUMPTION',
                'PAUSE_AND_ESCALATE'
            )),
        ADD COLUMN IF NOT EXISTS workflow_mode VARCHAR(32) NOT NULL DEFAULT 'standard'
            CHECK (workflow_mode IN ('standard', 'brownfield_bootstrap'));
    """,
    """
    CREATE TABLE workflow_triggers (
        id UUID PRIMARY KEY,
        trigger_key VARCHAR(128) NOT NULL UNIQUE,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        workflow_def_id UUID NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
        trigger_type VARCHAR(32) NOT NULL CHECK (
            trigger_type IN ('WEBHOOK', 'LOG_SINK_ALERT', 'CRON', 'MANUAL_AUTONOMOUS')
        ),
        cron_expr VARCHAR(128) NULL,
        webhook_secret_vault_ref VARCHAR(255) NULL,
        event_filter_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        cooldown_window_seconds INTEGER NOT NULL DEFAULT 300 CHECK (cooldown_window_seconds >= 0),
        service_principal_id VARCHAR(128) NULL,
        max_runs_per_hour INTEGER NOT NULL DEFAULT 10 CHECK (max_runs_per_hour > 0),
        max_daily_cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 25.000000
            CHECK (max_daily_cost_usd >= 0),
        max_consecutive_failures INTEGER NOT NULL DEFAULT 3 CHECK (max_consecutive_failures > 0),
        post_hoc_sampling_rate NUMERIC(5, 4) NOT NULL DEFAULT 0.1000
            CHECK (post_hoc_sampling_rate >= 0 AND post_hoc_sampling_rate <= 1),
        contract_signature_id UUID NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' CHECK (
            status IN ('ACTIVE', 'PAUSED', 'CIRCUIT_OPEN')
        ),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_workflow_triggers_workspace_status "
        "ON workflow_triggers(workspace_id, status);"
    ),
    """
    CREATE TABLE workflow_runs (
        id UUID PRIMARY KEY,
        run_key VARCHAR(128) NOT NULL UNIQUE,
        workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
        workflow_def_id UUID NOT NULL REFERENCES workflow_definitions(id) ON DELETE RESTRICT,
        parent_run_id UUID NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
        parent_step_execution_id UUID NULL,
        root_run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
        nesting_depth INTEGER NOT NULL DEFAULT 0 CHECK (nesting_depth >= 0 AND nesting_depth <= 3),
        execution_regime VARCHAR(32) NOT NULL DEFAULT 'INTERACTIVE_COACHING' CHECK (
            execution_regime IN (
                'INTERACTIVE_COACHING', 'BACKGROUND_FAST_PATH', 'AUTONOMOUS_CONTRACT'
            )
        ),
        criticality VARCHAR(32) NOT NULL DEFAULT 'STANDARD' CHECK (
            criticality IN ('LOW_NON_CRITICAL', 'STANDARD', 'HIGH_CRITICAL')
        ),
        trigger_id UUID NULL REFERENCES workflow_triggers(id) ON DELETE SET NULL,
        trigger_idempotency_key VARCHAR(255) NULL,
        status VARCHAR(48) NOT NULL DEFAULT 'INITIALIZED' CHECK (
            status IN (
                'INITIALIZED',
                'RUNNING',
                'WAITING_FOR_HUMAN_ARBITRATION',
                'WAITING_FOR_HUMAN_GATE',
                'PAUSED_CIRCUIT_BREAKER',
                'PAUSED_BUDGET_EXCEEDED',
                'COMPLETED',
                'FAILED',
                'ROLLED_BACK'
            )
        ),
        initiated_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        execution_identity_mode VARCHAR(32) NOT NULL DEFAULT 'passthrough' CHECK (
            execution_identity_mode IN ('passthrough', 'service_principal')
        ),
        budget_max_usd NUMERIC(12, 6) NOT NULL DEFAULT 10.000000 CHECK (budget_max_usd >= 0),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_workflow_runs_trigger_idempotency
            UNIQUE (trigger_id, trigger_idempotency_key)
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_workflow_runs_workspace_status "
        "ON workflow_runs(workspace_id, status);"
    ),
    "CREATE INDEX IF NOT EXISTS idx_workflow_runs_root_run_id ON workflow_runs(root_run_id);",
    """
    CREATE TABLE run_lock_manifests (
        run_id UUID PRIMARY KEY REFERENCES workflow_runs(id) ON DELETE CASCADE,
        manifest_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        overrides_sha256 VARCHAR(64) NOT NULL,
        kb_snapshot_hash VARCHAR(64) NOT NULL,
        manifest_sha256 VARCHAR(64) NOT NULL,
        locked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_run_lock_manifests_sha256 "
        "ON run_lock_manifests(manifest_sha256);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS run_lock_manifests;",
    "DROP TABLE IF EXISTS workflow_runs;",
    "DROP TABLE IF EXISTS workflow_triggers;",
    """
    ALTER TABLE workflow_definitions
        DROP COLUMN IF EXISTS workflow_mode,
        DROP COLUMN IF EXISTS tie_break_policy,
        DROP COLUMN IF EXISTS execution_regime,
        DROP COLUMN IF EXISTS criticality;
    """,
)


def upgrade() -> None:
    """Create Story 3.1 workflow_triggers, workflow_runs, and run_lock_manifests tables."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 3.1 workflow_triggers, workflow_runs, and run_lock_manifests tables."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
