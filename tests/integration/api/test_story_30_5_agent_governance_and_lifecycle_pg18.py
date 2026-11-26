"""Layer 2 Real PG18 + Redis 7.4 Integration Tests for `Story 30.5` (`UX30-11`..`UX30-15`)."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

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


def _prepare_sock_dir(prefix: str) -> Path:
    target = Path(tempfile.mkdtemp(prefix=f"orcia_{prefix}_"))
    target.chmod(0o777)
    return target


def _load_reset_script() -> Any:
    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
    spec = importlib.util.spec_from_file_location("reset_db_first_boot_30_5", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


async def _seed_marc_workspace_scope(engine: Any) -> None:
    async with engine.begin() as conn:
        ou_uuid = UUID("0192c4e0-0000-7000-8000-000000000101")
        marc_uuid = UUID("0192c4e0-0000-7000-8000-000000000603")
        ws_uuid = UUID(_SEEDED_WS_ID)
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type) "
                "VALUES (:id, 'ou-30-5', 'Product 30.5', 'TEAM') ON CONFLICT (id) DO NOTHING;"
            ),
            {"id": ou_uuid},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO users (id, email, display_name, auth_mode, "
                "human_profile_archetype, platform_role, primary_org_unit_id, is_active) "
                "VALUES (:id, 'marc.lead@orcia.io', 'Marc', 'HYBRID', "
                "'TEAM_LEAD', 'CONTRIBUTOR', :ou_id, TRUE) ON CONFLICT (id) DO NOTHING;"
            ),
            {"id": marc_uuid, "ou_id": ou_uuid},
        )
        await conn.execute(
            sa.text("UPDATE org_units SET lead_user_id = :lead_id WHERE id = :id;"),
            {"lead_id": str(marc_uuid), "id": ou_uuid},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (:id, 'ws-30-5', 'Workspace 30.5', :ou_id, 'STANDARD') "
                "ON CONFLICT (id) DO NOTHING;"
            ),
            {"id": ws_uuid, "ou_id": ou_uuid},
        )


@pytest.fixture(scope="module")
def pg18_and_redis74_urls() -> Iterator[tuple[str, str]]:
    """Spin up ephemeral PostgreSQL 18 (`pgvector:pg18`) and Redis 7.4 containers."""
    pg_sock_dir = _prepare_sock_dir("pg18_30_5")
    rd_sock_dir = _prepare_sock_dir("rd74_30_5")
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
            yield (
                f"postgresql+asyncpg://{pg_auth}@/orcia?host={pg_sock_dir}",
                f"unix://{rd_sock_path}",
            )
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
        shutil.rmtree(rd_sock_dir, ignore_errors=True)


async def test_story_30_5_pg18_agent_governance_cold_sync_and_draft_lifecycle(
    pg18_and_redis74_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify real PG18 cold sync on PATCH governance, DRAFT 422 blocking, and Day-0 reset."""
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
                )
            )

        await _seed_marc_workspace_scope(engine)

        monkeypatch.setenv("DATABASE_URL", pg_url)
        monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
        monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
        monkeypatch.setenv("REDIS_URL", redis_url)
        monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "1")
        monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

        agent_id = "agent-pg18-conformite"
        # 1. Boot #1: create DRAFT agent, enforce 422 on DRAFT & 403 on observer, then pass bench
        app1 = create_app()
        async with (
            app1.router.lifespan_context(app1),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app1), base_url="http://testserver"
            ) as c1,
        ):
            created = await c1.post(
                "/api/v1/agents-and-skills/agents?persona_key=marc",
                json={
                    "agent_id": agent_id,
                    "name": "Agent PG18 Conformite",
                    "role_mission": "Audit enterprise architecture",
                    "instructions": "Inspect controls with evidence.",
                    "thinking_level": "medium",
                },
            )
            assert created.status_code == 200, created.text
            assert created.json()["lifecycle_status"] == "DRAFT"
            assert created.json()["test_bench_status"] == "UNTESTED"

            obs = await c1.patch(
                f"/api/v1/agents-and-skills/agents/{agent_id}/governance?persona_key=claire",
                json={"mcp_exposed": True},
            )
            assert obs.status_code == 403
            assert obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            mcp_draft = await c1.patch(
                f"/api/v1/agents-and-skills/agents/{agent_id}/governance?persona_key=marc",
                json={"mcp_exposed": True},
            )
            assert mcp_draft.status_code == 422
            assert mcp_draft.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

            turn_draft = await c1.post(
                "/api/v1/assistant/turns?persona_key=marc",
                json={"workspace_id": _SEEDED_WS_ID, "user_prompt": "Check @pg18-conformite"},
            )
            assert turn_draft.status_code == 422
            assert turn_draft.json()["error_code"] == "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED"

            exec_ok = await c1.post(
                f"/api/v1/agents-and-skills/agents/{agent_id}/execute?persona_key=marc",
                json={"prompt": "Validate compliance report"},
            )
            assert exec_ok.status_code == 200, exec_ok.text
            assert exec_ok.json()["lifecycle_status"] == "ACTIVE"
            assert exec_ok.json()["test_bench_status"] == "PASSED"

        # 2. Boot #2 (0 RAM state): direct PATCH .../governance WITHOUT prior GET must succeed
        app2 = create_app()
        async with (
            app2.router.lifespan_context(app2),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app2), base_url="http://testserver"
            ) as c2,
        ):
            mcp_ok = await c2.patch(
                f"/api/v1/agents-and-skills/agents/{agent_id}/governance?persona_key=marc",
                json={"mcp_exposed": True},
            )
            assert mcp_ok.status_code == 200, mcp_ok.text
            assert mcp_ok.json()["mcp_exposed"] is True
            assert mcp_ok.json()["lifecycle_status"] == "ACTIVE"

            turn_ok = await c2.post(
                "/api/v1/assistant/turns?persona_key=marc",
                json={"workspace_id": _SEEDED_WS_ID, "user_prompt": "Check @pg18-conformite"},
            )
            assert turn_ok.status_code == 202, turn_ok.text

        # Direct SQL check in PG18
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        "SELECT metadata_jsonb FROM catalog_items "
                        "WHERE resource_id = :resource_id AND item_type = 'USER_AGENT' "
                        "ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"resource_id": agent_id},
                )
            ).first()
            assert row is not None
            meta = row[0] if isinstance(row[0], dict) else json.loads(str(row[0]))
            assert meta["mcp_exposed"] is True
            assert meta["lifecycle_status"] == "ACTIVE"
            assert meta["test_bench_status"] == "PASSED"

        # 3. Boot #3: demote ACTIVE -> DRAFT clears mcp_exposed in PG18
        app3 = create_app()
        async with (
            app3.router.lifespan_context(app3),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app3), base_url="http://testserver"
            ) as c3,
        ):
            demote = await c3.patch(
                f"/api/v1/agents-and-skills/agents/{agent_id}/governance?persona_key=marc",
                json={"lifecycle_status": "DRAFT"},
            )
            assert demote.status_code == 200
            assert demote.json()["lifecycle_status"] == "DRAFT"
            assert demote.json()["mcp_exposed"] is False

        # 4. Day-0 Reset clears custom agent rows cleanly
        reset_mod = _load_reset_script()
        await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        async with engine.connect() as conn:
            remaining = (
                await conn.execute(
                    sa.text("SELECT COUNT(*) FROM catalog_items WHERE resource_id = :resource_id"),
                    {"resource_id": agent_id},
                )
            ).scalar_one()
            assert remaining == 0
    finally:
        await engine.dispose()
