"""Story 17.6 — Temporary password & Local IAM Auth persistence (`FR-31`, `AD-6`, `AD-19`).

Revision ID: 20261114_1706
Revises: 20261114_1802
Create Date: 2026-11-14

Pure raw SQL migration (`op.execute(sa.text(...))`), zero ORM imports, fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261114_1706"
down_revision: str | None = "20261114_1802"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE users
                ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ NULL;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE users
                DROP COLUMN IF EXISTS password_changed_at,
                DROP COLUMN IF EXISTS must_change_password;
            """
        )
    )
