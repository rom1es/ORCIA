"""Story 17.5 — AI Models Hub, Secrets AES-256 & Health Supervision (`FR-31`, `AD-21`).

Revision ID: 20261114_1705
Revises: 20261111_1704
Create Date: 2026-11-14

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261114_1705"
down_revision: str | None = "20261111_1704"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_llm_tier_mappings
                ADD COLUMN IF NOT EXISTS display_name VARCHAR(160) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS fallback_model_name VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS endpoint_uri TEXT NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS auth_mode VARCHAR(32) NOT NULL DEFAULT 'api_key'
                    CHECK (auth_mode IN ('api_key', 'env_var', 'none_local')),
                ADD COLUMN IF NOT EXISTS protocol_mode VARCHAR(32) NOT NULL
                    DEFAULT 'openai_compatible'
                    CHECK (
                        protocol_mode IN (
                            'openai_compatible', 'gemini_native', 'anthropic_messages'
                        )
                    ),
                ADD COLUMN IF NOT EXISTS env_var_name VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS encrypted_api_key TEXT NULL,
                ADD COLUMN IF NOT EXISTS secret_fingerprint VARCHAR(64) NULL,
                ADD COLUMN IF NOT EXISTS secret_masked_hint VARCHAR(32) NULL,
                ADD COLUMN IF NOT EXISTS secret_updated_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS secret_updated_by VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS health_status VARCHAR(32) NOT NULL DEFAULT 'UNTESTED'
                    CHECK (health_status IN ('OPERATIONAL', 'DEGRADED', 'ERROR', 'UNTESTED')),
                ADD COLUMN IF NOT EXISTS last_tested_at TIMESTAMPTZ NULL,
                ADD COLUMN IF NOT EXISTS last_latency_ms INTEGER NULL,
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_llm_tier_mappings_scope_tier_active
                ON workspace_llm_tier_mappings (scope_level, inference_tier, is_active);
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DROP INDEX IF EXISTS idx_llm_tier_mappings_scope_tier_active;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_llm_tier_mappings
                DROP COLUMN IF EXISTS created_at,
                DROP COLUMN IF EXISTS last_latency_ms,
                DROP COLUMN IF EXISTS last_tested_at,
                DROP COLUMN IF EXISTS health_status,
                DROP COLUMN IF EXISTS secret_updated_by,
                DROP COLUMN IF EXISTS secret_updated_at,
                DROP COLUMN IF EXISTS secret_masked_hint,
                DROP COLUMN IF EXISTS secret_fingerprint,
                DROP COLUMN IF EXISTS encrypted_api_key,
                DROP COLUMN IF EXISTS env_var_name,
                DROP COLUMN IF EXISTS protocol_mode,
                DROP COLUMN IF EXISTS auth_mode,
                DROP COLUMN IF EXISTS endpoint_uri,
                DROP COLUMN IF EXISTS fallback_model_name,
                DROP COLUMN IF EXISTS display_name;
            """
        )
    )
