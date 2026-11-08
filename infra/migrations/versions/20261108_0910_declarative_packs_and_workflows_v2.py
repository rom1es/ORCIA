"""0028 / 20261108_0910 — Declarative Packs, VSM v2, Bounded Workflows v2 & Claim-Check Artifacts.

Revision ID: 20261108_0910
Revises: 0027_story_11_2
Create Date: 2026-11-08 17:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "20261108_0910"
down_revision: str | None = "0027_story_11_2"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Create declarative pack bundles, VSM v2, workflow v2, and claim-check tables."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS declarative_pack_bundles (
                id UUID PRIMARY KEY,
                pack_id VARCHAR(128) NOT NULL UNIQUE,
                slug VARCHAR(128) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                version VARCHAR(64) NOT NULL,
                rbac_namespace VARCHAR(64) NOT NULL,
                bundle_sha256 CHAR(64) NOT NULL,
                manifest_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS vsm_definitions_v2 (
                id UUID PRIMARY KEY,
                vsm_id VARCHAR(128) NOT NULL UNIQUE,
                slug VARCHAR(128) NOT NULL UNIQUE,
                pack_id VARCHAR(128) NOT NULL,
                title VARCHAR(255) NOT NULL,
                spec_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS workflow_definitions_v2 (
                id UUID PRIMARY KEY,
                workflow_id VARCHAR(128) NOT NULL,
                slug VARCHAR(128) NOT NULL,
                version VARCHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'draft',
                pack_id VARCHAR(128) NOT NULL,
                execution_mode VARCHAR(32) NOT NULL DEFAULT 'native_orcia',
                spec_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_workflow_definitions_v2_id_ver UNIQUE (workflow_id, version)
            );

            CREATE TABLE IF NOT EXISTS claim_check_artifacts (
                id UUID PRIMARY KEY,
                run_id VARCHAR(128) NOT NULL,
                step_id VARCHAR(128) NOT NULL,
                iteration_index INTEGER NOT NULL DEFAULT 0,
                s3_uri TEXT NOT NULL UNIQUE,
                sha256 CHAR(64) NOT NULL,
                byte_size BIGINT NOT NULL CHECK (byte_size >= 0),
                mime_type VARCHAR(128) NOT NULL DEFAULT 'text/markdown',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS ix_claim_check_artifacts_run_step_iter
                ON claim_check_artifacts (run_id, step_id, iteration_index);
            """
        )
    )


def downgrade() -> None:
    """Drop tables created in 20261108_0910."""
    op.execute(
        sa.text(
            """
            DROP INDEX IF EXISTS ix_claim_check_artifacts_run_step_iter;
            DROP TABLE IF EXISTS claim_check_artifacts;
            DROP TABLE IF EXISTS workflow_definitions_v2;
            DROP TABLE IF EXISTS vsm_definitions_v2;
            DROP TABLE IF EXISTS declarative_pack_bundles;
            """
        )
    )
