"""Real Container Integration Tests for Story 3.2b (`testcontainers-python`, AD-17).

Validates on real `pgvector/pgvector:pg18`:
1. `SqlOrchestrationRepository` + `DbosDurableWorkflowEngine` (`ARCH-P1`, `ARCH-P2`, `C4`)
   persisting `workflow_runs`, `step_executions`, and append-only `blackboard_snapshots`,
   surviving process restart (`DBOS.recv_async` / `DBOS.send_async`), and performing
   targeted rewind (`rewind_and_fork_from_step`).
2. `SqlHybridRagRepository` (`ARCH-P1`, `ARCH-P7`) executing native SQL hybrid search
   (`halfvec(1024) <=>` + `tsvector` GIN `ts_rank_cd` RRF `k=60`) and bounded recursive
   CTE (`WITH RECURSIVE ... WHERE depth <= 2`) on `tripartite_trace_edges`.
3. `SqlAlchemyOtelInstrumenter` (`ARCH-P9`) correlating SQL spans with W3C `trace_id`.
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

from orcia_core.observability._internal.otel_sqlalchemy import SqlAlchemyOtelInstrumenter
from orcia_core.observability.logging import bind_trace_context, clear_trace_context
from orcia_core.orchestration._internal.dbos_engine import DbosDurableWorkflowEngine
from orcia_core.rag import compute_deterministic_halfvec_1024
from orcia_core.rag._internal.sql_repository import SqlHybridRagRepository
from orcia_kernel.ids import new_uuid7_str

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_3_2b"


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
async def test_story_3_2b_sql_persistence_dbos_crash_recovery_rag_rrf_and_otel() -> None:
    """Validate Story 3.2b SQL repositories, DBOS crash recovery, Hybrid RAG RRF & OTel."""
    pg_sock_dir = _prepare_sock_dir("pg18")
    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
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

                # Apply reference seed backfills 00..06 so foreign keys & RAG chunks exist
                for idx, script in (
                    ("00", "00_verify_db_invariants.py"),
                    ("01", "01_backfill_default_org_tree.py"),
                    ("02", "02_backfill_federated_catalog.py"),
                    ("03", "03_backfill_permission_broker.py"),
                    ("04", "04_backfill_system_bootstrap.py"),
                    ("05", "05_backfill_ontology_and_rag_graph.py"),
                    ("06", "06_backfill_workflow_orchestration_and_locks.py"),
                ):
                    mod = _load_script_module(f"bf_3_2b_{idx}", script)
                    fn_name = next(
                        name
                        for name in dir(mod)
                        if name.startswith(("verify_database_", "backfill_"))
                    )
                    await getattr(mod, fn_name)(setup_engine, apply_changes=True)
            finally:
                await setup_engine.dispose()

            trace_ctx = bind_trace_context("4bf92f3577b34da6a3ce929d0e0e4736")
            otel_instrumenter = SqlAlchemyOtelInstrumenter()

            engine = DbosDurableWorkflowEngine(
                system_database_url=system_db_url,
                application_database_url=async_app_url,
                app_name="orcia-3-2b-integration",
            )
            await engine.launch()
            otel_instrumenter.instrument_engine(engine.uow.engine)

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
                run_key="run-3-2b-durable-001",
                workspace_id=ws_id,
                workflow_def_id=wf_def_id,
                parent_run_id=None,
                parent_step_execution_id=None,
                root_run_id=run_id,
                nesting_depth=0,
                execution_regime="INTERACTIVE_COACHING",
                criticality="STANDARD",
                trigger_id=trigger_id,
                trigger_idempotency_key="idem-3-2b-001",
                status="INITIALIZED",
                initiated_by_user_id=user_id,
                execution_identity_mode="passthrough",
                budget_max_usd=10.0,
            )

            # 1. Start durable workflow that pauses on WAITING_FOR_HUMAN_ARBITRATION after step 1
            handle = await engine.start_durable_run(
                trigger_id=trigger_id,
                idempotency_key="idem-3-2b-001",
                run_id=run_id,
                steps=("step-frame-intent", "step-validate-architecture"),
                pause_for_arbitration_after_step="step-frame-intent",
                timeout_seconds=30.0,
            )
            wf_id = handle.workflow_id

            for _ in range(30):
                status = await engine.repository.get_run_status(run_id)
                if status == "WAITING_FOR_HUMAN_ARBITRATION":
                    break
                await asyncio.sleep(0.1)
            assert await engine.repository.get_run_status(run_id) == "WAITING_FOR_HUMAN_ARBITRATION"

            # 2. Simulate process crash and restart on a fresh DbosDurableWorkflowEngine
            await engine.shutdown()

            engine_restarted = DbosDurableWorkflowEngine(
                system_database_url=system_db_url,
                application_database_url=async_app_url,
                app_name="orcia-3-2b-integration",
            )
            await engine_restarted.launch()
            otel_instrumenter.instrument_engine(engine_restarted.uow.engine)

            try:
                await engine_restarted.send_human_arbitration(
                    workflow_id=wf_id,
                    decision="APPROVE_ARCHITECTURE",
                )
                recovered_handle = await DBOS.retrieve_workflow_async(wf_id)
                summary = await recovered_handle.get_result()
                assert summary.final_status == "COMPLETED"
                assert summary.arbitration_decision == "APPROVE_ARCHITECTURE"
                assert len(summary.committed_snapshot_ids) == 2
                assert await engine_restarted.repository.get_run_status(run_id) == "COMPLETED"

                # 3. Rewind from step-validate-architecture via append-only SUPERSEDED + DBOS fork
                forked_handle = await engine_restarted.rewind_and_fork_from_step(
                    workflow_id=wf_id,
                    run_id=run_id,
                    target_step_key="step-validate-architecture",
                    start_step=3,
                )
                forked_summary = await forked_handle.get_result()
                assert forked_summary.final_status == "COMPLETED"

                all_snaps = await engine_restarted.repository.list_snapshots(run_id)
                assert any(s.branch_status == "SUPERSEDED" for s in all_snaps)
                assert any(s.branch_status == "ACTIVE" for s in all_snaps)

                # 4. Native PostgreSQL 18 Hybrid RAG (`halfvec(1024)` + `ts_rank_cd` RRF `k=60`)
                rag_repo = SqlHybridRagRepository(engine_restarted.uow.session_factory)
                q_vec = compute_deterministic_halfvec_1024("LossEvent PAY-142")
                hits = await rag_repo.search_hybrid_rrf(
                    workspace_id=ws_id,
                    query_text="LossEvent PAY-142 sinistre",
                    query_embedding=q_vec,
                    rrf_k=60,
                    limit=5,
                )
                assert len(hits) >= 1
                assert hits[0].chunk_key == "chunk-confluence-claims-seuil-1"
                assert hits[0].rrf_score > 0.0
                assert hits[0].is_stale is True
                assert hits[0].stale_warning_marker is not None

                # 5. Bounded recursive CTE (`depth <= 2`) on tripartite_trace_edges
                edges = await rag_repo.traverse_tripartite_neighborhood(
                    workspace_id=ws_id,
                    seed_uri="git://claims/core-engine#calculate_reserve",
                    max_depth=2,
                )
                assert len(edges) >= 1
                assert edges[0].edge_key == "trace-git-jira-calculate-reserve-pay-142"

                # 6. Verify OpenTelemetry SQL spans carry the W3C trace_id
                assert len(otel_instrumenter.recorded_spans) > 0
                assert any(
                    s.trace_id == trace_ctx.trace_id for s in otel_instrumenter.recorded_spans
                )
                assert all(len(s.trace_id) == 32 for s in otel_instrumenter.recorded_spans)
            finally:
                await engine_restarted.shutdown()
                clear_trace_context()
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
