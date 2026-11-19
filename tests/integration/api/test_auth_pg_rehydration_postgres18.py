"""Integration test for PostgreSQL 18 auth rehydration after RAM miss (`uvicorn --reload`).

Proves that:
1. When `AuthAndOrganizationService` RAM cache is wiped (simulating a server restart),
   valid sessions are seamlessly rehydrated from PostgreSQL 18.
2. `GET /api/v1/auth/session` (with refresh cookie) recovers active session (HTTP 200).
3. `GET /api/v1/org-units` and `GET /api/v1/settings/authentication` succeed with HTTP 200.
4. Deactivated users in PostgreSQL are rejected upon reload attempt.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_core.permissions import AuthAndOrganizationService

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_rehydrate_test"
DB_USER = "orcia"
DB_PASSWORD = "orcia_rehydrate_pw"  # pragma: allowlist secret
JWT_SECRET = "orcia-test-jwt-secret-rehydration-2026"  # pragma: allowlist secret
VAULT_KEY = "orcia-test-vault-secret-rehydration-2026"  # pragma: allowlist secret


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
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


def _build_app(database_url: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", JWT_SECRET)
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", VAULT_KEY)
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    monkeypatch.delenv("ORCIA_SEED_TEST_PERSONAS", raising=False)
    monkeypatch.delenv("ORCIA_E2E_SEED_FIXTURES", raising=False)
    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    app = create_app()
    initialize_app_services(app)
    return app


@pytest.mark.asyncio
async def test_auth_rehydration_after_uvicorn_reload_postgres18(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _build_app(database_url, monkeypatch)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        cookies={},
    ) as client:
        # 1. Initialize First Admin
        admin_email = "karim.admin@orcia.io"
        admin_pw = "OrciaAdmin!2026"  # pragma: allowlist secret
        init_res = await client.post(
            "/api/v1/bootstrap/welcome-setup/first-admin",
            json={
                "email": admin_email,
                "password": admin_pw,
                "display_name": "Karim Tech Lead",
            },
        )
        assert init_res.status_code == 200
        admin_id = init_res.json()["user_id"]
        assert admin_id

        # 2. Login to acquire Bearer JWT and Refresh Cookie
        login_res = await client.post(
            "/api/v1/auth/login/local",
            json={"email": admin_email, "password": admin_pw},
        )
        assert login_res.status_code == 200
        tokens = login_res.json()
        access_token = tokens["access_token"]
        bearer_header = {"Authorization": f"Bearer {access_token}"}
        refresh_cookie = client.cookies.get("orcia_refresh_token")
        assert refresh_cookie is not None

        # 3. Verify user is in memory
        auth_svc = app.state.auth_service
        assert isinstance(auth_svc, AuthAndOrganizationService)
        assert auth_svc.has_user_in_memory(admin_id) is True

        # =====================================================================
        # SIMULATE uvicorn --reload: Fresh Composition Root app (empty RAM)
        # =====================================================================
        app2 = _build_app(database_url, monkeypatch)
        assert app2.state.auth_service.has_user_in_memory(admin_id) is False

        async with AsyncClient(
            transport=ASGITransport(app=app2),
            base_url="http://testserver",
            cookies=client.cookies,
        ) as client2:
            # 4. GET /api/v1/auth/session with refresh cookie -> must rehydrate and return HTTP 200
            session_res = await client2.get("/api/v1/auth/session")
            assert session_res.status_code == 200
            session_body = session_res.json()
            assert session_body["authenticated"] is True
            assert session_body["session"] is not None
            assert session_body["session"]["email"] == admin_email
            assert session_body["session"]["platform_role"] == "PLATFORM_ADMIN"
            assert app2.state.auth_service.has_user_in_memory(admin_id) is True

        # =====================================================================
        # SIMULATE uvicorn --reload AGAIN before Bearer requests
        # =====================================================================
        app3 = _build_app(database_url, monkeypatch)
        assert app3.state.auth_service.has_user_in_memory(admin_id) is False

        async with AsyncClient(
            transport=ASGITransport(app=app3),
            base_url="http://testserver",
            cookies=client.cookies,
        ) as client3:
            # 5. GET /api/v1/org-units with Bearer token -> middleware must rehydrate from PG (200)
            orgs_res = await client3.get("/api/v1/org-units", headers=bearer_header)
            assert orgs_res.status_code == 200
            assert app3.state.auth_service.has_user_in_memory(admin_id) is True

        # =====================================================================
        # SIMULATE uvicorn --reload AGAIN before settings request
        # =====================================================================
        app4 = _build_app(database_url, monkeypatch)
        assert app4.state.auth_service.has_user_in_memory(admin_id) is False

        async with AsyncClient(
            transport=ASGITransport(app=app4),
            base_url="http://testserver",
            cookies=client.cookies,
        ) as client4:
            # 6. GET /api/v1/settings/authentication with Bearer token -> HTTP 200
            settings_res = await client4.get(
                "/api/v1/settings/authentication",
                headers=bearer_header,
            )
            assert settings_res.status_code == 200
            settings_body = settings_res.json()
            assert settings_body["auth_mode"] == "LOCAL"
            assert settings_body["boot_epoch"]
            assert app4.state.auth_service.has_user_in_memory(admin_id) is True

        # =====================================================================
        # DEACTIVATED USER TEST: user is marked inactive in PG
        # =====================================================================
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("UPDATE users SET is_active = FALSE WHERE id = :uid"),
                    {"uid": admin_id},
                )
        finally:
            await engine.dispose()

        # Fresh Composition Root app (empty RAM)
        app5 = _build_app(database_url, monkeypatch)
        assert app5.state.auth_service.has_user_in_memory(admin_id) is False

        async with AsyncClient(
            transport=ASGITransport(app=app5),
            base_url="http://testserver",
            cookies=client.cookies,
        ) as client5:
            # Session bootstrap must fail gracefully (authenticated: False, clears cookie)
            deact_session = await client5.get("/api/v1/auth/session")
            assert deact_session.status_code == 200
            assert deact_session.json()["authenticated"] is False
            assert deact_session.json()["session"] is None
            assert "Max-Age=0" in deact_session.headers.get("set-cookie", "")

        # Fresh Composition Root app again for Bearer check
        app6 = _build_app(database_url, monkeypatch)
        async with AsyncClient(
            transport=ASGITransport(app=app6),
            base_url="http://testserver",
        ) as client6:
            deact_orgs = await client6.get("/api/v1/org-units", headers=bearer_header)
            assert deact_orgs.status_code in (401, 403, 404)
