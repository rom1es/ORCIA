"""Layer 2 Real PG18 + Redis 7.4 Integration Tests for `Story 30.3` (`UX30-06`, `UX30-07`)."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_api.main import create_app

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[3]
_SEEDED_WS_ID = "0192c4e0-0000-7000-8000-000000000201"
_CONF_WS_ID = "0192c4e0-0000-7000-8000-000000000203"
_FORBIDDEN_WS_ID = "0195f000-0000-7000-8000-000000009999"


def _prepare_sock_dir(prefix: str) -> Path:
    target = Path(tempfile.mkdtemp(prefix=f"orcia_{prefix}_"))
    target.chmod(0o777)
    return target


def _load_reset_script() -> Any:
    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
    spec = importlib.util.spec_from_file_location("reset_db_first_boot_30_3", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pg18_and_redis74_urls() -> Iterator[tuple[str, str]]:
    """Spin up ephemeral PostgreSQL 18 (`pgvector:pg18`) and Redis 7.4 containers."""
    pg_sock_dir = _prepare_sock_dir("pg18")
    rd_sock_dir = _prepare_sock_dir("rd74")
    rd_sock_path = rd_sock_dir / "redis.sock"

    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
    )
    redis_container = (
        DockerContainer("redis:7.4.2-alpine")
        .with_volume_mapping(str(rd_sock_dir), "/sock", "rw")
        .with_command("redis-server --unixsocket /sock/redis.sock --unixsocketperm 777 --port 6379")
    )

    try:
        with pg_container as pg, redis_container as rc:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            wait_for_logs(rc, "Ready to accept connections", timeout=20)
            for _ in range(40):
                if (pg_sock_dir / ".s.PGSQL.5432").exists() and rd_sock_path.exists():
                    break
                time.sleep(0.15)
            pg_auth = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            pg_url = f"postgresql+asyncpg://{pg_auth}@/orcia?host={pg_sock_dir}"
            redis_url = f"unix://{rd_sock_path}"
            yield pg_url, redis_url
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
        shutil.rmtree(rd_sock_dir, ignore_errors=True)


async def test_story_30_3_pg18_pending_runs_scope_guard_cold_rehydration_and_live_guard(
    pg18_and_redis74_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Alembic 30.3 reversibility, Day-0 empty runs, live guard, and F5 survival."""
    pg_url, redis_url = pg18_and_redis74_urls
    alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", pg_url)

    engine = create_async_engine(pg_url)
    try:
        for _ in range(30):
            try:
                async with engine.connect() as probe:
                    await probe.execute(sa.text("SELECT 1"))
                break
            except Exception:
                time.sleep(0.2)

        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sc: (
                    alembic_cfg.attributes.__setitem__("connection", sc),
                    command.upgrade(alembic_cfg, "head"),
                    command.downgrade(alembic_cfg, "20261122_267"),
                    command.upgrade(alembic_cfg, "head"),
                )
            )

        monkeypatch.setenv("DATABASE_URL", pg_url)
        monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
        monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
        monkeypatch.setenv("REDIS_URL", redis_url)
        monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
        monkeypatch.delenv("ORCIA_LLM_GATEWAY", raising=False)
        monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

        # 1. Live mode (non-cassette) on clean Day-0: 0 pending runs & 422 on missing LLM
        app_live = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_live),
            base_url="http://testserver",
        ) as live_client:
            day0_global = await live_client.get(
                "/api/v1/workflows/v2/runs",
                params={"workspace_id": "scope-global", "persona_key": "marc"},
            )
            assert day0_global.status_code == 200, day0_global.text
            assert day0_global.json()["items"] == []
            assert day0_global.json()["pending_count"] == 0

            missing_llm = await live_client.post(
                "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
                params={"persona_key": "marc"},
                headers={"Accept-Language": "fr"},
                json={"inputs": {"objective": "Qualification"}, "workspace_id": _SEEDED_WS_ID},
            )
            assert missing_llm.status_code == 422
            assert missing_llm.json()["error_code"] == "ERR_NO_ACTIVE_CHAT_MODEL_DETAIL"
            assert missing_llm.json()["trace_id"]

        # 2. Seed org_unit & workspace in PG18, then run cassette workflow with ScopeAccessGuard
        from uuid import UUID

        async with engine.begin() as conn:
            ou_uuid = UUID("0192c4e0-0000-7000-8000-000000000101")
            other_ou_uuid = UUID("0192c4e0-0000-7000-8000-000000000102")
            marc_uuid = UUID("0192c4e0-0000-7000-8000-000000000603")
            nadia_uuid = UUID("0192c4e0-0000-7000-8000-000000000604")
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type) "
                    "VALUES (:id, 'ou-30-3', 'Product 30.3', 'TEAM'), "
                    "(:other_id, 'ou-30-3-other', 'Other 30.3', 'TEAM') "
                    "ON CONFLICT (id) DO NOTHING;"
                ),
                {"id": ou_uuid, "other_id": other_ou_uuid},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO users (id, email, display_name, auth_mode, "
                    "human_profile_archetype, platform_role, primary_org_unit_id, is_active) "
                    "VALUES (:marc_id, 'marc.lead@orcia.io', 'Marc', 'HYBRID', "
                    "'TEAM_LEAD', 'CONTRIBUTOR', :ou_id, TRUE), "
                    "(:nadia_id, 'nadia.dev@orcia.io', 'Nadia', 'LOCAL', "
                    "'DEVELOPER', 'CONTRIBUTOR', :other_ou_id, TRUE) "
                    "ON CONFLICT (id) DO NOTHING;"
                ),
                {
                    "marc_id": marc_uuid,
                    "nadia_id": nadia_uuid,
                    "ou_id": ou_uuid,
                    "other_ou_id": other_ou_uuid,
                },
            )
            await conn.execute(
                sa.text("UPDATE org_units SET lead_user_id = :lead_id WHERE id = :id;"),
                {"id": ou_uuid, "lead_id": str(marc_uuid)},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                    "VALUES (:id, 'ws-30-3', 'Workspace 30.3', :ou_id, 'STANDARD'), "
                    "(:conf_id, 'ws-30-3-conf', 'Confidential 30.3', :ou_id, "
                    "'CONFIDENTIAL_RESTRICTED'), "
                    "(:fid, 'ws-30-3-forbidden', 'Forbidden WS', :other_ou_id, 'STANDARD') "
                    "ON CONFLICT (id) DO NOTHING;"
                ),
                {
                    "id": UUID(_SEEDED_WS_ID),
                    "conf_id": UUID(_CONF_WS_ID),
                    "ou_id": ou_uuid,
                    "fid": UUID(_FORBIDDEN_WS_ID),
                    "other_ou_id": other_ou_uuid,
                },
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workspace_memberships "
                    "(id, workspace_id, user_id, role, access_mode) "
                    "VALUES (:m_pay, :ws_id, :marc_id, 'TEAM_LEAD', "
                    "'CONTRIBUTOR_ACTION_REQUIRED'), "
                    "(:m_conf, :conf_id, :marc_id, 'TEAM_LEAD', 'CONTRIBUTOR_ACTION_REQUIRED'), "
                    "(:m_obs, :ws_id, :nadia_id, 'OBSERVER', 'READ_ONLY_OBSERVER') "
                    "ON CONFLICT DO NOTHING;"
                ),
                {
                    "m_pay": UUID("0195f000-0000-7000-8000-000000003039"),
                    "m_conf": UUID("0195f000-0000-7000-8000-000000003040"),
                    "m_obs": UUID("0195f000-0000-7000-8000-000000003041"),
                    "ws_id": UUID(_SEEDED_WS_ID),
                    "conf_id": UUID(_CONF_WS_ID),
                    "marc_id": marc_uuid,
                    "nadia_id": nadia_uuid,
                },
            )

        monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
        app_one = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_one),
            base_url="http://testserver",
        ) as client1:
            start_resp = await client1.post(
                "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
                params={"persona_key": "marc"},
                json={"inputs": {"demande_source": "MCIA-303"}, "workspace_id": _SEEDED_WS_ID},
            )
            assert start_resp.status_code == 200, start_resp.text
            run = start_resp.json()["run"]
            run_id = run["run_id"]
            assert run["status"] == "WAITING_SUBSTEP_HITL"

            conf_start = await client1.post(
                "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
                params={"persona_key": "marc"},
                json={"inputs": {"demande_source": "CONF-303"}, "workspace_id": _CONF_WS_ID},
            )
            assert conf_start.status_code == 200, conf_start.text
            conf_run_id = conf_start.json()["run"]["run_id"]

            # Unauthorized workspace rejected by ScopeAccessGuard for non-admin user
            denied = await client1.get(
                "/api/v1/workflows/v2/runs",
                params={"workspace_id": _FORBIDDEN_WS_ID, "persona_key": "marc"},
            )
            assert denied.status_code == 403

            # Non-member rejected on CONFIDENTIAL_RESTRICTED GET run & RAM-hot HITL signal
            conf_get_denied = await client1.get(
                f"/api/v1/runs/{conf_run_id}",
                params={"persona_key": "nadia"},
            )
            assert conf_get_denied.status_code == 403
            assert conf_get_denied.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            conf_sig_denied = await client1.post(
                f"/api/v1/runs/{conf_run_id}/hitl-signal",
                params={"persona_key": "nadia"},
                json={"action": "APPROVE", "actor_id": "nadia"},
            )
            assert conf_sig_denied.status_code == 403
            assert conf_sig_denied.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            # Global & workspace-scoped READ_ONLY_OBSERVER rejected on RAM-hot HITL signal
            obs_sig = await client1.post(
                f"/api/v1/runs/{run_id}/hitl-signal",
                params={"persona_key": "claire"},
                json={"action": "APPROVE", "actor_id": "claire"},
            )
            assert obs_sig.status_code == 403
            assert obs_sig.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            ws_obs_sig = await client1.post(
                f"/api/v1/runs/{run_id}/hitl-signal",
                params={"persona_key": "nadia"},
                json={"action": "APPROVE", "actor_id": "nadia"},
            )
            assert ws_obs_sig.status_code == 403
            assert ws_obs_sig.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # Direct SQL verification in PostgreSQL 18
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        "SELECT run_id, workspace_id::text, status "
                        "FROM workflow_v2_runs WHERE run_id = :run_id"
                    ),
                    {"run_id": run_id},
                )
            ).first()
            assert row is not None
            assert row[0] == run_id
            assert row[1] == _SEEDED_WS_ID
            assert row[2] == "WAITING_SUBSTEP_HITL"

        # 3. Cold F5 survival on brand-new `create_app()` (0 RAM state) & complete lifecycle
        app_two = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_two),
            base_url="http://testserver",
        ) as client2:
            pending_ws = await client2.get(
                "/api/v1/workflows/v2/runs",
                params={"workspace_id": _SEEDED_WS_ID, "persona_key": "marc"},
            )
            assert pending_ws.status_code == 200
            assert pending_ws.json()["pending_count"] == 1
            assert pending_ws.json()["items"][0]["run_id"] == run_id
            assert pending_ws.json()["items"][0]["status"] == "WAITING_SUBSTEP_HITL"

            pending_global = await client2.get(
                "/api/v1/workflows/v2/runs",
                params={"workspace_id": "scope-global", "persona_key": "marc"},
            )
            assert pending_global.status_code == 200
            assert any(item["run_id"] == run_id for item in pending_global.json()["items"])

            cold_get = await client2.get(
                f"/api/v1/runs/{run_id}",
                params={"persona_key": "marc"},
            )
            assert cold_get.status_code == 200
            assert cold_get.json()["run"]["run_id"] == run_id

            cold_conf_denied = await client2.get(
                f"/api/v1/runs/{conf_run_id}",
                params={"persona_key": "nadia"},
            )
            assert cold_conf_denied.status_code == 403
            assert cold_conf_denied.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            cold_ws_obs_denied = await client2.post(
                f"/api/v1/runs/{run_id}/hitl-signal",
                params={"persona_key": "nadia"},
                json={"action": "APPROVE", "actor_id": "nadia"},
            )
            assert cold_ws_obs_denied.status_code == 403
            assert cold_ws_obs_denied.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            # Advance through sub-steps & final anchor to COMPLETED_APPROVED
            for _ in range(4):
                sig = await client2.post(
                    f"/api/v1/runs/{run_id}/hitl-signal",
                    params={"persona_key": "marc"},
                    json={"action": "APPROVE", "actor_id": "marc"},
                )
                assert sig.status_code == 200
                if sig.json()["run"]["status"] == "COMPLETED_APPROVED":
                    break

            after_done = await client2.get(
                "/api/v1/workflows/v2/runs",
                params={"workspace_id": _SEEDED_WS_ID, "persona_key": "marc"},
            )
            assert after_done.status_code == 200
            assert after_done.json()["pending_count"] == 0
            assert after_done.json()["items"] == []

            with_completed = await client2.get(
                "/api/v1/workflows/v2/runs",
                params={
                    "workspace_id": _SEEDED_WS_ID,
                    "include_completed": "true",
                    "persona_key": "marc",
                },
            )
            assert with_completed.status_code == 200
            assert with_completed.json()["items"][0]["status"] == "COMPLETED"

        # 4. Day-0 Reset clears `workflow_v2_runs`
        reset_mod = _load_reset_script()
        assert "workflow_v2_runs" in reset_mod.ORDERED_MUTABLE_TABLES_TO_CLEAR
        await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        async with engine.connect() as conn:
            remaining = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_v2_runs"))
            ).scalar_one()
            assert remaining == 0
    finally:
        await engine.dispose()
