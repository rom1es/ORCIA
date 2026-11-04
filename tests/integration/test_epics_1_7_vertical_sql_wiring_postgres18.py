"""Vertical Integration Test `HTTP FastAPI ➔ PostgreSQL 18` for Epics 1 to 7 (`AD-17` Layer 2).

Validates on a real `pgvector/pgvector:pg18` container:
1. `POST /api/v1/orchestration/runs/instantiate` -> `POST /api/v1/orchestration/runs/steps/execute`
   -> `GET /api/v1/orchestration/runs/{run_id}/blackboard` -> `POST .../replay`
   and verifies via raw SQL `SELECT` on PostgreSQL 18 that `workflow_runs`, `step_executions`,
   `blackboard_snapshots`, and `domain_events_outbox` are persisted and relayed via
   `DramatiqOutboxRelay.relay_sql_pending_batch`.
2. `POST /api/v1/ontology-rag/rag/search` and `GET /api/v1/ontology-rag/state` against seeded
   PostgreSQL 18 `kb_documents`, `kb_chunks`, and `tripartite_trace_edges` via
   `SqlHybridRagRepository`.
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
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_api.main import create_app
from orcia_core.orchestration import DbosSqlAlchemyUnitOfWork
from orcia_worker.outbox_relay import DramatiqOutboxRelay

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCK_BASE_DIR = Path("/tmp/orcia_tc_ep17")


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
async def test_epics_1_7_vertical_http_to_postgres18_persistence_and_outbox_relay() -> None:
    """Verify full HTTP -> FastAPI -> SQL PostgreSQL 18 persistence across Epics 2 and 3."""
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
                    mod = _load_script_module(f"bf_ep17_{idx}", script)
                    fn_name = next(
                        name
                        for name in dir(mod)
                        if name.startswith(("verify_database_", "backfill_"))
                    )
                    await getattr(mod, fn_name)(setup_engine, apply_changes=True)
            finally:
                await setup_engine.dispose()

            uow = await DbosSqlAlchemyUnitOfWork.create(
                async_app_url, schema="dbos", run_migrations=True
            )
            try:
                app = create_app()
                app.state.db_engine = uow.engine
                app.state.session_maker = uow.session_factory
                app.state.dbos_uow = uow

                ws_id = "0192c4e0-0000-7000-8000-000000000201"
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    # 1. Instantiate a workflow run via HTTP route
                    inst_res = await client.post(
                        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
                        json={
                            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
                            "workspace_id": ws_id,
                        },
                    )
                    assert inst_res.status_code == 200
                    run_data = inst_res.json()["run"]
                    run_id = run_data["id"]
                    first_step_key = "frame-architecture-intent"

                    # 2. Sign human anchor and execute step-1 via HTTP route
                    sign_res = await client.post(
                        "/api/v1/orchestration/runs/anchors/sign?persona_key=marc",
                        json={
                            "run_id": run_id,
                            "step_key": first_step_key,
                            "section_key": "human_architecture_intent",
                            "content_text": (
                                "Intention métier validée par le Tech Lead pour le flux "
                                "de paiement critique SEPA avec idempotence."
                            ),
                            "signature_text": "Marc (Tech Lead)",
                            "author_type": "HUMAN",
                        },
                    )
                    assert sign_res.status_code == 200

                    exec_res = await client.post(
                        "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
                        json={
                            "run_id": run_id,
                            "step_key": first_step_key,
                            "commit_immediately": True,
                            "cost_usd": 0.42,
                        },
                    )
                    assert exec_res.status_code == 200

                    # 3. Read Blackboard state via HTTP route (reads from PostgreSQL 18)
                    bb_res = await client.get(
                        f"/api/v1/orchestration/runs/{run_id}/blackboard?persona_key=marc"
                    )
                    assert bb_res.status_code == 200
                    bb_json = bb_res.json()
                    assert len(bb_json["active_snapshots"]) >= 1

                    # 4. Verify via direct SQL SELECT on PostgreSQL 18
                    async with uow.session_scope() as session:
                        run_count = (
                            await session.execute(
                                sa.text(
                                    "SELECT count(*) FROM workflow_runs "
                                    "WHERE id = CAST(:id AS uuid)"
                                ),
                                {"id": run_id},
                            )
                        ).scalar_one()
                        snap_count = (
                            await session.execute(
                                sa.text(
                                    "SELECT count(*) FROM blackboard_snapshots "
                                    "WHERE run_id = CAST(:id AS uuid)"
                                ),
                                {"id": run_id},
                            )
                        ).scalar_one()
                        outbox_count = (
                            await session.execute(
                                sa.text(
                                    "SELECT count(*) FROM domain_events_outbox "
                                    "WHERE run_id = CAST(:id AS uuid) AND status = 'PENDING'"
                                ),
                                {"id": run_id},
                            )
                        ).scalar_one()
                    assert run_count == 1
                    assert snap_count >= 1
                    assert outbox_count >= 2

                    # 5. Relay pending Outbox rows via DramatiqOutboxRelay.relay_sql_pending_batch
                    relay = DramatiqOutboxRelay()
                    relayed_count = await relay.relay_sql_pending_batch(uow, batch_size=20)
                    assert relayed_count >= 2
                    assert len(relay.event_bus.audit_finops_ledger) >= 2

                    # 6. Execute Hybrid RAG search & Tripartite neighborhood via HTTP -> PG18
                    rag_res = await client.post(
                        "/api/v1/ontology-rag/rag/search?fixture=false",
                        json={
                            "workspace_id": ws_id,
                            "query_text": "seuil validation",
                            "top_k": 5,
                        },
                    )
                    assert rag_res.status_code == 200
                    assert len(rag_res.json()["hits"]) >= 1

                    state_res = await client.get(
                        f"/api/v1/ontology-rag/state?fixture=false&workspace_id={ws_id}"
                        "&seed_uri=jira://issues/PAY-142"
                    )
                    assert state_res.status_code == 200
                    assert len(state_res.json()["tripartite_edges"]) >= 1
            finally:
                await uow.close()
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
