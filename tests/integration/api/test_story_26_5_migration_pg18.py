"""Story 26.5 — PG18 Alembic Migration Reversibility & Day-0 Guard Tests (`20261122_265`)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import sqlalchemy as sa
from infra.scripts.maintenance._first_boot_reset_guards import ORDERED_MUTABLE_TABLES_TO_CLEAR
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._pg18_story_26_4b_helpers import pg18_db_url

__all__ = ["pg18_db_url"]
REPO_ROOT = Path(__file__).resolve().parents[3]


def _run_alembic(pg_url: str, *args: str) -> str:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    res = subprocess.run(
        [str(REPO_ROOT / ".venv/bin/alembic"), "-c", "infra/migrations/alembic.ini", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout


@pytest.mark.asyncio
async def test_story_26_5_migration_upgrade_downgrade_upgrade_and_reset_guard(
    pg18_db_url: str,
) -> None:
    """Verify `20261122_265` schema, index/constraint reversibility, and Day-0 reset allowlist."""
    assert "assistant_thread_messages" in ORDERED_MUTABLE_TABLES_TO_CLEAR
    assert ORDERED_MUTABLE_TABLES_TO_CLEAR.index(
        "assistant_thread_messages"
    ) < ORDERED_MUTABLE_TABLES_TO_CLEAR.index("assistant_threads")
    heads_out = _run_alembic(pg18_db_url, "heads").strip()
    assert len([ln for ln in heads_out.splitlines() if ln.strip()]) == 1
    assert "20261122_265" in _run_alembic(pg18_db_url, "history")

    engine = create_async_engine(pg18_db_url)
    try:
        async with engine.connect() as conn:
            exists_up = (
                await conn.execute(
                    sa.text("SELECT to_regclass('public.assistant_thread_messages')")
                )
            ).scalar_one()
            assert exists_up == "assistant_thread_messages"
            idx_exists = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_indexes "
                        "WHERE tablename = 'assistant_thread_messages' "
                        "AND indexname = 'idx_assistant_thread_messages_thread_created'"
                    )
                )
            ).scalar_one()
            assert idx_exists == 1

        _run_alembic(pg18_db_url, "downgrade", "20261122_264b")
        async with engine.connect() as conn:
            exists_down = (
                await conn.execute(
                    sa.text("SELECT to_regclass('public.assistant_thread_messages')")
                )
            ).scalar_one()
            assert exists_down is None

        _run_alembic(pg18_db_url, "upgrade", "head")
        async with engine.connect() as conn:
            exists_reup = (
                await conn.execute(
                    sa.text("SELECT to_regclass('public.assistant_thread_messages')")
                )
            ).scalar_one()
            assert exists_reup == "assistant_thread_messages"
            con_cnt = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM pg_constraint "
                        "WHERE conname = 'uq_assistant_thread_messages_turn_role'"
                    )
                )
            ).scalar_one()
            assert con_cnt == 1
    finally:
        await engine.dispose()
