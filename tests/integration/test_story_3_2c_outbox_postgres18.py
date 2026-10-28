"""Real Container Integration Tests for Story 3.2c (`testcontainers-python`, AD-17).

Validates on real `pgvector/pgvector:pg18`:
1. Alembic migration `0012_story_3_2c` (`domain_events_outbox` + partial index) upgrade/downgrade.
2. Transactional Outbox write in the exact same `AsyncSession` transaction as `append_snapshot`.
3. Crash recovery simulation right after SQL `COMMIT` before the Outbox relay runs:
   100% of `PENDING` events are claimed via `SELECT ... FOR UPDATE SKIP LOCKED` and delivered
   to `OutboxEventBus` (`audit_finops`, `ontology`, `sse`) with `0` duplicates on retry.
"""

from __future__ import annotations

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
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_core.blackboard.models import StepExecutionEntity
from orcia_core.orchestration._internal.outbox_repository import SqlDomainEventsOutboxRepository
from orcia_core.orchestration._internal.sql_repository import SqlOrchestrationRepository
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_kernel.events import ArtifactProduced, RunTerminated, StepCompleted
from orcia_kernel.ids import new_uuid7_str
from orcia_worker.outbox_relay import OutboxEventBus

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_3_2c"


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
async def test_story_3_2c_transactional_outbox_crash_recovery_and_zero_duplicates() -> None:
    """Verify migration 0012 and transactional Outbox crash recovery on PostgreSQL 18."""
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

                # Test upgrade("head") -> downgrade("0011_story_3_2") -> upgrade("head")
                async with setup_engine.begin() as conn:
                    await conn.run_sync(
                        lambda sync_conn: (
                            alembic_cfg.attributes.__setitem__("connection", sync_conn),
                            command.upgrade(alembic_cfg, "head"),
                            command.downgrade(alembic_cfg, "0011_story_3_2"),
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
                    mod = _load_script_module(f"bf_3_2c_{idx}", script)
                    fn_name = next(
                        name
                        for name in dir(mod)
                        if name.startswith(("verify_database_", "backfill_"))
                    )
                    await getattr(mod, fn_name)(setup_engine, apply_changes=True)
            finally:
                await setup_engine.dispose()

            # 1. Process 1: Commit snapshot + Outbox events in the same SQL transaction, then crash!
            uow_writer = await DbosSqlAlchemyUnitOfWork.create(
                async_app_url, schema="dbos", run_migrations=True
            )
            orch_repo = SqlOrchestrationRepository(uow_writer)
            outbox_repo = SqlDomainEventsOutboxRepository(uow_writer)

            ws_id = "0192c4e0-0000-7000-8000-000000000201"
            user_id = "0192c4e0-0000-7000-8000-000000000603"
            async with uow_writer.session_scope() as s:
                wf_def_id = str(
                    (
                        await s.execute(
                            sa.text("SELECT id::text FROM workflow_definitions LIMIT 1;")
                        )
                    ).scalar_one()
                )
            run_id = new_uuid7_str()
            step_id = new_uuid7_str()

            await orch_repo.upsert_workflow_run(
                run_id=run_id,
                run_key="run-3-2c-outbox-001",
                workspace_id=ws_id,
                workflow_def_id=wf_def_id,
                parent_run_id=None,
                parent_step_execution_id=None,
                root_run_id=run_id,
                nesting_depth=0,
                execution_regime="INTERACTIVE_COACHING",
                criticality="STANDARD",
                trigger_id=None,
                trigger_idempotency_key=None,
                status="RUNNING",
                initiated_by_user_id=user_id,
                execution_identity_mode="passthrough",
                budget_max_usd=10.0,
            )
            await orch_repo.upsert_step_execution(
                StepExecutionEntity(
                    id=step_id,
                    step_execution_key=f"stepexec-{run_id[-6:]}-step-1",
                    run_id=run_id,
                    step_key="step-1",
                    step_index=0,
                    step_type="AGENT",
                    execution_mode="INTERACTIVE_COACHING",
                    status="EXECUTING_AGENT",
                    cost_usd=0.25,
                )
            )

            evt_step = StepCompleted.create(
                step_execution_id=step_id,
                run_id=run_id,
                workspace_id=ws_id,
                step_key="step-1",
                cost_usd=0.25,
                trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            )
            evt_art = ArtifactProduced.create(
                snapshot_id=new_uuid7_str(),
                run_id=run_id,
                workspace_id=ws_id,
                artifact_cas_key="cas/sha256/step-1",
                artifact_sha256="b" * 64,
                trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
            )
            await orch_repo.append_snapshot(
                run_id=run_id,
                step_execution_id=step_id,
                step_key="step-1",
                branch_status="ACTIVE",
                artifact_payload={"result": "ok"},
                outbox_events=(evt_step, evt_art),
            )
            await outbox_repo.enqueue_event(
                RunTerminated.create(
                    run_id=run_id,
                    workspace_id=ws_id,
                    final_status="COMPLETED",
                    total_cost_usd=0.25,
                    trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
                )
            )

            # Simulate crash right after SQL COMMIT before the Outbox relay runs!
            await uow_writer.close()

            # 2. Process 2: Restart on a fresh UoW and run Outbox relay (`FOR UPDATE SKIP LOCKED`)
            uow_relay = await DbosSqlAlchemyUnitOfWork.create(
                async_app_url, schema="dbos", run_migrations=False
            )
            try:
                recovered_outbox = SqlDomainEventsOutboxRepository(uow_relay)
                pending_before = await recovered_outbox.list_events_by_run(run_id)
                assert len(pending_before) == 3
                assert all(e.status == "PENDING" for e in pending_before)

                bus = OutboxEventBus()
                relayed_first = await recovered_outbox.claim_and_relay_pending_batch(
                    batch_size=10,
                    subscriber_fn=bus.publish_idempotent_async,
                )
                assert relayed_first == 3

                # Second relay call claims 0 rows (all already PUBLISHED)
                relayed_second = await recovered_outbox.claim_and_relay_pending_batch(
                    batch_size=10,
                    subscriber_fn=bus.publish_idempotent_async,
                )
                assert relayed_second == 0

                after_events = await recovered_outbox.list_events_by_run(run_id)
                assert all(e.status == "PUBLISHED" and e.attempts == 1 for e in after_events)
                assert len(bus.audit_finops_ledger) == 3
                assert len(bus.ontology_extraction_queue) == 1
                assert len(bus.sse_published_messages) == 3
            finally:
                await uow_relay.close()
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
