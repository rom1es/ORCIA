"""Story 19.7 — RAG reindexing jobs, lock, and pending ingestions queue (`AD-24.7`, `D9`, `D12`).

Revision ID: 20261115_2307
Revises: 20261115_2206
Create Date: 2026-11-15

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261115_2307"
down_revision: str | None = "20261115_2206"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create rag_reindexing_jobs table
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS rag_reindexing_jobs (
                id UUID PRIMARY KEY,
                target_model_id UUID NOT NULL
                    REFERENCES workspace_llm_tier_mappings(id) ON DELETE CASCADE,
                target_model_name VARCHAR(128) NOT NULL,
                status VARCHAR(32) NOT NULL CHECK (
                    status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED')
                ),
                total_chunks INTEGER NOT NULL DEFAULT 0,
                processed_chunks INTEGER NOT NULL DEFAULT 0,
                progress_percentage INTEGER NOT NULL DEFAULT 0,
                error_message TEXT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                started_at TIMESTAMPTZ NULL,
                completed_at TIMESTAMPTZ NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                created_by VARCHAR(128) NOT NULL DEFAULT 'system',
                cancelled_by_job_id UUID NULL REFERENCES rag_reindexing_jobs(id) ON DELETE SET NULL
            );
            """
        )
    )

    # 2. Unique partial index guaranteeing at most 1 active job ('PENDING' or 'IN_PROGRESS')
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_rag_reindex_single_active
                ON rag_reindexing_jobs ((true))
                WHERE status IN ('PENDING', 'IN_PROGRESS');
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_rag_reindexing_jobs_created_at
                ON rag_reindexing_jobs (created_at DESC);
            """
        )
    )

    # 3. Create rag_reindexing_pending_ingestions table for concurrent sync during reindex
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS rag_reindexing_pending_ingestions (
                id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                datasource_id UUID NOT NULL REFERENCES workspace_datasources(id) ON DELETE CASCADE,
                job_id UUID NULL REFERENCES rag_reindexing_jobs(id) ON DELETE SET NULL,
                payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                status VARCHAR(32) NOT NULL CHECK (
                    status IN ('PENDING', 'PROCESSED', 'FAILED')
                ) DEFAULT 'PENDING',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                processed_at TIMESTAMPTZ NULL
            );
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_rag_reindex_pending_ingestions_status
                ON rag_reindexing_pending_ingestions (status, created_at);
            """
        )
    )

    # 4. Expand domain_events_outbox_event_type_check with embedding reindex events
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
                    'DatasourceFreshnessEvaluated',
                    'EmbeddingReindexStarted',
                    'EmbeddingReindexCompleted',
                    'EmbeddingReindexFailed'
                ));
            """
        )
    )


def downgrade() -> None:
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
    op.execute(sa.text("DROP TABLE IF EXISTS rag_reindexing_pending_ingestions;"))
    op.execute(sa.text("DROP TABLE IF EXISTS rag_reindexing_jobs;"))
