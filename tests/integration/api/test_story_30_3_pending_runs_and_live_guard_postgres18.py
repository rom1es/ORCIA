"""Layer 2 Real PG18 + Redis 7.4 Integration Tests for `Story 30.3` (`<= 280 L`)."""

from __future__ import annotations

import time

import httpx
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._story_30_3_fixtures import (
    CONF_WS_ID,
    FORBIDDEN_WS_ID,
    REPO_ROOT,
    SEEDED_WS_ID,
    activate_system_packs_with_slots_in_ws,
    load_reset_script,
    pg18_and_redis74_urls,
    seed_story_30_3_topology,
)

from orcia_api.main import create_app

_PG_REDIS_FIXTURE = pg18_and_redis74_urls


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
        async with (
            app_live.router.lifespan_context(app_live),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app_live),
                base_url="http://testserver",
            ) as live_client,
        ):
            day0_global = await live_client.get(
                "/api/v1/workflows/v2/runs",
                params={"workspace_id": "scope-global", "persona_key": "marc"},
            )
            assert day0_global.status_code == 200, day0_global.text
            assert day0_global.json()["items"] == []
            assert day0_global.json()["pending_count"] == 0

            await seed_story_30_3_topology(engine)
            await activate_system_packs_with_slots_in_ws(engine, workspace_id=SEEDED_WS_ID)
            await activate_system_packs_with_slots_in_ws(engine, workspace_id=CONF_WS_ID)

            missing_llm = await live_client.post(
                "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
                params={"persona_key": "marc"},
                headers={"Accept-Language": "fr"},
                json={"inputs": {"objective": "Qualification"}, "workspace_id": SEEDED_WS_ID},
            )
            assert missing_llm.status_code == 422
            assert missing_llm.json()["error_code"] == "ERR_NO_ACTIVE_CHAT_MODEL_DETAIL"
            assert missing_llm.json()["trace_id"]

        # 2. Run cassette workflow with ScopeAccessGuard on seeded PG18 topology
        monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
        app_one = create_app()
        async with (
            app_one.router.lifespan_context(app_one),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app_one),
                base_url="http://testserver",
            ) as client1,
        ):
            start_resp = await client1.post(
                "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
                params={"persona_key": "marc"},
                json={"inputs": {"demande_source": "MCIA-303"}, "workspace_id": SEEDED_WS_ID},
            )
            assert start_resp.status_code == 200, start_resp.text
            run = start_resp.json()["run"]
            run_id = run["run_id"]
            assert run["status"] == "WAITING_SUBSTEP_HITL"

            conf_start = await client1.post(
                "/api/v1/workflows/v2/wf-01-qualification-prd/runs",
                params={"persona_key": "marc"},
                json={"inputs": {"demande_source": "CONF-303"}, "workspace_id": CONF_WS_ID},
            )
            assert conf_start.status_code == 200, conf_start.text
            conf_run_id = conf_start.json()["run"]["run_id"]

            denied = await client1.get(
                "/api/v1/workflows/v2/runs",
                params={"workspace_id": FORBIDDEN_WS_ID, "persona_key": "marc"},
            )
            assert denied.status_code == 403

            conf_get_denied = await client1.get(
                f"/api/v1/runs/{conf_run_id}", params={"persona_key": "nadia"}
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
            assert row[1] == SEEDED_WS_ID
            assert row[2] == "WAITING_SUBSTEP_HITL"

        # 3. Cold F5 survival on brand-new `create_app()` (0 RAM state) & complete lifecycle
        app_two = create_app()
        async with (
            app_two.router.lifespan_context(app_two),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app_two),
                base_url="http://testserver",
            ) as client2,
        ):
            pending_ws = await client2.get(
                "/api/v1/workflows/v2/runs",
                params={"workspace_id": SEEDED_WS_ID, "persona_key": "marc"},
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

            cold_get = await client2.get(f"/api/v1/runs/{run_id}", params={"persona_key": "marc"})
            assert cold_get.status_code == 200
            assert cold_get.json()["run"]["run_id"] == run_id

            cold_conf_denied = await client2.get(
                f"/api/v1/runs/{conf_run_id}", params={"persona_key": "nadia"}
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
                params={"workspace_id": SEEDED_WS_ID, "persona_key": "marc"},
            )
            assert after_done.status_code == 200
            assert after_done.json()["pending_count"] == 0
            assert after_done.json()["items"] == []

            with_completed = await client2.get(
                "/api/v1/workflows/v2/runs",
                params={
                    "workspace_id": SEEDED_WS_ID,
                    "include_completed": "true",
                    "persona_key": "marc",
                },
            )
            assert with_completed.status_code == 200
            assert with_completed.json()["items"][0]["status"] == "COMPLETED"

        # 4. Day-0 Reset clears `workflow_v2_runs`
        reset_mod = load_reset_script()
        assert "workflow_v2_runs" in reset_mod.ORDERED_MUTABLE_TABLES_TO_CLEAR
        await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        async with engine.connect() as conn:
            remaining = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_v2_runs"))
            ).scalar_one()
            assert remaining == 0
    finally:
        await engine.dispose()
