"""Story 6.1: Immutable append-only audit ledger and hot test-bench provenance.

Revision ID: 20261116_0601
Revises: 20261115_2359
Create Date: 2026-11-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261116_0601"
down_revision: str | Sequence[str] | None = "20261115_2359"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create audit_ledger table
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS audit_ledger (
                id UUID PRIMARY KEY,
                source_event_id UUID UNIQUE NOT NULL,
                workspace_id UUID NULL,
                org_unit_id UUID NULL,
                scope_path VARCHAR(256) NOT NULL DEFAULT 'GLOBAL',
                run_id UUID NULL,
                root_run_id UUID NULL,
                step_execution_id UUID NULL,
                actor_type VARCHAR(64) NOT NULL,
                actor_id VARCHAR(128) NOT NULL,
                actor_display_name VARCHAR(256) NULL,
                actor_email VARCHAR(256) NULL,
                event_type VARCHAR(64) NOT NULL,
                summary TEXT NOT NULL,
                model_id VARCHAR(128) NULL,
                inference_tier VARCHAR(32) NULL,
                effort VARCHAR(32) NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
                cost_source VARCHAR(32) NOT NULL DEFAULT 'INTERNAL_VERIFIED',
                native_metric_type VARCHAR(64) NULL,
                native_metric_value NUMERIC(16, 6) NULL,
                native_currency VARCHAR(8) NULL,
                reported_by_remote BOOLEAN NOT NULL DEFAULT FALSE,
                latency_ms INTEGER NOT NULL DEFAULT 0,
                trace_id VARCHAR(64) NOT NULL,
                run_lock_sha256 VARCHAR(64) NULL,
                pre_prompt_sha256 VARCHAR(64) NULL,
                workflow_contract_sha256 VARCHAR(64) NULL,
                cas_references_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )

    # 2. Indexes for audit_ledger (each executed individually for asyncpg compatibility)
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_ledger_run_id
                ON audit_ledger (run_id) WHERE run_id IS NOT NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_ledger_root_run_id
                ON audit_ledger (root_run_id) WHERE root_run_id IS NOT NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_ledger_workspace_id
                ON audit_ledger (workspace_id) WHERE workspace_id IS NOT NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_ledger_actor
                ON audit_ledger (actor_type, actor_id);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_ledger_created_at
                ON audit_ledger (created_at DESC);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_ledger_trace_id
                ON audit_ledger (trace_id);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_ledger_scope_path
                ON audit_ledger (scope_path);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_ledger_event_type
                ON audit_ledger (event_type);
            """
        )
    )

    # 3. Immutability trigger: prevent any UPDATE or DELETE on audit_ledger
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION prevent_audit_ledger_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'ERR_AUDIT_LEDGER_IMMUTABLE: audit_ledger is strictly append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
    )
    op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_audit_ledger_mutation ON audit_ledger;"))
    op.execute(
        sa.text(
            """
            CREATE TRIGGER prevent_audit_ledger_mutation
                BEFORE UPDATE OR DELETE ON audit_ledger
                FOR EACH ROW
                EXECUTE FUNCTION prevent_audit_ledger_mutation();
            """
        )
    )

    # 4. Expand domain_events_outbox_event_type_check with 5 new event types
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


def downgrade() -> None:
    # 1. Drop trigger and function
    op.execute(sa.text("DROP TRIGGER IF EXISTS prevent_audit_ledger_mutation ON audit_ledger;"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS prevent_audit_ledger_mutation();"))

    # 2. Drop table
    op.execute(sa.text("DROP TABLE IF EXISTS audit_ledger;"))

    # 3. Restore previous 14-event CHECK constraint on domain_events_outbox
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
                    'EmbeddingReindexFailed'
                ));
            """
        )
    )
