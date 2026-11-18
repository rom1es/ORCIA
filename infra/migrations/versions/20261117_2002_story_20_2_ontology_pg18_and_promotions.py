"""Story 20.2 — Ontology PG18 4_WORKSPACE CHECKs & promotion workflow columns.

Revision ID: 20261117_2002
Revises: 20261117_2001
Create Date: 2026-11-17

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261117_2002"
down_revision: str | Sequence[str] | None = "20261117_2001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EXTENDED_CONCEPT_LEVELS = (
    "'1_ENTERPRISE', '2_DOMAIN', '3_TEAM', '3_WORKSPACE', '4_WORKSPACE', '4_RUN_EPHEMERAL'"
)
_LEGACY_CONCEPT_LEVELS = "'1_ENTERPRISE', '2_DOMAIN', '3_TEAM', '3_WORKSPACE', '4_RUN_EPHEMERAL'"

_EXTENDED_PROMO_SOURCE_LEVELS = (
    "'4_RUN_EPHEMERAL', '4_WORKSPACE', '3_WORKSPACE', '3_TEAM', '2_DOMAIN'"
)
_LEGACY_PROMO_SOURCE_LEVELS = "'4_RUN_EPHEMERAL', '3_WORKSPACE', '3_TEAM', '2_DOMAIN'"

_EXTENDED_PROMO_TARGET_LEVELS = "'4_WORKSPACE', '3_WORKSPACE', '3_TEAM', '2_DOMAIN', '1_ENTERPRISE'"
_LEGACY_PROMO_TARGET_LEVELS = "'3_WORKSPACE', '3_TEAM', '2_DOMAIN', '1_ENTERPRISE'"


def upgrade() -> None:
    """Widen ontology level CHECKs for `4_WORKSPACE` and add promotion review columns."""
    op.execute(
        sa.text(
            f"""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                IF to_regclass('public.ontology_concepts') IS NOT NULL THEN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.ontology_concepts'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%level%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE ontology_concepts DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE ontology_concepts
                        ADD CONSTRAINT chk_ontology_concepts_level
                        CHECK (level IN ({_EXTENDED_CONCEPT_LEVELS}));
                END IF;

                IF to_regclass('public.ontology_axioms') IS NOT NULL THEN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.ontology_axioms'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%level%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE ontology_axioms DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE ontology_axioms
                        ADD CONSTRAINT chk_ontology_axioms_level
                        CHECK (level IN ({_EXTENDED_CONCEPT_LEVELS}));
                END IF;

                IF to_regclass('public.ontology_promotion_proposals') IS NOT NULL THEN
                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.ontology_promotion_proposals'::regclass
                          AND contype = 'c'
                          AND (
                              pg_get_constraintdef(oid) ILIKE '%source_level%'
                              OR pg_get_constraintdef(oid) ILIKE '%target_level%'
                          )
                    ) LOOP
                        EXECUTE 'ALTER TABLE ontology_promotion_proposals '
                            || 'DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE ontology_promotion_proposals
                        ADD CONSTRAINT chk_ontology_promotions_source_level
                        CHECK (source_level IN ({_EXTENDED_PROMO_SOURCE_LEVELS})),
                        ADD CONSTRAINT chk_ontology_promotions_target_level
                        CHECK (target_level IN ({_EXTENDED_PROMO_TARGET_LEVELS}));
                END IF;
            END $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            ALTER TABLE ontology_promotion_proposals
                ADD COLUMN IF NOT EXISTS source_concept_id UUID NULL,
                ADD COLUMN IF NOT EXISTS term VARCHAR(255) NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS definition TEXT NOT NULL DEFAULT '',
                ADD COLUMN IF NOT EXISTS source_scope_id VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS reviewed_by_user_id VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS review_comment TEXT NULL,
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ NULL;
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_ontology_promotions_status_target
                ON ontology_promotion_proposals (status, target_level, target_scope_id);
            """
        )
    )


def downgrade() -> None:
    """Revert Story 20.2 promotion columns, index, and legacy level CHECK constraints."""
    op.execute(sa.text("DROP INDEX IF EXISTS ix_ontology_promotions_status_target;"))

    op.execute(
        sa.text(
            """
            ALTER TABLE ontology_promotion_proposals
                DROP COLUMN IF EXISTS reviewed_at,
                DROP COLUMN IF EXISTS review_comment,
                DROP COLUMN IF EXISTS reviewed_by_user_id,
                DROP COLUMN IF EXISTS source_scope_id,
                DROP COLUMN IF EXISTS definition,
                DROP COLUMN IF EXISTS term,
                DROP COLUMN IF EXISTS source_concept_id;
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
                IF to_regclass('public.ontology_promotion_proposals') IS NOT NULL THEN
                    UPDATE ontology_promotion_proposals
                    SET source_level = '3_WORKSPACE'
                    WHERE source_level = '4_WORKSPACE';

                    UPDATE ontology_promotion_proposals
                    SET target_level = '3_WORKSPACE'
                    WHERE target_level = '4_WORKSPACE';

                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.ontology_promotion_proposals'::regclass
                          AND contype = 'c'
                          AND (
                              pg_get_constraintdef(oid) ILIKE '%source_level%'
                              OR pg_get_constraintdef(oid) ILIKE '%target_level%'
                          )
                    ) LOOP
                        EXECUTE 'ALTER TABLE ontology_promotion_proposals '
                            || 'DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE ontology_promotion_proposals
                        ADD CONSTRAINT ontology_promotion_proposals_source_level_check
                        CHECK (source_level IN ({_LEGACY_PROMO_SOURCE_LEVELS})),
                        ADD CONSTRAINT ontology_promotion_proposals_target_level_check
                        CHECK (target_level IN ({_LEGACY_PROMO_TARGET_LEVELS}));
                END IF;

                IF to_regclass('public.ontology_axioms') IS NOT NULL THEN
                    UPDATE ontology_axioms
                    SET level = '3_WORKSPACE'
                    WHERE level = '4_WORKSPACE';

                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.ontology_axioms'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%level%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE ontology_axioms DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE ontology_axioms
                        ADD CONSTRAINT ontology_axioms_level_check
                        CHECK (level IN ({_LEGACY_CONCEPT_LEVELS}));
                END IF;

                IF to_regclass('public.ontology_concepts') IS NOT NULL THEN
                    UPDATE ontology_concepts
                    SET level = '3_WORKSPACE'
                    WHERE level = '4_WORKSPACE';

                    FOR r IN (
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'public.ontology_concepts'::regclass
                          AND contype = 'c'
                          AND pg_get_constraintdef(oid) ILIKE '%level%'
                    ) LOOP
                        EXECUTE 'ALTER TABLE ontology_concepts DROP CONSTRAINT IF EXISTS '
                            || quote_ident(r.conname);
                    END LOOP;

                    ALTER TABLE ontology_concepts
                        ADD CONSTRAINT ontology_concepts_level_check
                        CHECK (level IN ({_LEGACY_CONCEPT_LEVELS}));
                END IF;
            END $$;
            """
        )
    )
