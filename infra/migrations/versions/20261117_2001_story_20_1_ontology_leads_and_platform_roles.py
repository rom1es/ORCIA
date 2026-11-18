"""Story 20.1 — Official roles, BU `ontology_lead_user_ids_jsonb`, and `audit_ledger` index.

Revision ID: 20261117_2001
Revises: 20261117_1601
Create Date: 2026-11-17

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261117_2001"
down_revision: str | Sequence[str] | None = "20261117_1601"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EXTENDED_ROLES_SQL = (
    "'PLATFORM_ADMIN', 'SECOPS', 'BU_LEAD', 'BU_DIRECTOR', "
    "'TEAM_LEAD', 'ONTOLOGY_LEAD', 'CONTRIBUTOR', 'GATE_REVIEWER', "
    "'ONTOLOGY_STEWARD_L3', 'OBSERVER'"
)

_LEGACY_USERS_ROLES_SQL = (
    "'PLATFORM_ADMIN', 'BU_DIRECTOR', 'TEAM_LEAD', "
    "'CONTRIBUTOR', 'GATE_REVIEWER', 'ONTOLOGY_STEWARD_L3', 'OBSERVER'"
)

_LEGACY_WS_ROLES_SQL = (
    "'TEAM_LEAD', 'CONTRIBUTOR', 'GATE_REVIEWER', 'ONTOLOGY_STEWARD_L3', 'OBSERVER'"
)


def upgrade() -> None:
    """Widen role CHECKs, add `org_units.ontology_lead_user_ids_jsonb`, and index `audit_ledger`."""
    # 1. Widen role CHECK constraints on users, memberships, and invitations
    op.execute(
        sa.text(
            f"""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                IF to_regclass('public.users') IS NOT NULL THEN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.users'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%platform_role%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE users DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE users
                        ADD CONSTRAINT chk_users_platform_role
                        CHECK (platform_role IN ({_EXTENDED_ROLES_SQL}));
                END IF;

                IF to_regclass('public.workspace_memberships') IS NOT NULL THEN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.workspace_memberships'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%role%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE workspace_memberships DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE workspace_memberships
                        ADD CONSTRAINT chk_workspace_memberships_role
                        CHECK (role IN ({_EXTENDED_ROLES_SQL}));
                END IF;

                IF to_regclass('public.workspace_invitations') IS NOT NULL THEN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.workspace_invitations'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%assigned_role%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE workspace_invitations DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE workspace_invitations
                        ADD CONSTRAINT chk_workspace_invitations_assigned_role
                        CHECK (assigned_role IN ({_EXTENDED_ROLES_SQL}));
                END IF;
            END $$;
            """
        )
    )

    # 2. Add ontology_lead_user_ids_jsonb on org_units with strict BU-only and array CHECKs
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                ADD COLUMN IF NOT EXISTS ontology_lead_user_ids_jsonb
                JSONB NOT NULL DEFAULT '[]'::jsonb;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                DROP CONSTRAINT IF EXISTS chk_org_units_ontology_leads_is_array,
                DROP CONSTRAINT IF EXISTS chk_org_units_ontology_leads_only_bu;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                ADD CONSTRAINT chk_org_units_ontology_leads_is_array
                    CHECK (jsonb_typeof(ontology_lead_user_ids_jsonb) = 'array'),
                ADD CONSTRAINT chk_org_units_ontology_leads_only_bu
                    CHECK (unit_type = 'BU' OR ontology_lead_user_ids_jsonb = '[]'::jsonb);
            """
        )
    )

    # 3. Partial index on audit_ledger(org_unit_id, created_at DESC)
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF to_regclass('public.audit_ledger') IS NOT NULL THEN
                    CREATE INDEX IF NOT EXISTS ix_audit_ledger_org_unit_created_at
                        ON audit_ledger (org_unit_id, created_at DESC)
                        WHERE org_unit_id IS NOT NULL;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    """Revert Story 20.1 index, `ontology_lead_user_ids_jsonb`, and role CHECK constraints."""
    op.execute(sa.text("DROP INDEX IF EXISTS ix_audit_ledger_org_unit_created_at;"))

    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                DROP CONSTRAINT IF EXISTS chk_org_units_ontology_leads_only_bu,
                DROP CONSTRAINT IF EXISTS chk_org_units_ontology_leads_is_array,
                DROP COLUMN IF EXISTS ontology_lead_user_ids_jsonb;
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                IF to_regclass('public.users') IS NOT NULL THEN
                    UPDATE users
                    SET platform_role = CASE platform_role
                        WHEN 'BU_LEAD' THEN 'BU_DIRECTOR'
                        WHEN 'ONTOLOGY_LEAD' THEN 'ONTOLOGY_STEWARD_L3'
                        WHEN 'SECOPS' THEN 'CONTRIBUTOR'
                        ELSE platform_role
                    END
                    WHERE platform_role IN ('BU_LEAD', 'ONTOLOGY_LEAD', 'SECOPS');

                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.users'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%platform_role%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE users DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE users
                        ADD CONSTRAINT users_platform_role_check
                        CHECK (platform_role IN ({_LEGACY_USERS_ROLES_SQL}));
                END IF;

                IF to_regclass('public.workspace_memberships') IS NOT NULL THEN
                    UPDATE workspace_memberships
                    SET role = CASE role
                        WHEN 'ONTOLOGY_LEAD' THEN 'ONTOLOGY_STEWARD_L3'
                        ELSE 'CONTRIBUTOR'
                    END
                    WHERE role NOT IN ({_LEGACY_WS_ROLES_SQL});

                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.workspace_memberships'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%role%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE workspace_memberships DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE workspace_memberships
                        ADD CONSTRAINT workspace_memberships_role_check
                        CHECK (role IN ({_LEGACY_WS_ROLES_SQL}));
                END IF;

                IF to_regclass('public.workspace_invitations') IS NOT NULL THEN
                    UPDATE workspace_invitations
                    SET assigned_role = CASE assigned_role
                        WHEN 'ONTOLOGY_LEAD' THEN 'ONTOLOGY_STEWARD_L3'
                        ELSE 'CONTRIBUTOR'
                    END
                    WHERE assigned_role NOT IN ({_LEGACY_WS_ROLES_SQL});

                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.workspace_invitations'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%assigned_role%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE workspace_invitations DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE workspace_invitations
                        ADD CONSTRAINT workspace_invitations_assigned_role_check
                        CHECK (assigned_role IN ({_LEGACY_WS_ROLES_SQL}));
                END IF;
            END $$;
            """
        )
    )
