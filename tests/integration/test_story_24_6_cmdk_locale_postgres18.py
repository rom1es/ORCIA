"""Story 24.6 Layer 2 PG18 + Redis 7.4 integration tests for Cmd+K locale filtering."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import redis.asyncio as aioredis
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_story_24_6_pg18"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_24_6_pg18_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def infra_urls() -> Iterator[tuple[str, str]]:
    """Start ephemeral PG18 + pgvector and Redis 7.4 containers migrated to head."""
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
async def test_cmdk_search_filters_help_articles_by_locale_and_isolates_redis_cache(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `GET /api/v1/search` with real `create_app()`, PG18 and Redis 7.4."""
    pg_url, redis_url = infra_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-24-6-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-24-6-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}

    engine = create_async_engine(pg_url)
    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            r_admin = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "cmdk.admin@orcia.ia",
                    "display_name": "CmdK Admin",
                    "password": "OrciaCmdK!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_admin.status_code == 200, r_admin.text
            headers = {"Authorization": f"Bearer {r_admin.json()['access_token']}"}

            r_bu = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={"name": "Direction CmdK", "slug": "bu-cmdk-246", "kind": "BU"},
            )
            assert r_bu.status_code == 200, r_bu.text
            bu_id = r_bu.json()["id"]

            r_team = await client.post(
                "/api/v1/org-units",
                headers=headers,
                json={
                    "name": "Équipe CmdK",
                    "slug": "team-cmdk-246",
                    "kind": "TEAM",
                    "parent_id": bu_id,
                },
            )
            assert r_team.status_code == 200, r_team.text
            team_id = r_team.json()["id"]

            r_ws = await client.post(
                "/api/v1/workspaces",
                headers=headers,
                json={
                    "name": "Espace CmdK 246",
                    "slug": "ws-cmdk-246",
                    "owner_org_unit_id": team_id,
                    "visibility_mode": "STANDARD",
                },
            )
            assert r_ws.status_code in (200, 201), r_ws.text
            async with engine.connect() as conn:
                ws_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text FROM workspaces WHERE slug = 'ws-cmdk-246' LIMIT 1"
                        )
                    )
                ).first()
            assert ws_row is not None
            ws_id = str(ws_row[0])

            r_emb = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=headers,
                json={
                    "scope_level": "GLOBAL",
                    "scope_id": ws_id,
                    "display_name": "Embedding PG18 246",
                    "inference_tier": "simple",
                    "effort": "default",
                    "provider_slug": "ollama",
                    "model_family": "ollama",
                    "model_name": "bge-m3:latest",
                    "endpoint_uri": "http://127.0.0.1:11434/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "embedding",
                },
            )
            assert r_emb.status_code in (200, 201), r_emb.text

            # Seed FR & EN HELP_ARTICLEs in PUBLISHED_ORG + 1 shared CATALOG_RESOURCE
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO catalog_items (
                            id, resource_id, uri, title, description, resource_type,
                            source_format, version, sha256, cas_key, visibility_scope,
                            owner_org_unit_id, owner_workspace_id, item_type, metadata_jsonb
                        ) VALUES
                        (
                            CAST(:id_fr AS uuid), 'help-cockpit-246-fr',
                            'orcia://help/cockpit/fr',
                            'Guide CockpitPilot246 Français',
                            'Piloter les validations humaines',
                            'template', 'ORCIA', '1.0.0', :sha_fr, :cas_fr, 'PUBLISHED_ORG',
                            CAST(:oid AS uuid), NULL, 'HELP_ARTICLE', CAST(:meta_fr AS jsonb)
                        ),
                        (
                            CAST(:id_en AS uuid), 'help-cockpit-246-en',
                            'orcia://help/cockpit/en',
                            'CockpitPilot246 English Guide',
                            'Manage human validations and gates',
                            'template', 'ORCIA', '1.0.0', :sha_en, :cas_en, 'PUBLISHED_ORG',
                            CAST(:oid AS uuid), NULL, 'HELP_ARTICLE', CAST(:meta_en AS jsonb)
                        ),
                        (
                            CAST(:id_cat AS uuid), 'cat-agent-cockpitpilot-246',
                            'orcia://agents/cockpitpilot-246',
                            'Agent CockpitPilot246 Universel',
                            'Assistant transverse multi-langue',
                            'agent', 'ORCIA', '1.0.0', :sha_cat, :cas_cat, 'PUBLISHED_ORG',
                            CAST(:oid AS uuid), NULL, 'CATALOG_RESOURCE', '{}'::jsonb
                        )
                        """
                    ),
                    {
                        "id_fr": new_uuid7_str(),
                        "id_en": new_uuid7_str(),
                        "id_cat": new_uuid7_str(),
                        "sha_fr": "1" * 64,
                        "cas_fr": "cas/" + "1" * 64,
                        "sha_en": "2" * 64,
                        "cas_en": "cas/" + "2" * 64,
                        "sha_cat": "3" * 64,
                        "cas_cat": "cas/" + "3" * 64,
                        "oid": team_id,
                        "meta_fr": json.dumps({"lang": "fr", "bound_routes": ["/cockpit"]}),
                        "meta_en": json.dumps({"lang": "en", "bound_routes": ["/cockpit"]}),
                    },
                )

            # 1. Search with locale=fr -> returns FR help article + CATALOG_RESOURCE, 0 EN help
            r_fr = await client.get(
                "/api/v1/search",
                headers=headers,
                params={
                    "q": "CockpitPilot246",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "locale": "fr",
                    "include_speed2": "true",
                    "force_semantic": "true",
                },
            )
            assert r_fr.status_code == 200, r_fr.text
            fr_json = r_fr.json()
            fr_ids = [h["item_id"] for h in fr_json["hits"]]
            assert "pg-catalog:help-cockpit-246-fr" in fr_ids
            assert "pg-catalog:cat-agent-cockpitpilot-246" in fr_ids
            assert "pg-catalog:help-cockpit-246-en" not in fr_ids
            assert ":fr:" in (fr_json["speed2_redis_key"] or "")

            # 2. Search with locale=en -> returns EN help article + CATALOG_RESOURCE, 0 FR help
            r_en = await client.get(
                "/api/v1/search",
                headers=headers,
                params={
                    "q": "CockpitPilot246",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "locale": "en",
                    "include_speed2": "true",
                    "force_semantic": "true",
                },
            )
            assert r_en.status_code == 200, r_en.text
            en_json = r_en.json()
            en_ids = [h["item_id"] for h in en_json["hits"]]
            assert "pg-catalog:help-cockpit-246-en" in en_ids
            assert "pg-catalog:cat-agent-cockpitpilot-246" in en_ids
            assert "pg-catalog:help-cockpit-246-fr" not in en_ids
            assert ":en:" in (en_json["speed2_redis_key"] or "")
            assert fr_json["speed2_redis_key"] != en_json["speed2_redis_key"]

            # 3. Verify distinct Speed-2 keys in real Redis 7.4 and warm cache hits per locale
            val_fr = await redis_client.get(fr_json["speed2_redis_key"])
            val_en = await redis_client.get(en_json["speed2_redis_key"])
            assert val_fr is not None
            assert val_en is not None
            assert "help-cockpit-246-en" not in val_fr
            assert "help-cockpit-246-fr" not in val_en

            r_fr_hit = await client.get(
                "/api/v1/search",
                headers=headers,
                params={
                    "q": "CockpitPilot246",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "locale": "fr",
                    "include_speed2": "true",
                    "force_semantic": "true",
                },
            )
            assert r_fr_hit.status_code == 200, r_fr_hit.text
            fr_hit_json = r_fr_hit.json()
            assert fr_hit_json["speed2_cache_hit"] is True
            fr_hit_ids = [h["item_id"] for h in fr_hit_json["hits"]]
            assert "pg-catalog:help-cockpit-246-fr" in fr_hit_ids
            assert "pg-catalog:help-cockpit-246-en" not in fr_hit_ids

            r_en_hit = await client.get(
                "/api/v1/search",
                headers=headers,
                params={
                    "q": "CockpitPilot246",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "locale": "en",
                    "include_speed2": "true",
                    "force_semantic": "true",
                },
            )
            assert r_en_hit.status_code == 200, r_en_hit.text
            en_hit_json = r_en_hit.json()
            assert en_hit_json["speed2_cache_hit"] is True
            en_hit_ids = [h["item_id"] for h in en_hit_json["hits"]]
            assert "pg-catalog:help-cockpit-246-en" in en_hit_ids
            assert "pg-catalog:help-cockpit-246-fr" not in en_hit_ids

            # 4. Accept-Language: en-US without locale query param selects EN help only
            r_hdr = await client.get(
                "/api/v1/search",
                headers={**headers, "Accept-Language": "en-US,en;q=0.9"},
                params={
                    "q": "CockpitPilot246",
                    "scope": "ALL_WORKSPACES",
                    "workspace_id": ws_id,
                    "include_speed2": "false",
                },
            )
            assert r_hdr.status_code == 200, r_hdr.text
            hdr_ids = [h["item_id"] for h in r_hdr.json()["hits"]]
            assert "pg-catalog:help-cockpit-246-en" in hdr_ids
            assert "pg-catalog:help-cockpit-246-fr" not in hdr_ids
    finally:
        await redis_client.aclose()
        await engine.dispose()
