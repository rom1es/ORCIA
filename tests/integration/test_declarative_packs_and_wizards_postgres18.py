"""Vertical HTTP -> PostgreSQL 18 + Redis integration tests for declarative packs & wizards."""

from __future__ import annotations

import io
import os
import subprocess
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_packs_wizards_pg18"
DB_USER = "orcia"
DB_PASSWORD = "orcia_packs_wizards_pg18_pw"  # pragma: allowlist secret


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


@pytest.mark.asyncio
async def test_declarative_packs_and_durable_wizards_persist_in_postgres18(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot real `create_app()` via lifespan without overrides and verify PG18 persistence."""
    pg_url, redis_url = infra_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-packs-wizards-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-packs-wizards-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")

    from orcia_api.main import create_app
    from orcia_core.packs import seed_system_packs_on_engine

    engine = create_async_engine(pg_url)
    try:
        # Phase 1: Boot real Composition Root via lifespan_context (zero overrides)
        app1 = create_app()
        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://test") as client1,
        ):
            # 1a. Lifespan Day-0 bootstrap seeded declarative_pack_bundles (`sdlc` & `orcia-docs`)
            async with engine.connect() as conn:
                boot_pack_count = (
                    await conn.execute(sa.text("SELECT COUNT(*) FROM declarative_pack_bundles"))
                ).scalar_one()
            assert boot_pack_count >= 2

            r_boot_packs = await client1.get("/api/v1/packs")
            assert r_boot_packs.status_code == 200, r_boot_packs.text
            boot_slugs = {p["slug"] for p in r_boot_packs.json()["packs"]}
            assert {"sdlc", "orcia-docs"}.issubset(boot_slugs)

            # 1b. Story 31.2 PG18-only contract: DELETE -> GET returns 0 (zero runtime disk rescan)
            async with engine.begin() as conn:
                await conn.execute(sa.text("DELETE FROM declarative_pack_bundles"))
                empty_count = (
                    await conn.execute(sa.text("SELECT COUNT(*) FROM declarative_pack_bundles"))
                ).scalar_one()
            assert empty_count == 0

            r_empty = await client1.get("/api/v1/packs")
            assert r_empty.status_code == 200, r_empty.text
            assert r_empty.json()["packs"] == []

            r_missing_export = await client1.post(
                "/api/v1/packs/export/ws-pg18-test",
                params={"pack_id": "orcia-pack-sdlc"},
            )
            assert r_missing_export.status_code == 404

            # Re-seed via Day-0 seeder -> PG18 packs restored & export returns valid APM .zip
            await seed_system_packs_on_engine(engine)

            r_packs = await client1.get("/api/v1/packs")
            assert r_packs.status_code == 200, r_packs.text
            slugs = {p["slug"] for p in r_packs.json()["packs"]}
            assert {"sdlc", "orcia-docs"}.issubset(slugs)

            r_export = await client1.post(
                "/api/v1/packs/export/ws-pg18-test",
                params={"pack_id": "orcia-pack-sdlc"},
            )
            assert r_export.status_code == 200, r_export.text
            assert r_export.headers["content-type"].startswith("application/zip")
            assert "sdlc-ws-pg18-test.zip" in r_export.headers["content-disposition"]
            with zipfile.ZipFile(io.BytesIO(r_export.content), "r") as zf:
                assert any(n.endswith(("apm.yml", "pack.yaml")) for n in zf.namelist())

            async with engine.connect() as conn:
                export_pack_rows = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT pack_id, slug, bundle_sha256 FROM declarative_pack_bundles "
                                "ORDER BY slug ASC"
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
            assert len(export_pack_rows) >= 2
            assert all(len(str(row["bundle_sha256"]).strip()) == 64 for row in export_pack_rows)

            # 2. Bootstrap Day-0 admin in PG18 `users` for real JWT-authenticated wizard lifecycle
            r_first = await client1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.wizards@orcia.ia",
                    "display_name": "Admin Wizards",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text
            admin_token = r_first.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {admin_token}"}

            r_start = await client1.post(
                "/api/v1/wizards/sessions",
                headers=auth_headers,
                json={
                    "wizard_type": "sdlc_tech_lead",
                    "scope_id": "0195f000-0000-7000-8000-000000000301",
                },
            )
            assert r_start.status_code == 200, r_start.text
            session_id = r_start.json()["id"]
            UUID(session_id)
            assert r_start.json()["current_step_index"] == 1
            assert r_start.json()["status"] == "IN_PROGRESS"

            # Advance step 1 -> 2
            r_step1 = await client1.post(
                f"/api/v1/wizards/sessions/{session_id}/steps",
                headers=auth_headers,
                json={
                    "step_index": 1,
                    "step_payload": {"org_unit_name": "Équipe Architecture PG18"},
                },
            )
            assert r_step1.status_code == 200, r_step1.text
            assert r_step1.json()["current_step_index"] == 2

            # Advance step 2 -> 3, then step-back preserving inputs from both step 1 & step 2
            r_step2 = await client1.post(
                f"/api/v1/wizards/sessions/{session_id}/steps",
                headers=auth_headers,
                json={
                    "step_index": 2,
                    "step_payload": {"workspace_name": "Espace Initial PG18"},
                },
            )
            assert r_step2.status_code == 200, r_step2.text
            assert r_step2.json()["current_step_index"] == 3

            r_back = await client1.post(
                f"/api/v1/wizards/sessions/{session_id}/step-back",
                headers=auth_headers,
                json={
                    "step_index": 3,
                    "step_payload": {"connector_alias": "draft-git"},
                },
            )
            assert r_back.status_code == 200, r_back.text
            assert r_back.json()["current_step_index"] == 2
            assert r_back.json()["status"] == "IN_PROGRESS"
            assert (
                r_back.json()["state_jsonb"]["step_1"]["org_unit_name"]
                == "Équipe Architecture PG18"
            )
            assert r_back.json()["state_jsonb"]["step_2"]["workspace_name"] == "Espace Initial PG18"
            assert r_back.json()["state_jsonb"]["step_3"]["connector_alias"] == "draft-git"

            # Complete steps 2 -> 5
            for idx, payload in [
                (2, {"workspace_name": "Espace Final PG18"}),
                (
                    3,
                    {
                        "connector_alias": "git-pg18",
                        "connector_uri": "https://git.internal.orcia/pg18.git",
                    },
                ),
                (4, {"primary_model_id": "qwen2.5:14b"}),
                (5, {"verify_rag_reciprocity": True}),
            ]:
                r_adv = await client1.post(
                    f"/api/v1/wizards/sessions/{session_id}/steps",
                    headers=auth_headers,
                    json={"step_index": idx, "step_payload": payload},
                )
                assert r_adv.status_code == 200, r_adv.text

            assert r_adv.json()["status"] == "COMPLETED"
            assert r_adv.json()["current_step_index"] == 5
            assert r_adv.json()["rag_reciprocity_verified"] is True

            # Direct PostgreSQL 18 verification
            async with engine.connect() as conn:
                db_row = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT current_step_index, status, state_jsonb "
                                "FROM wizard_sessions WHERE id = CAST(:id AS uuid)"
                            ),
                            {"id": session_id},
                        )
                    )
                    .mappings()
                    .one()
                )
            assert db_row["current_step_index"] == 5
            assert db_row["status"] == "COMPLETED"
            assert db_row["state_jsonb"]["step_1"]["org_unit_name"] == "Équipe Architecture PG18"
            assert db_row["state_jsonb"]["step_2"]["workspace_name"] == "Espace Final PG18"
            assert db_row["state_jsonb"]["step_4"]["primary_model_id"] == "qwen2.5:14b"

        # Phase 2: Cold restart with fresh create_app() -> GET /api/v1/wizards reads from PG18
        app2 = create_app()
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as client2,
        ):
            r_list = await client2.get("/api/v1/wizards", headers=auth_headers)
            assert r_list.status_code == 200, r_list.text
            sessions = r_list.json()["sessions"]
            matched = [s for s in sessions if s["id"] == session_id]
            assert len(matched) == 1
            assert matched[0]["status"] == "COMPLETED"
            assert matched[0]["current_step_index"] == 5
            assert matched[0]["rag_reciprocity_verified"] is True
            assert (
                matched[0]["state_jsonb"]["step_1"]["org_unit_name"] == "Équipe Architecture PG18"
            )
    finally:
        await engine.dispose()
