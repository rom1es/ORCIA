"""Vertical HTTP -> PG18 + Redis integration tests for contextual help and accostage."""

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
from testcontainers.redis import RedisContainer

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_help_accostage_pg18"
DB_USER = "orcia"
DB_PASSWORD = "orcia_help_accostage_pg18_pw"  # pragma: allowlist secret


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
async def test_contextual_help_routes_and_accostage_counts_persist_in_postgres18(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot real `create_app()` via lifespan without overrides and verify PG18 help + accostage."""
    pg_url, redis_url = infra_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-help-accostage-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-help-accostage-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")

    from orcia_api.main import create_app

    engine = create_async_engine(pg_url)
    try:
        app = create_app()
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            # 1. Day-0 Accostage status before any user exists
            r_day0 = await client.get("/api/v1/bootstrap/accostage-status")
            assert r_day0.status_code == 200, r_day0.text
            day0_json = r_day0.json()
            assert day0_json["first_admin_initialized"] is False
            assert day0_json["admin_created"] is False
            assert day0_json["users_count"] == 0
            assert day0_json["org_units_count"] == 0
            assert day0_json["workspaces_count"] == 0

            # 2. Create first admin -> verify PG18 users & accostage-status
            r_first = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.help@orcia.ia",
                    "display_name": "Admin Help",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text
            admin_token = r_first.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {admin_token}"}

            r_post_admin = await client.get("/api/v1/bootstrap/accostage-status")
            assert r_post_admin.status_code == 200, r_post_admin.text
            post_admin_json = r_post_admin.json()
            assert post_admin_json["first_admin_initialized"] is True
            assert post_admin_json["admin_created"] is True
            assert post_admin_json["users_count"] == 1
            assert post_admin_json["org_units_count"] == 0
            assert post_admin_json["workspaces_count"] == 0

            # 3. Create BU + Team -> verify org_units_count matches PG18
            r_bu = await client.post(
                "/api/v1/org-units",
                headers=auth_headers,
                json={"name": "Direction Produit", "slug": "bu-produit", "kind": "BU"},
            )
            assert r_bu.status_code == 200, r_bu.text
            bu_id = r_bu.json()["id"]

            r_team = await client.post(
                "/api/v1/org-units",
                headers=auth_headers,
                json={
                    "name": "Équipe Socle",
                    "slug": "team-socle",
                    "kind": "TEAM",
                    "parent_id": bu_id,
                },
            )
            assert r_team.status_code == 200, r_team.text
            team_id = r_team.json()["id"]

            # 4. Create Workspace -> verify workspaces_count matches PG18
            r_ws = await client.post(
                "/api/v1/workspaces",
                headers=auth_headers,
                json={
                    "name": "Espace Socle",
                    "slug": "espace-socle",
                    "owner_org_unit_id": team_id,
                    "visibility_mode": "STANDARD",
                },
            )
            assert r_ws.status_code in (200, 201), r_ws.text

            r_final = await client.get("/api/v1/bootstrap/accostage-status")
            assert r_final.status_code == 200, r_final.text
            final_json = r_final.json()

            async with engine.connect() as conn:
                counts_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT "
                            "(SELECT COUNT(*)::int FROM users WHERE is_active = TRUE) "
                            "AS users_count, "
                            "(SELECT COUNT(*)::int FROM org_units "
                            "WHERE unit_type <> 'ENTERPRISE') AS org_units_count, "
                            "(SELECT COUNT(*)::int FROM workspaces) AS workspaces_count"
                        )
                    )
                ).first()
            assert counts_row is not None
            assert final_json["users_count"] == int(counts_row[0]) == 1
            assert final_json["org_units_count"] == int(counts_row[1]) == 2
            assert final_json["workspaces_count"] == int(counts_row[2]) == 1
            assert final_json["admin_created"] is True

            # 5. Resolve contextual help via HTTP -> lazy-seeds PG18 `catalog_items`
            resolved_by_route: dict[str, tuple[str, str]] = {}
            resolved_articles_by_route: dict[str, dict[str, object]] = {}
            for route, expected_resource_id in [
                ("/finops", "help-base-finops-fr"),
                ("/assistant", "help-base-assistant-fr"),
                ("/cockpit", "help-base-cockpit-fr"),
                ("/profile", "help-base-profile-fr"),
            ]:
                r_help = await client.get(
                    "/api/v1/help/resolve",
                    params={"route": route, "lang": "fr", "pack": "core"},
                )
                assert r_help.status_code == 200, r_help.text
                article = r_help.json()["active_article"]
                assert article["resource_id"] == expected_resource_id
                assert article["resource_id"] != "help-base-spaces-sources-fr"
                assert str(article.get("summary_what_for") or "").strip() != ""
                assert len(article.get("step_by_step_items") or []) >= 1
                assert str(article.get("real_example_text") or "").strip() != ""
                assert len(article.get("common_pitfalls_items") or []) >= 1
                resolved_by_route[expected_resource_id] = (
                    str(article["resource_id"]),
                    str(article["title"]),
                )
                resolved_articles_by_route[route] = article

            # Story 23.3: /assistant and /cockpit return strictly distinct 4-block narratives
            assistant_art = resolved_articles_by_route["/assistant"]
            cockpit_art = resolved_articles_by_route["/cockpit"]
            assert assistant_art["title"] != cockpit_art["title"]
            assert assistant_art["summary_what_for"] != cockpit_art["summary_what_for"]
            assert assistant_art["real_example_text"] != cockpit_art["real_example_text"]
            assert "Le Cockpit regroupe" not in str(assistant_art["summary_what_for"])

            # Verify every resolved article exists verbatim in PG18 `catalog_items`
            async with engine.connect() as conn:
                help_rows = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT resource_id, title, metadata_jsonb FROM catalog_items "
                                "WHERE item_type = 'HELP_ARTICLE'"
                            )
                        )
                    )
                    .mappings()
                    .all()
                )
            help_rows_by_id = {str(row["resource_id"]): row for row in help_rows}
            for resource_id, (_, api_title) in resolved_by_route.items():
                assert resource_id in help_rows_by_id
                row = help_rows_by_id[resource_id]
                assert api_title == str(row["title"])
                meta = dict(row["metadata_jsonb"] or {})
                assert str(meta.get("real_example_text") or "").strip() != ""
                assert len(meta.get("common_pitfalls_items") or []) >= 1

            # 6. Verify Redis cache hit on second GET, then hot publish + rollback in PG18
            r_help_cached = await client.get(
                "/api/v1/help/resolve",
                params={"route": "/finops", "lang": "fr", "pack": "core"},
            )
            assert r_help_cached.status_code == 200, r_help_cached.text
            assert r_help_cached.json()["cache_hit"] is True

            r_pub = await client.post(
                "/api/v1/help/publish",
                headers=auth_headers,
                json={
                    "resource_id": "help-base-finops-fr",
                    "new_version": "1.1.0",
                    "new_title": "FinOps : budgets et alertes v1.1",
                    "new_summary_what_for": "Résumé mis à jour en PG18.",
                    "new_markdown_body": "# FinOps v1.1\n\nContenu mis à jour.",
                    "layer": "WORKSPACE",
                },
            )
            assert r_pub.status_code == 200, r_pub.text
            assert r_pub.json()["version"] == "1.1.0"

            r_after_pub = await client.get(
                "/api/v1/help/resolve",
                params={"route": "/finops", "lang": "fr", "pack": "core"},
            )
            assert r_after_pub.status_code == 200
            assert r_after_pub.json()["active_article"]["version"] == "1.1.0"
            assert r_after_pub.json()["rollback_available"] is True

            r_rb = await client.post(
                "/api/v1/help/rollback",
                headers=auth_headers,
                json={"resource_id": "help-base-finops-fr"},
            )
            assert r_rb.status_code == 200, r_rb.text
            assert r_rb.json()["version"] == "1.0.0"
    finally:
        await engine.dispose()
