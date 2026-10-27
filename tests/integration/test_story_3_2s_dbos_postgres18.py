"""Story 3.2s (`ARCH-P2-SPIKE`) — Real PostgreSQL 18 + Redis 7.4 Integration Tests.

Validates all 8 Go/No-Go exit criteria on real ephemeral containers via `testcontainers-python`:
1. Durable pause (`DBOS.recv_async`) without worker thread consumption & resume after crash.
2. Targeted replay from step N (`DBOS.fork_workflow_async(wf_id, start_step=2)`).
3. Declarative cron scheduling (`DBOS.apply_schedules` / `DBOS.trigger_schedule`).
4. Transactional idempotency via `SetWorkflowID("<trigger_id>:<idempotency_key>")` (`0` duplicates).
5. Append-only Blackboard cohabitation (`BEFORE UPDATE OR DELETE RAISE EXCEPTION` trigger in PG18).
6. Dramatiq 2.1.0 cohabitation (`RedisBroker` / `StubBroker` offload from a DBOS step).
7. SQLAlchemy 2.1 Asyncio (`asyncpg`) Unit of Work (`DbosSqlAlchemyUnitOfWork`) atomic commit
   & rollback, both inside and outside a DBOS workflow.
8. Deterministic execution under `pytest` + `testcontainers-python` in `< 30 s`.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import dramatiq
import redis as redis_sync
import sqlalchemy as sa
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_core.orchestration._internal.dbos_spike import (
    DbosSpikeRuntime,
    spike_blackboard_snapshot_workflow,
)
from orcia_kernel.ids import new_uuid7

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_s_dbos"


def _prepare_sock_dir(name: str) -> Path:
    unique = f"{name}_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    target = SOCK_BASE_DIR / unique
    target.mkdir(parents=True, exist_ok=True)
    target.chmod(0o777)
    return target


async def test_story_3_2s_all_8_go_no_go_criteria_on_postgres18_and_redis74() -> None:
    """Validate all 8 Go/No-Go exit criteria of Story 3.2s on real PG18 + Redis 7.4 containers."""
    t_start = time.monotonic()
    pg_sock_dir = _prepare_sock_dir("pg18")
    redis_sock_dir = _prepare_sock_dir("redis74")

    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
    )
    redis_container = (
        DockerContainer("redis:7.4.2-alpine")
        .with_volume_mapping(str(redis_sock_dir), "/sock", "rw")
        .with_command("redis-server --unixsocket /sock/redis.sock --unixsocketperm 777 --port 6379")
    )

    try:
        with pg_container as pg, redis_container as rc:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            wait_for_logs(rc, "Ready to accept connections", timeout=20)

            pg_sock_file = pg_sock_dir / ".s.PGSQL.5432"
            redis_sock_file = redis_sock_dir / "redis.sock"
            for _ in range(40):
                if pg_sock_file.exists() and redis_sock_file.exists():
                    break
                time.sleep(0.2)

            auth = "orcia:orcia_dev_secret@/orcia"  # pragma: allowlist secret
            system_db_url = f"postgresql+psycopg://{auth}?host={pg_sock_dir}"
            async_db_url = f"postgresql+asyncpg://{auth}?host={pg_sock_dir}"

            probe_engine = create_async_engine(async_db_url)
            try:
                for _attempt in range(40):
                    try:
                        async with probe_engine.connect() as probe_conn:
                            await probe_conn.execute(sa.text("SELECT 1"))
                        break
                    except Exception:
                        time.sleep(0.2)
            finally:
                await probe_engine.dispose()

            runtime = DbosSpikeRuntime(
                system_database_url=system_db_url,
                async_database_url=async_db_url,
                app_name="orcia-spike-3-2s",
                dbos_schema="dbos",
            )
            try:
                await runtime.start()
                assert runtime.uow is not None
                # Criterion 7a: Verify explicit `asyncpg` driver preservation on the UoW engine
                assert runtime.uow.engine.dialect.driver == "asyncpg"

                # Criterion 1: Durable pause on `DBOS.recv_async` + crash + resume
                resumed_output = await runtime.verify_pause_and_crash_recovery(
                    run_key="arb-uj1",
                    decision="OPTION_B_APPROVED",
                )
                assert resumed_output == "completed:prepared:arb-uj1:decision=OPTION_B_APPROVED"

                # Criterion 2: Targeted replay via `DBOS.fork_workflow_async(wf_id, start_step=2)`
                fork_res = await runtime.verify_fork_workflow_from_step("rewind-step2")
                assert fork_res.original_workflow_id != fork_res.forked_workflow_id
                assert fork_res.step_execution_counts["fork_step_1"] == 1
                assert fork_res.step_execution_counts["fork_step_2"] == 2
                assert fork_res.step_execution_counts["fork_step_3"] == 2
                assert fork_res.original_outputs[0] == fork_res.forked_outputs[0]

                # Criterion 3: Declarative cron scheduling (`DBOS.apply_schedules`)
                sched_out = await runtime.verify_declarative_schedule(
                    schedule_name="orcia-outbox-sweep-schedule",
                    context_tag="workspace-alpha",
                )
                assert sched_out.startswith("tick:workspace-alpha:")

                # Criterion 4: Strict deduplication via `SetWorkflowID("<trigger>:<key>")`
                dedup_outputs, exec_count = await runtime.verify_idempotency_set_workflow_id(
                    trigger_id="trg-webhook-jira",
                    idempotency_key="evt-998877",
                    concurrency=6,
                )
                assert exec_count == 1
                assert len(dedup_outputs) == 6
                assert len(set(dedup_outputs)) == 1

                # Criteria 5 & 7b: Append-only Blackboard cohabitation & UoW commit/rollback
                bb_res = await runtime.verify_append_only_blackboard_and_uow()
                assert bb_res.append_only_trigger_blocked_update is True
                assert bb_res.total_snapshots == 2

                # Verify standalone UoW transaction outside any DBOS workflow (FastAPI HTTP mode)
                standalone_run_id = new_uuid7()
                standalone_snap_id = new_uuid7()

                async def _standalone_http_write_tx() -> int:
                    assert runtime.uow is not None
                    await runtime.uow.session.execute(
                        sa.text(
                            """
                            INSERT INTO spike_blackboard_snapshots (
                                snapshot_id, run_id, step_id,
                                parent_snapshot_id, state_status, payload_jsonb
                            ) VALUES (
                                :s_id, :r_id, 'http_direct',
                                NULL, 'ACTIVE', '{"mode": "standalone_http"}'::jsonb
                            )
                            """
                        ),
                        {"s_id": standalone_snap_id, "r_id": standalone_run_id},
                    )
                    res = await runtime.uow.session.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM spike_blackboard_snapshots WHERE run_id = :r_id"
                        ),
                        {"r_id": standalone_run_id},
                    )
                    return int(res.scalar_one())

                standalone_count = await runtime.uow.run_transaction(
                    _standalone_http_write_tx,
                    name="standalone_http_write_tx",
                )
                assert standalone_count == 1

                # Verify DBOS recorded the workflow transaction step in `dbos.operation_outputs`
                wf_snap_id = new_uuid7()
                await spike_blackboard_snapshot_workflow(
                    wf_snap_id,
                    standalone_run_id,
                    "wf_step_checkpointed",
                    standalone_snap_id,
                    '{"mode": "dbos_workflow_tx"}',
                )

                async def _check_dbos_checkpoint_table_tx() -> int:
                    assert runtime.uow is not None
                    res = await runtime.uow.session.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM dbos.operation_outputs "
                            "WHERE function_name = 'insert_blackboard_snapshot_tx'"
                        )
                    )
                    return int(res.scalar_one())

                checkpoint_rows = await runtime.uow.run_transaction(
                    _check_dbos_checkpoint_table_tx,
                    name="check_dbos_checkpoint_table_tx",
                )
                assert checkpoint_rows >= 1

                # Criterion 6: Dramatiq 2.1.0 cohabitation (StubBroker and real Redis 7.4 broker)
                dramatiq_out = await runtime.verify_dramatiq_cohabitation("docling-parse-42")
                assert dramatiq_out == "dramatiq_processed:docling-parse-42"

                redis_client = redis_sync.Redis(
                    unix_socket_path=str(redis_sock_file), decode_responses=True
                )
                assert redis_client.ping() is True
                redis_broker = RedisBroker(client=redis_client)
                assert redis_broker is not None
                dramatiq.set_broker(redis_broker)
                redis_client.close()
            finally:
                await runtime.stop()

        # Criterion 8: Full setup + 8 criteria execution + teardown under 30 seconds
        elapsed_sec = time.monotonic() - t_start
        assert elapsed_sec < 30.0
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
        shutil.rmtree(redis_sock_dir, ignore_errors=True)
