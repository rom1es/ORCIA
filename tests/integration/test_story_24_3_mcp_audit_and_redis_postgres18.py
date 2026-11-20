"""Layer 2 integration tests for Story 24.3 on real PG18 + Redis 7.4 via `create_app()`."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import redis.asyncio as aioredis
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_story_24_3"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_24_3_pw"  # pragma: allowlist secret


def _run_alembic(pg_url: str, *args: str) -> None:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    alembic_bin = str(Path(sys.executable).with_name("alembic"))
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


@pytest.fixture(scope="module")
def infra_urls() -> Iterator[tuple[str, str]]:
    """Start ephemeral PostgreSQL 18 + pgvector and Redis 7.4 containers."""
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
        yield pg_url, redis_url


@pytest.mark.asyncio
async def test_alembic_24_3_upgrade_downgrade_roundtrip(infra_urls: tuple[str, str]) -> None:
    """Verify `20261120_2403` upgrade -> downgrade (`20261120_2402`) -> upgrade `head`."""
    pg_url, _ = infra_urls
    _run_alembic(pg_url, "upgrade", "20261120_2403")

    engine = create_async_engine(pg_url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            agents_tbl = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_exposed_agents')"))
            ).scalar_one()
            pat_tbl = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_governed_pat_tokens')"))
            ).scalar_one()
            agents_idx = (
                await conn.execute(
                    sa.text(
                        "SELECT 1 FROM pg_indexes WHERE tablename = 'mcp_exposed_agents' "
                        "AND indexname = 'ix_mcp_exposed_agents_ws_updated'"
                    )
                )
            ).scalar_one_or_none()
            check_def = (
                await conn.execute(
                    sa.text(
                        "SELECT pg_get_constraintdef(c.oid) "
                        "FROM pg_constraint c "
                        "JOIN pg_class cl ON cl.oid = c.conrelid "
                        "WHERE cl.relname = 'domain_events_outbox' "
                        "AND c.conname = 'domain_events_outbox_event_type_check'"
                    )
                )
            ).scalar_one()
        assert agents_tbl == "mcp_exposed_agents"
        assert pat_tbl == "mcp_governed_pat_tokens"
        assert agents_idx == 1
        assert "ADMIN_CONNECTION_TEST" in str(check_def)

        _run_alembic(pg_url, "downgrade", "20261120_2402")
        async with engine.connect() as conn:
            agents_after_down = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_exposed_agents')"))
            ).scalar_one()
            pat_after_down = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_governed_pat_tokens')"))
            ).scalar_one()
        assert agents_after_down is None
        assert pat_after_down is None

        _run_alembic(pg_url, "upgrade", "head")
        async with engine.connect() as conn:
            agents_head = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_exposed_agents')"))
            ).scalar_one()
            pat_head = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_governed_pat_tokens')"))
            ).scalar_one()
        assert agents_head == "mcp_exposed_agents"
        assert pat_head == "mcp_governed_pat_tokens"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_real_composition_root_mcp_audit_redis_cold_pg18_and_reset(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify test bench audit_ledger, cold MCP exposure/PAT hash, Redis 7.4 Speed-2 & Day-0."""
    pg_url, redis_url = infra_urls
    _run_alembic(pg_url, "upgrade", "head")

    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-24-3-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-24-3-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    engine = create_async_engine(pg_url, poolclass=NullPool)
    redis_client = aioredis.from_url(redis_url)
    raw_pat = "pat_mcp_pg18_story_24_3_token"  # pragma: allowlist secret
    expected_pat_sha256 = hashlib.sha256(raw_pat.encode("utf-8")).hexdigest()

    try:
        app1 = create_app()
        assert app1.dependency_overrides == {}

        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://test") as client1,
        ):
            r_first = await client1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.243@orcia.ia",
                    "display_name": "Admin Story 24.3",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text
            admin_token = r_first.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            r_ws = await client1.post(
                "/api/v1/workspaces",
                headers=admin_headers,
                json={
                    "name": "Espace Story 24.3",
                    "slug": "espace-story-24-3",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]
            ws_slug = r_ws.json()["slug"]
            UUID(ws_id)

            # 1. Test Bench execution -> audit_ledger ADMIN_CONNECTION_TEST in PG18
            r_bench = await client1.post(
                "/api/v1/settings/connectors/test-and-discover",
                headers=admin_headers,
                json={
                    "protocol": "MCP_STREAMABLE_HTTP_SSE",
                    "endpoint_url": "https://mcp.partner.io/sse",
                    "identity_mode": "SECRET_REF",
                    "secret_ref_valid": True,
                    "raw_tool_names": ["search_documents", "propose_draft_update"],
                },
            )
            assert r_bench.status_code == 200, r_bench.text
            bench_payload = r_bench.json()
            assert bench_payload["can_activate"] is True
            assert all(step["status"] == "PASS" for step in bench_payload["steps"])

            async with engine.connect() as conn:
                audit_rows = (
                    await conn.execute(
                        sa.text(
                            "SELECT event_type, actor_type, metadata_jsonb::text "
                            "FROM audit_ledger WHERE event_type = 'ADMIN_CONNECTION_TEST'"
                        )
                    )
                ).fetchall()
            assert len(audit_rows) >= 1
            assert audit_rows[0][0] == "ADMIN_CONNECTION_TEST"
            assert audit_rows[0][1] == "ADMIN_CONNECTION_TEST"
            assert raw_pat not in str(audit_rows)

            # 2. PUT /api/v1/mcp/exposure -> PG18 persistence + SHA-256 PAT hash
            r_expose = await client1.put(
                "/api/v1/mcp/exposure",
                headers=admin_headers,
                json={
                    "workspace_slug": ws_slug,
                    "agent_slug": "spec-reviewer-243",
                    "display_name": "Agent Relecteur 24.3",
                    "mcp_exposed": True,
                    "regime": "GOVERNED_STAGED_COPILOT",
                    "pat_token_to_register": raw_pat,
                },
            )
            assert r_expose.status_code == 200, r_expose.text
            assert "agent.spec-reviewer-243" in r_expose.json()["exposed_tools"]

            # 3. Configure active global embedding model & create second user for Redis isolation
            r_emb = await client1.post(
                "/api/v1/settings/ai-models/mappings",
                headers=admin_headers,
                json={
                    "scope_level": "GLOBAL",
                    "scope_id": "0192c4e0-0000-7000-8000-000000000001",
                    "display_name": "Ollama BGE-M3 24.3",
                    "inference_tier": "simple",
                    "provider_slug": "ollama",
                    "model_family": "BGE",
                    "model_name": "bge-m3:latest",
                    "endpoint_uri": "http://127.0.0.1:11434/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "embedding",
                },
            )
            assert r_emb.status_code == 201, r_emb.text

            r_contrib = await client1.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_headers,
                json={
                    "account_kind": "HUMAN",
                    "display_name": "Contributeur 24.3",
                    "email": "contrib.243@orcia.ia",
                    "principal_id": "contrib.243@orcia.ia",
                    "roles": ["CONTRIBUTOR"],
                    "team_ids": [],
                    "status": "ACTIVE",
                },
            )
            assert r_contrib.status_code in (200, 201), r_contrib.text
            contrib_pw = r_contrib.json()["temporary_password"]
            r_login_contrib = await client1.post(
                "/api/v1/auth/login/local",
                json={"email": "contrib.243@orcia.ia", "password": contrib_pw},
            )
            assert r_login_contrib.status_code == 200, r_login_contrib.text
            contrib_headers = {"Authorization": f"Bearer {r_login_contrib.json()['access_token']}"}

            # 4. Speed-2 search on real Redis 7.4 (TTL <= 300s & strict user/role/locale isolation)
            search_params = {
                "q": "guide arbitrage cockpit verdict",
                "scope": "WORKSPACE",
                "workspace_id": ws_id,
                "screen_route": "/cockpit",
                "include_speed2": "true",
                "force_semantic": "true",
            }
            r_search_miss = await client1.get(
                "/api/v1/search",
                headers={**admin_headers, "Accept-Language": "fr"},
                params=search_params,
            )
            assert r_search_miss.status_code == 200, r_search_miss.text
            s1_data = r_search_miss.json()
            assert s1_data["speed2_executed"] is True
            assert s1_data["speed2_cache_hit"] is False
            assert s1_data["speed2_cache_ttl_seconds"] == 300
            admin_fr_key = s1_data["speed2_redis_key"]
            assert isinstance(admin_fr_key, str) and admin_fr_key.startswith("search:v2:")

            # Verify directly in Redis 7.4
            raw_redis_val = await redis_client.get(admin_fr_key)
            assert raw_redis_val is not None
            ttl_val = await redis_client.ttl(admin_fr_key)
            assert 0 < ttl_val <= 300

            # Second identical call -> cache HIT
            r_search_hit = await client1.get(
                "/api/v1/search",
                headers={**admin_headers, "Accept-Language": "fr"},
                params=search_params,
            )
            assert r_search_hit.status_code == 200
            assert r_search_hit.json()["speed2_cache_hit"] is True
            assert r_search_hit.json()["speed2_redis_key"] == admin_fr_key

            # Different locale (en) -> cache MISS and distinct key
            r_search_en = await client1.get(
                "/api/v1/search",
                headers={**admin_headers, "Accept-Language": "en"},
                params=search_params,
            )
            assert r_search_en.status_code == 200
            assert r_search_en.json()["speed2_cache_hit"] is False
            assert r_search_en.json()["speed2_redis_key"] != admin_fr_key

            # Different user & role (CONTRIBUTOR) -> cache MISS and zero leakage
            r_search_contrib = await client1.get(
                "/api/v1/search",
                headers={**contrib_headers, "Accept-Language": "fr"},
                params=search_params,
            )
            assert r_search_contrib.status_code == 200
            assert r_search_contrib.json()["speed2_cache_hit"] is False
            assert r_search_contrib.json()["speed2_redis_key"] != admin_fr_key

        # 5. Cold new `create_app()` instance -> re-read MCP exposure from PG18 (no RAM cache)
        app2 = create_app()
        assert app2.dependency_overrides == {}
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as client2,
        ):
            r_cold_get = await client2.get(
                "/api/v1/mcp/exposure",
                headers=admin_headers,
                params={"workspace_slug": ws_slug},
            )
            assert r_cold_get.status_code == 200, r_cold_get.text
            cold_payload = r_cold_get.json()
            assert cold_payload["any_exposed"] is True
            assert "agent.spec-reviewer-243" in cold_payload["exposed_tools"]

            # Invoke over MCP using PAT verified against PG18 hash
            r_invoke = await client2.post(
                f"/api/v1/mcp/spaces/{ws_slug}/invoke",
                headers=admin_headers,
                json={
                    "raw_pat_token": raw_pat,
                    "agent_slug": "spec-reviewer-243",
                    "caller_verbs": ["execute"],
                    "passthrough_identity": "oidc:admin.243@orcia.ia",
                    "prompt_text": "Relis la spec 24.3",
                },
            )
            assert r_invoke.status_code == 200, r_invoke.text
            assert r_invoke.json()["audit_actor_type"] == "MCP_IDE_CLIENT"

            # Real /api/v1/packs/health endpoint
            r_packs_health = await client2.get("/api/v1/packs/health", headers=admin_headers)
            assert r_packs_health.status_code == 200, r_packs_health.text
            assert r_packs_health.json()["total_count"] >= 1

        # 6. Direct SQL verification of PG18 tables (zero plaintext PAT!)
        async with engine.connect() as conn:
            mcp_row = (
                await conn.execute(
                    sa.text(
                        "SELECT mcp_exposed, regime FROM mcp_exposed_agents "
                        "WHERE workspace_slug = :ws AND agent_slug = 'spec-reviewer-243'"
                    ),
                    {"ws": ws_slug},
                )
            ).one()
            cat_row = (
                await conn.execute(
                    sa.text(
                        "SELECT item_type, visibility_scope FROM catalog_items "
                        "WHERE resource_id = :rid"
                    ),
                    {"rid": f"mcp-exposed:{ws_slug}:spec-reviewer-243"},
                )
            ).one()
            pat_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT token_sha256, allowed_workspace_slugs_jsonb::text "
                        "FROM mcp_governed_pat_tokens"
                    )
                )
            ).fetchall()
        assert bool(mcp_row[0]) is True
        assert mcp_row[1] == "GOVERNED_STAGED_COPILOT"
        assert cat_row[0] == "MCP_EXPOSED_AGENT"
        assert cat_row[1] == "SHARED_WORKSPACE"
        assert any(row[0] == expected_pat_sha256 for row in pat_rows)
        assert raw_pat not in str(pat_rows)

        # 7. Day-0 reset purges mcp_exposed_agents & mcp_governed_pat_tokens, keeps audit_ledger
        reset_script = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
        spec = importlib.util.spec_from_file_location("orcia_test_09_reset_24_3", reset_script)
        assert spec is not None and spec.loader is not None
        reset_mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reset_mod
        spec.loader.exec_module(reset_mod)
        report = await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        assert report.committed is True
        assert report.remaining_users_count == 0

        async with engine.connect() as conn:
            agents_after = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM mcp_exposed_agents"))
            ).scalar_one()
            pats_after = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM mcp_governed_pat_tokens"))
            ).scalar_one()
            audit_after = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM audit_ledger "
                        "WHERE event_type = 'ADMIN_CONNECTION_TEST'"
                    )
                )
            ).scalar_one()
        assert agents_after == 0
        assert pats_after == 0
        assert audit_after >= 1
    finally:
        await redis_client.aclose()
        await engine.dispose()
