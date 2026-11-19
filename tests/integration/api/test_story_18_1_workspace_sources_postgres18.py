"""Story 18.1 — Vertical HTTP -> PostgreSQL 18 Integration Tests for Workspace Sources.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261114_1801` idempotency (`upgrade head` -> `downgrade` -> `upgrade`).
2. Vertical CRUD operations on `/api/v1/workspaces/{workspace_id}/datasources`.
3. RBAC Observer Guard (`403 ERR_OBSERVER_MODE_READ_ONLY`) on write operations.
4. RBAC Codegraph Lead Guard (`403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED`) on activation.
5. Trigger sync endpoint `/api/v1/workspaces/{workspace_id}/datasources/{datasource_id}/sync`.
6. Direct PostgreSQL 18 verification (`SELECT` on `workspace_datasources` columns).
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_18_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_18_1_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
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
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261114_1801
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261114_1705"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-18-1-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-18-1-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build_client() -> AsyncClient:
        app = create_app()
        initialize_app_services(app)
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build_client


@pytest.mark.asyncio
async def test_workspace_sources_multi_nature_and_codegraph_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    headers_lead = {"X-Orcia-Persona": "karim"}
    headers_contributor = {"X-Orcia-Persona": "nadia"}
    headers_observer = {
        "X-Orcia-Persona": "partenaire",
        "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER",
    }

    ws_id = str(UUID(new_uuid7_str()))

    # 1. Ensure workspace exists in PG18
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        res = await conn.execute(sa.text("SELECT id FROM org_units LIMIT 1;"))
        row = res.fetchone()
        if row:
            ou_id = row[0]
        else:
            ou_id = UUID(new_uuid7_str())
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type) "
                    "VALUES (:id, 'test-ou', 'Test OU', 'TEAM') "
                    "ON CONFLICT (id) DO NOTHING;"
                ),
                {"id": ou_id},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (:id, :slug, :name, :ou_id, 'STANDARD') "
                "ON CONFLICT (id) DO NOTHING;"
            ),
            {
                "id": UUID(ws_id),
                "name": "Workspace 18-1 Test",
                "slug": f"ws-{ws_id[:8]}",
                "ou_id": ou_id,
            },
        )
        check = (
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE id = :wid"),
                {"wid": UUID(ws_id)},
            )
        ).scalar()
        assert check is not None, f"Workspace {ws_id} not found immediately after insert!"

    async with app_client_factory() as client:
        # 2. Contributor attaches a SOURCE_CODE datasource (codegraph_enabled=False)
        create_payload = {
            "alias": "Microservices Core Repo",
            "scheme": "git",
            "uri": "https://gitlab.corp.local/core/backend.git",
            "source_nature": "SOURCE_CODE",
            "sync_mode": "WEBHOOK_PUSH",
            "target_scope": "services/api",
            "target_ref": "main",
            "codegraph_enabled": False,
        }
        resp = await client.post(
            f"/api/v1/workspaces/{ws_id}/datasources",
            json=create_payload,
            headers=headers_contributor,
        )
        assert resp.status_code == 201, resp.text
        created = resp.json()
        ds_id = created["id"]
        assert created["alias"] == "Microservices Core Repo"
        assert created["source_nature"] == "SOURCE_CODE"
        assert created["sync_mode"] == "WEBHOOK_PUSH"
        assert created["target_scope"] == "services/api"
        assert created["target_ref"] == "main"
        assert created["codegraph_enabled"] is False
        assert created["codegraph_status"] == "DISABLED"

        # 3. Contributor tries to enable codegraph -> 403 ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED
        resp_forbidden = await client.patch(
            f"/api/v1/workspaces/{ws_id}/datasources/{ds_id}",
            json={"codegraph_enabled": True},
            headers=headers_contributor,
        )
        assert resp_forbidden.status_code == 403
        problem = resp_forbidden.json()
        assert problem["error_code"] == "ERR_CODEGRAPH_WORKSPACE_LEAD_REQUIRED"

        # 4. Lead persona enables codegraph -> succeeds and sets codegraph_status
        resp_lead = await client.patch(
            f"/api/v1/workspaces/{ws_id}/datasources/{ds_id}",
            json={
                "codegraph_enabled": True,
                "codegraph_auth_mode": "SERVICE_ACCOUNT",
            },
            headers=headers_lead,
        )
        assert resp_lead.status_code == 200, resp_lead.text
        updated = resp_lead.json()
        assert updated["codegraph_enabled"] is True
        assert updated["codegraph_status"] in ("READY", "INDEXING")

        # 5. Trigger sync endpoint
        resp_sync = await client.post(
            f"/api/v1/workspaces/{ws_id}/datasources/{ds_id}/sync",
            headers=headers_lead,
        )
        assert resp_sync.status_code == 200, resp_sync.text
        sync_result = resp_sync.json()
        assert sync_result["datasource"]["id"] == ds_id
        assert sync_result["datasource"]["freshness_status"] == "SYNCED"
        assert sync_result["datasource"]["last_sync_at_iso"] is not None

        # 6. Observer cannot trigger sync or delete -> 403 ERR_OBSERVER_MODE_READ_ONLY
        resp_obs_sync = await client.post(
            f"/api/v1/workspaces/{ws_id}/datasources/{ds_id}/sync",
            headers=headers_observer,
        )
        assert resp_obs_sync.status_code == 403
        assert resp_obs_sync.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        resp_obs_delete = await client.delete(
            f"/api/v1/workspaces/{ws_id}/datasources/{ds_id}",
            headers=headers_observer,
        )
        assert resp_obs_delete.status_code == 403
        assert resp_obs_delete.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 7. Direct SELECT on PostgreSQL 18 verifying state persistence
        async with engine.connect() as conn:
            row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT source_nature, sync_mode, target_scope, target_ref, "
                            "codegraph_enabled, codegraph_status, freshness_status "
                            "FROM workspace_datasources WHERE id = :id"
                        ),
                        {"id": UUID(ds_id)},
                    )
                )
                .mappings()
                .first()
            )
            assert row is not None
            assert row["source_nature"] == "SOURCE_CODE"
            assert row["sync_mode"] == "WEBHOOK_PUSH"
            assert row["target_scope"] == "services/api"
            assert row["target_ref"] == "main"
            assert row["codegraph_enabled"] is True
            assert row["freshness_status"] == "SYNCED"

        # 8. Lead persona deletes datasource -> 200/204
        resp_delete = await client.delete(
            f"/api/v1/workspaces/{ws_id}/datasources/{ds_id}",
            headers=headers_lead,
        )
        assert resp_delete.status_code in (200, 204)

        # 9. Verify deletion in PostgreSQL 18
        async with engine.connect() as conn:
            deleted_row = (
                await conn.execute(
                    sa.text("SELECT id FROM workspace_datasources WHERE id = :id"),
                    {"id": UUID(ds_id)},
                )
            ).first()
            assert deleted_row is None

    await engine.dispose()
