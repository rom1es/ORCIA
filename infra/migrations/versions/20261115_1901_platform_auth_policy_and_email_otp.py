"""Exclusive auth policy (`LOCAL` vs `SSO`), 2FA (`EMAIL_OTP`/`TOTP`) & `SMTP_MAIL`.

Revision ID: 20261115_1901
Revises: 20261114_1706
Create Date: 2026-11-15

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261115_1901"
down_revision: str | None = "20261114_1706"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS platform_auth_settings (
                singleton_key VARCHAR(16) PRIMARY KEY CHECK (singleton_key = 'GLOBAL'),
                auth_mode VARCHAR(16) NOT NULL DEFAULT 'LOCAL'
                    CHECK (auth_mode IN ('LOCAL', 'SSO')),
                two_factor_mode VARCHAR(16) NOT NULL DEFAULT 'NONE'
                    CHECK (two_factor_mode IN ('NONE', 'EMAIL_OTP', 'TOTP')),
                oidc_issuer_url VARCHAR(512) NULL,
                oidc_client_id VARCHAR(255) NULL,
                oidc_client_secret_encrypted TEXT NULL,
                oidc_client_secret_fingerprint VARCHAR(32) NULL,
                oidc_scopes VARCHAR(255) NOT NULL DEFAULT 'openid profile email',
                oidc_redirect_uri VARCHAR(512) NULL,
                sso_button_label VARCHAR(160) NULL,
                boot_epoch UUID NOT NULL,
                updated_by VARCHAR(255) NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO platform_auth_settings (
                singleton_key,
                auth_mode,
                two_factor_mode,
                oidc_scopes,
                boot_epoch
            )
            VALUES (
                'GLOBAL',
                'LOCAL',
                'NONE',
                'openid profile email',
                gen_random_uuid()
            )
            ON CONFLICT (singleton_key) DO NOTHING;
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS auth_login_challenges (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                challenge_token_hash CHAR(64) NOT NULL UNIQUE,
                challenge_kind VARCHAR(16) NOT NULL
                    CHECK (challenge_kind IN ('EMAIL_OTP', 'TOTP', 'TOTP_ENROLL')),
                otp_code_hash CHAR(64) NULL,
                pending_totp_secret_encrypted TEXT NULL,
                masked_destination VARCHAR(255) NULL,
                attempts_count INTEGER NOT NULL DEFAULT 0 CHECK (attempts_count >= 0),
                max_attempts INTEGER NOT NULL DEFAULT 5 CHECK (max_attempts > 0),
                expires_at TIMESTAMPTZ NOT NULL,
                consumed_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_login_challenges_user_expires
                ON auth_login_challenges (user_id, expires_at DESC);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_login_challenges_expires
                ON auth_login_challenges (expires_at);
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                constraint_row RECORD;
            BEGIN
                FOR constraint_row IN
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'enterprise_connectors'::regclass
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%connector_kind%'
                LOOP
                    EXECUTE format(
                        'ALTER TABLE enterprise_connectors DROP CONSTRAINT IF EXISTS %I',
                        constraint_row.conname
                    );
                END LOOP;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE enterprise_connectors
                ADD CONSTRAINT enterprise_connectors_connector_kind_check
                CHECK (
                    connector_kind IN (
                        'GITLAB',
                        'JIRA',
                        'CONFLUENCE',
                        'OIDC_SSO',
                        'S3_OBJECT_STORE',
                        'SMTP_MAIL'
                    )
                );
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE enterprise_connectors
                DROP CONSTRAINT IF EXISTS enterprise_connectors_connector_kind_check;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM enterprise_connectors WHERE connector_kind = 'SMTP_MAIL';
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE enterprise_connectors
                ADD CONSTRAINT enterprise_connectors_connector_kind_check
                CHECK (
                    connector_kind IN (
                        'GITLAB',
                        'JIRA',
                        'CONFLUENCE',
                        'OIDC_SSO',
                        'S3_OBJECT_STORE'
                    )
                );
            """
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_auth_login_challenges_expires;"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_auth_login_challenges_user_expires;"))
    op.execute(sa.text("DROP TABLE IF EXISTS auth_login_challenges;"))
    op.execute(sa.text("DROP TABLE IF EXISTS platform_auth_settings;"))
