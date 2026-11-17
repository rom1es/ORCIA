"""Layer 2 Real PostgreSQL 18 + Redis 7.4 Integration Tests for `Story 16.3` (`CAP-160`).

Validates full vertical `HTTP -> FastAPI -> ProcessExecutionDispatcher -> PostgreSQL 18`:
1. `GET /api/v1/workflows/v2` lists both `non_deterministic` (`wf-generate-orcia-documentation`)
   and `deterministic_dbos` (`wf-01-qualification-prd`, `wf-03-etude-architecture`, etc.).
2. `PUT /api/v1/workflows/v2/wf-01-qualification-prd` switches `orchestration_type`, updates
   `reflexive_objective` and `allowed_delegate_agents`, persists in PostgreSQL 18
   `workflow_definitions_v2` (verified via direct SQL `SELECT`), and survives `F5` across a
   brand-new `create_app()` instance (`0` RAM state).
3. `POST /api/v1/workflows/v2/wf-generate-orcia-documentation/runs` executes end-to-end in
   `non_deterministic` mode (`NonDeterministicReflexiveRuntime` + `GatePipelineExecutor` +
   `ClaimCheckPointer`) and persists its session in `reflexive_execution_sessions`.
4. `POST /api/v1/workflows/v2/wf-03-etude-architecture/runs` executes end-to-end in
   `deterministic_dbos` mode with Principle 7 encapsulated `reflexive_execution_id` and zero
   scratchpad bloat in `sub_step_records`.
5. `READ_ONLY_OBSERVER` (`persona_key="claire"`) receives `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`
   (`application/problem+json` with `trace_id`) on `PUT` and `POST .../runs`.
6. Day-0 reset (`09_reset_db_first_boot.py`) clears `workflow_definitions_v2` (`0` rows).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
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
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_s16_3"


def _prepare_sock_dir(prefix: str) -> Path:
    unique = f"{prefix}_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    target = SOCK_BASE_DIR / unique
    target.mkdir(parents=True, exist_ok=True)
    target.chmod(0o777)
    return target


def _load_reset_script() -> Any:
    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
    spec = importlib.util.spec_from_file_location("reset_db_first_boot_16_3", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pg18_and_redis74_urls() -> Iterator[tuple[str, str]]:
    """Spin up real ephemeral PostgreSQL 18 (`pgvector:pg18`) and Redis 7.4 containers."""
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


async def test_dual_mode_workflows_v2_pg18_persistence_dispatcher_runs_and_observer_guard(
    pg18_and_redis74_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify PG18 Studio persistence, dual-mode Dispatcher runs, F5 survival, and 403 guard."""
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

        monkeypatch.setenv("DATABASE_URL", pg_url)
        monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
        monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
        monkeypatch.setenv("REDIS_URL", redis_url)
        monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
        monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

        # 1. App #1: List dual-mode workflows, edit & persist in PG18, and run both modes
        app_one = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_one),
            base_url="http://testserver",
        ) as client1:
            list_resp = await client1.get("/api/v1/workflows/v2")
            assert list_resp.status_code == 200, list_resp.text
            workflows = {w["id"]: w for w in list_resp.json()["items"]}
            assert workflows["wf-generate-orcia-documentation"]["orchestration_type"] == (
                "non_deterministic"
            )
            assert workflows["wf-generate-orcia-documentation"]["allowed_delegate_agents"] == [
                "redacteur-documentation-orcia"
            ]
            assert workflows["wf-01-qualification-prd"]["orchestration_type"] == (
                "deterministic_dbos"
            )

            # Observer Claire blocked with 403 ERR_OBSERVER_MODE_READ_ONLY on PUT and POST /runs
            wf01_candidate = dict(workflows["wf-01-qualification-prd"])
            obs_put = await client1.put(
                "/api/v1/workflows/v2/wf-01-qualification-prd",
                params={"persona_key": "claire"},
                json={"workflow": wf01_candidate, "publish": False},
            )
            assert obs_put.status_code == 403
            assert obs_put.headers["content-type"].startswith("application/problem+json")
            assert obs_put.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
            assert obs_put.json()["trace_id"]

            obs_run = await client1.post(
                "/api/v1/workflows/v2/wf-generate-orcia-documentation/runs",
                params={"persona_key": "claire"},
                json={"inputs": {"help_key": "studio.five-blocks"}},
            )
            assert obs_run.status_code == 403
            assert obs_run.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            # Switch wf-01-qualification-prd to non_deterministic and save via PUT
            wf01_candidate["orchestration_type"] = "non_deterministic"
            wf01_candidate["reflexive_objective"] = (
                "Qualifier le besoin produit de maniere adaptative et proposer un PRD complet."
            )
            wf01_candidate["allowed_delegate_agents"] = [
                "orchestrateur-produit",
                "redacteur-documentation-orcia",
            ]
            put_resp = await client1.put(
                "/api/v1/workflows/v2/wf-01-qualification-prd",
                params={"persona_key": "marc"},
                json={"workflow": wf01_candidate, "publish": False},
            )
            assert put_resp.status_code == 200, put_resp.text
            saved_body = put_resp.json()
            assert saved_body["forked_as_draft"] is True
            assert saved_body["workflow"]["status"] == "draft"
            assert saved_body["workflow"]["orchestration_type"] == "non_deterministic"

            # Execute Goal-driven process (`wf-generate-orcia-documentation`)
            goal_run_resp = await client1.post(
                "/api/v1/workflows/v2/wf-generate-orcia-documentation/runs",
                params={"persona_key": "marc"},
                json={"inputs": {"help_key": "studio.five-blocks"}},
            )
            assert goal_run_resp.status_code == 200, goal_run_resp.text
            goal_run = goal_run_resp.json()["run"]
            assert goal_run["orchestration_type"] == "non_deterministic"
            assert goal_run["status"] in ("WAITING_FINAL_ANCHOR", "COMPLETED_APPROVED")
            assert goal_run["reflexive_execution_id"] is not None
            assert goal_run["final_artifact_pointer"] is not None
            goal_exec_id = goal_run["reflexive_execution_id"]

            # Execute Milestone-driven process (`wf-03-etude-architecture`)
            ms_run_resp = await client1.post(
                "/api/v1/workflows/v2/wf-03-etude-architecture/runs",
                params={"persona_key": "marc"},
                json={
                    "inputs": {"prd_valide_uri": "catalog://docs/prd-mon-compte"},
                    "auto_approve_checkpoints": True,
                },
            )
            assert ms_run_resp.status_code == 200, ms_run_resp.text
            ms_run = ms_run_resp.json()["run"]
            assert ms_run["orchestration_type"] == "deterministic_dbos"
            assert ms_run["status"] == "COMPLETED_APPROVED"
            assert len(ms_run["sub_step_records"]) >= 1
            assert ms_run["reflexive_execution_id"] is not None
            for sub_rec in ms_run["sub_step_records"]:
                assert sub_rec["reflexive_execution_id"] is not None
                assert "scratchpad" not in sub_rec

        # 2. Direct SQL SELECT on PostgreSQL 18 (Garde-Fou #2)
        async with engine.connect() as conn:
            wf_row = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT status, spec_jsonb
                        FROM workflow_definitions_v2
                        WHERE workflow_id = 'wf-01-qualification-prd'
                        """
                    )
                )
            ).first()
            assert wf_row is not None
            assert wf_row[0] == "draft"
            spec_dict = json.loads(wf_row[1]) if isinstance(wf_row[1], str) else dict(wf_row[1])
            assert spec_dict["orchestration_type"] == "non_deterministic"
            assert spec_dict["allowed_delegate_agents"] == [
                "orchestrateur-produit",
                "redacteur-documentation-orcia",
            ]

            exec_row = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT status
                        FROM reflexive_execution_sessions
                        WHERE execution_id = :exec_id
                        """
                    ),
                    {"exec_id": goal_exec_id},
                )
            ).first()
            assert exec_row is not None
            assert exec_row[0] == "COMPLETED"

        # 3. F5 Reload Survival across a BRAND-NEW FastAPI app instance (`0` RAM state)
        app_two = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_two),
            base_url="http://testserver",
        ) as client2:
            f5_get = await client2.get("/api/v1/workflows/v2/wf-01-qualification-prd")
            assert f5_get.status_code == 200, f5_get.text
            f5_wf = f5_get.json()
            assert f5_wf["status"] == "draft"
            assert f5_wf["orchestration_type"] == "non_deterministic"
            assert "adaptative" in (f5_wf["reflexive_objective"] or "")
            assert f5_wf["allowed_delegate_agents"] == [
                "orchestrateur-produit",
                "redacteur-documentation-orcia",
            ]

        # 4. Day-0 Reset (`09_reset_db_first_boot.py --apply`) clears workflow_definitions_v2
        reset_mod = _load_reset_script()
        assert "workflow_definitions_v2" in reset_mod.ORDERED_MUTABLE_TABLES_TO_CLEAR
        await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        async with engine.connect() as conn:
            remaining = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_definitions_v2"))
            ).scalar_one()
            assert remaining == 0
    finally:
        await engine.dispose()
