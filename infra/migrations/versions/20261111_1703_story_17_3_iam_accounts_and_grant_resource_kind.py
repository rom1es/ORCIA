"""Story 17.3 — IAM Accounts directory & granular SecOps grant columns (`FR21`, `FR31`, `AD-21`).

Revision ID: 20261111_1703
Revises: 20261111_1702
Create Date: 2026-11-11

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_1703"
down_revision: str | None = "20261111_1702"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS iam_accounts (
                id UUID PRIMARY KEY,
                principal_id VARCHAR(128) UNIQUE NOT NULL,
                display_name VARCHAR(160) NOT NULL,
                email VARCHAR(255) NULL,
                account_kind VARCHAR(32) NOT NULL
                    CHECK (account_kind IN ('HUMAN', 'SERVICE_PRINCIPAL')),
                auth_source VARCHAR(32) NOT NULL
                    CHECK (auth_source IN ('LOCAL_BOOTSTRAP', 'OIDC_FEDERATED', 'SERVICE_TOKEN')),
                roles_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                team_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('ACTIVE', 'INVITED', 'DISABLED')),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_iam_accounts_kind_status
                ON iam_accounts (account_kind, status);
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE role_permission_grants
                DROP CONSTRAINT IF EXISTS role_permission_grants_effect_check;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE role_permission_grants
                ALTER COLUMN effect TYPE VARCHAR(32);
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE role_permission_grants
                ADD CONSTRAINT role_permission_grants_effect_check
                    CHECK (effect IN ('ALLOW', 'DENY', 'INHERITANCE_BLOCK'));
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE role_permission_grants
                ADD COLUMN IF NOT EXISTS resource_kind VARCHAR(32) NOT NULL DEFAULT 'ALL'
                    CHECK (
                        resource_kind IN ('ALL', 'WORKFLOW', 'AGENT', 'DATASOURCE', 'CONNECTOR')
                    );
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE role_permission_grants
                DROP CONSTRAINT IF EXISTS
                    role_permission_grants_subject_type_subject_id_scope_path_ve_key;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_role_permission_grants_resource_scope
                ON role_permission_grants (
                    subject_type, subject_id, scope_path, resource_kind, verb, effect
                );
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_role_permission_grants_resource_scope;"))
    op.execute(
        sa.text(
            """
            UPDATE role_permission_grants
            SET effect = 'ALLOW', inheritance_block = TRUE
            WHERE effect = 'INHERITANCE_BLOCK';
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM role_permission_grants a
            USING role_permission_grants b
            WHERE a.ctid < b.ctid
              AND a.subject_type = b.subject_type
              AND a.subject_id = b.subject_id
              AND a.scope_path = b.scope_path
              AND a.verb = b.verb
              AND a.effect = b.effect;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE role_permission_grants
                DROP COLUMN IF EXISTS resource_kind,
                DROP CONSTRAINT IF EXISTS role_permission_grants_effect_check;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE role_permission_grants
                ALTER COLUMN effect TYPE VARCHAR(16),
                ADD CONSTRAINT role_permission_grants_effect_check
                    CHECK (effect IN ('ALLOW', 'DENY')),
                ADD CONSTRAINT role_permission_grants_subject_type_subject_id_scope_path_ve_key
                    UNIQUE (subject_type, subject_id, scope_path, verb, effect);
            """
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_iam_accounts_kind_status;"))
    op.execute(sa.text("DROP TABLE IF EXISTS iam_accounts;"))
