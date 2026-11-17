"""Merge Epic 7 review (`20261117_0705`) and Epic 16 reflexive sessions (`20261111_01`) heads.

Revision ID: 20261117_1601
Revises: 20261117_0705, 20261111_01
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "20261117_1601"
down_revision: str | Sequence[str] | None = ("20261117_0705", "20261111_01")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
