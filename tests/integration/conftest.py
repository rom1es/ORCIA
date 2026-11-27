"""Session-scoped PG18 + Redis + SeaweedFS fixtures with xdist worker isolation."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import redis
from tests.integration._shared_topology_fixture import (
    SharedIntegrationTopology,
    clone_worker_database_from_template,
    open_shared_integration_topology,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _flush_worker_redis(redis_url: str) -> None:
    client = redis.Redis.from_url(redis_url)
    try:
        client.flushdb()
    finally:
        client.close()


@pytest.fixture(scope="session")
def shared_integration_topology() -> Iterator[SharedIntegrationTopology]:
    """Boot session-scoped PG18, Redis 7.4, and SeaweedFS S3 isolated per xdist worker."""
    with open_shared_integration_topology() as topo:
        yield topo


@pytest.fixture
def isolated_worker_pg18_env(
    shared_integration_topology: SharedIntegrationTopology,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[SharedIntegrationTopology]:
    """Reset worker DB/Redis and configure worker-isolated PG18/Redis/S3 env vars."""
    topo = shared_integration_topology
    creds = "orcia:orcia_dev_secret"  # pragma: allowlist secret
    admin_sync_url = f"postgresql+psycopg://{creds}@/postgres?host={topo.pg_sock_dir}"
    clone_worker_database_from_template(
        admin_sync_url,
        template_db=topo.template_db,
        app_db_name=topo.app_db_name,
        dbos_db_name=topo.dbos_db_name,
    )
    _flush_worker_redis(topo.redis_url)
    bucket_name = f"{topo.s3_bucket_prefix}-cas"
    monkeypatch.setenv("DATABASE_URL", topo.async_database_url)
    monkeypatch.setenv("DBOS_SYSTEM_DATABASE_URL", topo.dbos_system_database_url)
    monkeypatch.setenv("REDIS_URL", topo.redis_url)
    monkeypatch.setenv("S3_ENDPOINT_URL", topo.s3_endpoint_url)
    monkeypatch.setenv("SEAWEEDFS_ENDPOINT_URL", topo.s3_endpoint_url)
    monkeypatch.setenv("ORCIA_SEAWEEDFS_ENDPOINT_URL", topo.s3_endpoint_url)
    monkeypatch.setenv("SEAWEEDFS_S3_ENDPOINT", topo.s3_endpoint_url)
    monkeypatch.setenv("S3_BUCKET_NAME", bucket_name)
    monkeypatch.setenv("ORCIA_S3_BUCKET", bucket_name)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(_REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    try:
        yield topo
    finally:
        _flush_worker_redis(topo.redis_url)
