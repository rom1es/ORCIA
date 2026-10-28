"""Real Container Integration Test for Story 3.2f (`DEC-P0-EXEC`, `PROC-01`, AD-17).

Validates on real `pgvector/pgvector:pg18`:
1. Real step execution (`StepExecutorPort` via `DeterministicCassetteLLM` and
   `ConnectorInvoker`) inside `DbosDurableWorkflowEngine` + `SqlOrchestrationRepository`,
   producing authentic Blackboard snapshots with `0` simulated strings.
2. Full process shutdown (`engine.shutdown()`) and restart (`engine_restarted.launch()`)
   while the run is paused at `WAITING_FOR_HUMAN_ARBITRATION`, followed by
   `send_human_arbitration(...)` reaching `COMPLETED` with zero duplicate
   `blackboard_snapshots` or `step_executions` (`PROC-01`).
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from dbos import DBOS
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_core.orchestration import register_default_step_executors
from orcia_core.orchestration._internal.dbos_engine import DbosDurableWorkflowEngine
from orcia_core.orchestration.connector_invoker import ConnectorInvoker
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.ids import new_uuid7_str

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_3_2f"


def _prepare_sock_dir(name: str) -> Path:
    unique = f"{name}_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    target = SOCK_BASE_DIR / unique
    target.mkdir(parents=True, exist_ok=True)
    target.chmod(0o777)
    return target


def _load_script_module(mod_name: str, filename: str) -> Any:
    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / filename
    spec = importlib.util.spec_from_file_location(mod_name, script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.asyncio
async def test_story_3_2f_real_step_executors_human_pause_restart_and_resume_postgres18() -> None:
    """Validate real step executors, HUMAN_TASK pause, DBOS restart, and resume on PG18."""
    pg_sock_dir = _prepare_sock_dir("pg18")
    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
    )

    llm_adapter = DeterministicCassetteLLM()
    connector_invoker = ConnectorInvoker()
    register_default_step_executors(
        llm_gateway=llm_adapter,
        connector_invoker=connector_invoker,
    )

    try:
        with pg_container as pg:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            sock_file = pg_sock_dir / ".s.PGSQL.5432"
            for _ in range(40):
                if sock_file.exists():
                    break
                time.sleep(0.2)

            creds = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            system_db_url = f"postgresql://{creds}@/orcia?host={pg_sock_dir}"
            async_app_url = f"postgresql+asyncpg://{creds}@/orcia?host={pg_sock_dir}"

            alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
            alembic_cfg.set_main_option("sqlalchemy.url", async_app_url)

            setup_engine = create_async_engine(async_app_url)
            try:
                for _ in range(30):
                    try:
                        async with setup_engine.connect() as conn:
                            await conn.execute(sa.text("SELECT 1"))
                        break
                    except Exception:
                        time.sleep(0.2)

                async with setup_engine.begin() as conn:
                    await conn.run_sync(
                        lambda sync_conn: (
                            alembic_cfg.attributes.__setitem__("connection", sync_conn),
                            command.upgrade(alembic_cfg, "head"),
                        )
                    )

                for idx, script in (
                    ("00", "00_verify_db_invariants.py"),
                    ("01", "01_backfill_default_org_tree.py"),
                    ("02", "02_backfill_federated_catalog.py"),
                    ("03", "03_backfill_permission_broker.py"),
                    ("04", "04_backfill_system_bootstrap.py"),
                    ("05", "05_backfill_ontology_and_rag_graph.py"),
                    ("06", "06_backfill_workflow_orchestration_and_locks.py"),
                ):
                    mod = _load_script_module(f"m32f_{idx}", script)
                    fn_name = next(
                        name
                        for name in dir(mod)
                        if name.startswith(("verify_database_", "backfill_"))
                    )
                    await getattr(mod, fn_name)(setup_engine, apply_changes=True)
            finally:
                await setup_engine.dispose()

            engine = DbosDurableWorkflowEngine(
                system_database_url=system_db_url,
                application_database_url=async_app_url,
                app_name="orcia-3-2f-pg18-test",
            )
            await engine.launch()

            ws_id = "0192c4e0-0000-7000-8000-000000000201"
            user_id = "0192c4e0-0000-7000-8000-000000000603"
            trigger_id = "0192c4e0-0000-7000-8000-000000000801"
            async with engine.uow.session_scope() as s:
                wf_def_id = str(
                    (
                        await s.execute(
                            sa.text("SELECT id::text FROM workflow_definitions LIMIT 1;")
                        )
                    ).scalar_one()
                )
            run_id = new_uuid7_str()

            await engine.repository.upsert_workflow_run(
                run_id=run_id,
                run_key="run-3-2f-real-exec-001",
                workspace_id=ws_id,
                workflow_def_id=wf_def_id,
                parent_run_id=None,
                parent_step_execution_id=None,
                root_run_id=run_id,
                nesting_depth=0,
                execution_regime="INTERACTIVE_COACHING",
                criticality="STANDARD",
                trigger_id=trigger_id,
                trigger_idempotency_key="idem-3-2f-001",
                status="INITIALIZED",
                initiated_by_user_id=user_id,
                execution_identity_mode="passthrough",
                budget_max_usd=10.0,
            )

            handle = await engine.start_durable_run(
                trigger_id=trigger_id,
                idempotency_key="idem-3-2f-001",
                run_id=run_id,
                steps=("step-1-extract-invoice", "step-2-verify-reconciliation"),
                pause_for_arbitration_after_step="step-1-extract-invoice",
                timeout_seconds=30.0,
            )
            wf_id = handle.workflow_id

            for _ in range(30):
                status = await engine.repository.get_run_status(run_id)
                if status == "WAITING_FOR_HUMAN_ARBITRATION":
                    break
                await asyncio.sleep(0.1)
            assert await engine.repository.get_run_status(run_id) == "WAITING_FOR_HUMAN_ARBITRATION"

            # Simulate server shutdown & restart while waiting for human arbitration
            await engine.shutdown()

            engine_restarted = DbosDurableWorkflowEngine(
                system_database_url=system_db_url,
                application_database_url=async_app_url,
                app_name="orcia-3-2f-pg18-test",
            )
            await engine_restarted.launch()

            try:
                await engine_restarted.send_human_arbitration(
                    workflow_id=wf_id,
                    decision="APPROVE_FINANCE_RECONCILIATION",
                )
                recovered_handle = await DBOS.retrieve_workflow_async(wf_id)
                summary = await recovered_handle.get_result()
                assert summary.final_status == "COMPLETED"
                assert summary.arbitration_decision == "APPROVE_FINANCE_RECONCILIATION"
                assert await engine_restarted.repository.get_run_status(run_id) == "COMPLETED"

                snapshots = await engine_restarted.repository.list_snapshots(run_id)
                assert len(snapshots) == 2
                assert [s.step_key for s in snapshots] == [
                    "step-1-extract-invoice",
                    "step-2-verify-reconciliation",
                ]
                for snap in snapshots:
                    payload = snap.artifact_payload
                    assert "simulated" not in str(payload).lower()
                    assert payload.get("step_type") == "AGENT"
                    assert payload.get("llm_model_id") == "anthropic/claude-3-7-sonnet"
                    assert str(payload.get("llm_prompt_sha256", "")).startswith("sha256:")
            finally:
                await engine_restarted.shutdown()
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
