"""Story 26.4a — Layer 2 Real PG18 + Redis 7.4 Multi-Worker Integration Tests."""

from __future__ import annotations

import asyncio
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import redis.asyncio as aioredis
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer

from orcia_api.main import create_app
from orcia_kernel.ids import new_uuid7_str

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_26_4a"
DB_USER = "orcia"
DB_PASSWORD = "orcia_26_4a_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg18_and_redis74() -> Iterator[tuple[str, str]]:
    """Spin up real ephemeral PostgreSQL 18 (`pgvector:pg18`) and Redis 7.4 containers."""
    pg_container = PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    )
    redis_container = DockerContainer("redis:7.4.2-alpine").with_exposed_ports(6379)

    with pg_container as pg, redis_container as rc:
        wait_for_logs(rc, "Ready to accept connections", timeout=20)
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_url = f"redis://127.0.0.1:{rc.get_exposed_port(6379)}/0"
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
        yield pg_url, redis_url


def test_alembic_26_4a_upgrade_downgrade_upgrade_reversibility(
    pg18_and_redis74: tuple[str, str],
) -> None:
    """Verify Story 26.4a Alembic migration cleanly downgrades and re-upgrades on PG18."""
    pg_url, _ = pg18_and_redis74
    env = {
        "PATH": "/usr/bin:/bin",
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    alembic_bin = str(REPO_ROOT / ".venv/bin/alembic")
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "downgrade", "20261120_2403"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


@pytest.mark.asyncio
async def test_two_workers_redis_lock_outbox_events_and_hub_snapshot_invalidation_pg18(
    pg18_and_redis74: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify 2 `create_app()` instances sharing PG18 + Redis 7.4 for locks, Outbox & Hub TTL."""
    pg_url, redis_url = pg18_and_redis74
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_ENV", "local")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-26-4a-jwt-secret-00000001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-26-4a-vault-key-00000001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")

    engine = create_async_engine(pg_url)
    redis_probe = aioredis.from_url(redis_url, decode_responses=True)
    try:
        app_w1 = create_app()
        app_w2 = create_app()
        assert app_w1.dependency_overrides == {} and app_w2.dependency_overrides == {}

        async with (
            app_w1.router.lifespan_context(app_w1),
            app_w2.router.lifespan_context(app_w2),
            AsyncClient(transport=ASGITransport(app=app_w1), base_url="http://w1") as c1,
            AsyncClient(transport=ASGITransport(app=app_w2), base_url="http://w2") as c2,
        ):
            boot = await c1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin264a@orcia.io",
                    "display_name": "Admin 26.4a",
                    "password": "Admin264a!StrongPassword",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert boot.status_code in (200, 201), boot.text
            admin_token = boot.json()["access_token"]
            hdrs_admin = {"Authorization": f"Bearer {admin_token}"}

            # Invite peer contributor inside the same workspace
            ou_res = await c1.post(
                "/api/v1/org-units",
                headers=hdrs_admin,
                json={"name": "BU 26.4a", "slug": "bu-26-4a", "kind": "BU"},
            )
            assert ou_res.status_code in (200, 201), ou_res.text
            ou_id = ou_res.json()["id"]

            ws_res = await c1.post(
                "/api/v1/workspaces",
                headers=hdrs_admin,
                json={
                    "name": "Workspace 26.4a",
                    "slug": "ws-26-4a",
                    "owner_org_unit_id": ou_id,
                    "visibility_mode": "STANDARD",
                },
            )
            assert ws_res.status_code in (200, 201), ws_res.text
            ws_id = ws_res.json()["id"]

            peer_email = "peer264a@orcia.io"
            inv_res = await c1.post(
                "/api/v1/settings/iam/accounts",
                headers=hdrs_admin,
                json={
                    "email": peer_email,
                    "display_name": "Peer 26.4a",
                    "roles": ["CONTRIBUTOR"],
                    "team_ids": [ou_id],
                },
            )
            assert inv_res.status_code in (200, 201), inv_res.text
            peer_temp_pw = inv_res.json()["temporary_password"]
            assert peer_temp_pw
            peer_login = await c2.post(
                "/api/v1/auth/login/local",
                json={
                    "email": peer_email,
                    "password": peer_temp_pw,  # pragma: allowlist secret
                },
            )
            assert peer_login.status_code == 200, peer_login.text
            peer_id = peer_login.json()["user_id"]
            hdrs_peer = {"Authorization": f"Bearer {peer_login.json()['access_token']}"}

            # Grant peer membership in ws-26-4a
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspace_memberships
                            (id, workspace_id, user_id, role, access_mode)
                        VALUES (
                            CAST(:mid AS uuid),
                            CAST(:ws AS uuid),
                            CAST(:uid AS uuid),
                            'CONTRIBUTOR',
                            'CONTRIBUTOR_ACTION_REQUIRED'
                        )
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {"mid": new_uuid7_str(), "ws": ws_id, "uid": peer_id},
                )

            # 1. Create folder + thread on w1, share with workspace
            fld_res = await c1.post(
                "/api/v1/assistant/folders",
                headers=hdrs_admin,
                json={"workspace_id": ws_id, "title": "Shared Folder 26.4a"},
            )
            assert fld_res.status_code == 200, fld_res.text
            fld_id = fld_res.json()["folder_id"]

            share_res = await c1.post(
                f"/api/v1/assistant/folders/{fld_id}/share",
                headers=hdrs_admin,
                json={
                    "workspace_id": ws_id,
                    "visibility_mode": "WORKSPACE_OPEN",
                    "shares": [],
                },
            )
            assert share_res.status_code == 200, share_res.text

            thr_res = await c1.post(
                "/api/v1/assistant/threads",
                headers=hdrs_admin,
                json={"workspace_id": ws_id, "folder_id": fld_id, "title": "Lock Thread 26.4a"},
            )
            assert thr_res.status_code == 200, thr_res.text
            thr_id = thr_res.json()["thread_id"]

            # Admin acquires Redis thread lock on Worker 1 (simulating active turn across workers)
            from orcia_api.routers._assistant_background_registry import (
                get_thread_turn_lock_from_request,
            )

            class _ReqStub:
                def __init__(self, app_obj: object) -> None:
                    self.app = app_obj

            lock1 = get_thread_turn_lock_from_request(_ReqStub(app_w1))
            lock_key, lock_token = await lock1.acquire_async(
                thread_id=thr_id, user_id="admin-26-4a", ttl_seconds=60
            )
            assert lock_key == f"lock:thread:{thr_id}" and lock_token
            lock_val = await redis_probe.get(f"lock:thread:{thr_id}")
            assert lock_val is not None
            ttl_val = await redis_probe.ttl(f"lock:thread:{thr_id}")
            assert 1 <= ttl_val <= 60

            # Peer on Worker 2 is blocked by Redis SET NX EX lock -> HTTP 409
            blocked = await c2.post(
                "/api/v1/assistant/turns",
                headers=hdrs_peer,
                json={
                    "workspace_id": ws_id,
                    "thread_id": thr_id,
                    "folder_id": fld_id,
                    "user_prompt": "Concurrent peer attempt",
                },
            )
            assert blocked.status_code == 409, blocked.text
            assert blocked.json()["error_code"] == "ERR_THREAD_TURN_LOCK_HELD"

            # Admin releases lock on Worker 1 -> Peer succeeds on Worker 2
            released = await lock1.release_async(
                thread_id=thr_id, user_id="admin-26-4a", token=lock_token
            )
            assert released is True
            assert await redis_probe.get(f"lock:thread:{thr_id}") is None

            peer_turn = await c2.post(
                "/api/v1/assistant/turns",
                headers=hdrs_peer,
                json={
                    "workspace_id": ws_id,
                    "thread_id": thr_id,
                    "folder_id": fld_id,
                    "user_prompt": "Peer turn succeeds after Lua release",
                },
            )
            assert peer_turn.status_code == 202, peer_turn.text
            peer_stream = await c2.get(peer_turn.json()["stream_url"], headers=hdrs_peer)
            assert peer_stream.status_code == 200
            assert "event: turn_completed" in peer_stream.text

            # 2. Outbox emission via Assistant turn + governance update -> SELECT PG18
            v2_turn = await c1.post(
                "/api/v1/assistant/turns",
                headers=hdrs_admin,
                json={"workspace_id": ws_id, "user_prompt": "Test outbox lifecycle"},
            )
            assert v2_turn.status_code == 202, v2_turn.text
            v2_turn_id = v2_turn.json()["turn_id"]

            # Drain stream so producer completes
            async with c1.stream(
                "GET", f"/api/v1/assistant/turns/{v2_turn_id}/stream", headers=hdrs_admin
            ) as stream_resp:
                assert stream_resp.status_code == 200
                _ = await stream_resp.aread()
            await asyncio.sleep(0.05)

            gov_upd = await c1.put(
                "/api/v1/assistant/governance/mode-a/workspace",
                headers=hdrs_admin,
                json={"workspace_id": ws_id, "workspace_instructions": "Strict outbox test"},
            )
            assert gov_upd.status_code == 200, gov_upd.text

            async with engine.connect() as conn:
                outbox_rows = (
                    await conn.execute(
                        sa.text(
                            """
                            SELECT event_type, aggregate_id
                            FROM domain_events_outbox
                            WHERE workspace_id = CAST(:ws AS uuid)
                            """
                        ),
                        {"ws": ws_id},
                    )
                ).fetchall()
            event_types = {str(r[0]) for r in outbox_rows}
            assert "AssistantTurnStarted" in event_types
            assert "AssistantTurnCompleted" in event_types
            assert "SettingsChanged" in event_types

            # 3. AI Hub mutation on Worker 1 invalidates platform_setup_snapshot on Worker 2
            snap_put = await c1.put(
                "/api/v1/bootstrap/platform-setup-state",
                headers=hdrs_admin,
                json={
                    "llm_tiers": [
                        {
                            "tier": "medium",
                            "primaryModel": "snap-model-v1",
                            "modelFamily": "OpenAI",
                            "endpointUrl": "https://api.openai.com/v1",
                        }
                    ]
                },
            )
            assert snap_put.status_code == 200
            snap_get_w2 = await c2.get(
                "/api/v1/bootstrap/platform-setup-state",
                params={"detail": "true"},
                headers=hdrs_admin,
            )
            assert snap_get_w2.status_code == 200
            assert getattr(app_w2.state, "platform_setup_snapshot", None) is not None

            ver_before = await redis_probe.get("orcia:platform_setup_snapshot:version")
            hub_create = await c1.post(
                "/api/v1/settings/ai-models/mappings",
                headers=hdrs_admin,
                json={
                    "scope_level": "GLOBAL",
                    "scope_id": "00000000-0000-7000-8000-000000000000",
                    "display_name": "Hub Model 26.4a",
                    "inference_tier": "medium",
                    "effort": "default",
                    "provider_slug": "openai",
                    "model_family": "OpenAI",
                    "model_name": "gpt-4o-hub-264a",
                    "endpoint_uri": "https://api.openai.com/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "chat",
                },
            )
            assert hub_create.status_code == 201, hub_create.text
            ver_after = await redis_probe.get("orcia:platform_setup_snapshot:version")
            assert ver_after is not None and ver_after != ver_before
            assert getattr(app_w1.state, "platform_setup_snapshot", None) is None

            from orcia_core.bootstrap.setup_snapshot_cache import (
                get_valid_platform_setup_snapshot_async,
            )

            assert (
                await get_valid_platform_setup_snapshot_async(
                    app_w2.state, redis_client=app_w2.state.redis_client
                )
                is None
            )
    finally:
        await redis_probe.aclose()
        await engine.dispose()
