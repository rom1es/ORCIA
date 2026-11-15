"""Merge multi-lead org units (`20261115_1902`) and Epic 19 RAG reindexing (`20261115_2307`) heads.

Revision ID: 20261115_2359
Revises: 20261115_1902, 20261115_2307
Create Date: 2026-11-15
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "20261115_2359"
down_revision: str | Sequence[str] | None = ("20261115_1902", "20261115_2307")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
