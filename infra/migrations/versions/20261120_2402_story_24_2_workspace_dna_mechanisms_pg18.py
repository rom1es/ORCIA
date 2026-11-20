"""Story 24.2 — Persist Starlark DNA mechanisms (`workspace_dna_mechanisms`) in PG18.

Revision ID: 20261120_2402
Revises: 20261120_2401
Create Date: 2026-11-20

Pure raw SQL Expand migration (`op.execute(sa.text(...))`), zero ORM imports, UUIDv7 PKs,
and reversible `downgrade()`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261120_2402"
down_revision: str | Sequence[str] | None = "20261120_2401"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `workspace_dna_mechanisms` table and index in PostgreSQL 18."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS workspace_dna_mechanisms (
                id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                rule_id VARCHAR(128) NOT NULL,
                directive_title VARCHAR(255) NOT NULL,
                norm_title VARCHAR(255) NOT NULL,
                script_name VARCHAR(255) NOT NULL,
                starlark_code TEXT NOT NULL,
                sha256 VARCHAR(128) NOT NULL,
                passing_test_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                failing_test_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                explanation_fr TEXT NOT NULL,
                self_corrected BOOLEAN NOT NULL DEFAULT FALSE,
                compile_elapsed_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                verified_badge_fr VARCHAR(255) NOT NULL,
                causal_breadcrumb TEXT NOT NULL,
                signed_and_active BOOLEAN NOT NULL DEFAULT TRUE,
                signed_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                signed_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_workspace_dna_mechanisms_ws_rule UNIQUE (workspace_id, rule_id)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_workspace_dna_mechanisms_ws_updated
                ON workspace_dna_mechanisms (workspace_id, updated_at DESC, id DESC);
            """
        )
    )


def downgrade() -> None:
    """Drop index and `workspace_dna_mechanisms` table introduced in Story 24.2."""
    op.execute(sa.text("DROP INDEX IF EXISTS ix_workspace_dna_mechanisms_ws_updated;"))
    op.execute(sa.text("DROP TABLE IF EXISTS workspace_dna_mechanisms;"))
