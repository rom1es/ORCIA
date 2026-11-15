"""Vertical HTTP -> PostgreSQL 18 Integration Tests for Local IAM Auth,

Temporary Passwords (12 chars), and Cookie-based Logout.
"""

from __future__ import annotations

import os
import re
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

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_temp_pwd_test"
DB_USER = "orcia"
DB_PASSWORD = "orcia_temp_pwd_pw"  # pragma: allowlist secret


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
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-test-jwt-secret-key-1234")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-test-vault-secret-key-1234")
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
async def test_first_admin_accostage_issues_tokens_and_cookie_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM role_permission_grants"))
        await conn.execute(sa.text("DELETE FROM iam_accounts"))
        await conn.execute(sa.text("DELETE FROM users"))

    client: AsyncClient = app_client_factory()
    async with client:
        res = await client.post(
            "/api/v1/bootstrap/welcome-setup/first-admin",
            json={
                "display_name": "Romain SuperAdmin",
                "email": "romain.admin@orcia.fr",
                "password": "PasswordAdmin123!",  # pragma: allowlist secret
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["email"] == "romain.admin@orcia.fr"
        assert data["platform_role"] == "PLATFORM_ADMIN"
        assert data["access_token"] is not None
        assert "orcia_refresh_token" in res.cookies

        # Direct SQL verification in PostgreSQL 18
        async with engine.connect() as conn:
            user_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT email, must_change_password, auth_mode "
                            "FROM users WHERE email = :e"
                        ),
                        {"e": "romain.admin@orcia.fr"},
                    )
                )
                .mappings()
                .first()
            )
            assert user_row is not None
            assert user_row["must_change_password"] is False
            assert user_row["auth_mode"] == "LOCAL"


@pytest.mark.asyncio
async def test_human_iam_account_creation_temp_password_and_login_lifecycle_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    client: AsyncClient = app_client_factory()
    headers = {"X-Orcia-Persona": "karim"}

    async with client:
        # 1. Create a HUMAN account via IAM endpoint
        create_res = await client.post(
            "/api/v1/settings/iam/accounts",
            headers=headers,
            json={
                "account_kind": "HUMAN",
                "display_name": "Claire Martin",
                "email": "claire.martin@orcia.fr",
                "principal_id": "claire.martin@orcia.fr",
                "roles": ["CONTRIBUTOR"],
                "team_ids": [],
                "status": "ACTIVE",
            },
        )
        assert create_res.status_code == 200, create_res.text
        create_data = create_res.json()
        temp_password = create_data["temporary_password"]  # pragma: allowlist secret
        assert temp_password is not None
        assert len(temp_password) == 12
        assert re.match(r"^[a-zA-Z0-9]{12}$", temp_password) is not None
        account_id = create_data["id"]

        # 2. Direct SQL verify in PostgreSQL 18: user created with must_change_password = True
        engine = create_async_engine(database_url)
        async with engine.connect() as conn:
            user_row = (
                (
                    await conn.execute(
                        sa.text("SELECT email, must_change_password FROM users WHERE email = :e"),
                        {"e": "claire.martin@orcia.fr"},
                    )
                )
                .mappings()
                .first()
            )
            assert user_row is not None
            assert user_row["must_change_password"] is True

        # 3. Login with generated temporary password
        login_res = await client.post(
            "/api/v1/auth/login/local",
            json={"email": "claire.martin@orcia.fr", "password": temp_password},
        )
        assert login_res.status_code == 200, login_res.text
        login_data = login_res.json()
        assert login_data["must_change_password"] is True
        token = login_data["access_token"]
        assert "orcia_refresh_token" in login_res.cookies

        # 4a. Wrong current password rejected with ERR_AUTH_CURRENT_PASSWORD_INVALID (422)
        auth_headers = {"Authorization": f"Bearer {token}"}
        wrong_curr_res = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "WrongCurrentPassword123",  # pragma: allowlist secret
                "new_password": "NewValidPassword2026",  # pragma: allowlist secret
            },
        )
        assert wrong_curr_res.status_code == 422
        wrong_body = wrong_curr_res.json()
        assert wrong_body["error_code"] == "ERR_AUTH_CURRENT_PASSWORD_INVALID"
        assert "OIDC" not in wrong_body.get("detail", "")
        assert "e-mail" not in wrong_body.get("detail", "").lower()

        # 4b. Same password rejected
        unchanged_res = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": temp_password, "new_password": temp_password},
        )
        assert unchanged_res.status_code == 422
        assert unchanged_res.json()["error_code"] == "ERR_AUTH_PASSWORD_UNCHANGED"

        # 5. Weak password rejected
        weak_res = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": temp_password,
                "new_password": "weak",  # pragma: allowlist secret
            },
        )
        assert weak_res.status_code == 422
        assert weak_res.json()["error_code"] == "ERR_AUTH_WEAK_PASSWORD"

        # 6. Valid new strong password succeeds
        new_pwd = "ClaireSecurePass2026"  # pragma: allowlist secret
        change_res = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={"current_password": temp_password, "new_password": new_pwd},
        )
        assert change_res.status_code == 200, change_res.text
        assert change_res.json()["must_change_password"] is False

        # Direct SQL verify must_change_password is now False
        async with engine.connect() as conn:
            updated_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT must_change_password, password_changed_at "
                            "FROM users WHERE email = :e"
                        ),
                        {"e": "claire.martin@orcia.fr"},
                    )
                )
                .mappings()
                .first()
            )
            assert updated_row is not None
            assert updated_row["must_change_password"] is False
            assert updated_row["password_changed_at"] is not None

        # 7. Regenerate temporary password via IAM admin endpoint
        regen_res = await client.post(
            f"/api/v1/settings/iam/accounts/{account_id}/temporary-password",
            headers=headers,
        )
        assert regen_res.status_code == 200, regen_res.text
        regen_data = regen_res.json()
        assert len(regen_data["temporary_password"]) == 12
        assert regen_data["must_change_password"] is True
        new_temp_pwd = regen_data["temporary_password"]

        # 8. Test RAM/PG desync: temporary password was regenerated in PG 18 while in-memory
        # session held Claire's previous password hash. hydrate_user_identity_from_pg pulls
        # the fresh hash from PG 18 so changing password with new_temp_pwd succeeds!
        desync_change_res = await client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": new_temp_pwd,
                "new_password": "ClaireFinalSecurePass2026",  # pragma: allowlist secret
            },
        )
        assert desync_change_res.status_code == 200, desync_change_res.text
        assert desync_change_res.json()["must_change_password"] is False

        # Direct SQL verify must_change_password is False again
        async with engine.connect() as conn:
            final_row = (
                (
                    await conn.execute(
                        sa.text("SELECT must_change_password FROM users WHERE email = :e"),
                        {"e": "claire.martin@orcia.fr"},
                    )
                )
                .mappings()
                .first()
            )
            assert final_row is not None
            assert final_row["must_change_password"] is False

        # 9. Logout revokes token and clears cookie
        logout_res = await client.post("/api/v1/auth/logout", headers=auth_headers)
        assert logout_res.status_code == 200
        # Cookie deletion directive present in Set-Cookie header
        set_cookie = logout_res.headers.get("set-cookie", "")
        assert "orcia_refresh_token" in set_cookie
