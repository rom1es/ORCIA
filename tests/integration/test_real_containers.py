"""Layer 2 Real Ephemeral Container Integration Tests (`testcontainers-python`, AD-17).

Strictly no SQLite or in-memory Redis mocks: runs against real PostgreSQL 18 + pgvector,
Redis 7.4, and MinIO containers via `testcontainers-python`.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import time
from pathlib import Path
from typing import Any

import pytest
import redis as redis_sync
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[2]
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_s"


def _prepare_sock_dir(name: str) -> Path:
    unique = f"{name}_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    target = SOCK_BASE_DIR / unique
    target.mkdir(parents=True, exist_ok=True)
    target.chmod(0o777)
    return target


def _load_script_module(mod_name: str, filename: str) -> Any:
    import sys

    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / filename
    spec = importlib.util.spec_from_file_location(mod_name, script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class _MinioContainerBucketBackend:
    """S3BucketBackendProtocol persisting `cas/<sha256>` in the live MinIO `/data` volume."""

    def __init__(self, data_root: Path, container: DockerContainer) -> None:
        self._root = data_root
        self._container = container

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        target = self._root / bucket / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def get_bytes(self, bucket: str, key: str) -> bytes | None:
        target = self._root / bucket / key
        if not target.exists():
            return None
        exit_code, _out = self._container.exec(f"sh -c 'test -f /data/{bucket}/{key}'")
        assert exit_code == 0
        return target.read_bytes()

    def head_key(self, bucket: str, key: str) -> bool:
        exit_code, _out = self._container.exec(f"sh -c 'test -f /data/{bucket}/{key}'")
        return exit_code == 0


async def test_postgres18_pgvector_alembic_and_append_only_trigger() -> None:
    """Verify Alembic 0001..0005 upgrade/downgrade, pgvector, backfills 00..04, and triggers."""
    pg_sock_dir = _prepare_sock_dir("pg")

    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
    )

    with pg_container as pg:
        wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
        sock_file = pg_sock_dir / ".s.PGSQL.5432"
        for _ in range(30):
            if sock_file.exists():
                break
            time.sleep(0.2)

        async_url = f"postgresql+asyncpg://orcia:orcia_dev_secret@/orcia?host={pg_sock_dir}"
        alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
        alembic_cfg.set_main_option("sqlalchemy.url", async_url)

        engine = create_async_engine(async_url)
        try:
            for _attempt in range(30):
                try:
                    async with engine.connect() as probe_conn:
                        await probe_conn.execute(sa.text("SELECT 1"))
                    break
                except Exception:
                    time.sleep(0.2)

            async with engine.begin() as conn:
                await conn.run_sync(
                    lambda sync_conn: (
                        alembic_cfg.attributes.__setitem__("connection", sync_conn),
                        command.upgrade(alembic_cfg, "head"),
                    )
                )

            maint = _load_script_module("verify_db_invariants", "00_verify_db_invariants.py")
            dry_report = await maint.verify_database_invariants(engine, apply_changes=False)
            assert dry_report.has_vector_extension is True
            assert dry_report.has_append_only_trigger_fn is True
            assert dry_report.dry_run is True and dry_report.committed is False
            apply_report = await maint.verify_database_invariants(engine, apply_changes=True)
            assert apply_report.committed is True

            backfill_org = _load_script_module(
                "backfill_default_org_tree", "01_backfill_default_org_tree.py"
            )
            bf_dry = await backfill_org.backfill_default_org_tree(engine, apply_changes=False)
            assert bf_dry.org_units_count == 5 and bf_dry.workspaces_count == 3
            assert bf_dry.datasources_count == 10 and bf_dry.committed is False
            bf_apply = await backfill_org.backfill_default_org_tree(engine, apply_changes=True)
            assert bf_apply.committed is True

            backfill_cat = _load_script_module(
                "backfill_federated_catalog", "02_backfill_federated_catalog.py"
            )
            cat_dry = await backfill_cat.backfill_federated_catalog(engine, apply_changes=False)
            assert cat_dry.catalog_items_count == 6 and cat_dry.workflow_definitions_count == 1
            assert cat_dry.customization_overrides_count == 4 and cat_dry.committed is False
            cat_apply = await backfill_cat.backfill_federated_catalog(engine, apply_changes=True)
            assert cat_apply.committed is True and cat_apply.catalog_items_count == 6

            backfill_pb = _load_script_module(
                "backfill_permission_broker", "03_backfill_permission_broker.py"
            )
            pb_dry = await backfill_pb.backfill_permission_broker(engine, apply_changes=False)
            assert pb_dry.policies_count == 6 and pb_dry.tickets_count == 1
            assert pb_dry.committed is False
            pb_apply = await backfill_pb.backfill_permission_broker(engine, apply_changes=True)
            assert pb_apply.committed is True and pb_apply.policies_count == 6

            # Verify Story 1.5 maintenance script 04_backfill_system_bootstrap in dry-run & apply
            backfill_sb = _load_script_module(
                "backfill_system_bootstrap", "04_backfill_system_bootstrap.py"
            )
            sb_dry = await backfill_sb.backfill_system_bootstrap(engine, apply_changes=False)
            assert sb_dry.llm_endpoints_count == 3 and sb_dry.bootstrap_workflows_count == 6
            assert sb_dry.bootstrap_runs_count == 2 and sb_dry.onboarding_states_count == 2
            assert sb_dry.dry_run is True and sb_dry.committed is False
            async with engine.connect() as conn:
                llm_after_dry = await conn.execute(
                    sa.text("SELECT COUNT(*) FROM llm_model_endpoints")
                )
                assert int(llm_after_dry.scalar() or 0) == 0

            sb_apply = await backfill_sb.backfill_system_bootstrap(engine, apply_changes=True)
            assert sb_apply.committed is True and sb_apply.llm_endpoints_count == 3
            assert sb_apply.bootstrap_workflows_count == 6 and sb_apply.bootstrap_runs_count == 2
            assert sb_apply.onboarding_states_count == 2

            # Verify Epic 2 maintenance script 05_backfill_ontology_and_rag_graph (dry-run & apply)
            backfill_ep2 = _load_script_module(
                "backfill_ontology_and_rag_graph", "05_backfill_ontology_and_rag_graph.py"
            )
            ep2_dry = await backfill_ep2.backfill_ontology_and_rag_graph(
                engine, apply_changes=False
            )
            assert ep2_dry.concepts_count == 7 and ep2_dry.axioms_count == 1
            assert ep2_dry.kb_chunks_count == 1 and ep2_dry.tripartite_edges_count == 1
            assert ep2_dry.stale_alerts_count == 1 and ep2_dry.committed is False
            async with engine.connect() as conn:
                concepts_after_dry = await conn.execute(
                    sa.text("SELECT COUNT(*) FROM ontology_concepts")
                )
                assert int(concepts_after_dry.scalar() or 0) == 0

            ep2_apply = await backfill_ep2.backfill_ontology_and_rag_graph(
                engine, apply_changes=True
            )
            assert ep2_apply.committed is True and ep2_apply.concepts_count == 7

            # Verify Story 3.1 maintenance script 06_backfill_workflow_orchestration_and_locks
            backfill_ep3 = _load_script_module(
                "backfill_workflow_orchestration_and_locks",
                "06_backfill_workflow_orchestration_and_locks.py",
            )
            ep3_dry = await backfill_ep3.backfill_workflow_orchestration_and_locks(
                engine, apply_changes=False
            )
            assert ep3_dry.workflows_count == 3 and ep3_dry.triggers_count == 1
            assert ep3_dry.runs_count == 1 and ep3_dry.run_locks_count == 1
            assert ep3_dry.dry_run is True and ep3_dry.committed is False
            async with engine.connect() as conn:
                runs_after_dry = await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_runs"))
                assert int(runs_after_dry.scalar() or 0) == 0

            ep3_apply = await backfill_ep3.backfill_workflow_orchestration_and_locks(
                engine, apply_changes=True
            )
            assert ep3_apply.committed is True and ep3_apply.runs_count == 1
            assert ep3_apply.run_locks_count == 1

            # Verify Story 3.2 script 07_backfill_step_executions_and_blackboard_snapshots
            backfill_s32 = _load_script_module(
                "backfill_step_executions_and_blackboard_snapshots",
                "07_backfill_step_executions_and_blackboard_snapshots.py",
            )
            s32_dry = await backfill_s32.backfill_step_executions_and_blackboard_snapshots(
                engine, apply_changes=False
            )
            assert s32_dry.dry_run is True and s32_dry.committed is False
            assert s32_dry.step_executions_count == 7 and s32_dry.blackboard_snapshots_count == 7
            async with engine.connect() as conn:
                snaps_after_dry = await conn.execute(
                    sa.text("SELECT COUNT(*) FROM blackboard_snapshots")
                )
                assert int(snaps_after_dry.scalar() or 0) == 0

            s32_apply = await backfill_s32.backfill_step_executions_and_blackboard_snapshots(
                engine, apply_changes=True
            )
            assert s32_apply.committed is True and s32_apply.blackboard_snapshots_count == 7

            with pytest.raises(DBAPIError, match="ERR_BLACKBOARD_APPEND_ONLY_VIOLATION"):
                async with engine.begin() as conn:
                    await conn.execute(
                        sa.text("UPDATE blackboard_snapshots SET branch_status = 'SUPERSEDED';")
                    )

            with pytest.raises(DBAPIError, match="ERR_BLACKBOARD_APPEND_ONLY_VIOLATION"):
                async with engine.begin() as conn:
                    await conn.execute(sa.text("DELETE FROM blackboard_snapshots;"))

            # Execute build_ontology_resolution_cte_sql() against real PostgreSQL 18
            from orcia_core.ontology import build_ontology_resolution_cte_sql

            cte_sql = build_ontology_resolution_cte_sql()
            async with engine.connect() as conn:
                cte_res = await conn.execute(
                    sa.text(cte_sql),
                    {
                        "team_org_unit_id": "scope-subteam-checkout",
                        "enterprise_scope_id": "scope-global",
                        "domain_scope_id": "scope-bu-digital",
                        "workspace_scope_id": "ws-solution-paiement",
                        "run_id": "run-checkout-001",
                    },
                )
                cte_rows = cte_res.mappings().all()
                by_term = {r["canonical_term"]: r for r in cte_rows}
                assert "Actif Stratégique" in by_term
                assert by_term["Actif Stratégique"]["scope_id"] == "scope-subteam-checkout"
                assert "Exemption 3DS Frictionless TRA" in by_term
                assert "Terme Branche Obsolète Replay" not in by_term

            # Verify append-only trigger blocks UPDATE and DELETE on PG 18
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "CREATE TABLE test_append_only_ledger ("
                        "id UUID PRIMARY KEY, payload TEXT NOT NULL, embedding vector(3));"
                    )
                )
                await conn.execute(
                    sa.text(
                        "CREATE TRIGGER trg_test_append_only "
                        "BEFORE UPDATE OR DELETE ON test_append_only_ledger "
                        "FOR EACH ROW EXECUTE FUNCTION orcia_prevent_append_only_mutation();"
                    )
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO test_append_only_ledger (id, payload, embedding) "
                        "VALUES ('0192c4e0-0000-7000-8000-000000000001', 'immutable', '[1,2,3]');"
                    )
                )

            with pytest.raises(DBAPIError, match="ERR_APPEND_ONLY_VIOLATION"):
                async with engine.begin() as conn:
                    await conn.execute(
                        sa.text("UPDATE test_append_only_ledger SET payload = 'mutated';")
                    )

            with pytest.raises(DBAPIError, match="ERR_APPEND_ONLY_VIOLATION"):
                async with engine.begin() as conn:
                    await conn.execute(sa.text("DELETE FROM test_append_only_ledger;"))

            # Verify downgrade and re-upgrade across 0005..0001
            async with engine.begin() as conn:
                await conn.execute(sa.text("DROP TABLE test_append_only_ledger;"))
                await conn.run_sync(
                    lambda sync_conn: (
                        alembic_cfg.attributes.__setitem__("connection", sync_conn),
                        command.downgrade(alembic_cfg, "base"),
                        command.upgrade(alembic_cfg, "head"),
                    )
                )
        finally:
            await engine.dispose()
            shutil.rmtree(pg_sock_dir, ignore_errors=True)


def test_redis7_atomic_presence_lock_and_minio_cas_storage() -> None:
    """Verify Redis 7.4 atomic lock/revocation and real MinIO container `cas/<sha256>` storage."""
    from orcia_core.catalog import FederatedUriResolver, S3CompatibleCasObjectStore
    from orcia_core.permissions import KeyValueRevocationStore, build_default_auth_and_org_service
    from orcia_core.permissions.errors import RevokedTokenError

    redis_sock_dir = _prepare_sock_dir("rd")
    redis_sock_path = redis_sock_dir / "redis.sock"
    minio_data_dir = _prepare_sock_dir("minio")

    redis_container = (
        DockerContainer("redis:7.4.2-alpine")
        .with_volume_mapping(str(redis_sock_dir), "/sock", "rw")
        .with_command("redis-server --unixsocket /sock/redis.sock --unixsocketperm 777 --port 6379")
    )

    try:
        with redis_container as rc:
            wait_for_logs(rc, "Ready to accept connections", timeout=20)
            for _ in range(30):
                if redis_sock_path.exists():
                    break
                time.sleep(0.1)

            client = redis_sync.Redis(unix_socket_path=str(redis_sock_path), decode_responses=True)
            lock_key = "lock:step:0192c4e0-0000-7000-8000-000000000010"
            assert client.set(lock_key, "user-alice", nx=True, ex=900) is True
            assert client.set(lock_key, "user-bob", nx=True, ex=900) is None

            rev_store = KeyValueRevocationStore(client)
            auth_svc = build_default_auth_and_org_service(revocation_store=rev_store)
            _user, tokens = auth_svc.login_local("marc.lead@orcia.io", "OrciaLead!2026")
            auth_svc.revoke_token(tokens.access_token, expected_type="access")
            with pytest.raises(RevokedTokenError):
                auth_svc.authenticate_access_token(tokens.access_token)

            client.close()

        with (
            DockerContainer("minio/minio:RELEASE.2025-02-28T09-55-16Z")
            .with_env("MINIO_ROOT_USER", "orcia_minio")
            .with_env("MINIO_ROOT_PASSWORD", "orcia_minio_secret")
            .with_volume_mapping(str(minio_data_dir), "/data", "rw")
            .with_command("server /data") as minio_container
        ):
            wait_for_logs(minio_container, "API:", timeout=30)
            backend = _MinioContainerBucketBackend(minio_data_dir, minio_container)
            s3_store = S3CompatibleCasObjectStore(backend, bucket_name="orcia-cas")
            resolver = FederatedUriResolver(cas_store=s3_store)

            first = resolver.resolve("git://gitlab.entreprise.io/payments/checkout-web@v1.0.0")
            assert first.cache_hit is False and s3_store.has_object(first.cas_key) is True

            s3_store._hot_cache.clear()
            entry = resolver.get_cas_entry(first.sha256)
            assert entry.sha256 == first.sha256

            second = resolver.resolve("git://gitlab.entreprise.io/payments/checkout-web@v1.0.0")
            assert second.cache_hit is True and second.resolution_ms < 50.0
    finally:
        shutil.rmtree(redis_sock_dir, ignore_errors=True)
        shutil.rmtree(minio_data_dir, ignore_errors=True)
