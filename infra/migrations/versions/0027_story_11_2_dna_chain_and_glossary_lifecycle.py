"""Story 11.2: Add `dna_stereotype`, `mechanism_payload_jsonb` & `ontology_rejected_candidates`.

Revision ID: 0027_story_11_2
Revises: 0026_story_11_1
Create Date: 2026-10-31 18:20:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_story_11_2"
down_revision: str | None = "0026_story_11_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enrich ontology tables with DNA chain columns and rejected candidate fingerprints."""
    op.execute(
        sa.text(
            """
            ALTER TABLE ontology_concepts
                ADD COLUMN IF NOT EXISTS dna_stereotype VARCHAR(32) NOT NULL DEFAULT 'CONCEPT'
                CONSTRAINT ontology_concepts_dna_stereotype_check
                CHECK (dna_stereotype IN ('CONCEPT', 'DIRECTIVE', 'NORM', 'MECHANISM'))
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE ontology_concepts
                ADD COLUMN IF NOT EXISTS mechanism_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE ontology_axioms
                ADD COLUMN IF NOT EXISTS dna_stereotype VARCHAR(32) NOT NULL DEFAULT 'NORM'
                CONSTRAINT ontology_axioms_dna_stereotype_check
                CHECK (dna_stereotype IN ('DIRECTIVE', 'NORM', 'MECHANISM'))
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE ontology_axioms
                ADD COLUMN IF NOT EXISTS mechanism_payload_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS ontology_rejected_candidates (
                id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                canonical_term_fingerprint VARCHAR(64) NOT NULL,
                canonical_term VARCHAR(255) NOT NULL,
                rejected_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                reason TEXT NOT NULL DEFAULT 'REJECTED_CANDIDATE',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_ontology_rejected_candidate_fp
                    UNIQUE (workspace_id, canonical_term_fingerprint)
            )
            """
        )
    )


def downgrade() -> None:
    """Drop `ontology_rejected_candidates` and DNA chain columns from ontology tables."""
    op.execute(sa.text("DROP TABLE IF EXISTS ontology_rejected_candidates"))
    op.execute(sa.text("ALTER TABLE ontology_axioms DROP COLUMN IF EXISTS mechanism_payload_jsonb"))
    op.execute(sa.text("ALTER TABLE ontology_axioms DROP COLUMN IF EXISTS dna_stereotype"))
    op.execute(
        sa.text("ALTER TABLE ontology_concepts DROP COLUMN IF EXISTS mechanism_payload_jsonb")
    )
    op.execute(sa.text("ALTER TABLE ontology_concepts DROP COLUMN IF EXISTS dna_stereotype"))
