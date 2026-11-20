"""Layer 2 integration tests for Story 24.1 on real PG18 + Redis via `create_app()`."""

from __future__ import annotations

import importlib.util
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
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_story_24_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_24_1_pw"  # pragma: allowlist secret


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
async def test_alembic_24_1_upgrade_downgrade_roundtrip(infra_urls: tuple[str, str]) -> None:
    """Verify `20261120_2401` upgrade -> downgrade (`20261117_2003`) -> upgrade `head`."""
    pg_url, _ = infra_urls
    _run_alembic(pg_url, "upgrade", "20261120_2401")

    engine = create_async_engine(pg_url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            jira_tbl = (
                await conn.execute(sa.text("SELECT to_regclass('public.jira_staged_actions')"))
            ).scalar_one()
            mcp_tbl = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_governed_proposals')"))
            ).scalar_one()
            vsm_idx = (
                await conn.execute(
                    sa.text(
                        "SELECT 1 FROM pg_indexes WHERE tablename = 'vsm_definitions_v2' "
                        "AND indexname = 'ix_vsm_definitions_v2_pack_id'"
                    )
                )
            ).scalar_one_or_none()
        assert jira_tbl == "jira_staged_actions"
        assert mcp_tbl == "mcp_governed_proposals"
        assert vsm_idx == 1

        _run_alembic(pg_url, "downgrade", "20261117_2003")
        async with engine.connect() as conn:
            jira_after_down = (
                await conn.execute(sa.text("SELECT to_regclass('public.jira_staged_actions')"))
            ).scalar_one()
            mcp_after_down = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_governed_proposals')"))
            ).scalar_one()
        assert jira_after_down is None
        assert mcp_after_down is None

        _run_alembic(pg_url, "upgrade", "head")
        async with engine.connect() as conn:
            jira_head = (
                await conn.execute(sa.text("SELECT to_regclass('public.jira_staged_actions')"))
            ).scalar_one()
            mcp_head = (
                await conn.execute(sa.text("SELECT to_regclass('public.mcp_governed_proposals')"))
            ).scalar_one()
        assert jira_head == "jira_staged_actions"
        assert mcp_head == "mcp_governed_proposals"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_real_composition_root_jira_mcp_vsm_cold_pg18_and_reset(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify full HTTP -> PG18 persistence, cache eviction, cold reload, and Day-0 reset."""
    pg_url, redis_url = infra_urls
    _run_alembic(pg_url, "upgrade", "head")

    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-24-1-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-24-1-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    engine = create_async_engine(pg_url, poolclass=NullPool)
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
                    "email": "admin.241@orcia.ia",
                    "display_name": "Admin Story 24.1",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text
            admin_token = r_first.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {admin_token}"}

            r_ws = await client1.post(
                "/api/v1/workspaces",
                headers=auth_headers,
                json={
                    "name": "Espace Story 24.1",
                    "slug": "espace-story-24-1",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]

            # 1. Jira Staged -> Commit -> Webhook -> Evict -> Cold GET + SELECT PG18
            r_stage = await client1.post(
                "/api/v1/jira/actions/stage",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "run_id": "0195f241-0000-7000-8000-000000000101",
                    "step_execution_id": "0195f241-0000-7000-8000-000000000201",
                    "project_alias": "jira:product",
                    "action_type": "transition_issue",
                    "issue_key": "PAYBUILD-101",
                    "target_transition": "IN_REVIEW",
                    "summary": "Transition vers revue architecture",
                    "fields_payload": {"pr_url": "https://git.local/pr/241"},
                },
            )
            assert r_stage.status_code == 200, r_stage.text
            staged_id = r_stage.json()["staged_action"]["staged_action_id"]
            assert r_stage.json()["staged_action"]["status"] == "STAGED"

            r_commit = await client1.post(
                "/api/v1/jira/actions/commit",
                headers=auth_headers,
                json={
                    "staged_action_id": staged_id,
                    "gate_status": "PASS",
                    "run_lock_sha256": "sha256:241deadbeef",
                },
            )
            assert r_commit.status_code == 200, r_commit.text
            assert r_commit.json()["executed_action"]["status"] == "EXECUTED"

            r_wh = await client1.post(
                "/api/v1/webhooks/jira/issue-updated",
                headers=auth_headers,
                json={
                    "webhook_event": "jira:issue_updated",
                    "issue_key": "PAYBUILD-101",
                    "new_status": "Done",
                    "workspace_id": ws_id,
                    "run_id": "0195f241-0000-7000-8000-000000000101",
                    "step_execution_id": "0195f241-0000-7000-8000-000000000201",
                },
            )
            assert r_wh.status_code == 200, r_wh.text
            assert r_wh.json()["replay_triggered"] is True

            r_evict1 = await client1.post("/api/v1/_e2e/evict-memory-caches", headers=auth_headers)
            assert r_evict1.status_code == 200, r_evict1.text

            r_staged_cold = await client1.get(
                "/api/v1/jira/actions/staged",
                headers=auth_headers,
                params={"workspace_id": ws_id},
            )
            assert r_staged_cold.status_code == 200, r_staged_cold.text
            actions = r_staged_cold.json()["actions"]
            assert any(
                a["staged_action_id"] == staged_id and a["status"] == "EXECUTED" for a in actions
            )

            # 2. MCP governed proposals -> Evict -> blackboard.read + SELECT PG18
            r_mcp_blocked = await client1.post(
                "/api/v1/mcp/call",
                headers=auth_headers,
                json={
                    "tool_name": "blackboard.propose_draft",
                    "workspace_id": ws_id,
                    "arguments": {
                        "run_id": "run-mcp-241",
                        "section_key": "intention-metier",
                        "human_authored_required": True,
                        "content_markdown": "Blocked overwrite",
                    },
                },
            )
            assert r_mcp_blocked.status_code == 422
            assert r_mcp_blocked.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

            r_mcp_ok = await client1.post(
                "/api/v1/mcp/call",
                headers=auth_headers,
                json={
                    "tool_name": "blackboard.propose_draft",
                    "workspace_id": ws_id,
                    "ide_client": "cursor",
                    "arguments": {
                        "run_id": "run-mcp-241",
                        "section_key": "architecture-sequence",
                        "human_authored_required": False,
                        "content_markdown": "Proposition persistée PG18",
                    },
                },
            )
            assert r_mcp_ok.status_code == 200, r_mcp_ok.text
            proposal_id = r_mcp_ok.json()["data"]["proposal"]["proposal_id"]

            r_evict2 = await client1.post("/api/v1/_e2e/evict-memory-caches", headers=auth_headers)
            assert r_evict2.status_code == 200

            r_mcp_read = await client1.post(
                "/api/v1/mcp/call",
                headers=auth_headers,
                json={
                    "tool_name": "blackboard.read",
                    "workspace_id": ws_id,
                    "arguments": {"run_id": "run-mcp-241"},
                },
            )
            assert r_mcp_read.status_code == 200, r_mcp_read.text
            proposals = r_mcp_read.json()["data"]["draft_proposals"]
            assert any(p["proposal_id"] == proposal_id for p in proposals)

            # 3. VSM v2 -> Evict -> Cold GET + SELECT PG18
            r_vsm_list = await client1.get("/api/v1/vsm", headers=auth_headers)
            assert r_vsm_list.status_code == 200, r_vsm_list.text
            assert any(v["id"] == "vsm-mon-compte-idea-to-prod" for v in r_vsm_list.json()["items"])

            r_vsm_get = await client1.get(
                "/api/v1/vsm/vsm-mon-compte-idea-to-prod", headers=auth_headers
            )
            assert r_vsm_get.status_code == 200, r_vsm_get.text

            r_evict3 = await client1.post("/api/v1/_e2e/evict-memory-caches", headers=auth_headers)
            assert r_evict3.status_code == 200

            r_vsm_cold = await client1.get(
                "/api/v1/vsm/vsm-mon-compte-idea-to-prod", headers=auth_headers
            )
            assert r_vsm_cold.status_code == 200, r_vsm_cold.text
            assert r_vsm_cold.json()["id"] == "vsm-mon-compte-idea-to-prod"

        # Direct PostgreSQL 18 assertions
        async with engine.connect() as conn:
            jira_row = (
                await conn.execute(
                    sa.text(
                        "SELECT status, provenance_run_lock_sha256 FROM jira_staged_actions "
                        "WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": staged_id},
                )
            ).one()
            assert jira_row[0] == "EXECUTED"
            assert jira_row[1] == "sha256:241deadbeef"

            outbox_types = {
                str(r[0])
                for r in (
                    await conn.execute(
                        sa.text(
                            "SELECT event_type FROM domain_events_outbox "
                            "WHERE workspace_id = CAST(:ws AS uuid)"
                        ),
                        {"ws": ws_id},
                    )
                ).fetchall()
            }
            assert "ArtifactProduced" in outbox_types
            assert "StepCompleted" in outbox_types

            mcp_row = (
                await conn.execute(
                    sa.text(
                        "SELECT status, section_key FROM mcp_governed_proposals "
                        "WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": proposal_id},
                )
            ).one()
            assert mcp_row[0] == "PROPOSED"
            assert mcp_row[1] == "architecture-sequence"

            vsm_count = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM vsm_definitions_v2"))
            ).scalar_one()
            assert vsm_count >= 1

        # Second cold Composition Root instance reads everything from PG18
        app2 = create_app()
        assert app2.dependency_overrides == {}
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as client2,
        ):
            r_jira_2 = await client2.get(
                "/api/v1/jira/actions/staged",
                headers=auth_headers,
                params={"workspace_id": ws_id},
            )
            assert r_jira_2.status_code == 200
            assert any(a["staged_action_id"] == staged_id for a in r_jira_2.json()["actions"])

            r_mcp_2 = await client2.post(
                "/api/v1/mcp/call",
                headers=auth_headers,
                json={
                    "tool_name": "blackboard.read",
                    "workspace_id": ws_id,
                    "arguments": {"run_id": "run-mcp-241"},
                },
            )
            assert r_mcp_2.status_code == 200
            assert any(
                p["proposal_id"] == proposal_id for p in r_mcp_2.json()["data"]["draft_proposals"]
            )

        # Day-0 reset script clears jira_staged_actions & mcp_governed_proposals and re-seeds VSM v2
        reset_script = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
        spec = importlib.util.spec_from_file_location("orcia_test_09_reset", reset_script)
        assert spec is not None and spec.loader is not None
        reset_mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = reset_mod
        spec.loader.exec_module(reset_mod)
        report = await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        assert report.committed is True
        assert report.remaining_users_count == 0

        async with engine.connect() as conn:
            jira_after = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM jira_staged_actions"))
            ).scalar_one()
            mcp_after = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM mcp_governed_proposals"))
            ).scalar_one()
            vsm_after = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM vsm_definitions_v2"))
            ).scalar_one()
        assert jira_after == 0
        assert mcp_after == 0
        assert vsm_after >= 1
    finally:
        await engine.dispose()
