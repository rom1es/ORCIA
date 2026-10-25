"""Layer 2 Real Ephemeral Container Integration Tests (`testcontainers-python`, AD-17).

Strictly no SQLite or in-memory Redis mocks: runs against real PostgreSQL 18 + pgvector,
Redis 7.4, and MinIO containers via `testcontainers-python`.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import time
from pathlib import Path

import pytest
import redis as redis_sync
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_s"


def _prepare_sock_dir(name: str) -> Path:
    unique = f"{name}_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    target = SOCK_BASE_DIR / unique
    target.mkdir(parents=True, exist_ok=True)
    target.chmod(0o777)
    return target


def _load_maintenance_module():
    import sys

    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "00_verify_db_invariants.py"
    spec = importlib.util.spec_from_file_location("verify_db_invariants", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


async def test_postgres18_pgvector_alembic_and_append_only_trigger() -> None:
    """Verify Alembic 0001 upgrade/downgrade, pgvector, and append-only trigger on PG 18."""
    pg_sock_dir = _prepare_sock_dir("pg")

    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
    )

    with pg_container as pg:
        wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
        sock_file = pg_sock_dir / ".s.PGSQL.5432"
        for _ in range(30):
            if sock_file.exists():
                break
            time.sleep(0.2)

        async_url = f"postgresql+asyncpg://orcia:orcia_dev_secret@/orcia?host={pg_sock_dir}"

        alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", async_url)

        engine = create_async_engine(async_url)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: (
                        alembic_cfg.attributes.__setitem__("connection", sync_conn),
                        command.upgrade(alembic_cfg, "head"),
                    )
                )

            # Verify maintenance script in dry-run (default rollback) and apply modes
            maint = _load_maintenance_module()
            dry_report = await maint.verify_database_invariants(engine, apply_changes=False)
            assert dry_report.has_vector_extension is True
            assert dry_report.has_append_only_trigger_fn is True
            assert dry_report.dry_run is True
            assert dry_report.committed is False

            apply_report = await maint.verify_database_invariants(engine, apply_changes=True)
            assert apply_report.committed is True

            # Verify append-only trigger blocks UPDATE and DELETE on PG 18
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "CREATE TABLE test_append_only_ledger ("
                        "id UUID PRIMARY KEY, payload TEXT NOT NULL, embedding vector(3));"
                    )
                )
                await conn.execute(
                    sa.text(
                        "CREATE TRIGGER trg_test_append_only "
                        "BEFORE UPDATE OR DELETE ON test_append_only_ledger "
                        "FOR EACH ROW EXECUTE FUNCTION orcia_prevent_append_only_mutation();"
                    )
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO test_append_only_ledger (id, payload, embedding) "
                        "VALUES ('0192c4e0-0000-7000-8000-000000000001', 'immutable', '[1,2,3]');"
                    )
                )

            with pytest.raises(DBAPIError, match="ERR_APPEND_ONLY_VIOLATION"):
                async with engine.begin() as conn:
                    await conn.execute(
                        sa.text("UPDATE test_append_only_ledger SET payload = 'mutated';")
                    )

            with pytest.raises(DBAPIError, match="ERR_APPEND_ONLY_VIOLATION"):
                async with engine.begin() as conn:
                    await conn.execute(sa.text("DELETE FROM test_append_only_ledger;"))

            # Verify downgrade and re-upgrade
            async with engine.begin() as conn:
                await conn.execute(sa.text("DROP TABLE test_append_only_ledger;"))
                await conn.run_sync(
                    lambda sync_conn: (
                        alembic_cfg.attributes.__setitem__("connection", sync_conn),
                        command.downgrade(alembic_cfg, "base"),
                        command.upgrade(alembic_cfg, "head"),
                    )
                )
        finally:
            await engine.dispose()
            shutil.rmtree(pg_sock_dir, ignore_errors=True)


def test_redis7_atomic_presence_lock_and_minio_container() -> None:
    """Verify atomic presence lock (`SET NX EX 900`, AD-4) on real Redis 7.4 and MinIO container."""
    redis_sock_dir = _prepare_sock_dir("rd")
    redis_sock_path = redis_sock_dir / "redis.sock"

    redis_container = (
        DockerContainer("redis:7.4.2-alpine")
        .with_volume_mapping(str(redis_sock_dir), "/sock", "rw")
        .with_command("redis-server --unixsocket /sock/redis.sock --unixsocketperm 777 --port 6379")
    )

    try:
        with redis_container as rc:
            wait_for_logs(rc, "Ready to accept connections", timeout=20)
            for _ in range(30):
                if redis_sock_path.exists():
                    break
                time.sleep(0.1)

            client = redis_sync.Redis(unix_socket_path=str(redis_sock_path), decode_responses=True)
            lock_key = "lock:step:0192c4e0-0000-7000-8000-000000000010"
            acquired_1 = client.set(lock_key, "user-alice", nx=True, ex=900)
            acquired_2 = client.set(lock_key, "user-bob", nx=True, ex=900)
            assert acquired_1 is True
            assert acquired_2 is None
            assert client.get(lock_key) == "user-alice"
            client.close()
    finally:
        shutil.rmtree(redis_sock_dir, ignore_errors=True)

    with (
        DockerContainer("minio/minio:RELEASE.2025-02-28T09-55-16Z")
        .with_env("MINIO_ROOT_USER", "orcia_minio")
        .with_env("MINIO_ROOT_PASSWORD", "orcia_minio_secret")
        .with_command("server /data") as minio_container
    ):
        wait_for_logs(minio_container, "API:", timeout=30)
        exit_code, _output = minio_container.exec("minio --version")
        assert exit_code == 0
