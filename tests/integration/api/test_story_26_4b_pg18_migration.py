"""Story 26.4b — PG18 Alembic Migration `20261122_264b` Reversibility & Schema Tests."""

from __future__ import annotations

import subprocess

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._pg18_story_26_4b_helpers import REPO_ROOT, pg18_db_url

__all__ = ["pg18_db_url"]


@pytest.mark.asyncio
async def test_alembic_26_4b_reversibility_and_no_mode_b_or_draft_tables(pg18_db_url: str) -> None:
    """Verify linear 26.4b migration upgrade/downgrade/upgrade & absence of Mode B/drafts tables."""
    alembic_bin = str(REPO_ROOT / ".venv/bin/alembic")
    env = {
        "PATH": "/usr/bin:/bin",
        "DATABASE_URL": pg18_db_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    heads_out = subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "heads"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert len([line for line in heads_out.splitlines() if line.strip()]) == 1
    history_out = subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "history"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "20261122_264b" in history_out

    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "downgrade", "20261122_264a"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )

    engine = create_async_engine(pg18_db_url)
    try:
        async with engine.connect() as conn:
            fb_tbl = (
                await conn.execute(sa.text("SELECT to_regclass('public.assistant_turn_feedback')"))
            ).scalar()
            assert fb_tbl is not None
            assert (
                await conn.execute(sa.text("SELECT to_regclass('public.assistant_studio_graphs')"))
            ).scalar() is None
            assert (
                await conn.execute(
                    sa.text("SELECT to_regclass('public.assistant_citation_drafts')")
                )
            ).scalar() is None
            cols = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name = 'assistant_folders'"
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert "working_attachments_uris" in cols
            assert "evidence_tags" in cols
    finally:
        await engine.dispose()
