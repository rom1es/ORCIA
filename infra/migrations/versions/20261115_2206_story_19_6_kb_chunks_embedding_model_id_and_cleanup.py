"""Story 19.6 — kb_chunks embedding model metadata, SHA-256 cleanup (`AD-24.7`, `D8`).

Revision ID: 20261115_2206
Revises: 20261115_2105
Create Date: 2026-11-15

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261115_2206"
down_revision: str | None = "20261115_2105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add embedding_model_id and embedding_generated_at on kb_chunks
    op.execute(
        sa.text(
            """
            ALTER TABLE kb_chunks
                ADD COLUMN IF NOT EXISTS embedding_model_id UUID NULL
                    REFERENCES workspace_llm_tier_mappings(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMPTZ NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_kb_chunks_embedding_model_id
                ON kb_chunks (embedding_model_id);
            """
        )
    )

    # 2. Reset existing SHA-256 pseudo-hash vectors to NULL in production storage
    op.execute(
        sa.text(
            """
            UPDATE kb_chunks
            SET embedding = NULL,
                embedding_model_id = NULL,
                embedding_generated_at = NULL;
            """
        )
    )

    # 3. Allow AWAITING_EMBEDDING_MODEL status on workspace_datasources
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE workspace_datasources
                    DROP CONSTRAINT IF EXISTS workspace_datasources_freshness_status_check;
                ALTER TABLE workspace_datasources
                    ADD CONSTRAINT workspace_datasources_freshness_status_check
                    CHECK (freshness_status IN (
                        'SYNCED', 'STALE', 'SYNC_ERROR', 'PENDING_INITIAL_SYNC',
                        'AWAITING_EMBEDDING_MODEL'
                    ));
            END $$;
            """
        )
    )

    # 4. Set document/work-tracker datasources to AWAITING_EMBEDDING_MODEL
    # (SOURCE_CODE / GitNexus remains unaffected)
    op.execute(
        sa.text(
            """
            UPDATE workspace_datasources
            SET freshness_status = 'AWAITING_EMBEDDING_MODEL'
            WHERE source_nature != 'SOURCE_CODE';
            """
        )
    )


def downgrade() -> None:
    # 1. Reset AWAITING_EMBEDDING_MODEL to PENDING_INITIAL_SYNC before restoring constraint
    op.execute(
        sa.text(
            """
            UPDATE workspace_datasources
            SET freshness_status = 'PENDING_INITIAL_SYNC'
            WHERE freshness_status = 'AWAITING_EMBEDDING_MODEL';
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                ALTER TABLE workspace_datasources
                    DROP CONSTRAINT IF EXISTS workspace_datasources_freshness_status_check;
                ALTER TABLE workspace_datasources
                    ADD CONSTRAINT workspace_datasources_freshness_status_check
                    CHECK (freshness_status IN (
                        'SYNCED', 'STALE', 'SYNC_ERROR', 'PENDING_INITIAL_SYNC'
                    ));
            END $$;
            """
        )
    )

    # 2. Drop index and columns on kb_chunks
    op.execute(sa.text("DROP INDEX IF EXISTS idx_kb_chunks_embedding_model_id;"))
    op.execute(
        sa.text(
            """
            ALTER TABLE kb_chunks
                DROP COLUMN IF EXISTS embedding_generated_at,
                DROP COLUMN IF EXISTS embedding_model_id;
            """
        )
    )
