"""Unit tests for Epics 1 to 7 Vertical Persistence Wiring (`AD-17` Layer 1, `AD-19`)."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.main import create_app
from orcia_core.catalog import (
    SeaweedFsObjectStorageAdapter,
    SeaweedFsS3HttpBackend,
    build_s3_sigv4_headers,
)
from orcia_core.orchestration import (
    DbosDurableWorkflowEngine,
    DbosSqlAlchemyUnitOfWork,
    DurableWorkflowRunSummary,
    SqlDomainEventsOutboxRepository,
    SqlOrchestrationRepository,
)
from orcia_core.rag import SqlHybridRagRepository
from orcia_worker.dbos_workflow_runner import execute_durable_sql_workflow
from orcia_worker.outbox_relay import DbosOutboxRelay, DramatiqOutboxRelay


class _InMemoryS3Backend:
    """Deterministic S3 backend double for testing `SeaweedFsObjectStorageAdapter` wiring."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], tuple[bytes, str]] = {}

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.objects[(bucket, key)] = (data, content_type)

    def get_bytes(self, bucket: str, key: str) -> bytes | None:
        entry = self.objects.get((bucket, key))
        return entry[0] if entry is not None else None

    def head_key(self, bucket: str, key: str) -> bool:
        return (bucket, key) in self.objects


@pytest.mark.asyncio
async def test_epics_1_7_public_exports_and_seaweedfs_router_wiring() -> None:
    """Verify public `AD-19` re-exports and `SeaweedFsObjectStorageAdapter` wiring in `/catalog`."""
    assert SqlOrchestrationRepository is not None
    assert SqlDomainEventsOutboxRepository is not None
    assert DbosSqlAlchemyUnitOfWork is not None
    assert DbosDurableWorkflowEngine is not None
    assert DurableWorkflowRunSummary is not None
    assert SqlHybridRagRepository is not None
    assert SeaweedFsS3HttpBackend is not None
    assert callable(build_s3_sigv4_headers)
    assert callable(execute_durable_sql_workflow)
    assert hasattr(DramatiqOutboxRelay, "relay_sql_pending_batch")
    assert hasattr(DbosOutboxRelay, "relay_sql_pending_batch")

    app = create_app()
    s3_backend = _InMemoryS3Backend()
    seaweed = SeaweedFsObjectStorageAdapter(backend=s3_backend)
    app.state.seaweedfs_storage_adapter = seaweed

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resolve_res = await client.post(
            "/api/v1/catalog/resolve?persona_key=marc",
            json={"uri": "git://gitlab.entreprise.io/payments/checkout-web"},
        )
        assert resolve_res.status_code == 200
        resolved = resolve_res.json()
        sha256 = resolved["sha256"]
        assert ("orcia-cas", f"cas/{sha256}") in s3_backend.objects

        cas_res = await client.get(f"/api/v1/cas/{sha256}?persona_key=marc")
        assert cas_res.status_code == 200
        assert cas_res.json()["sha256"] == sha256


def test_litellm_gateway_resolution_when_env_configured() -> None:
    """Verify `initialize_app_services` wires `LiteLLMAdapter` when `ORCIA_LLM_GATEWAY=litellm`."""
    with patch.dict(os.environ, {"ORCIA_LLM_GATEWAY": "litellm"}):
        app = create_app()
        assert app.state.llm_gateway.__class__.__name__ == "LiteLLMAdapter"
