"""Story 11.1: Create `workspace_exception_waivers` & expand `chunk_approvals` status.

Revision ID: 0026_story_11_1
Revises: 0025_story_10_4
Create Date: 2026-10-31 18:10:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_story_11_1"
down_revision: str | None = "0025_story_10_4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `workspace_exception_waivers` & expand `chunk_approvals` (`Story 11.1`)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS workspace_exception_waivers (
                waiver_id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                source_uri VARCHAR(512) NOT NULL,
                source_sha256 VARCHAR(64) NOT NULL,
                conflict_rule_id VARCHAR(128) NOT NULL,
                norm_level VARCHAR(32) NOT NULL DEFAULT '3_WORKSPACE'
                    CONSTRAINT workspace_exception_waivers_norm_level_check
                    CHECK (norm_level IN ('1_ENTERPRISE', '2_DOMAIN', '3_TEAM', '3_WORKSPACE')),
                dna_chain_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                approved_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                approved_by_role VARCHAR(64) NOT NULL,
                reason TEXT NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
                    CONSTRAINT workspace_exception_waivers_status_check
                    CHECK (status IN ('ACTIVE', 'INVALIDATED_SHA_DRIFT', 'EXPIRED', 'REVOKED')),
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_workspace_exception_waiver_rule_sha
                    UNIQUE (workspace_id, source_uri, source_sha256, conflict_rule_id)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_workspace_exception_waivers_lookup
                ON workspace_exception_waivers (workspace_id, source_uri, conflict_rule_id, status)
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE chunk_approvals
                DROP CONSTRAINT IF EXISTS chunk_approvals_status_check
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE chunk_approvals
                ADD CONSTRAINT chunk_approvals_status_check
                CHECK (
                    status IN (
                        'PENDING',
                        'APPROVED',
                        'CO_EDITED',
                        'CHALLENGED',
                        'HUMAN_AMENDED_EXTERNAL'
                    )
                )
            """
        )
    )


def downgrade() -> None:
    """Restore `chunk_approvals` status check and drop `workspace_exception_waivers`."""
    op.execute(
        sa.text(
            """
            UPDATE chunk_approvals
            SET status = 'CO_EDITED'
            WHERE status = 'HUMAN_AMENDED_EXTERNAL'
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE chunk_approvals
                DROP CONSTRAINT IF EXISTS chunk_approvals_status_check
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE chunk_approvals
                ADD CONSTRAINT chunk_approvals_status_check
                CHECK (status IN ('PENDING', 'APPROVED', 'CO_EDITED', 'CHALLENGED'))
            """
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS workspace_exception_waivers"))
