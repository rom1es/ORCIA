"""Story 17.2 — Org units multi-level FinOps billing, lead, and members columns (`FR22`, `FR23`).

Revision ID: 20261111_1702
Revises: 20261108_0910
Create Date: 2026-11-11

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_1702"
down_revision: str | None = "20261108_0910"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                ADD COLUMN IF NOT EXISTS billing_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                ADD COLUMN IF NOT EXISTS lead_user_id VARCHAR(128) NULL,
                ADD COLUMN IF NOT EXISTS member_user_ids_jsonb JSONB NOT NULL DEFAULT '[]'::jsonb;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE org_units
                DROP COLUMN IF EXISTS member_user_ids_jsonb,
                DROP COLUMN IF EXISTS lead_user_id,
                DROP COLUMN IF EXISTS billing_enabled;
            """
        )
    )
