"""Story 2.2 Real-Time L4 Ontology Extraction, Branch Isolation & What-If Promotions.

Revision ID: 0007_story_2_2
Revises: 0006_story_2_1
Create Date: 2026-10-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0007_story_2_2"
down_revision: str | None = "0006_story_2_1"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE ontology_promotion_proposals (
        id UUID PRIMARY KEY,
        proposal_key VARCHAR(128) NOT NULL UNIQUE,
        concept_id UUID NOT NULL REFERENCES ontology_concepts(id) ON DELETE CASCADE,
        source_level VARCHAR(32) NOT NULL CHECK (
            source_level IN ('4_RUN_EPHEMERAL', '3_WORKSPACE', '3_TEAM', '2_DOMAIN')
        ),
        target_level VARCHAR(32) NOT NULL CHECK (
            target_level IN ('3_WORKSPACE', '3_TEAM', '2_DOMAIN', '1_ENTERPRISE')
        ),
        target_scope_id VARCHAR(128) NOT NULL,
        proposed_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        status VARCHAR(32) NOT NULL CHECK (
            status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')
        ),
        impact_report_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """,
    (
        "CREATE INDEX IF NOT EXISTS idx_ontology_promotion_proposals_status "
        "ON ontology_promotion_proposals(status, target_level);"
    ),
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = ("DROP TABLE IF EXISTS ontology_promotion_proposals;",)


def upgrade() -> None:
    """Create Story 2.2 ontology_promotion_proposals table."""
    for sql in UPGRADE_STATEMENTS:
        op.execute(sa.text(sql))


def downgrade() -> None:
    """Drop Story 2.2 ontology_promotion_proposals table."""
    for sql in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(sql))
