"""Story 25.1 Layer 2 Vertical HTTP -> PostgreSQL 18 Integration Tests.

Uses the real Composition Root (`create_app()` + `app.router.lifespan_context(app)`)
with zero `dependency_overrides` and zero manual `app.state.*` injection against
ephemeral `pgvector/pgvector:pg18` + `redis:7.4.2-alpine` containers.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer
try:
    from testcontainers.community.redis import RedisContainer
except ImportError:
    from testcontainers.redis import RedisContainer

from orcia_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_25_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_25_1_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg_and_redis_urls() -> Iterator[tuple[str, str]]:
    with (
        PostgresContainer(
            "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        ) as pg,
        RedisContainer("redis:7.4.2-alpine") as redis_c,
    ):
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_url = f"redis://127.0.0.1:{redis_c.get_exposed_port(6379)}/0"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        res = subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Alembic upgrade head failed:\n{res.stdout}\n{res.stderr}")
        yield pg_url, redis_url


@pytest_asyncio.fixture
async def real_lifespan_client_factory(
    pg_and_redis_urls: tuple[str, str], monkeypatch: pytest.MonkeyPatch
):  # type: ignore[no-untyped-def]
    pg_url, redis_url = pg_and_redis_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-25-1-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-25-1-vault-key-0001")

    def _open_client():  # type: ignore[no-untyped-def]
        @asynccontextmanager
        async def _ctx() -> AsyncIterator[AsyncClient]:
            app = create_app()
            async with (
                app.router.lifespan_context(app),
                AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
            ):
                yield client

        return _ctx()

    return _open_client, pg_url


@pytest.mark.asyncio
async def test_personal_workspace_provisioning_isolation_and_accostage_postgres18(
    real_lifespan_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    open_client, pg_url = real_lifespan_client_factory
    engine = create_async_engine(pg_url)
    try:
        # Clean state (0 users, 0 workspaces)
        async with engine.begin() as conn:
            for tbl in (
                "workspace_memberships",
                "workspaces",
                "role_permission_grants",
                "iam_accounts",
                "users",
            ):
                await conn.execute(sa.text(f"DELETE FROM {tbl}"))
            await conn.execute(sa.text("DELETE FROM org_units WHERE unit_type <> 'ENTERPRISE'"))

        async with open_client() as client:
            # 1. Day 0 -> 0 users, 0 workspaces, Accostage 0/6
            async with engine.connect() as conn:
                ws_count_0 = (
                    await conn.execute(sa.text("SELECT COUNT(*)::int FROM workspaces"))
                ).scalar_one()
            assert ws_count_0 == 0

            acc_0 = await client.get("/api/v1/bootstrap/accostage-status")
            assert acc_0.status_code == 200, acc_0.text
            assert acc_0.json()["completed_count"] == 0
            assert acc_0.json()["workspaces_count"] == 0

            # 2. Create 1st Admin -> creates personal workspace in PG18
            res_admin1 = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "alice.admin@orcia.fr",
                    "display_name": "Alice Admin",
                    "password": "Admin1Password!",  # pragma: allowlist secret
                },
            )
            assert res_admin1.status_code == 200, res_admin1.text
            admin1_token = res_admin1.json()["access_token"]
            admin1_headers = {"Authorization": f"Bearer {admin1_token}"}

            async with engine.connect() as conn:
                admin1_row = (
                    (
                        await conn.execute(
                            sa.text("SELECT id FROM users WHERE email = :email"),
                            {"email": "alice.admin@orcia.fr"},
                        )
                    )
                    .mappings()
                    .one()
                )
                admin1_id = str(admin1_row["id"])

                ws_rows = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT id, slug, visibility_mode, settings_jsonb FROM workspaces"
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
            assert len(ws_rows) == 1
            ws1 = ws_rows[0]
            assert ws1["slug"] == f"personal-{admin1_id}"
            assert ws1["visibility_mode"] == "CONFIDENTIAL_RESTRICTED"
            st1 = (
                json.loads(ws1["settings_jsonb"])
                if isinstance(ws1["settings_jsonb"], str)
                else ws1["settings_jsonb"]
            )
            assert st1["ui_visibility_mode"] == "PRIVATE_USER"
            assert st1["is_personal_workspace"] is True
            assert st1["personal_owner_user_id"] == admin1_id

            # GET /api/v1/workspaces returns personal workspace with PRIVATE_USER & is_personal=True
            r_ws1 = await client.get("/api/v1/workspaces", headers=admin1_headers)
            assert r_ws1.status_code == 200, r_ws1.text
            ws1_list = r_ws1.json()["workspaces"]
            assert len(ws1_list) == 1
            assert ws1_list[0]["id"] == str(ws1["id"])
            assert ws1_list[0]["visibility_mode"] == "PRIVATE_USER"
            assert ws1_list[0]["is_personal"] is True

            # 3. Accostage stays at 1/6 (first-space=False despite personal workspace)
            acc_1 = await client.get("/api/v1/bootstrap/accostage-status", headers=admin1_headers)
            assert acc_1.status_code == 200, acc_1.text
            acc_1_body = acc_1.json()
            assert acc_1_body["completed_count"] == 1
            assert acc_1_body["workspaces_count"] == 0
            assert "first-space" not in acc_1_body["completed_milestone_keys"]

            # 4. Create 2nd PLATFORM_ADMIN via IAM + login -> gets own isolated personal workspace
            r_iam2 = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin1_headers,
                json={
                    "account_kind": "HUMAN",
                    "display_name": "Bob Admin",
                    "email": "bob.admin@orcia.fr",
                    "principal_id": "bob.admin@orcia.fr",
                    "roles": ["PLATFORM_ADMIN"],
                    "team_ids": [],
                    "status": "ACTIVE",
                },
            )
            assert r_iam2.status_code == 200, r_iam2.text
            temp_pw2 = r_iam2.json()["temporary_password"]

            r_login2 = await client.post(
                "/api/v1/auth/login/local",
                json={"email": "bob.admin@orcia.fr", "password": temp_pw2},
            )
            assert r_login2.status_code == 200, r_login2.text
            admin2_token = r_login2.json()["access_token"]
            admin2_headers = {"Authorization": f"Bearer {admin2_token}"}

            r_ws2 = await client.get("/api/v1/workspaces", headers=admin2_headers)
            assert r_ws2.status_code == 200, r_ws2.text
            ws2_list = r_ws2.json()["workspaces"]
            assert len(ws2_list) == 1
            assert ws2_list[0]["visibility_mode"] == "PRIVATE_USER"
            assert ws2_list[0]["is_personal"] is True
            assert ws2_list[0]["id"] != str(ws1["id"])

            # Verify Admin 1 still NEVER sees Admin 2's personal workspace
            r_ws1_after = await client.get("/api/v1/workspaces", headers=admin1_headers)
            assert r_ws1_after.status_code == 200, r_ws1_after.text
            assert [w["id"] for w in r_ws1_after.json()["workspaces"]] == [str(ws1["id"])]

            async with engine.connect() as conn:
                total_ws = (
                    await conn.execute(sa.text("SELECT COUNT(*)::int FROM workspaces"))
                ).scalar_one()
            assert total_ws == 2

            # 5. Add 1 AI model -> 2/6 ; add 1 team workspace -> first-space becomes True
            r_llm = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=admin1_headers,
                json={
                    "scope_level": "GLOBAL",
                    "scope_id": "0195f000-0000-7000-8000-000000000301",
                    "display_name": "Qwen Local",
                    "inference_tier": "medium",
                    "effort": "default",
                    "provider_slug": "ollama",
                    "model_family": "qwen-2.5",
                    "model_name": "qwen2.5-coder:14b",
                    "endpoint_uri": "http://127.0.0.1:11434/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                },
            )
            assert r_llm.status_code == 201, r_llm.text

            acc_2 = await client.get("/api/v1/bootstrap/accostage-status", headers=admin1_headers)
            assert acc_2.status_code == 200, acc_2.text
            assert acc_2.json()["completed_count"] == 2
            assert "first-llm-model" in acc_2.json()["completed_milestone_keys"]
            assert "first-space" not in acc_2.json()["completed_milestone_keys"]

            r_team_ws = await client.post(
                "/api/v1/workspaces",
                headers=admin1_headers,
                json={
                    "name": "Espace Équipe Finance",
                    "slug": "espace-equipe-finance",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_team_ws.status_code == 201, r_team_ws.text

            acc_3 = await client.get("/api/v1/bootstrap/accostage-status", headers=admin1_headers)
            assert acc_3.status_code == 200, acc_3.text
            assert acc_3.json()["workspaces_count"] == 1
            assert acc_3.json()["completed_count"] == 3
            assert "first-space" in acc_3.json()["completed_milestone_keys"]

        # 6. Cold-reload against fresh create_app() + lifespan proves PG18 isolation
        async with open_client() as fresh_client:
            r_cold_1 = await fresh_client.get("/api/v1/workspaces", headers=admin1_headers)
            assert r_cold_1.status_code == 200
            ids_1 = {w["id"] for w in r_cold_1.json()["workspaces"]}
            assert str(ws1["id"]) in ids_1
            assert ws2_list[0]["id"] not in ids_1

            r_cold_2 = await fresh_client.get("/api/v1/workspaces", headers=admin2_headers)
            assert r_cold_2.status_code == 200
            ids_2 = {w["id"] for w in r_cold_2.json()["workspaces"]}
            assert ws2_list[0]["id"] in ids_2
            assert str(ws1["id"]) not in ids_2
    finally:
        await engine.dispose()
