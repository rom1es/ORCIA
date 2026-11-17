"""Story 7.4: Autonomous post-hoc audits, `KILL_SWITCH_STOPPED` & Outbox event types (`AD-18`).

Revision ID: 20261117_0704
Revises: 20261117_0702
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261117_0704"
down_revision: str | Sequence[str] | None = "20261117_0702"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `autonomous_post_hoc_audits` & expand `workflow_runs.status` and outbox types."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS autonomous_post_hoc_audits (
                id UUID PRIMARY KEY,
                run_id UUID NOT NULL UNIQUE REFERENCES workflow_runs(id) ON DELETE CASCADE,
                workspace_id UUID NOT NULL,
                contract_id UUID NOT NULL REFERENCES autonomy_contracts(id) ON DELETE CASCADE,
                review_status VARCHAR(48) NOT NULL DEFAULT 'PENDING_SAMPLE'
                    CHECK (
                        review_status IN (
                            'PENDING_SAMPLE',
                            'VALIDATED',
                            'INVALIDATED_ROLLED_BACK'
                        )
                    ),
                reviewer_user_id UUID NULL,
                review_comment TEXT NULL,
                sampled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                reviewed_at TIMESTAMPTZ NULL
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_post_hoc_audits_ws_status
                ON autonomous_post_hoc_audits (workspace_id, review_status);
            """
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'workflow_runs'::regclass
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%status%IN%'
                ) LOOP
                    EXECUTE 'ALTER TABLE workflow_runs DROP CONSTRAINT IF EXISTS '
                        || quote_ident(r.conname);
                END LOOP;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_runs ADD CONSTRAINT ck_workflow_runs_status CHECK (
                status IN (
                    'INITIALIZED',
                    'RUNNING',
                    'WAITING_FOR_HUMAN_ARBITRATION',
                    'WAITING_FOR_HUMAN_GATE',
                    'PAUSED_CIRCUIT_BREAKER',
                    'PAUSED_BUDGET_EXCEEDED',
                    'PAUSED_MAX_RETRIES',
                    'PAUSED_AUTONOMOUS_ESCALATION',
                    'COMMITTED_AUTONOMOUS',
                    'KILL_SWITCH_STOPPED',
                    'COMPLETED',
                    'FAILED',
                    'ROLLED_BACK'
                )
            );
            """
        )
    )

    op.execute(
        sa.text(
            "ALTER TABLE domain_events_outbox "
            "DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE domain_events_outbox
                ADD CONSTRAINT domain_events_outbox_event_type_check
                CHECK (event_type IN (
                    'StepCompleted',
                    'ArtifactProduced',
                    'GateEvaluated',
                    'RunTerminated',
                    'HumanArbitrationRequested',
                    'PermissionGranted',
                    'PermissionRevoked',
                    'AccessRequested',
                    'SettingsChanged',
                    'DatasourceSyncRequested',
                    'DatasourceFreshnessEvaluated',
                    'EmbeddingReindexStarted',
                    'EmbeddingReindexCompleted',
                    'EmbeddingReindexFailed',
                    'AdminConnectionTested',
                    'BudgetCircuitTripped',
                    'BudgetOverrideApproved',
                    'RemoteUsageAnomalyCapped',
                    'ConnectorCircuitTripped',
                    'AutonomousContractSigned',
                    'AutonomousContractRevoked',
                    'AutonomousEscalated',
                    'TriggerFired',
                    'SelfTriggerBlocked',
                    'TriggerCircuitOpened',
                    'WorkflowPublished',
                    'PostHocSampleSelected',
                    'KillSwitchActivated',
                    'AutonomousArtifactRolledBack'
                ));
            """
        )
    )


def downgrade() -> None:
    """Revert Story 7.4 schema additions cleanly."""
    op.execute(
        sa.text(
            """
            DELETE FROM domain_events_outbox
            WHERE event_type IN (
                'PostHocSampleSelected',
                'KillSwitchActivated',
                'AutonomousArtifactRolledBack'
            );
            """
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE domain_events_outbox "
            "DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE domain_events_outbox
                ADD CONSTRAINT domain_events_outbox_event_type_check
                CHECK (event_type IN (
                    'StepCompleted',
                    'ArtifactProduced',
                    'GateEvaluated',
                    'RunTerminated',
                    'HumanArbitrationRequested',
                    'PermissionGranted',
                    'PermissionRevoked',
                    'AccessRequested',
                    'SettingsChanged',
                    'DatasourceSyncRequested',
                    'DatasourceFreshnessEvaluated',
                    'EmbeddingReindexStarted',
                    'EmbeddingReindexCompleted',
                    'EmbeddingReindexFailed',
                    'AdminConnectionTested',
                    'BudgetCircuitTripped',
                    'BudgetOverrideApproved',
                    'RemoteUsageAnomalyCapped',
                    'ConnectorCircuitTripped',
                    'AutonomousContractSigned',
                    'AutonomousContractRevoked',
                    'AutonomousEscalated',
                    'TriggerFired',
                    'SelfTriggerBlocked',
                    'TriggerCircuitOpened',
                    'WorkflowPublished'
                ));
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE workflow_runs
            SET status = 'FAILED'
            WHERE status = 'KILL_SWITCH_STOPPED';
            """
        )
    )
    op.execute(
        sa.text("ALTER TABLE workflow_runs DROP CONSTRAINT IF EXISTS ck_workflow_runs_status;")
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_runs ADD CONSTRAINT ck_workflow_runs_status CHECK (
                status IN (
                    'INITIALIZED',
                    'RUNNING',
                    'WAITING_FOR_HUMAN_ARBITRATION',
                    'WAITING_FOR_HUMAN_GATE',
                    'PAUSED_CIRCUIT_BREAKER',
                    'PAUSED_BUDGET_EXCEEDED',
                    'PAUSED_MAX_RETRIES',
                    'PAUSED_AUTONOMOUS_ESCALATION',
                    'COMMITTED_AUTONOMOUS',
                    'COMPLETED',
                    'FAILED',
                    'ROLLED_BACK'
                )
            );
            """
        )
    )

    op.execute(sa.text("DROP INDEX IF EXISTS idx_post_hoc_audits_ws_status;"))
    op.execute(sa.text("DROP TABLE IF EXISTS autonomous_post_hoc_audits;"))
