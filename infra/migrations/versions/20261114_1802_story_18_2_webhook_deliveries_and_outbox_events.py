"""Story 18.2 — Webhook Deliveries & Outbox Freshness Events (`FR-23`, `FR-24`, `AD-12`, `AD-19`).

Revision ID: 20261114_1802
Revises: 20261114_1801
Create Date: 2026-11-14

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261114_1802"
down_revision: str | None = "20261114_1801"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Expand domain_events_outbox_event_type_check with 2 new event types
    op.execute(
        sa.text(
            """
            ALTER TABLE domain_events_outbox
                DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;
            """
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
                    'DatasourceFreshnessEvaluated'
                ));
            """
        )
    )

    # 2. Create datasource_webhook_deliveries table and index
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS datasource_webhook_deliveries (
                id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                datasource_id UUID NOT NULL REFERENCES workspace_datasources(id) ON DELETE CASCADE,
                delivery_key VARCHAR(128) NOT NULL,
                provider_event VARCHAR(64) NOT NULL,
                remote_fingerprint_sha256 VARCHAR(64) NOT NULL,
                reconcile_outcome VARCHAR(32) NOT NULL,
                received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_datasource_webhook_deliveries_ds_key
                    UNIQUE (datasource_id, delivery_key)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_ds_received
                ON datasource_webhook_deliveries (datasource_id, received_at DESC);
            """
        )
    )


def downgrade() -> None:
    # 1. Drop datasource_webhook_deliveries table
    op.execute(
        sa.text(
            """
            DROP TABLE IF EXISTS datasource_webhook_deliveries CASCADE;
            """
        )
    )

    # 2. Revert domain_events_outbox constraint to 0024 state (9 event types)
    op.execute(
        sa.text(
            """
            DELETE FROM domain_events_outbox
            WHERE event_type IN (
                'DatasourceSyncRequested',
                'DatasourceFreshnessEvaluated'
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE domain_events_outbox
                DROP CONSTRAINT IF EXISTS domain_events_outbox_event_type_check;
            """
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
                    'SettingsChanged'
                ));
            """
        )
    )
