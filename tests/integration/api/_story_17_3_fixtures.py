"""Shared Testcontainers fixtures for Story 17.3 integration tests (`AD-17`)."""

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
from testcontainers.postgres import PostgresContainer

from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_17_3"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_17_3_pw"  # pragma: allowlist secret


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
            [*alembic_cmd, "downgrade", "20261111_1702"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-17-3-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-17-3-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    def _build_client() -> AsyncClient:
        app = create_app()
        initialize_app_services(app)
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build_client


async def reset_iam_test_db(engine: sa.ext.asyncio.AsyncEngine) -> None:
    """Clear all IAM, grant, user and workspace records from test database."""
    async with engine.begin() as conn:
        for tbl in ("role_permission_grants", "iam_accounts", "workspaces", "users"):
            await conn.execute(sa.text(f"DELETE FROM {tbl}"))
        await conn.execute(sa.text("DELETE FROM org_units WHERE unit_type <> 'ENTERPRISE'"))


async def seed_day0_admin_user(
    engine: sa.ext.asyncio.AsyncEngine, email: str, display_name: str
) -> None:
    """Seed Day-0 admin user in PostgreSQL 18 users table."""
    async with engine.begin() as conn:
        root_ou = (
            await conn.execute(
                sa.text("SELECT id FROM org_units WHERE unit_type = 'ENTERPRISE' LIMIT 1")
            )
        ).scalar()
        if root_ou is None:
            root_ou = UUID(new_uuid7_str())
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                    "VALUES (:id, 'orcia-root', 'ORCIA Enterprise', 'ENTERPRISE', NULL)"
                ),
                {"id": root_ou},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO users (id, email, display_name, auth_mode, human_profile_archetype, "
                "platform_role, primary_org_unit_id, is_active) VALUES "
                "(:id, :email, :name, 'LOCAL', 'SECOPS', 'PLATFORM_ADMIN', :ou_id, TRUE)"
            ),
            {"id": UUID(new_uuid7_str()), "email": email, "name": display_name, "ou_id": root_ou},
        )


async def count_grants_by_id(engine: sa.ext.asyncio.AsyncEngine, grant_id: str) -> int:
    """Count role_permission_grants records matching UUID grant_id."""
    async with engine.connect() as conn:
        res = await conn.execute(
            sa.text("SELECT COUNT(*) FROM role_permission_grants WHERE id = :id"),
            {"id": UUID(grant_id)},
        )
        return int(res.scalar_one())
