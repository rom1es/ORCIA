"""Session-scoped PG18/Redis/SeaweedFS topology and `flock` template cloning helpers."""

from __future__ import annotations

import fcntl
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import sqlalchemy as sa
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from tests.integration._shared_pg18_seeds_fixture import (
    ActivatedPackSlotsResult as ActivatedPackSlotsResult,
)
from tests.integration._shared_pg18_seeds_fixture import (
    SeededWorkspaceAdmin as SeededWorkspaceAdmin,
)
from tests.integration._shared_pg18_seeds_fixture import (
    activate_pack_with_slots as activate_pack_with_slots,
)
from tests.integration._shared_pg18_seeds_fixture import (
    seed_org_workspace_admin as seed_org_workspace_admin,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PG_CREDS = "orcia:orcia_dev_secret"  # pragma: allowlist secret
DEFAULT_TEMPLATE_DB = "orcia_template"


@dataclass(frozen=True, slots=True)
class SharedIntegrationTopology:
    """Isolated per-xdist-worker connection endpoints for PG18, DBOS, Redis, and SeaweedFS."""

    worker_id: str
    pg_sock_dir: Path
    template_db: str
    app_db_name: str
    dbos_db_name: str
    async_database_url: str
    sync_database_url: str
    dbos_system_database_url: str
    redis_url: str
    redis_db_index: int
    s3_endpoint_url: str
    s3_bucket_prefix: str


def resolve_worker_identity() -> tuple[str, int]:
    """Return `(worker_id, worker_index)` isolated for `pytest-xdist` (`gw0..gwN` or `master`)."""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master").strip() or "master"
    if worker_id.startswith("gw") and worker_id[2:].isdigit():
        return worker_id, int(worker_id[2:]) % 8
    return worker_id, 0


@contextmanager
def _acquire_file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _quote_pg_ident(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Invalid PostgreSQL identifier: {name!r}")
    return f'"{name}"'


def run_alembic_upgrade_head(pg_url: str) -> None:
    """Run Alembic `upgrade head` against `pg_url` with isolated environment."""
    alembic_bin = str(Path(sys.executable).with_name("alembic"))
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


def prepare_pg18_template_database(
    admin_sync_url: str,
    *,
    template_db: str = DEFAULT_TEMPLATE_DB,
    sock_dir: Path,
) -> None:
    """Create `template_db`, run Alembic `upgrade head`, dispose engines, and mark `IS_TEMPLATE`."""
    tpl_ident = _quote_pg_ident(template_db)
    admin_engine = sa.create_engine(admin_sync_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            conn.execute(sa.text(f"DROP DATABASE IF EXISTS {tpl_ident} WITH (FORCE)"))
            conn.execute(sa.text(f"CREATE DATABASE {tpl_ident}"))
    finally:
        admin_engine.dispose()

    tpl_async_url = f"postgresql+asyncpg://{PG_CREDS}@/{template_db}?host={sock_dir}"
    run_alembic_upgrade_head(tpl_async_url)

    finalize_engine = sa.create_engine(admin_sync_url, isolation_level="AUTOCOMMIT")
    try:
        with finalize_engine.connect() as conn:
            conn.execute(
                sa.text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :tpl AND pid <> pg_backend_pid()"
                ),
                {"tpl": template_db},
            )
            conn.execute(sa.text(f"ALTER DATABASE {tpl_ident} IS_TEMPLATE true"))
    finally:
        finalize_engine.dispose()


def clone_worker_database_from_template(
    admin_sync_url: str,
    *,
    template_db: str,
    app_db_name: str,
    dbos_db_name: str,
    lock_path: Path | None = None,
) -> None:
    """Serialize `CREATE DATABASE ... TEMPLATE` under `fcntl.flock` to prevent ObjectInUseError."""
    effective_lock = lock_path or Path("/tmp/orcia_pg18_template_clone.lock")
    app_ident = _quote_pg_ident(app_db_name)
    tpl_ident = _quote_pg_ident(template_db)
    dbos_ident = _quote_pg_ident(dbos_db_name)
    with _acquire_file_lock(effective_lock):
        engine = sa.create_engine(admin_sync_url, isolation_level="AUTOCOMMIT")
        try:
            with engine.connect() as conn:
                conn.execute(
                    sa.text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :tpl AND pid <> pg_backend_pid()"
                    ),
                    {"tpl": template_db},
                )
                conn.execute(sa.text(f"DROP DATABASE IF EXISTS {app_ident} WITH (FORCE)"))
                conn.execute(sa.text(f"CREATE DATABASE {app_ident} TEMPLATE {tpl_ident}"))
                conn.execute(sa.text(f"DROP DATABASE IF EXISTS {dbos_ident} WITH (FORCE)"))
                conn.execute(sa.text(f"CREATE DATABASE {dbos_ident}"))
        finally:
            engine.dispose()


@contextmanager
def open_shared_integration_topology() -> Iterator[SharedIntegrationTopology]:
    """Boot session PG18 + Redis 7.4 + SeaweedFS S3 and isolate DB/Redis/S3 per xdist worker."""
    os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
    worker_id, worker_idx = resolve_worker_identity()
    sock_dir = Path(tempfile.mkdtemp(prefix=f"orcia_shared_pg_{worker_id}_"))
    sock_dir.chmod(0o777)

    pg_box = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "postgres")
        .with_volume_mapping(str(sock_dir), "/var/run/postgresql", "rw")
    )
    redis_box = DockerContainer("redis:7.4.2-alpine").with_exposed_ports(6379)
    s3_box = (
        DockerContainer("chrislusf/seaweedfs:4.17")
        .with_command("server -s3 -s3.port=9000 -ip.bind=0.0.0.0 -dir=/tmp")
        .with_env("AWS_ACCESS_KEY_ID", "orcia_seaweed")
        .with_env("AWS_SECRET_ACCESS_KEY", "orcia_seaweed_secret")  # pragma: allowlist secret
        .with_exposed_ports(9000)
    )
    try:
        with pg_box as pg, redis_box as rc, s3_box as s3:
            for _ in range(150):
                out_b, err_b = pg.get_logs()
                logs = (out_b + err_b).decode("utf-8", errors="ignore")
                if (
                    logs.count("database system is ready to accept connections") >= 2
                    and (sock_dir / ".s.PGSQL.5432").exists()
                ):
                    break
                time.sleep(0.2)
            wait_for_logs(rc, "Ready to accept connections", timeout=20)
            wait_for_logs(s3, "Start Seaweed S3 API Server", timeout=30)

            admin_sync_url = f"postgresql+psycopg://{PG_CREDS}@/postgres?host={sock_dir}"
            prepare_pg18_template_database(
                admin_sync_url, template_db=DEFAULT_TEMPLATE_DB, sock_dir=sock_dir
            )
            app_db = f"orcia_test_{worker_id}"
            dbos_db = f"orcia_dbos_{worker_id}"
            clone_worker_database_from_template(
                admin_sync_url,
                template_db=DEFAULT_TEMPLATE_DB,
                app_db_name=app_db,
                dbos_db_name=dbos_db,
            )

            redis_port = int(rc.get_exposed_port(6379))
            s3_port = int(s3.get_exposed_port(9000))
            yield SharedIntegrationTopology(
                worker_id=worker_id,
                pg_sock_dir=sock_dir,
                template_db=DEFAULT_TEMPLATE_DB,
                app_db_name=app_db,
                dbos_db_name=dbos_db,
                async_database_url=f"postgresql+asyncpg://{PG_CREDS}@/{app_db}?host={sock_dir}",
                sync_database_url=f"postgresql+psycopg://{PG_CREDS}@/{app_db}?host={sock_dir}",
                dbos_system_database_url=f"postgresql://{PG_CREDS}@/{dbos_db}?host={sock_dir}",
                redis_url=f"redis://127.0.0.1:{redis_port}/{worker_idx}",
                redis_db_index=worker_idx,
                s3_endpoint_url=f"http://127.0.0.1:{s3_port}",
                s3_bucket_prefix=f"orcia-{worker_id}",
            )
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)
