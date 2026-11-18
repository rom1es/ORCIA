"""Story 20.3 — Persist user preferences & personal IDE/MCP tokens in PostgreSQL 18.

Revision ID: 20261117_2003
Revises: 20261117_2002
Create Date: 2026-11-18

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261117_2003"
down_revision: str | Sequence[str] | None = "20261117_2002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `user_preferences` and `user_mcp_tokens` tables in PostgreSQL 18."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id VARCHAR(128) PRIMARY KEY,
                theme VARCHAR(16) NOT NULL DEFAULT 'light'
                    CHECK (theme IN ('light', 'dark', 'system')),
                locale VARCHAR(8) NOT NULL DEFAULT 'fr'
                    CHECK (locale IN ('fr', 'en')),
                default_assistant_hat VARCHAR(64) NOT NULL DEFAULT 'ANALYST_PM_PO',
                assistant_tone VARCHAR(32) NOT NULL DEFAULT 'balanced'
                    CHECK (assistant_tone IN ('balanced', 'concise', 'detailed')),
                personal_instructions TEXT NOT NULL DEFAULT '',
                auto_open_help BOOLEAN NOT NULL DEFAULT TRUE,
                notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS user_mcp_tokens (
                id UUID PRIMARY KEY,
                user_id VARCHAR(128) NOT NULL,
                label VARCHAR(128) NOT NULL,
                token_prefix VARCHAR(24) NOT NULL,
                token_sha256 VARCHAR(64) NOT NULL UNIQUE,
                scopes_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                expires_in_days INTEGER NOT NULL DEFAULT 30
                    CHECK (expires_in_days IN (30, 90)),
                rpm_limit INTEGER NOT NULL DEFAULT 60
                    CHECK (rpm_limit >= 1 AND rpm_limit <= 600),
                target_kind VARCHAR(16) NOT NULL DEFAULT 'SPACE'
                    CHECK (target_kind IN ('SPACE', 'AGENT')),
                target_slug VARCHAR(128) NOT NULL DEFAULT 'default',
                mcp_endpoint_uri VARCHAR(256) NOT NULL DEFAULT '/api/v1/mcp/spaces/default',
                ide_json_snippet TEXT NOT NULL DEFAULT '',
                expires_at TIMESTAMPTZ NULL,
                revoked_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_user_mcp_tokens_user_id
                ON user_mcp_tokens (user_id, created_at DESC)
            """
        )
    )


def downgrade() -> None:
    """Drop `user_mcp_tokens` and `user_preferences` tables."""
    op.execute(sa.text("DROP INDEX IF EXISTS ix_user_mcp_tokens_user_id"))
    op.execute(sa.text("DROP TABLE IF EXISTS user_mcp_tokens"))
    op.execute(sa.text("DROP TABLE IF EXISTS user_preferences"))
