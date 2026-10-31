"""Real Container Integration Test for Story 9.2 (`testcontainers` PostgreSQL 18, `AD-17`).

Verifies that on a virgin PostgreSQL 18 database (`COUNT(*) FROM users == 0`), concurrent
requests to `create_first_platform_admin_on_postgres18` serialize via
`LOCK TABLE users IN EXCLUSIVE MODE` and create exactly 1 `PLATFORM_ADMIN` account,
while enforcing `ORCIA_BOOTSTRAP_TOKEN` when `ORCIA_ENV != 'local'`.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_core.bootstrap._internal.sql_first_user_guard import (
    create_first_platform_admin_on_postgres18,
)
from orcia_core.bootstrap.errors import (
    FirstUserAlreadyInitializedError,
    InvalidBootstrapTokenError,
)

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_9_2"


def _prepare_sock_dir(name: str) -> Path:
    unique = f"{name}_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    target = SOCK_BASE_DIR / unique
    target.mkdir(parents=True, exist_ok=True)
    target.chmod(0o777)
    return target


@pytest.mark.asyncio
async def test_story_9_2_postgres18_exclusive_users_table_lock_under_concurrency() -> None:
    """Validate `LOCK TABLE users IN EXCLUSIVE MODE` on real PostgreSQL 18 under concurrency."""
    pg_sock_dir = _prepare_sock_dir("pg18_9_2")
    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
    )

    try:
        with pg_container as pg:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            sock_file = pg_sock_dir / ".s.PGSQL.5432"
            for _ in range(40):
                if sock_file.exists():
                    break
                time.sleep(0.2)

            creds = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            async_app_url = f"postgresql+asyncpg://{creds}@/orcia?host={pg_sock_dir}"

            alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
            alembic_cfg.set_main_option("sqlalchemy.url", async_app_url)

            engine = create_async_engine(async_app_url, pool_size=5, max_overflow=5)
            try:
                for _ in range(30):
                    try:
                        async with engine.connect() as conn:
                            await conn.execute(sa.text("SELECT 1"))
                        break
                    except Exception:
                        await asyncio.sleep(0.2)

                async with engine.begin() as conn:
                    await conn.run_sync(
                        lambda sync_conn: (
                            alembic_cfg.attributes.__setitem__("connection", sync_conn),
                            command.upgrade(alembic_cfg, "head"),
                        )
                    )

                # Verify virgin database: COUNT(*) FROM users == 0
                async with engine.connect() as conn:
                    cnt0 = await conn.execute(sa.text("SELECT COUNT(*) FROM users"))
                    assert int(cnt0.scalar_one()) == 0

                dummy_hash = "argon2id$test"  # pragma: allowlist secret

                # 1. Invalid token on non-local env raises 403 ERR_INVALID_BOOTSTRAP_TOKEN
                with pytest.raises(InvalidBootstrapTokenError):
                    await create_first_platform_admin_on_postgres18(
                        engine,
                        email="intruder@orcia.io",
                        display_name="Intruder",
                        password_hash=dummy_hash,
                        orcia_env="production",
                        expected_bootstrap_token="secret-prod-token",
                        provided_bootstrap_token="wrong-token",
                    )

                # 2. Fire 3 concurrent transactions with valid token on virgin users table
                results = await asyncio.gather(
                    create_first_platform_admin_on_postgres18(
                        engine,
                        email="karim1@orcia.io",
                        display_name="Karim 1",
                        password_hash=dummy_hash,
                        orcia_env="production",
                        expected_bootstrap_token="secret-prod-token",
                        provided_bootstrap_token="secret-prod-token",
                    ),
                    create_first_platform_admin_on_postgres18(
                        engine,
                        email="karim2@orcia.io",
                        display_name="Karim 2",
                        password_hash=dummy_hash,
                        orcia_env="production",
                        expected_bootstrap_token="secret-prod-token",
                        provided_bootstrap_token="secret-prod-token",
                    ),
                    create_first_platform_admin_on_postgres18(
                        engine,
                        email="karim3@orcia.io",
                        display_name="Karim 3",
                        password_hash=dummy_hash,
                        orcia_env="production",
                        expected_bootstrap_token="secret-prod-token",
                        provided_bootstrap_token="secret-prod-token",
                    ),
                    return_exceptions=True,
                )

                winners = [r for r in results if not isinstance(r, BaseException)]
                losers = [r for r in results if isinstance(r, FirstUserAlreadyInitializedError)]
                assert len(winners) == 1
                assert len(losers) == 2

                async with engine.connect() as conn:
                    cnt1 = await conn.execute(sa.text("SELECT COUNT(*) FROM users"))
                    assert int(cnt1.scalar_one()) == 1
            finally:
                await engine.dispose()
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
