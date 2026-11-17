"""Epic 6 review (MAJOR-01): Expand workflow_definitions.adaptive_gate_policy CHECK constraint.

Revision ID: 20261117_0605
Revises: 20261116_0604
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261117_0605"
down_revision: str | Sequence[str] | None = "20261116_0604"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'workflow_definitions'::regclass
                      AND contype = 'c'
                      AND pg_get_constraintdef(oid) LIKE '%adaptive_gate_policy%'
                ) LOOP
                    EXECUTE 'ALTER TABLE workflow_definitions DROP CONSTRAINT IF EXISTS '
                        || quote_ident(r.conname);
                END LOOP;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_definitions
                ADD CONSTRAINT ck_workflow_definitions_adaptive_gate_policy
                CHECK (adaptive_gate_policy IN (
                    'STRICT',
                    'STANDARD',
                    'FAST_TRACK',
                    'RISK_OR_EXCEPTION_BASED',
                    'SAMPLING_20_PCT',
                    'STRENGTHEN_ANCHORS'
                ));
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE workflow_definitions
            SET adaptive_gate_policy = 'STANDARD'
            WHERE adaptive_gate_policy NOT IN ('STRICT', 'STANDARD', 'FAST_TRACK');
            """
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE workflow_definitions "
            "DROP CONSTRAINT IF EXISTS ck_workflow_definitions_adaptive_gate_policy;"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE workflow_definitions
                ADD CONSTRAINT ck_workflow_definitions_adaptive_gate_policy
                CHECK (adaptive_gate_policy IN ('STRICT', 'STANDARD', 'FAST_TRACK'));
            """
        )
    )
