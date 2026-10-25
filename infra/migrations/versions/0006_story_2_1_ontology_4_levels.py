"""Story 2.1 Relational-Graph 4-Level Ontology (`3_TEAM` & `3_WORKSPACE`), CTE & Axioms.

Revision ID: 0006_story_2_1
Revises: 0005_story_1_5
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0006_story_2_1"
down_revision: str | None = "0005_story_1_5"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE ontology_concepts (
        id UUID PRIMARY KEY,
        concept_key VARCHAR(128) NOT NULL UNIQUE,
        canonical_term VARCHAR(255) NOT NULL,
        level VARCHAR(32) NOT NULL CHECK (
            level IN ('1_ENTERPRISE', '2_DOMAIN', '3_TEAM', '3_WORKSPACE', '4_RUN_EPHEMERAL')
        ),
        scope_id VARCHAR(128) NOT NULL,
        parent_concept_id UUID NULL REFERENCES ontology_concepts(id) ON DELETE SET NULL,
        definition_text TEXT NOT NULL,
        synonyms_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
        banned_terms_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
        profile_translations_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        expected_schema_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        introduced_in_snapshot_id VARCHAR(128) NULL,
        snapshot_branch_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE' CHECK (
            snapshot_branch_status IN ('ACTIVE', 'SUPERSEDED')
        ),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (level, scope_id, canonical_term)
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_ontology_concepts_level_scope_term "
        "ON ontology_concepts(level, scope_id, canonical_term);"
    ),
    """
    CREATE TABLE ontology_relations (
        id UUID PRIMARY KEY,
        relation_key VARCHAR(128) NOT NULL UNIQUE,
        source_concept_id UUID NOT NULL REFERENCES ontology_concepts(id) ON DELETE CASCADE,
        target_concept_id UUID NOT NULL REFERENCES ontology_concepts(id) ON DELETE CASCADE,
        relation_type VARCHAR(64) NOT NULL,
        cardinality VARCHAR(32) NOT NULL DEFAULT '1..N',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_ontology_relations_source_target "
        "ON ontology_relations(source_concept_id, target_concept_id);"
    ),
    """
    CREATE TABLE ontology_axioms (
        id UUID PRIMARY KEY,
        axiom_key VARCHAR(128) NOT NULL UNIQUE,
        concept_id UUID NOT NULL REFERENCES ontology_concepts(id) ON DELETE CASCADE,
        level VARCHAR(32) NOT NULL CHECK (
            level IN ('1_ENTERPRISE', '2_DOMAIN', '3_TEAM', '3_WORKSPACE', '4_RUN_EPHEMERAL')
        ),
        scope_id VARCHAR(128) NOT NULL,
        rule_expression TEXT NOT NULL,
        immutable BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_ontology_axioms_concept_level "
        "ON ontology_axioms(concept_id, level, scope_id);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS ontology_axioms;",
    "DROP TABLE IF EXISTS ontology_relations;",
    "DROP TABLE IF EXISTS ontology_concepts;",
)


def upgrade() -> None:
    """Create Story 2.1 ontology_concepts, ontology_relations, and ontology_axioms tables."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 2.1 ontology tables."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
