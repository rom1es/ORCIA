"""Real PG18 Composition Root boot & IAM setup helpers for Story 29.2 integration tests."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from httpx import AsyncClient
from testcontainers.postgres import PostgresContainer

from orcia_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]


def _to_async_pg_url(sync_url: str) -> str:
    if sync_url.startswith("postgresql+psycopg2://"):
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return sync_url


@asynccontextmanager
async def boot_real_app_pg18(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[object, object]]:
    """Boot real `create_app()` against ephemeral PG18 with Alembic `upgrade head`."""
    with PostgresContainer("pgvector/pgvector:pg18") as pg:
        sync_url = pg.get_connection_url()
        async_url = _to_async_pg_url(sync_url)
        monkeypatch.setenv("DATABASE_URL", async_url)
        monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
        monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
        monkeypatch.setenv("ORCIA_ENV", "e2e")
        monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
        monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

        from alembic import command
        from alembic.config import Config

        cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
        cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        cfg.set_main_option("sqlalchemy.url", sync_url)
        await asyncio.to_thread(command.upgrade, cfg, "head")

        app = create_app()
        async with app.router.lifespan_context(app):
            yield app, app.state.db_engine


async def setup_org_and_users_pg18(client: AsyncClient) -> dict[str, str]:
    """Bootstrap first admin, BU, Team A/B, and Lead A / Dev A / Lead B on PG18."""
    r_setup = await client.post(
        "/api/v1/bootstrap/welcome-setup/first-admin",
        json={
            "email": "admin292@orcia.test",
            "display_name": "Admin 292",
            "password": "OrciaAdmin292!2026",  # pragma: allowlist secret
        },
    )
    assert r_setup.status_code in (200, 201), r_setup.text
    admin_token = r_setup.json()["access_token"]
    admin_hdrs = {"Authorization": f"Bearer {admin_token}"}

    r_bu = await client.post(
        "/api/v1/org-units",
        headers=admin_hdrs,
        json={"name": "BU 29.2", "slug": "bu-292", "kind": "BU"},
    )
    assert r_bu.status_code == 200, r_bu.text
    bu_id = r_bu.json()["id"]

    r_ta = await client.post(
        "/api/v1/org-units",
        headers=admin_hdrs,
        json={"name": "Team A", "slug": "team-a-292", "kind": "TEAM", "parent_id": bu_id},
    )
    assert r_ta.status_code == 200, r_ta.text
    team_a_id = r_ta.json()["id"]

    r_tb = await client.post(
        "/api/v1/org-units",
        headers=admin_hdrs,
        json={"name": "Team B", "slug": "team-b-292", "kind": "TEAM", "parent_id": bu_id},
    )
    assert r_tb.status_code == 200, r_tb.text
    team_b_id = r_tb.json()["id"]

    async def _create_and_login(
        email: str, name: str, role: str, team_ids: list[str]
    ) -> tuple[str, str]:
        r_acc = await client.post(
            "/api/v1/settings/iam/accounts",
            headers=admin_hdrs,
            json={
                "account_kind": "HUMAN",
                "display_name": name,
                "email": email,
                "principal_id": email,
                "roles": [role],
                "team_ids": team_ids,
                "status": "ACTIVE",
            },
        )
        assert r_acc.status_code in (200, 201), r_acc.text
        pw = r_acc.json()["temporary_password"]
        r_log = await client.post("/api/v1/auth/login/local", json={"email": email, "password": pw})
        assert r_log.status_code == 200, r_log.text
        return r_log.json()["user_id"], r_log.json()["access_token"]

    lead_a_id, lead_a_tok = await _create_and_login(
        "leada@orcia.test", "Lead A", "TEAM_LEAD", [team_a_id]
    )
    dev_a_id, dev_a_tok = await _create_and_login(
        "deva@orcia.test", "Dev A", "CONTRIBUTOR", [team_a_id]
    )
    _, lead_b_tok = await _create_and_login("leadb@orcia.test", "Lead B", "TEAM_LEAD", [team_b_id])
    await client.patch(
        f"/api/v1/org-units/{team_a_id}",
        headers=admin_hdrs,
        json={"lead_user_ids": [lead_a_id]},
    )
    return {
        "admin_tok": admin_token,
        "team_a_id": team_a_id,
        "lead_a_id": lead_a_id,
        "lead_a_tok": lead_a_tok,
        "dev_a_id": dev_a_id,
        "dev_a_tok": dev_a_tok,
        "lead_b_tok": lead_b_tok,
    }
