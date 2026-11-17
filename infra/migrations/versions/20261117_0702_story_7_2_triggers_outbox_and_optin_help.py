"""Story 7.2: Idempotent event triggers, deliveries & opt-in help (`AD-18`, `AD-23`).

Revision ID: 20261117_0702
Revises: 20261117_0701
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261117_0702"
down_revision: str | Sequence[str] | None = "20261117_0701"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Expand `workflow_triggers`, create `trigger_webhook_deliveries` & outbox types."""
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
                    WHERE conrelid = 'workflow_triggers'::regclass
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%trigger_type%IN%'
                ) LOOP
                    EXECUTE 'ALTER TABLE workflow_triggers DROP CONSTRAINT IF EXISTS '
                        || quote_ident(r.conname);
                END LOOP;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_triggers
                ADD CONSTRAINT ck_workflow_triggers_type
                CHECK (trigger_type IN (
                    'WEBHOOK',
                    'LOG_SINK_ALERT',
                    'CRON',
                    'OUTBOX_EVENT',
                    'MANUAL_AUTONOMOUS'
                ));
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_triggers
                ADD COLUMN IF NOT EXISTS workflow_id VARCHAR(160) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS contract_id UUID NULL
                    REFERENCES autonomy_contracts(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS auto_help_on_publish BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS consecutive_failures INTEGER NOT NULL DEFAULT 0
                    CHECK (consecutive_failures >= 0),
                ADD COLUMN IF NOT EXISTS last_fired_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ADD COLUMN IF NOT EXISTS webhook_secret_encrypted TEXT NULL,
                ADD COLUMN IF NOT EXISTS webhook_secret_fingerprint VARCHAR(80) NULL,
                ADD COLUMN IF NOT EXISTS webhook_secret_masked_hint VARCHAR(64) NULL,
                ADD COLUMN IF NOT EXISTS webhook_secret_updated_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS webhook_secret_updated_by VARCHAR(160) NULL,
                ADD COLUMN IF NOT EXISTS log_sink_service VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS log_sink_query_text VARCHAR(255) NULL,
                ADD COLUMN IF NOT EXISTS outbox_event_filter VARCHAR(128) NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE workflow_triggers wt
            SET workflow_id = COALESCE(wd.uri, wt.workflow_def_id::text)
            FROM workflow_definitions wd
            WHERE wt.workflow_def_id = wd.id
              AND (wt.workflow_id IS NULL OR wt.workflow_id = '');
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_workflow_triggers_workspace_wf
                ON workflow_triggers (workspace_id, workflow_id, status);
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS trigger_webhook_deliveries (
                id UUID PRIMARY KEY,
                trigger_id UUID NOT NULL REFERENCES workflow_triggers(id) ON DELETE CASCADE,
                delivery_key VARCHAR(255) NOT NULL,
                received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_trigger_webhook_delivery UNIQUE (trigger_id, delivery_key)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_trigger_webhook_deliveries_trigger
                ON trigger_webhook_deliveries (trigger_id, received_at DESC);
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


def downgrade() -> None:
    """Revert Story 7.2 schema additions cleanly."""
    op.execute(
        sa.text(
            """
            DELETE FROM domain_events_outbox
            WHERE event_type IN (
                'TriggerFired',
                'SelfTriggerBlocked',
                'TriggerCircuitOpened',
                'WorkflowPublished'
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

    op.execute(sa.text("DROP INDEX IF EXISTS idx_trigger_webhook_deliveries_trigger;"))
    op.execute(sa.text("DROP TABLE IF EXISTS trigger_webhook_deliveries;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_workflow_triggers_workspace_wf;"))

    op.execute(sa.text("DELETE FROM workflow_triggers WHERE trigger_type = 'OUTBOX_EVENT';"))
    op.execute(
        sa.text(
            "ALTER TABLE workflow_triggers DROP CONSTRAINT IF EXISTS ck_workflow_triggers_type;"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_triggers
                ADD CONSTRAINT ck_workflow_triggers_type
                CHECK (trigger_type IN (
                    'WEBHOOK',
                    'LOG_SINK_ALERT',
                    'CRON',
                    'MANUAL_AUTONOMOUS'
                ));
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_triggers
                DROP COLUMN IF EXISTS outbox_event_filter,
                DROP COLUMN IF EXISTS log_sink_query_text,
                DROP COLUMN IF EXISTS log_sink_service,
                DROP COLUMN IF EXISTS webhook_secret_updated_by,
                DROP COLUMN IF EXISTS webhook_secret_updated_at,
                DROP COLUMN IF EXISTS webhook_secret_masked_hint,
                DROP COLUMN IF EXISTS webhook_secret_fingerprint,
                DROP COLUMN IF EXISTS webhook_secret_encrypted,
                DROP COLUMN IF EXISTS updated_at,
                DROP COLUMN IF EXISTS last_fired_at,
                DROP COLUMN IF EXISTS consecutive_failures,
                DROP COLUMN IF EXISTS auto_help_on_publish,
                DROP COLUMN IF EXISTS contract_id,
                DROP COLUMN IF EXISTS workflow_id;
            """
        )
    )
