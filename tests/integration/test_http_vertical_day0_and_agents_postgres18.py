"""TEST-07 — Intégration verticale HTTP → FastAPI → PostgreSQL 18 (`AD-17` couche 2, garde-fou n°2).

Chaque test sollicite la route FastAPI (`AsyncClient` + `ASGITransport`) **et** vérifie par un
`SELECT` sur un vrai PostgreSQL 18 (`pgvector/pgvector:pg18`, testcontainers) que l'état est
persisté.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_http_vertical"
DB_USER = "orcia"
DB_PASSWORD = "orcia_http_vertical_pw"  # pragma: allowlist secret
ADMIN_EMAIL = "http.vertical.admin@orcia.test"
ADMIN_PASSWORD = "Http-Vertical-Passw0rd!"  # pragma: allowlist secret


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
            "PATH": "/usr/bin:/bin",
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "alembic"), "-c", "infra/migrations/alembic.ini"]
            + ["upgrade", "head"],
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
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-http-vertical-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-http-vertical-vault-key-0001")
    from orcia_api.main import create_app

    return lambda: AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://test")


@pytest.mark.asyncio
async def test_first_admin_http_persists_hashed_account_and_is_single_use(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    payload = {
        "email": ADMIN_EMAIL,
        "display_name": "Admin HTTP Vertical",
        "password": ADMIN_PASSWORD,
        "orcia_env": "local",
    }
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            first = await client.post("/api/v1/bootstrap/welcome-setup/first-admin", json=payload)
            assert first.status_code == 200, first.text

            second = await client.post("/api/v1/bootstrap/welcome-setup/first-admin", json=payload)
            assert second.status_code == 409, second.text
            assert second.json()["error_code"]

        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    sa.text(
                        "SELECT platform_role, password_hash_argon2id, is_active "
                        "FROM users WHERE email = :e"
                    ),
                    {"e": ADMIN_EMAIL},
                )
            ).all()
        assert len(rows) == 1, "exactement un premier administrateur en base"
        role, password_hash, is_active = rows[0]
        assert role == "PLATFORM_ADMIN" and is_active is True
        assert password_hash.startswith("$argon2id$"), "mot de passe jamais stocké en clair"
        assert ADMIN_PASSWORD not in password_hash
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_agent_creation_http_persists_in_catalog_items(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    agent_name = "Agent Vertical HTTP PG18"
    engine = create_async_engine(database_url)
    try:
        async with app_client_factory() as client:
            res = await client.post(
                "/api/v1/agents-and-skills/agents?persona_key=marc",
                json={
                    "name": agent_name,
                    "role_mission": "Valider la persistance verticale.",
                    "instructions": "Répondre brièvement.",
                },
            )
            assert res.status_code == 200, res.text

        async with engine.connect() as conn:
            count = (
                await conn.execute(
                    sa.text(
                        "SELECT count(*) FROM catalog_items WHERE catalog_items::text ILIKE :n"
                    ),
                    {"n": f"%{agent_name}%"},
                )
            ).scalar_one()
        assert count >= 1, "l'agent créé par HTTP doit être présent dans catalog_items"
    finally:
        await engine.dispose()
