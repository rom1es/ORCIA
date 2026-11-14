"""Story 18.1 — Workspace Sources Multi-Nature & Codegraph (`FR-23`, `FR-34`, `AD-19`, `AD-21`).

Revision ID: 20261114_1801
Revises: 20261114_1705
Create Date: 2026-11-14

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261114_1801"
down_revision: str | None = "20261114_1705"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. enterprise_connectors webhook secrets
    op.execute(
        sa.text(
            """
            ALTER TABLE enterprise_connectors
                ADD COLUMN IF NOT EXISTS webhook_secret_encrypted TEXT NULL,
                ADD COLUMN IF NOT EXISTS webhook_secret_fingerprint VARCHAR(32) NULL;
            """
        )
    )

    # 2. workspace_datasources multi-nature, freshness and codegraph governance
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                ADD COLUMN IF NOT EXISTS source_nature VARCHAR(32) NOT NULL DEFAULT 'DOCUMENT_KB'
                    CHECK (source_nature IN (
                        'DOCUMENT_KB', 'WORK_TRACKER', 'SOURCE_CODE', 'RELATIONAL_SCHEMA'
                    )),
                ADD COLUMN IF NOT EXISTS sync_mode VARCHAR(32) NOT NULL DEFAULT 'POLLING_24H'
                    CHECK (sync_mode IN ('WEBHOOK_PUSH', 'POLLING_24H')),
                ADD COLUMN IF NOT EXISTS target_scope VARCHAR(255) NULL,
                ADD COLUMN IF NOT EXISTS target_ref VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS last_probe_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS fingerprint_hash VARCHAR(64) NULL,
                ADD COLUMN IF NOT EXISTS freshness_status VARCHAR(32)
                    NOT NULL DEFAULT 'PENDING_INITIAL_SYNC'
                    CHECK (freshness_status IN (
                        'SYNCED', 'STALE', 'SYNC_ERROR', 'PENDING_INITIAL_SYNC'
                    )),
                ADD COLUMN IF NOT EXISTS codegraph_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS codegraph_auth_mode VARCHAR(32)
                    NOT NULL DEFAULT 'SERVICE_ACCOUNT'
                    CHECK (codegraph_auth_mode IN ('SERVICE_ACCOUNT', 'WORKSPACE_LEAD_TOKEN')),
                ADD COLUMN IF NOT EXISTS codegraph_owner_user_id VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS codegraph_status VARCHAR(40) NOT NULL DEFAULT 'DISABLED'
                    CHECK (codegraph_status IN (
                        'DISABLED', 'INDEXING', 'READY',
                        'PAUSED_REFERENT_RENEWAL_REQUIRED', 'ERROR'
                    )),
                ADD COLUMN IF NOT EXISTS codegraph_last_indexed_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS codegraph_head_sha VARCHAR(64) NULL;
            """
        )
    )

    # 3. Deterministic backfill based on scheme
    op.execute(
        sa.text(
            """
            UPDATE workspace_datasources
            SET source_nature = CASE
                WHEN LOWER(scheme) IN ('confluence', 'docs', 'nexus') THEN 'DOCUMENT_KB'
                WHEN LOWER(scheme) IN ('jira', 'tracker', 'linear') THEN 'WORK_TRACKER'
                WHEN LOWER(scheme) IN ('git', 'gitlab', 'github') THEN 'SOURCE_CODE'
                WHEN LOWER(scheme) IN ('sql', 'postgres', 'db') THEN 'RELATIONAL_SCHEMA'
                ELSE 'DOCUMENT_KB'
            END;
            """
        )
    )

    # 4. Indexes
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_workspace_datasources_ws_nature
                ON workspace_datasources (workspace_id, source_nature);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_workspace_datasources_freshness
                ON workspace_datasources (freshness_status, last_probe_at);
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_workspace_datasources_freshness;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_workspace_datasources_ws_nature;"))
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                DROP COLUMN IF EXISTS codegraph_head_sha,
                DROP COLUMN IF EXISTS codegraph_last_indexed_at,
                DROP COLUMN IF EXISTS codegraph_status,
                DROP COLUMN IF EXISTS codegraph_owner_user_id,
                DROP COLUMN IF EXISTS codegraph_auth_mode,
                DROP COLUMN IF EXISTS codegraph_enabled,
                DROP COLUMN IF EXISTS freshness_status,
                DROP COLUMN IF EXISTS fingerprint_hash,
                DROP COLUMN IF EXISTS last_probe_at,
                DROP COLUMN IF EXISTS last_sync_at,
                DROP COLUMN IF EXISTS target_ref,
                DROP COLUMN IF EXISTS target_scope,
                DROP COLUMN IF EXISTS sync_mode,
                DROP COLUMN IF EXISTS source_nature;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE enterprise_connectors
                DROP COLUMN IF EXISTS webhook_secret_fingerprint,
                DROP COLUMN IF EXISTS webhook_secret_encrypted;
            """
        )
    )
