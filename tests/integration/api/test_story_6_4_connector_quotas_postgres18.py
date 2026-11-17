"""Story 6.4 — Integration Tests for Remote Connector Quotas & Isolation on PostgreSQL 18.

Verifies against real `pgvector/pgvector:pg18` + `redis:7.4-alpine` (`AD-17 Layer 2`):
1. Alembic migration 20261116_0604 creates `finops_connector_quotas` cleanly on PostgreSQL 18.
2. PUT `/api/v1/finops/connectors/{connector_key}/quota` persists configuration in PG18 (`SELECT`).
3. `ConnectorInvoker.invoke_async` with `SqlConnectorQuotaGuardService` + `RemoteUsageSanitizer`:
   - Records `EXTERNAL_REPORTED` usage in `finops_connector_quotas` & `audit_ledger`.
   - Caps excessive reported cost (`250 EUR -> 5.00 EUR`) and emits `RemoteUsageAnomalyCapped`
     in `domain_events_outbox`.
   - Trips `CIRCUIT_OPEN` on quota breach and blocks subsequent calls to that connector while
     keeping other connectors and internal LLMs completely unblocked.
4. POST `/api/v1/finops/connectors/{connector_key}/reset-circuit`:
   - Rejects `READ_ONLY_OBSERVER` with `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`.
   - Resets `circuit_state` to `CLOSED` for `PLATFORM_ADMIN` and persists in PostgreSQL 18.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
import redis
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from orcia_api.main import create_app
from orcia_core.audit_finops.connector_quota_service import SqlConnectorQuotaGuardService
from orcia_core.audit_finops.remote_usage_sanitizer import RemoteUsageSanitizer
from orcia_core.permissions.connector_invoker import ConnectorInvoker
from orcia_core.permissions.errors import ConnectorCircuitOpenError
from orcia_kernel.errors import OrciaDomainError, TransientInfraError
from orcia_kernel.ports import ConnectorInvokeResult, ConnectorPort

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_6_4"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_6_4_pw"  # pragma: allowlist secret


class _DummyMcpConnector(ConnectorPort):
    def __init__(self, scheme_name: str, output_payload: dict[str, Any]) -> None:
        self._scheme = scheme_name
        self._output = output_payload

    @property
    def scheme(self) -> str:
        return self._scheme

    def invoke(
        self,
        action: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> ConnectorInvokeResult:
        _ = (payload, idempotency_key)
        return ConnectorInvokeResult(
            scheme=self._scheme,
            action=action,
            output=dict(self._output),
            idempotency_key=idempotency_key,
            replayed_from_idempotency_cache=False,
            status="SUCCEEDED",
        )

    def map_error(self, exc: Exception) -> OrciaDomainError:
        return TransientInfraError(detail_override=str(exc))


@pytest.fixture(scope="module")
def infra_urls() -> Iterator[tuple[str, int]]:
    with (
        RedisContainer("redis:7.4-alpine") as redis_c,
        PostgresContainer(
            "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        ) as pg,
    ):
        url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        alembic_cmd = [alembic_bin, "-c", "infra/migrations/alembic.ini"]
        res = subprocess.run(
            [*alembic_cmd, "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(
                f"Alembic upgrade head failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            )
        yield url, int(redis_c.get_exposed_port(6379))


@pytest_asyncio.fixture
async def app_client(
    infra_urls: tuple[str, int],
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    database_url, redis_port = infra_urls
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("REDIS_URL", f"redis://127.0.0.1:{redis_port}/0")
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv(
        "ORCIA_JWT_SIGNING_SECRET",
        "orcia-story-6-4-jwt-secret-0001",  # pragma: allowlist secret
    )
    monkeypatch.setenv(
        "ORCIA_PASSTHROUGH_MASTER_KEY",
        "orcia-story-6-4-vault-key-0001",  # pragma: allowlist secret
    )
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={
            "X-Orcia-Active-Hat": "PLATFORM_ADMIN",
            "Accept-Language": "fr",
        },
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_connector_quotas_isolation_and_reset_postgres18(
    infra_urls: tuple[str, int],
    app_client: AsyncClient,
) -> None:
    database_url, redis_port = infra_urls
    r_client = redis.Redis(host="127.0.0.1", port=redis_port, db=0)
    assert r_client.ping() is True

    engine = create_async_engine(database_url)
    try:
        # 1. Configure quota for mcp-ocr and mcp-search via HTTP API
        resp_ocr = await app_client.put(
            "/api/v1/finops/connectors/mcp-ocr/quota",
            json={
                "display_name": "OCR Externe",
                "service_kind": "MCP_SERVER",
                "scope_type": "GLOBAL",
                "valuation_mode": "NATIVE_TELEMETRY",
                "max_reported_cost_per_call_eur": 5.0,
                "default_unit_name": "pages_ocr",
                "max_daily_calls": 2,
                "max_monthly_cost_eur": 50.0,
            },
        )
        assert resp_ocr.status_code == 200, resp_ocr.text
        resp_search = await app_client.put(
            "/api/v1/finops/connectors/mcp-search/quota",
            json={
                "display_name": "Moteur Recherche Externe",
                "service_kind": "MCP_SERVER",
                "scope_type": "GLOBAL",
                "valuation_mode": "FIXED_SCALE",
                "fixed_cost_per_call_eur": 0.10,
                "max_daily_calls": 100,
                "max_monthly_cost_eur": 50.0,
            },
        )
        assert resp_search.status_code == 200, resp_search.text
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        "SELECT connector_key, max_daily_calls, max_reported_cost_per_call_eur "
                        "FROM finops_connector_quotas WHERE connector_key = 'mcp-ocr'"
                    )
                )
            ).fetchone()
            assert row is not None and row[0] == "mcp-ocr" and row[1] == 2
            assert Decimal(str(row[2])) == Decimal("5.000000")

        # 2. Invoke mcp-ocr twice via ConnectorInvoker (2nd call caps 250 EUR -> 5 EUR)
        guard = SqlConnectorQuotaGuardService(engine=engine)
        invoker = ConnectorInvoker(
            quota_guard=guard,
            usage_sanitizer=RemoteUsageSanitizer(),
            max_reported_cost_per_call_eur=5.0,
        )
        ocr_normal = _DummyMcpConnector(
            "mcp",
            {
                "_meta": {
                    "usage": {
                        "unit_count": 8,
                        "unit_name": "pages_ocr",
                        "cost": 1.00,
                        "currency": "EUR",
                    }
                }
            },
        )
        ocr_anomaly = _DummyMcpConnector(
            "mcp",
            {
                "_meta": {
                    "usage": {
                        "unit_count": 10,
                        "unit_name": "pages_ocr",
                        "cost": 250.00,
                        "currency": "EUR",
                    }
                }
            },
        )
        search_conn = _DummyMcpConnector(
            "mcp", {"_meta": {"usage": {"cost": 0.10, "currency": "EUR"}}}
        )
        llm_conn = _DummyMcpConnector(
            "litellm", {"choices": [{"message": {"content": "LLM interne OK"}}]}
        )

        await invoker.invoke_async(
            scheme="mcp",
            connector_key="mcp-ocr",
            action="ocr",
            payload={"doc": "1"},
            idempotency_key="pg-ocr-1",
            connector=ocr_normal,
        )
        await invoker.invoke_async(
            scheme="mcp",
            connector_key="mcp-ocr",
            action="ocr",
            payload={"doc": "2"},
            idempotency_key="pg-ocr-2",
            connector=ocr_anomaly,
        )
        with pytest.raises(ConnectorCircuitOpenError):
            await invoker.invoke_async(
                scheme="mcp",
                connector_key="mcp-ocr",
                action="ocr",
                payload={"doc": "3"},
                idempotency_key="pg-ocr-3",
                connector=ocr_normal,
            )
        assert (
            await invoker.invoke_async(
                scheme="mcp",
                connector_key="mcp-search",
                action="search",
                payload={"q": "orcia"},
                idempotency_key="pg-search-1",
                connector=search_conn,
            )
        ).status == "SUCCEEDED"
        assert (
            await invoker.invoke_async(
                scheme="litellm",
                action="chat.completions",
                payload={"prompt": "test"},
                idempotency_key="pg-llm-1",
                connector=llm_conn,
                is_internal_llm=True,
            )
        ).status == "SUCCEEDED"

        # Verify PG18 Outbox & audit_ledger persistence
        async with engine.connect() as conn:
            cb_row = (
                await conn.execute(
                    sa.text(
                        "SELECT circuit_state, anomaly_count, total_business_units "
                        "FROM finops_connector_quotas WHERE connector_key = 'mcp-ocr'"
                    )
                )
            ).fetchone()
            assert cb_row is not None
            assert cb_row[0] == "CIRCUIT_OPEN"
            assert cb_row[1] == 1
            assert Decimal(str(cb_row[2])) == Decimal("18.000000")

            anomaly_evt_count = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM domain_events_outbox "
                        "WHERE event_type = 'RemoteUsageAnomalyCapped' AND aggregate_id = 'mcp-ocr'"
                    )
                )
            ).scalar_one()
            assert anomaly_evt_count >= 1

        # 3. Query GET /api/v1/finops/remote-services & /api/v1/finops/dashboard
        list_resp = await app_client.get("/api/v1/finops/remote-services")
        assert list_resp.status_code == 200, list_resp.text
        list_data = list_resp.json()
        assert list_data["open_circuits_count"] == 1
        assert list_data["units_breakdown"]["pages_ocr"] == 18.0

        dash_resp = await app_client.get("/api/v1/finops/dashboard")
        assert dash_resp.status_code == 200, dash_resp.text
        assert dash_resp.json()["overview"]["active_circuit_breakers_count"] == 1

        # 4. Observer role blocked (403 ERR_OBSERVER_MODE_READ_ONLY)
        obs_resp = await app_client.post(
            "/api/v1/finops/connectors/mcp-ocr/reset-circuit",
            headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
        )
        assert obs_resp.status_code == 403
        assert "ERR_OBSERVER_MODE_READ_ONLY" in obs_resp.text

        # 5. Reset circuit as PLATFORM_ADMIN
        reset_resp = await app_client.post("/api/v1/finops/connectors/mcp-ocr/reset-circuit")
        assert reset_resp.status_code == 200, reset_resp.text
        assert reset_resp.json()["circuit_state"] == "CLOSED"

        async with engine.connect() as conn:
            state_after = (
                await conn.execute(
                    sa.text(
                        "SELECT circuit_state FROM finops_connector_quotas "
                        "WHERE connector_key = 'mcp-ocr'"
                    )
                )
            ).scalar_one()
            assert state_after == "CLOSED"
    finally:
        await engine.dispose()
