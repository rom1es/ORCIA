"""Shared `/tmp` socket & Alembic PG18 helpers for testcontainers (prevents `AF_UNIX` > 107 B)."""

from __future__ import annotations

import shutil
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs


def prepare_tc_sock_dir(prefix: str) -> Path:
    """Create a world-writable `/tmp` socket directory short enough for `AF_UNIX` sockets."""
    target = Path(tempfile.mkdtemp(prefix=f"orcia_{prefix}_"))
    target.chmod(0o777)
    return target


@contextmanager
def open_pg18_alembic_container(
    prefix: str, monkeypatch: pytest.MonkeyPatch, repo_root: Path
) -> Iterator[tuple[sa.Engine, Config]]:
    """Boot an ephemeral PG18 container over `/tmp` socket and yield `(engine, alembic_cfg)`."""
    monkeypatch.setenv("TESTCONTAINERS_RYUK_DISABLED", "true")
    sock_dir = prepare_tc_sock_dir(prefix)
    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(sock_dir), "/var/run/postgresql", "rw")
    )
    try:
        with pg_container as pg:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            sock_file = sock_dir / ".s.PGSQL.5432"
            for _ in range(50):
                if sock_file.exists():
                    break
                time.sleep(0.2)

            creds = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            sync_url = f"postgresql+psycopg://{creds}@/orcia?host={sock_dir}"
            monkeypatch.setenv("DATABASE_URL", sync_url)
            alembic_cfg = Config(str(repo_root / "infra" / "migrations" / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(repo_root / "infra" / "migrations"))
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)
            engine = sa.create_engine(sync_url)
            for _ in range(30):
                try:
                    with engine.connect() as conn:
                        conn.execute(sa.text("SELECT 1"))
                    break
                except Exception:
                    time.sleep(0.2)
            try:
                yield engine, alembic_cfg
            finally:
                engine.dispose()
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)
