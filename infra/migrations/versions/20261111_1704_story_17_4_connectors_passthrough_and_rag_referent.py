"""Story 17.4 — Connectors, Passthrough & RAG Referent (`FR22`, `FR31`, `FR34`, `AD-21`).

Revision ID: 20261111_1704
Revises: 20261111_1703
Create Date: 2026-11-11

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_1704"
down_revision: str | None = "20261111_1703"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS enterprise_connectors (
                id UUID PRIMARY KEY,
                connector_kind VARCHAR(32) NOT NULL
                    CHECK (
                        connector_kind IN (
                            'GITLAB', 'JIRA', 'CONFLUENCE', 'OIDC_SSO', 'S3_OBJECT_STORE'
                        )
                    ),
                name VARCHAR(160) NOT NULL,
                base_url VARCHAR(512) NOT NULL,
                auth_mode VARCHAR(32) NOT NULL
                    CHECK (
                        auth_mode IN (
                            'OAUTH2_PASSTHROUGH',
                            'PERSONAL_ACCESS_TOKEN',
                            'OIDC_FEDERATION',
                            'SERVICE_SECRET'
                        )
                    ),
                encrypted_admin_secret TEXT NULL,
                admin_secret_fingerprint VARCHAR(32) NULL,
                admin_secret_updated_at TIMESTAMPTZ NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_enterprise_connectors_kind_enabled
                ON enterprise_connectors (connector_kind, enabled);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS user_connector_passthrough_tokens (
                id UUID PRIMARY KEY,
                user_id VARCHAR(128) NOT NULL,
                connector_id UUID NOT NULL REFERENCES enterprise_connectors(id) ON DELETE CASCADE,
                external_author_login VARCHAR(160) NULL,
                encrypted_token TEXT NOT NULL,
                secret_fingerprint VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'REVOKED')),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, connector_id)
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_user_connector_passthrough_user
                ON user_connector_passthrough_tokens (user_id, status);
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                ADD COLUMN IF NOT EXISTS connector_id UUID NULL
                    REFERENCES enterprise_connectors(id) ON DELETE SET NULL,
                ADD COLUMN IF NOT EXISTS sync_identity_mode VARCHAR(32) NOT NULL
                    DEFAULT 'SERVICE_ACCOUNT'
                    CHECK (sync_identity_mode IN ('SERVICE_ACCOUNT', 'TEAM_REFERENT_USER')),
                ADD COLUMN IF NOT EXISTS service_account_id VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS referent_user_id VARCHAR(128) NULL;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_workspace_datasources_connector_id
                ON workspace_datasources (connector_id);
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_workspace_datasources_connector_id;"))
    op.execute(
        sa.text(
            """
            ALTER TABLE workspace_datasources
                DROP COLUMN IF EXISTS referent_user_id,
                DROP COLUMN IF EXISTS service_account_id,
                DROP COLUMN IF EXISTS sync_identity_mode,
                DROP COLUMN IF EXISTS connector_id;
            """
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_user_connector_passthrough_user;"))
    op.execute(sa.text("DROP TABLE IF EXISTS user_connector_passthrough_tokens;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_enterprise_connectors_kind_enabled;"))
    op.execute(sa.text("DROP TABLE IF EXISTS enterprise_connectors;"))
