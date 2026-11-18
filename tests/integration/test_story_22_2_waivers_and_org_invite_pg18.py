"""Story 22.2 (Couche 2) — Vertical HTTP -> PostgreSQL 18 integration tests."""

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

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_story_22_2"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_22_2_pw"  # pragma: allowlist secret
ROOT_ENTERPRISE_ID = "0192c4e0-0000-7000-8000-000000000001"


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
        subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-22-2-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-22-2-vault-key-0001")
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
async def test_story_22_2_waivers_and_root_enterprise_invite_pg18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Verify PG18 vertical persistence for exception waivers & ENTERPRISE root invitations."""
    admin_headers = {"X-Orcia-Persona": "karim"}
    admin_params = {"persona_key": "karim"}
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            # 0. Day-0 Platform Admin in PG18 `users`
            r_first = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.222@orcia.ia",
                    "display_name": "Admin 22.2",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text

            # 1. Create Workspace -> UUIDv7 persisted in PG18
            r_ws = await client.post(
                "/api/v1/workspaces",
                headers=admin_headers,
                params=admin_params,
                json={
                    "name": "Espace 22.2 PG18",
                    "slug": "espace-22-2-pg18",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]
            UUID(ws_id)

            # 2. POST & GET /api/v1/workspaces/{uuid}/exception-waivers
            waiver_reason = "Dérogation validée pour migration PG18 Story 22.2"
            r_post_waiver = await client.post(
                f"/api/v1/workspaces/{ws_id}/exception-waivers",
                headers=admin_headers,
                params=admin_params,
                json={
                    "source_uri": "orcia://workspaces/espace-22-2-pg18/sources/rfc.md",
                    "source_sha256": "sha256:22200000abcdef",
                    "conflict_rule_id": "RULE_FRESHNESS_DRIFT",
                    "norm_level": "3_WORKSPACE",
                    "dna_chain": [
                        {
                            "node_key": "norm-freshness",
                            "stereotype": "NORM",
                            "level": "3_WORKSPACE",
                            "inviolable": False,
                        }
                    ],
                    "reason": waiver_reason,
                    "ttl_days": 30,
                },
            )
            assert r_post_waiver.status_code == 200, r_post_waiver.text
            waiver_id = r_post_waiver.json()["waiver_id"]
            assert r_post_waiver.json()["status"] == "ACTIVE"

            r_get_waivers = await client.get(
                f"/api/v1/workspaces/{ws_id}/exception-waivers",
                headers=admin_headers,
                params=admin_params,
            )
            assert r_get_waivers.status_code == 200, r_get_waivers.text
            assert any(w["waiver_id"] == waiver_id for w in r_get_waivers.json())

            # 3. Invite user directly on ENTERPRISE root under PLATFORM_ADMIN
            invited_email = "root.invite.222@orcia.ia"
            r_invite = await client.post(
                "/api/v1/org-units/invite-user",
                headers=admin_headers,
                params=admin_params,
                json={
                    "target_org_unit_id": ROOT_ENTERPRISE_ID,
                    "email": invited_email,
                    "display_name": "Root Invited 22.2",
                    "assignment_role": "CONTRIBUTOR",
                },
            )
            assert r_invite.status_code == 200, r_invite.text
            assert r_invite.json()["effective_roles"] == ["CONTRIBUTOR"]
            assert r_invite.json()["target_org_unit_id"] in {
                ROOT_ENTERPRISE_ID,
                "0192c4e0-0000-7000-8000-000000000101",
            }

        # 4. Restart simulation: fresh FastAPI app reads waivers from PG18
        async with app_client_factory() as fresh_client:
            r_five_tabs = await fresh_client.get(
                f"/api/v1/workspaces/{ws_id}/five-tabs",
                headers=admin_headers,
                params=admin_params,
            )
            assert r_five_tabs.status_code == 200, r_five_tabs.text
            assert any(w["waiver_id"] == waiver_id for w in r_five_tabs.json()["active_waivers"])

        # 5. Direct PostgreSQL 18 SELECT checks
        async with engine.connect() as conn:
            waiver_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT waiver_id, reason, status "
                            "FROM workspace_exception_waivers "
                            "WHERE workspace_id = CAST(:ws_id AS uuid)"
                        ),
                        {"ws_id": ws_id},
                    )
                )
                .mappings()
                .one()
            )
            assert str(waiver_row["waiver_id"]) == waiver_id
            assert waiver_row["reason"] == waiver_reason
            assert waiver_row["status"] == "ACTIVE"

            iam_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT principal_id, email, status "
                            "FROM iam_accounts WHERE lower(email) = lower(:email)"
                        ),
                        {"email": invited_email},
                    )
                )
                .mappings()
                .one()
            )
            assert iam_row["email"] == invited_email
            assert iam_row["status"] == "ACTIVE"

            user_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT email, platform_role, must_change_password "
                            "FROM users WHERE lower(email) = lower(:email)"
                        ),
                        {"email": invited_email},
                    )
                )
                .mappings()
                .one()
            )
            assert user_row["email"] == invited_email
            assert user_row["platform_role"] == "CONTRIBUTOR"
            assert bool(user_row["must_change_password"]) is True
    finally:
        await engine.dispose()
