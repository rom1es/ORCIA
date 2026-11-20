"""Story 24.5 Layer 2 PG18 integration tests: Accostage role filtering & /inbox help."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_story_24_5_pg18"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_24_5_pg18_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def infra_urls() -> Iterator[tuple[str, str]]:
    """Start ephemeral PostgreSQL 18 + pgvector and Redis 7.4 containers migrated to head."""
    with (
        PostgresContainer(
            "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        ) as pg,
        RedisContainer("redis:7.4-alpine") as redis_box,
    ):
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_host = redis_box.get_container_host_ip()
        redis_port = int(redis_box.get_exposed_port(6379))
        redis_url = f"redis://{redis_host}:{redis_port}/0"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield pg_url, redis_url


async def _create_and_login_user(
    client: AsyncClient,
    *,
    admin_headers: dict[str, str],
    email: str,
    display_name: str,
    role: str,
) -> dict[str, str]:
    r_create = await client.post(
        "/api/v1/settings/iam/accounts",
        headers=admin_headers,
        json={
            "email": email,
            "display_name": display_name,
            "account_kind": "HUMAN",
            "auth_source": "LOCAL_PASSWORD",
            "roles": [role],
        },
    )
    assert r_create.status_code in (200, 201), r_create.text
    temp_password = r_create.json()["temporary_password"]

    r_login = await client.post(
        "/api/v1/auth/login/local",
        json={"email": email, "password": temp_password},
    )
    assert r_login.status_code == 200, r_login.text
    token = r_login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_accostage_status_identity_role_filtering_and_inbox_help_against_postgres18(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot real `create_app()` without overrides and verify PG18 Accostage & /inbox help."""
    pg_url, redis_url = infra_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-24-5-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-24-5-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")

    from orcia_api.main import create_app

    app = create_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        # 1. Create the single first PLATFORM_ADMIN in PG18
        r_first = await client.post(
            "/api/v1/bootstrap/welcome-setup/first-admin",
            json={
                "email": "alice.admin@orcia.ia",
                "display_name": "Alice Administratrice",
                "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                "orcia_env": "local",
            },
        )
        assert r_first.status_code == 200, r_first.text
        admin_token = r_first.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. PLATFORM_ADMIN sees all 6 milestones, with first-admin -> /profile
        #    (never /welcome-setup)
        r_admin_acc = await client.get(
            "/api/v1/bootstrap/accostage-status",
            headers=admin_headers,
        )
        assert r_admin_acc.status_code == 200, r_admin_acc.text
        admin_acc = r_admin_acc.json()
        assert admin_acc["platform_admin_display_name"] == "Alice Administratrice"
        assert admin_acc["first_admin_display_name"] == "Alice Administratrice"
        admin_keys = [m["key"] for m in admin_acc["visible_milestones"]]
        assert admin_keys == [
            "first-admin",
            "first-llm-model",
            "first-org-unit",
            "first-space",
            "first-datasource",
            "pilot-workflow-run",
        ]
        assert admin_acc["visible_milestones"][0]["target_route"] == "/profile"
        assert all(m["target_route"] != "/welcome-setup" for m in admin_acc["visible_milestones"])

        # 3. Create CONTRIBUTOR, BU_LEAD, and OBSERVER in PG18 and verify identity & filtering
        contrib_headers = await _create_and_login_user(
            client,
            admin_headers=admin_headers,
            email="claire.contrib@orcia.ia",
            display_name="Claire Collaboratrice",
            role="CONTRIBUTOR",
        )
        bu_lead_headers = await _create_and_login_user(
            client,
            admin_headers=admin_headers,
            email="marc.bulead@orcia.ia",
            display_name="Marc Directeur BU",
            role="BU_LEAD",
        )
        observer_headers = await _create_and_login_user(
            client,
            admin_headers=admin_headers,
            email="olivier.obs@orcia.ia",
            display_name="Olivier Observateur",
            role="OBSERVER",
        )

        # CONTRIBUTOR: real platform_admin_display_name == Alice Administratrice
        # (never Claire Collaboratrice)
        r_contrib_acc = await client.get(
            "/api/v1/bootstrap/accostage-status",
            headers=contrib_headers,
        )
        assert r_contrib_acc.status_code == 200, r_contrib_acc.text
        contrib_acc = r_contrib_acc.json()
        assert contrib_acc["platform_admin_display_name"] == "Alice Administratrice"
        assert [m["key"] for m in contrib_acc["visible_milestones"]] == [
            "first-space",
            "pilot-workflow-run",
        ]

        # BU_LEAD: sees org-unit, space, pilot-workflow-run (no admin milestones)
        r_bulead_acc = await client.get(
            "/api/v1/bootstrap/accostage-status",
            headers=bu_lead_headers,
        )
        assert r_bulead_acc.status_code == 200, r_bulead_acc.text
        bulead_acc = r_bulead_acc.json()
        assert bulead_acc["platform_admin_display_name"] == "Alice Administratrice"
        assert [m["key"] for m in bulead_acc["visible_milestones"]] == [
            "first-org-unit",
            "first-space",
            "pilot-workflow-run",
        ]

        # READ_ONLY_OBSERVER: sees 0 interactive milestones, still real admin name
        r_obs_acc = await client.get(
            "/api/v1/bootstrap/accostage-status",
            headers=observer_headers,
        )
        assert r_obs_acc.status_code == 200, r_obs_acc.text
        obs_acc = r_obs_acc.json()
        assert obs_acc["platform_admin_display_name"] == "Alice Administratrice"
        assert obs_acc["visible_milestones"] == []

        # 4. Dedicated /inbox Zone 4 contextual help resolution in FR and EN against PG18
        for lang in ("fr", "en"):
            r_help = await client.get(
                f"/api/v1/help/resolve?route=/inbox&lang={lang}",
                headers=admin_headers,
            )
            assert r_help.status_code == 200, r_help.text
            help_json = r_help.json()
            article = help_json["active_article"]
            assert article["resource_id"] == f"help-base-inbox-{lang}"
            assert "assistant" not in article["resource_id"]
            assert "/inbox" in article["bound_routes"]
