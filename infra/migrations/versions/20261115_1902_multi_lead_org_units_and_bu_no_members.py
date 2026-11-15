"""Multi-lead org units, BU no direct members constraint, and LOCAL_PASSWORD auth source.

Revision ID: 20261115_1902
Revises: 20261115_1901
Create Date: 2026-11-15

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261115_1902"
down_revision: str | None = "20261115_1901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add lead_user_ids_jsonb column to org_units
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                ADD COLUMN IF NOT EXISTS lead_user_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb;
            """
        )
    )

    # 2. Backfill lead_user_id into lead_user_ids_jsonb when empty
    op.execute(
        sa.text(
            """
            UPDATE org_units
            SET lead_user_ids_jsonb = jsonb_build_array(btrim(lead_user_id))
            WHERE lead_user_id IS NOT NULL
              AND btrim(lead_user_id) <> ''
              AND (lead_user_ids_jsonb IS NULL OR lead_user_ids_jsonb = '[]'::jsonb);
            """
        )
    )

    # 3. Purge direct members on BU units
    op.execute(
        sa.text(
            """
            UPDATE org_units
            SET member_user_ids_jsonb = '[]'::jsonb
            WHERE unit_type = 'BU'
              AND member_user_ids_jsonb <> '[]'::jsonb;
            """
        )
    )

    # 4. Constraints on org_units
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                DROP CONSTRAINT IF EXISTS chk_org_units_lead_user_ids_is_array,
                DROP CONSTRAINT IF EXISTS chk_org_units_bu_no_members;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                ADD CONSTRAINT chk_org_units_lead_user_ids_is_array
                    CHECK (jsonb_typeof(lead_user_ids_jsonb) = 'array'),
                ADD CONSTRAINT chk_org_units_bu_no_members
                    CHECK (unit_type <> 'BU' OR member_user_ids_jsonb = '[]'::jsonb);
            """
        )
    )

    # 5. Drop old check constraints on iam_accounts auth_source & add updated constraint
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                IF to_regclass('public.iam_accounts') IS NOT NULL THEN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.iam_accounts'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%auth_source%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE iam_accounts DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE iam_accounts
                        ADD CONSTRAINT chk_iam_accounts_auth_source
                        CHECK (auth_source IN (
                            'LOCAL_BOOTSTRAP', 'LOCAL_PASSWORD', 'OIDC_FEDERATED', 'SERVICE_TOKEN'
                        ));
                END IF;
            END $$;
            """
        )
    )

    # 6. Backfill HUMAN accounts in LOCAL auth mode or having password to LOCAL_PASSWORD
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF to_regclass('public.platform_auth_settings') IS NOT NULL
                   AND to_regclass('public.iam_accounts') IS NOT NULL THEN
                    IF EXISTS (SELECT 1 FROM platform_auth_settings WHERE auth_mode = 'LOCAL') THEN
                        UPDATE iam_accounts
                        SET auth_source = 'LOCAL_PASSWORD'
                        WHERE account_kind = 'HUMAN' AND auth_source = 'OIDC_FEDERATED';
                    END IF;
                END IF;

                IF to_regclass('public.users') IS NOT NULL
                   AND to_regclass('public.iam_accounts') IS NOT NULL THEN
                    UPDATE iam_accounts a
                    SET auth_source = 'LOCAL_PASSWORD'
                    FROM users u
                    WHERE a.account_kind = 'HUMAN'
                      AND a.auth_source = 'OIDC_FEDERATED'
                      AND LOWER(a.principal_id) = LOWER(u.email)
                      AND u.password_hash_argon2id IS NOT NULL;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    # 1. Resynchronize legacy lead_user_id with lead_user_ids_jsonb[0]
    op.execute(
        sa.text(
            """
            UPDATE org_units
            SET lead_user_id = lead_user_ids_jsonb ->> 0
            WHERE jsonb_typeof(lead_user_ids_jsonb) = 'array'
              AND jsonb_array_length(lead_user_ids_jsonb) > 0;
            """
        )
    )

    # 2. Revert LOCAL_PASSWORD to OIDC_FEDERATED and restore original check constraint
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                IF to_regclass('public.iam_accounts') IS NOT NULL THEN
                    UPDATE iam_accounts
                    SET auth_source = 'OIDC_FEDERATED'
                    WHERE auth_source = 'LOCAL_PASSWORD';

                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.iam_accounts'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%auth_source%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE iam_accounts DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE iam_accounts
                        ADD CONSTRAINT iam_accounts_auth_source_check
                        CHECK (auth_source IN (
                            'LOCAL_BOOTSTRAP', 'OIDC_FEDERATED', 'SERVICE_TOKEN'
                        ));
                END IF;
            END $$;
            """
        )
    )

    # 3. Drop org_units constraints and lead_user_ids_jsonb column
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                DROP CONSTRAINT IF EXISTS chk_org_units_bu_no_members,
                DROP CONSTRAINT IF EXISTS chk_org_units_lead_user_ids_is_array,
                DROP COLUMN IF EXISTS lead_user_ids_jsonb;
            """
        )
    )
