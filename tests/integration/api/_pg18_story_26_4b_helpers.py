"""Shared PG18 ephemeral container and vertical test helpers for Story 26.4b."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
from httpx import AsyncClient
from testcontainers.postgres import PostgresContainer

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_26_4b"
DB_USER = "orcia"
DB_PASSWORD = "orcia_26_4b_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg18_db_url() -> Iterator[str]:
    """Spin up an ephemeral PostgreSQL 18 (`pgvector:pg18`) container upgraded to head."""
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": "/usr/bin:/bin",
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        subprocess.run(
            [
                str(REPO_ROOT / ".venv/bin/alembic"),
                "-c",
                "infra/migrations/alembic.ini",
                "upgrade",
                "head",
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield pg_url


def configure_pg18_test_env(monkeypatch: pytest.MonkeyPatch, pg18_db_url: str) -> None:
    """Apply clean local PG18 environment variables for a fresh `create_app()` instance."""
    monkeypatch.setenv("DATABASE_URL", pg18_db_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_ENV", "local")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-26-4b-jwt-secret-00000001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-26-4b-vault-key-00000001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")


async def bootstrap_admin_and_workspace(
    client: AsyncClient,
    *,
    email: str,
    slug_suffix: str,
) -> tuple[dict[str, str], str]:
    """Bootstrap Day-0 admin and create an org unit + workspace returning auth headers & ID."""
    boot = await client.post(
        "/api/v1/bootstrap/welcome-setup/first-admin",
        json={
            "email": email,
            "display_name": f"Admin {slug_suffix}",
            "password": "Admin264b!StrongPassword",  # pragma: allowlist secret
            "orcia_env": "local",
        },
    )
    assert boot.status_code in (200, 201), boot.text
    hdrs = {"Authorization": f"Bearer {boot.json()['access_token']}"}
    ou = await client.post(
        "/api/v1/org-units",
        headers=hdrs,
        json={"name": f"BU {slug_suffix}", "slug": f"bu-{slug_suffix}", "kind": "BU"},
    )
    assert ou.status_code in (200, 201), ou.text
    ws = await client.post(
        "/api/v1/workspaces",
        headers=hdrs,
        json={
            "name": f"WS {slug_suffix}",
            "slug": f"ws-{slug_suffix}",
            "owner_org_unit_id": ou.json()["id"],
            "visibility_mode": "STANDARD",
        },
    )
    assert ws.status_code in (200, 201), ws.text
    return hdrs, ws.json()["id"]
