"""Story 22.1 (Couche 2) — Vertical HTTP -> PostgreSQL 18 integration tests."""

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
DB_NAME = "orcia_story_22_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_22_1_pw"  # pragma: allowlist secret


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
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-22-1-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-22-1-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")

    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build_app_and_client():  # type: ignore[no-untyped-def]
        app = create_app()
        initialize_app_services(app)
        return app, AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build_app_and_client


@pytest.mark.asyncio
async def test_story_22_1_workspaces_datasources_gates_and_reflexive_pg18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    """Verify full vertical HTTP -> PostgreSQL 18 wiring for REM-01 & REM-02."""
    from orcia_core.permissions import UserIdentity

    admin_headers = {"X-Orcia-Persona": "karim"}
    admin_params = {"persona_key": "karim"}
    engine = create_async_engine(database_url)
    app, client = app_client_factory()
    try:
        async with client:
            # 0. Initialize Day-0 PLATFORM_ADMIN in PG18 `users`
            r_first = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.221@orcia.ia",
                    "display_name": "Admin 22.1",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text

            # 1. Create BU + Team via /api/v1/org-units
            r_bu = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                params=admin_params,
                json={"name": "Direction Comptabilité", "slug": "bu-compta", "kind": "BU"},
            )
            assert r_bu.status_code == 200, r_bu.text
            bu_id = r_bu.json()["id"]

            r_team = await client.post(
                "/api/v1/org-units",
                headers=admin_headers,
                params=admin_params,
                json={
                    "name": "Équipe Compta",
                    "slug": "team-compta",
                    "kind": "TEAM",
                    "parent_id": bu_id,
                },
            )
            assert r_team.status_code == 200, r_team.text
            team_id = r_team.json()["id"]

            # 2. Provision real OBSERVER user in IAM for negative 403 verification
            r_obs_user = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_headers,
                params=admin_params,
                json={
                    "principal_id": "observateur.221@orcia.ia",
                    "display_name": "Observateur 22.1",
                    "email": "observateur.221@orcia.ia",
                    "account_kind": "HUMAN",
                    "roles": ["OBSERVER"],
                },
            )
            assert r_obs_user.status_code == 200, r_obs_user.text
            obs_acc_id = r_obs_user.json()["id"]
            obs_user = UserIdentity(
                id=obs_acc_id,
                email="observateur.221@orcia.ia",
                display_name="Observateur 22.1",
                auth_mode="LOCAL",
                human_profile_archetype="OBSERVER",
                platform_role="OBSERVER",
                primary_org_unit_id=team_id,
                roles=("OBSERVER",),
            )
            app.state.auth_service.register_user(obs_user)
            obs_token = app.state.auth_service.jwt_manager.issue_token_pair(
                user_id=obs_user.id,
                email=obs_user.email,
                role="OBSERVER",
                org_unit_id=team_id,
                archetype="OBSERVER",
                auth_mode="LOCAL",
            ).access_token

            # 3. Create Workspace via POST /api/v1/workspaces -> returns UUIDv7 + exact slug
            r_ws = await client.post(
                "/api/v1/workspaces",
                headers=admin_headers,
                params=admin_params,
                json={
                    "name": "Espace E2E Comptabilité",
                    "slug": "espace-e2e-compta",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                    "owner_org_unit_id": team_id,
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_payload = r_ws.json()
            ws_uuid = ws_payload["id"]
            parsed_uuid = UUID(ws_uuid)
            assert parsed_uuid.version == 7
            assert ws_payload["slug"] == "espace-e2e-compta"
            assert ws_payload["effective_role"] == "PLATFORM_ADMIN"
            assert ws_payload["access_mode"] == "CONTRIBUTOR_ACTION_REQUIRED"

            # Verify PostgreSQL 18 tables directly (`workspaces` and `workspace_memberships`)
            async with engine.connect() as conn:
                ws_row = (
                    await conn.execute(
                        sa.text("SELECT id, slug FROM workspaces WHERE id = :id"),
                        {"id": parsed_uuid},
                    )
                ).first()
                assert ws_row is not None
                assert str(ws_row[0]) == ws_uuid
                assert ws_row[1] == "espace-e2e-compta"

                mem_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT role, access_mode FROM workspace_memberships "
                            "WHERE workspace_id = :ws_id AND role = 'PLATFORM_ADMIN'"
                        ),
                        {"ws_id": parsed_uuid},
                    )
                ).first()
                assert mem_row is not None
                assert mem_row[0] == "PLATFORM_ADMIN"
                assert mem_row[1] == "CONTRIBUTOR_ACTION_REQUIRED"

            # 4. Attach a Datasource via POST /api/v1/workspaces/{uuid}/datasources + SELECT PG18
            r_ds = await client.post(
                f"/api/v1/workspaces/{ws_uuid}/datasources",
                headers=admin_headers,
                params={"persona": "karim"},
                json={
                    "alias": "Repo Compta Git",
                    "scheme": "git",
                    "uri": "https://git.orcia.local/compta/ledger",
                    "sync_identity_mode": "SERVICE_ACCOUNT",
                },
            )
            assert r_ds.status_code == 201, r_ds.text

            async with engine.connect() as conn:
                ds_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT alias FROM workspace_datasources WHERE workspace_id = :ws_id"
                        ),
                        {"ws_id": parsed_uuid},
                    )
                ).first()
                assert ds_row is not None
                assert ds_row[0] == "Repo Compta Git"

            # 5. Evaluate Deterministic Gate & Reflexive Execution as PLATFORM_ADMIN (no 403!)
            r_gate = await client.post(
                "/api/v1/gates/deterministic/evaluate",
                headers=admin_headers,
                params=admin_params,
                json={
                    "workspace_id": ws_uuid,
                    "run_id": "0195f000-0000-7000-8000-000000009001",
                    "step_execution_id": "0195f000-0000-7000-8000-000000009002",
                    "step_key": "validate-ledger",
                    "artifact_payload": {"artifact": "ok", "summary": "valid"},
                    "required_sections": ["artifact"],
                },
            )
            assert r_gate.status_code == 200, r_gate.text

            r_reflexive = await client.post(
                "/api/v1/executions/reflexive",
                headers=admin_headers,
                params=admin_params,
                json={
                    "objective": "Analyser la conformité comptable",
                    "workspace_id": ws_uuid,
                },
            )
            assert r_reflexive.status_code in (200, 201), r_reflexive.text

            # 6. Explicit READ_ONLY_OBSERVER header & real OBSERVER user must get 403
            r_gate_hdr_obs = await client.post(
                "/api/v1/gates/deterministic/evaluate",
                headers={**admin_headers, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                params=admin_params,
                json={
                    "workspace_id": ws_uuid,
                    "run_id": "0195f000-0000-7000-8000-000000009001",
                    "step_execution_id": "0195f000-0000-7000-8000-000000009002",
                    "step_key": "validate-ledger",
                    "artifact_payload": {"artifact": "ok"},
                },
            )
            assert r_gate_hdr_obs.status_code == 403
            assert r_gate_hdr_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            r_refl_hdr_obs = await client.post(
                "/api/v1/executions/reflexive",
                headers={**admin_headers, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                params=admin_params,
                json={"objective": "Bloqué en mode observateur", "workspace_id": ws_uuid},
            )
            assert r_refl_hdr_obs.status_code == 403
            assert r_refl_hdr_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            # Real OBSERVER user (authenticated JWT with role OBSERVER)
            obs_headers = {"Authorization": f"Bearer {obs_token}"}
            r_gate_obs = await client.post(
                "/api/v1/gates/deterministic/evaluate",
                headers=obs_headers,
                json={
                    "workspace_id": ws_uuid,
                    "run_id": "0195f000-0000-7000-8000-000000009001",
                    "step_execution_id": "0195f000-0000-7000-8000-000000009002",
                    "step_key": "validate-ledger",
                    "artifact_payload": {"artifact": "ok"},
                },
            )
            assert r_gate_obs.status_code == 403
            assert r_gate_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            r_refl_obs = await client.post(
                "/api/v1/executions/reflexive",
                headers=obs_headers,
                json={"objective": "Observateur réel", "workspace_id": ws_uuid},
            )
            assert r_refl_obs.status_code == 403
            assert r_refl_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
    finally:
        await engine.dispose()
