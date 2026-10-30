"""Story 4.1: `gate_evaluations` table for Deterministic, Agentic & Human Gates (`AD-9..11`).

Revision ID: 0017_story_4_1
Revises: 0016_story_3_5
Create Date: 2026-10-30 07:30:00.000000

Conventions (AGENTS.md):
- Never import application ORM models inside an Alembic migration.
- Use raw SQL (`op.execute(sa.text(...))`) following Expand -> Backfill SQL -> Contract.
- All database primary keys use UUIDv7 (`UUID`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_story_4_1"
down_revision: str | None = "0016_story_3_5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create `gate_evaluations` table (`FR-17`, `FR-18`, `FR-19`, `AD-9`, `AD-10`, `AD-11`)."""
    op.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS gate_evaluations (
                id UUID PRIMARY KEY,
                workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                run_id UUID NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
                step_execution_id UUID NOT NULL REFERENCES step_executions(id) ON DELETE CASCADE,
                step_key VARCHAR(128) NOT NULL,
                gate_type VARCHAR(32) NOT NULL
                    CHECK (gate_type IN ('DETERMINISTIC', 'AGENTIC', 'HUMAN')),
                sandbox_tier VARCHAR(32) NOT NULL DEFAULT 'TIER_1_WASM'
                    CHECK (sandbox_tier IN ('TIER_1_WASM', 'TIER_2_CONTAINER', 'NONE')),
                status VARCHAR(32) NOT NULL
                    CHECK (status IN ('PASS', 'FAIL', 'ERROR', 'PENDING_HUMAN_REVIEW')),
                score DOUBLE PRECISION NOT NULL DEFAULT 1.0
                    CHECK (score >= 0.0 AND score <= 1.0),
                schema_validation_passed BOOLEAN NOT NULL DEFAULT TRUE,
                ontology_axioms_passed BOOLEAN NOT NULL DEFAULT TRUE,
                pattern_drift_passed BOOLEAN NOT NULL DEFAULT TRUE,
                pattern_drift_findings_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                lens_findings_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb,
                briefing_4blocks_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb,
                evaluator_model_id VARCHAR(128) NULL,
                duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (duration_ms >= 0),
                review_duration_ms INTEGER NOT NULL DEFAULT 0 CHECK (review_duration_ms >= 0),
                fast_approval_warning BOOLEAN NOT NULL DEFAULT FALSE,
                outbox_event_id UUID NULL,
                evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_gate_evaluations_run_step
                ON gate_evaluations (run_id, step_execution_id, gate_type);
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_gate_evaluations_workspace_type
                ON gate_evaluations (workspace_id, gate_type, status);
            """
        )
    )


def downgrade() -> None:
    """Drop `gate_evaluations` table."""
    op.execute(sa.text("DROP TABLE IF EXISTS gate_evaluations;"))
