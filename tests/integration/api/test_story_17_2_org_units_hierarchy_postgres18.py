"""Story 17.2 — Vertical HTTP -> PostgreSQL 18 Integration Tests for `/api/v1/org-units`.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic revision `20261111_1702` (`upgrade head`, `downgrade 20261108_0910`, `upgrade head`).
2. Multi-level `BU -> Sous-BU -> TEAM` creation, DFS ordering, `billing_enabled`, `lead_user_id`,
   and `member_user_ids_jsonb` verified via direct SQL `SELECT` on `org_units`.
3. Hierarchy invariants (`422 ERR_ORG_UNIT_INVALID_PARENT_KIND`, `422 ERR_ORG_UNIT_HIERARCHY_CYCLE`,
   `409 ERR_ORG_UNIT_DUPLICATE_SLUG`).
4. Non-empty deletion protection (`409 ERR_ORG_UNIT_NOT_EMPTY` for child unit and workspace)
   and `READ_ONLY_OBSERVER` guard (`403 ERR_OBSERVER_MODE_READ_ONLY`).
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_kernel.ids import new_uuid7

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_17_2"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_17_2_pw"  # pragma: allowlist secret


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
        alembic_cmd = [
            str(REPO_ROOT / ".venv" / "bin" / "alembic"),
            "-c",
            "infra/migrations/alembic.ini",
        ]
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261111_1702
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261108_0910"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-17-2-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-17-2-vault-key-0001")
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
async def test_org_units_multi_level_hierarchy_billing_members_and_guards_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    headers = {"X-Orcia-Persona": "karim"}
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text("DELETE FROM workspaces"))
            await conn.execute(sa.text("DELETE FROM org_units WHERE unit_type <> 'ENTERPRISE'"))

        async with app_client_factory() as client:
            # 1. Create Root BU -> Sub-BU (Pôle) -> Team
            r_root = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={
                    "name": "Direction Générale Produit",
                    "kind": "BU",
                    "billing_enabled": True,
                    "lead_user_id": "claire.dir@orcia.fr",
                },
            )
            assert r_root.status_code == 200, r_root.text
            root_id = r_root.json()["id"]

            r_pole = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={
                    "name": "Pôle Plateforme IA",
                    "kind": "BU",
                    "parent_id": root_id,
                    "billing_enabled": False,
                },
            )
            assert r_pole.status_code == 200, r_pole.text
            pole_id = r_pole.json()["id"]
            assert r_pole.json()["parent_id"] == root_id
            assert r_pole.json()["billing_enabled"] is False

            r_team = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={
                    "name": "Équipe Orchestration",
                    "kind": "TEAM",
                    "parent_id": pole_id,
                    "billing_enabled": True,
                    "lead_user_id": "marc.lead@orcia.fr",
                    "member_user_ids": ["alice@orcia.fr", "bob@orcia.fr"],
                },
            )
            assert r_team.status_code == 200, r_team.text
            team_id = r_team.json()["id"]
            team_slug = r_team.json()["slug"]

            # 2. Verify SQL persistence directly on PostgreSQL 18 org_units table
            async with engine.connect() as conn:
                db_row = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT slug, unit_type, parent_id, billing_enabled,
                                   lead_user_id, member_user_ids_jsonb
                            FROM org_units WHERE id = :id
                            """
                        ),
                        {"id": UUID(team_id)},
                    )
                ).one()
            assert db_row[0] == team_slug
            assert db_row[1] == "TEAM"
            assert str(db_row[2]) == pole_id
            assert db_row[3] is True
            assert db_row[4] == "marc.lead@orcia.fr"
            assert list(db_row[5]) == ["alice@orcia.fr", "bob@orcia.fr"]

            # 3. Verify DFS tree order via GET /api/v1/org-units
            listed = await client.get("/api/v1/org-units", headers=headers)
            assert listed.status_code == 200
            listed_ids = [u["id"] for u in listed.json()["org_units"]]
            assert listed_ids == [root_id, pole_id, team_id]

            # 4. Hierarchy guards: BU under TEAM (422), cycle (422), dup slug (409), 404
            invalid_bu = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={"name": "Direction Sous Équipe", "kind": "BU", "parent_id": team_id},
            )
            assert invalid_bu.status_code == 422
            assert invalid_bu.json()["error_code"] == "ERR_ORG_UNIT_INVALID_PARENT_KIND"

            cycle_patch = await client.patch(
                f"/api/v1/org-units/{root_id}",
                headers=headers,
                json={"parent_id": pole_id},
            )
            assert cycle_patch.status_code == 422
            assert cycle_patch.json()["error_code"] == "ERR_ORG_UNIT_HIERARCHY_CYCLE"

            dup_slug = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={"name": "Doublon", "slug": r_root.json()["slug"], "kind": "BU"},
            )
            assert dup_slug.status_code == 409
            assert dup_slug.json()["error_code"] == "ERR_ORG_UNIT_DUPLICATE_SLUG"

            missing_patch = await client.patch(
                "/api/v1/org-units/does-not-exist-slug",
                headers=headers,
                json={"name": "Introuvable"},
            )
            assert missing_patch.status_code == 404

            # 5. Observer read-only guard -> 403 ERR_OBSERVER_MODE_READ_ONLY
            obs_patch = await client.patch(
                f"/api/v1/org-units/{pole_id}",
                headers={**headers, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                json={"name": "Interdit"},
            )
            assert obs_patch.status_code == 403
            assert obs_patch.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            # 6. PATCH rename + lead + members update by slug persisted to PostgreSQL 18
            updated = await client.patch(
                f"/api/v1/org-units/{team_slug}",
                headers=headers,
                json={
                    "name": "Équipe Orchestration & Noyau",
                    "billing_enabled": False,
                    "lead_user_id": "claire.lead@orcia.fr",
                    "member_user_ids": ["alice@orcia.fr", "chloe@orcia.fr"],
                },
            )
            assert updated.status_code == 200
            assert updated.json()["billing_enabled"] is False
            assert updated.json()["lead_user_id"] == "claire.lead@orcia.fr"
            assert updated.json()["member_user_ids"] == ["alice@orcia.fr", "chloe@orcia.fr"]

            # 7. Non-empty delete guard: child unit (pole_id has team_id) -> 409
            del_pole_blocked = await client.delete(f"/api/v1/org-units/{pole_id}", headers=headers)
            assert del_pole_blocked.status_code == 409
            assert del_pole_blocked.json()["error_code"] == "ERR_ORG_UNIT_NOT_EMPTY"

            # Insert a real workspace attached to team_id -> deleting team_id returns 409
            ws_uuid = new_uuid7()
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspaces (
                            id, slug, name, owner_org_unit_id, visibility_mode
                        )
                        VALUES (
                            :id, 'ws-story-17-2', 'Espace Story 17.2',
                            :owner_id, 'STANDARD'
                        )
                        """
                    ),
                    {"id": ws_uuid, "owner_id": UUID(team_id)},
                )

            listed_with_ws = await client.get("/api/v1/org-units", headers=headers)
            team_entry = next(u for u in listed_with_ws.json()["org_units"] if u["id"] == team_id)
            assert team_entry["attached_workspaces_count"] == 1

            del_team_blocked = await client.delete(f"/api/v1/org-units/{team_id}", headers=headers)
            assert del_team_blocked.status_code == 409
            assert del_team_blocked.json()["error_code"] == "ERR_ORG_UNIT_NOT_EMPTY"

            # Remove workspace -> cascade clean leaf-to-root deletion succeeds and removes SQL rows
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("DELETE FROM workspaces WHERE id = :id"), {"id": ws_uuid}
                )

            assert (
                await client.delete(f"/api/v1/org-units/{team_id}", headers=headers)
            ).status_code == 200
            assert (
                await client.delete(f"/api/v1/org-units/{pole_id}", headers=headers)
            ).status_code == 200
            assert (
                await client.delete(f"/api/v1/org-units/{root_id}", headers=headers)
            ).status_code == 200

            async with engine.connect() as conn:
                remaining = (
                    await conn.execute(
                        sa.text("SELECT COUNT(*) FROM org_units WHERE unit_type <> 'ENTERPRISE'")
                    )
                ).scalar_one()
            assert int(remaining) == 0
    finally:
        await engine.dispose()
