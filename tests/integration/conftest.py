"""Session-scoped PG18 + Redis + SeaweedFS fixtures with xdist worker isolation."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from tests.integration._shared_topology_fixture import (
    SharedIntegrationTopology,
    clone_worker_database_from_template,
    open_shared_integration_topology,
)


@pytest.fixture(scope="session")
def shared_integration_topology() -> Iterator[SharedIntegrationTopology]:
    """Boot session-scoped PG18, Redis 7.4, and SeaweedFS S3 isolated per xdist worker."""
    with open_shared_integration_topology() as topo:
        yield topo


@pytest.fixture
def isolated_worker_pg18_env(
    shared_integration_topology: SharedIntegrationTopology,
    monkeypatch: pytest.MonkeyPatch,
) -> SharedIntegrationTopology:
    """Reset worker DB from `IS_TEMPLATE` and configure worker-isolated PG18/Redis/S3 env vars."""
    topo = shared_integration_topology
    creds = "orcia:orcia_dev_secret"  # pragma: allowlist secret
    admin_sync_url = f"postgresql+psycopg://{creds}@/postgres?host={topo.pg_sock_dir}"
    clone_worker_database_from_template(
        admin_sync_url,
        template_db=topo.template_db,
        app_db_name=topo.app_db_name,
        dbos_db_name=topo.dbos_db_name,
    )
    monkeypatch.setenv("DATABASE_URL", topo.async_database_url)
    monkeypatch.setenv("DBOS_SYSTEM_DATABASE_URL", topo.dbos_system_database_url)
    monkeypatch.setenv("REDIS_URL", topo.redis_url)
    monkeypatch.setenv("SEAWEEDFS_S3_ENDPOINT", topo.s3_endpoint_url)
    monkeypatch.setenv("ORCIA_S3_BUCKET", f"{topo.s3_bucket_prefix}-cas")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    return topo
