"""Story 23.2 (Couche 2) — Authenticated SSE & E2E fail-closed verification on PG18 + Redis."""

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
DB_NAME = "orcia_story_23_2"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_23_2_pw"  # pragma: allowlist secret


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
async def test_story_23_2_sse_streams_auth_scope_and_cassette_on_real_composition_root_pg18(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot real `create_app()` lifespan without overrides under `ORCIA_ENV=e2e`."""
    pg_url, redis_url = infra_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-23-2-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-23-2-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}

    engine = create_async_engine(pg_url)
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            # 0. Bootstrap Day-0 admin -> real JWT Bearer
            r_admin = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.232@orcia.ia",
                    "display_name": "Admin 23.2",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_admin.status_code == 200, r_admin.text
            admin_token = r_admin.json()["access_token"]
            admin_auth = {"Authorization": f"Bearer {admin_token}"}

            # 1. Create dedicated BU + Team + CONFIDENTIAL_RESTRICTED workspace
            r_bu = await client.post(
                "/api/v1/org-units",
                headers=admin_auth,
                json={"name": "BU SSE 23.2", "slug": "bu-sse-232", "kind": "BU"},
            )
            assert r_bu.status_code == 200, r_bu.text
            bu_id = r_bu.json()["id"]

            r_team = await client.post(
                "/api/v1/org-units",
                headers=admin_auth,
                json={
                    "name": "Team SSE 23.2",
                    "slug": "team-sse-232",
                    "kind": "TEAM",
                    "parent_id": bu_id,
                },
            )
            assert r_team.status_code == 200, r_team.text
            team_id = r_team.json()["id"]

            r_ws = await client.post(
                "/api/v1/workspaces",
                headers=admin_auth,
                json={
                    "name": "Espace SSE 23.2",
                    "slug": "espace-sse-232",
                    "visibility_mode": "CONFIDENTIAL_RESTRICTED",
                    "lifecycle_phase": "BUILD",
                    "owner_org_unit_id": team_id,
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]

            # 2. Create outsider user (no access to ws_id) and log in to obtain real JWT
            r_outsider = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_auth,
                json={
                    "account_kind": "HUMAN",
                    "display_name": "Outsider 23.2",
                    "email": "outsider.232@orcia.ia",
                    "principal_id": "outsider.232@orcia.ia",
                    "roles": ["CONTRIBUTOR"],
                    "team_ids": [],
                    "status": "ACTIVE",
                },
            )
            assert r_outsider.status_code in (200, 201), r_outsider.text
            outsider_pw = r_outsider.json()["temporary_password"]
            r_login = await client.post(
                "/api/v1/auth/login/local",
                json={"email": "outsider.232@orcia.ia", "password": outsider_pw},
            )
            assert r_login.status_code == 200, r_login.text
            outsider_token = r_login.json()["access_token"]
            outsider_auth = {"Authorization": f"Bearer {outsider_token}"}

            # 3. GET /api/v1/events/stream -> 401 anonymous under ORCIA_ENV="e2e"
            r_evt_anon = await client.get(
                "/api/v1/events/stream",
                params={"workspace_id": ws_id, "live": "false"},
            )
            assert r_evt_anon.status_code == 401
            assert r_evt_anon.json()["error_code"] == "ERR_AUTH_REQUIRED"
            assert r_evt_anon.headers["content-type"].startswith("application/problem+json")

            # 4. GET /api/v1/events/stream -> 403 for outsider without workspace scope
            r_evt_forbidden = await client.get(
                "/api/v1/events/stream",
                params={"workspace_id": ws_id, "live": "false"},
                headers=outsider_auth,
            )
            assert r_evt_forbidden.status_code == 403
            assert r_evt_forbidden.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"
            assert r_evt_forbidden.headers["content-type"].startswith("application/problem+json")

            # 5. Claim a step in ws_id (PG18) -> authorized Bearer streams 200 text/event-stream
            r_claim = await client.post(
                "/api/v1/runs/0195f232-0000-7000-8000-000000000001/steps/0195f232-0000-7000-8000-000000000002/claim",
                headers=admin_auth,
                json={
                    "workspace_id": ws_id,
                    "step_key": "step-sse-232",
                    "ttl_seconds": 900,
                    "force": False,
                },
            )
            assert r_claim.status_code == 200, r_claim.text
            task_id = r_claim.json()["notification"]["id"]

            r_evt_ok = await client.get(
                "/api/v1/events/stream",
                params={"workspace_id": ws_id, "live": "false"},
                headers=admin_auth,
            )
            assert r_evt_ok.status_code == 200, r_evt_ok.text
            assert "text/event-stream" in r_evt_ok.headers["content-type"]
            assert "event: connected" in r_evt_ok.text
            assert "event: task.claim.locked" in r_evt_ok.text
            assert ws_id in r_evt_ok.text

            # 5b. Release claim (no workspace_id) -> OPEN + task.claim.released
            r_release = await client.post(
                f"/api/v1/tasks/{task_id}/release",
                headers=admin_auth,
                json={"force": False},
            )
            assert r_release.status_code == 200, r_release.text

            # 5c. Observer header on write endpoint -> 403 ERR_OBSERVER_MODE_READ_ONLY (L110)
            r_obs_hdr = await client.post(
                f"/api/v1/tasks/{task_id}/claim",
                headers={**admin_auth, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                json={"workspace_id": ws_id, "ttl_seconds": 900, "force": False},
            )
            assert r_obs_hdr.status_code == 403
            assert r_obs_hdr.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            # 5d. Rollup supervisor on STANDARD child workspace -> READ_ONLY_OBSERVER 403 (L119)
            r_ws_std = await client.post(
                "/api/v1/workspaces",
                headers=admin_auth,
                json={
                    "name": "Espace Standard 23.2",
                    "slug": "espace-std-232",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                    "owner_org_unit_id": team_id,
                },
            )
            assert r_ws_std.status_code == 201, r_ws_std.text
            ws_std_id = r_ws_std.json()["id"]

            r_rollup = await client.post(
                "/api/v1/settings/iam/accounts",
                headers=admin_auth,
                json={
                    "account_kind": "HUMAN",
                    "display_name": "Rollup Lead 23.2",
                    "email": "rollup.232@orcia.ia",
                    "principal_id": "rollup.232@orcia.ia",
                    "roles": ["TEAM_LEAD"],
                    "team_ids": [bu_id],
                    "status": "ACTIVE",
                },
            )
            assert r_rollup.status_code in (200, 201), r_rollup.text
            rollup_pw = r_rollup.json()["temporary_password"]
            r_rollup_login = await client.post(
                "/api/v1/auth/login/local",
                json={"email": "rollup.232@orcia.ia", "password": rollup_pw},
            )
            assert r_rollup_login.status_code == 200, r_rollup_login.text
            rollup_auth = {"Authorization": f"Bearer {r_rollup_login.json()['access_token']}"}

            r_rollup_write = await client.post(
                "/api/v1/runs/0195f232-0000-7000-8000-000000000003/steps/0195f232-0000-7000-8000-000000000004/claim",
                headers=rollup_auth,
                json={
                    "workspace_id": ws_std_id,
                    "step_key": "step-rollup-232",
                    "ttl_seconds": 900,
                    "force": False,
                },
            )
            assert r_rollup_write.status_code == 403
            assert r_rollup_write.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            r_evt_released = await client.get(
                "/api/v1/events/stream",
                params={"workspace_id": ws_id, "live": "false"},
                headers=admin_auth,
            )
            assert r_evt_released.status_code == 200
            assert "event: task.claim.released" in r_evt_released.text

            # 6. Configure active embedding model in PG18, then test three-speed/stream
            r_emb = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=admin_auth,
                json={
                    "scope_level": "GLOBAL",
                    "scope_id": ws_id,
                    "display_name": "Embedding 23.2 Cassette",
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

            turn_payload = {
                "workspace_id": ws_id,
                "hat": "PLATFORM_ADMIN",
                "user_prompt": "Résume l'état du projet en une phrase.",
                "requested_speed": "SPEED_1_FAST",
                "deep_audit_pill_active": False,
                "requested_tier": "medium",
                "thinking_effort": "balanced",
                "conversation_history": [],
                "locale": "fr",
            }

            r_stream_anon = await client.post(
                "/api/v1/assistant/three-speed/stream",
                json=turn_payload,
            )
            assert r_stream_anon.status_code == 401
            assert r_stream_anon.json()["error_code"] == "ERR_AUTH_REQUIRED"

            r_stream_ok = await client.post(
                "/api/v1/assistant/three-speed/stream",
                headers=admin_auth,
                json=turn_payload,
            )
            assert r_stream_ok.status_code == 200, r_stream_ok.text
            assert "text/event-stream" in r_stream_ok.headers["content-type"]
            assert "event: cache_status" in r_stream_ok.text
            assert "event: token_delta" in r_stream_ok.text
            assert "event: turn_completed" in r_stream_ok.text

        # 7. Verify PostgreSQL 18 persisted state directly
        async with engine.connect() as conn:
            notif_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, status FROM task_notifications "
                        "WHERE id::text = :tid AND status = 'OPEN'"
                    ),
                    {"tid": task_id},
                )
            ).all()
            assert len(notif_rows) == 1

            emb_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT model_name, is_active FROM workspace_llm_tier_mappings "
                        "WHERE usage = 'embedding' AND is_active = TRUE"
                    )
                )
            ).all()
            assert len(emb_rows) >= 1
    finally:
        await engine.dispose()
