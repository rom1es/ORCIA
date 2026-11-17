"""Story 7.1: Autonomy contracts table, autonomous run statuses & Epic 7 outbox events (`AD-18`).

Revision ID: 20261117_0701
Revises: 20261117_0605
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261117_0701"
down_revision: str | Sequence[str] | None = "20261117_0605"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `autonomy_contracts` and expand `workflow_runs.status` & `domain_events_outbox`."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS autonomy_contracts (
                id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL,
                workflow_id VARCHAR(160) NOT NULL,
                workflow_version VARCHAR(64) NOT NULL,
                workflow_sha256 VARCHAR(80) NOT NULL,
                criticality VARCHAR(32) NOT NULL
                    CHECK (criticality IN ('LOW_NON_CRITICAL', 'STANDARD')),
                service_principal_id UUID NOT NULL
                    REFERENCES iam_accounts(id) ON DELETE RESTRICT,
                allowed_read_sources_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                allowed_write_actions_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                max_cost_per_run_usd NUMERIC(12, 6) NOT NULL
                    CHECK (max_cost_per_run_usd > 0),
                tie_break_policy VARCHAR(64) NOT NULL
                    CHECK (
                        tie_break_policy IN (
                            'ONTOLOGY_AXIOM_FIRST',
                            'DEFER_AND_CONTINUE_WITH_ASSUMPTION',
                            'PAUSE_AND_ESCALATE'
                        )
                    ),
                post_hoc_sampling_rate NUMERIC(5, 4) NOT NULL DEFAULT 0.15
                    CHECK (post_hoc_sampling_rate >= 0.10 AND post_hoc_sampling_rate <= 0.20),
                status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'REVOKED', 'SUPERSEDED')),
                signed_by_user_id UUID NOT NULL,
                signed_by_role VARCHAR(48) NOT NULL
                    CHECK (signed_by_role IN ('TEAM_LEAD', 'BU_LEAD', 'PLATFORM_ADMIN')),
                signature_sha256 VARCHAR(80) NOT NULL,
                signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                revoked_at TIMESTAMPTZ NULL,
                revoked_by_user_id UUID NULL
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_autonomy_contracts_active_wf
                ON autonomy_contracts (workspace_id, workflow_id)
                WHERE status = 'ACTIVE';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_autonomy_contracts_sp
                ON autonomy_contracts (service_principal_id);
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
                    'AutonomousEscalated'
                ));
            """
        )
    )


def downgrade() -> None:
    """Revert Story 7.1 `autonomy_contracts`, `workflow_runs.status`, and outbox event types."""
    op.execute(
        sa.text(
            """
            DELETE FROM domain_events_outbox
            WHERE event_type IN (
                'AutonomousContractSigned',
                'AutonomousContractRevoked',
                'AutonomousEscalated'
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
                    'ConnectorCircuitTripped'
                ));
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE workflow_runs
            SET status = 'FAILED'
            WHERE status IN ('PAUSED_AUTONOMOUS_ESCALATION', 'COMMITTED_AUTONOMOUS');
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
                    'COMPLETED',
                    'FAILED',
                    'ROLLED_BACK'
                )
            );
            """
        )
    )

    op.execute(sa.text("DROP INDEX IF EXISTS idx_autonomy_contracts_sp;"))
    op.execute(sa.text("DROP INDEX IF EXISTS uq_autonomy_contracts_active_wf;"))
    op.execute(sa.text("DROP TABLE IF EXISTS autonomy_contracts;"))
