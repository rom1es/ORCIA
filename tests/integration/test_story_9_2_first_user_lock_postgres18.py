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
    get_first_platform_admin_from_postgres18,
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
    """Validate `LOCK TABLE users IN EXCLUSIVE MODE`, DB lookup, and 1st-boot reset on PG 18."""
    import importlib.util

    reset_script_path = (
        REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
    )
    spec = importlib.util.spec_from_file_location("reset_db_first_boot", reset_script_path)
    assert spec is not None and spec.loader is not None
    reset_mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules["reset_db_first_boot"] = reset_mod
    spec.loader.exec_module(reset_mod)

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

                # Verify virgin database: COUNT(*) FROM users == 0 and lookup is None
                async with engine.connect() as conn:
                    cnt0 = await conn.execute(sa.text("SELECT COUNT(*) FROM users"))
                    assert int(cnt0.scalar_one()) == 0
                assert await get_first_platform_admin_from_postgres18(engine) is None

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

                # 3. Verify get_first_platform_admin_from_postgres18 returns the persisted winner
                persisted_admin = await get_first_platform_admin_from_postgres18(
                    engine, orcia_env="production"
                )
                assert persisted_admin is not None
                assert persisted_admin.email == winners[0].email
                assert persisted_admin.display_name == winners[0].display_name
                assert persisted_admin.platform_role == "PLATFORM_ADMIN"

                # 4. Verify 09_reset_db_first_boot.py dry-run rolls back and apply clears users
                dry_report = await reset_mod.reset_database_to_first_boot(
                    engine, apply_changes=False
                )
                assert dry_report.dry_run is True
                assert dry_report.committed is False
                assert await get_first_platform_admin_from_postgres18(engine) is not None

                apply_report = await reset_mod.reset_database_to_first_boot(
                    engine, apply_changes=True
                )
                assert apply_report.dry_run is False
                assert apply_report.committed is True
                assert apply_report.remaining_users_count == 0
                assert await get_first_platform_admin_from_postgres18(engine) is None
            finally:
                await engine.dispose()
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
