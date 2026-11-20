"""Layer 2 integration test (Story 23.1): PG18 + Redis 7.4 + `create_app()` Day-0 reset."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import redis
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_e2e"
DB_USER = "orcia"
DB_PASSWORD = "orcia_e2e_reset_day0_pw"  # pragma: allowlist secret

RESET_FIRST_BOOT_PATH = (
    REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
)
RESET_DAY0_PATH = REPO_ROOT / "infra" / "scripts" / "e2e" / "reset_day0.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def e2e_infra_urls() -> Iterator[tuple[str, str]]:
    """Start isolated `orcia_e2e` PostgreSQL 18 + Redis 7.4 containers migrated to head."""
    with (
        PostgresContainer(
            "pgvector/pgvector:pg18",
            username=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
        ) as pg,
        RedisContainer("redis:7.4-alpine") as redis_box,
    ):
        pg_port = int(pg.get_exposed_port(5432))
        assert pg_port not in (5432, 5433)
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg_port}/{DB_NAME}"
        )
        redis_host = redis_box.get_container_host_ip()
        redis_port = int(redis_box.get_exposed_port(6379))
        redis_url = f"redis://{redis_host}:{redis_port}/0"

        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield pg_url, redis_url


@pytest.mark.asyncio
async def test_e2e_reset_day0_truncates_cascade_protects_schemes_flushes_redis_and_evicts_caches(
    e2e_infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Story 23.1 end-to-end against real PG18 + Redis 7.4 + real `create_app()`."""
    pg_url, redis_url = e2e_infra_urls

    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV", "e2e")
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-e2e-day0-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-e2e-day0-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    reset_first_boot_mod = _load_module("it_09_reset_db_first_boot", RESET_FIRST_BOOT_PATH)
    reset_day0_mod = _load_module("it_reset_day0", RESET_DAY0_PATH)

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}

    engine = create_async_engine(pg_url)
    redis_client = redis.Redis.from_url(redis_url)
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            assert getattr(app.state, "db_engine", None) is not None
            assert getattr(app.state, "session_maker", None) is not None
            assert getattr(app.state, "dbos_uow", None) is not None
            assert getattr(app.state, "dbos_datasource", None) is not None
            assert getattr(app.state, "redis_client", None) is not None

            org_id = new_uuid7_str()
            user_id = new_uuid7_str()
            ws_id = new_uuid7_str()
            wf_def_id = new_uuid7_str()
            run_id = new_uuid7_str()
            step_exec_id = new_uuid7_str()
            snapshot_id = new_uuid7_str()
            audit_id = new_uuid7_str()
            source_event_id = new_uuid7_str()
            old_boot_epoch = new_uuid7_str()

            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO org_units (
                            id, slug, name, unit_type, lead_user_ids_jsonb, member_user_ids_jsonb
                        )
                        VALUES (
                            CAST(:id AS uuid), 'org-e2e-23-1', 'Org E2E 23.1',
                            'ENTERPRISE', '[]'::jsonb, '[]'::jsonb
                        )
                        """
                    ),
                    {"id": org_id},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO users (
                            id, email, display_name, auth_mode,
                            human_profile_archetype, platform_role, primary_org_unit_id
                        )
                        VALUES (
                            CAST(:id AS uuid), 'alice.23.1@orcia.ia', 'Alice 23.1',
                            'LOCAL', 'TECH_LEAD', 'PLATFORM_ADMIN', CAST(:org_id AS uuid)
                        )
                        """
                    ),
                    {"id": user_id, "org_id": org_id},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode)
                        VALUES (
                            CAST(:id AS uuid), 'ws-e2e-23-1', 'Workspace 23.1',
                            CAST(:org_id AS uuid), 'STANDARD'
                        )
                        """
                    ),
                    {"id": ws_id, "org_id": org_id},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workflow_definitions (
                            id, workspace_id, uri, version, source_format, sha256
                        )
                        VALUES (
                            CAST(:id AS uuid), CAST(:ws_id AS uuid),
                            'orcia://workflows/e2e-23-1-test', '1.0.0', 'ORCIA', :sha256
                        )
                        """
                    ),
                    {"id": wf_def_id, "ws_id": ws_id, "sha256": "a" * 64},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO workflow_runs (
                            id, run_key, workspace_id, workflow_def_id,
                            root_run_id, status, initiated_by_user_id
                        )
                        VALUES (
                            CAST(:id AS uuid), 'run-e2e-23-1', CAST(:ws_id AS uuid),
                            CAST(:wf_def_id AS uuid), CAST(:id AS uuid),
                            'RUNNING', CAST(:user_id AS uuid)
                        )
                        """
                    ),
                    {
                        "id": run_id,
                        "ws_id": ws_id,
                        "wf_def_id": wf_def_id,
                        "user_id": user_id,
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO step_executions (
                            id, step_execution_key, run_id, step_key, step_index, status
                        )
                        VALUES (
                            CAST(:id AS uuid), 'step-e2e-23-1', CAST(:run_id AS uuid),
                            'frame-intent', 0, 'COMMITTED'
                        )
                        """
                    ),
                    {"id": step_exec_id, "run_id": run_id},
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO blackboard_snapshots (
                            id, snapshot_key, run_id, step_execution_id, step_key,
                            branch_status, artifact_cas_key, artifact_sha256
                        )
                        VALUES (
                            CAST(:id AS uuid), 'snap-e2e-23-1', CAST(:run_id AS uuid),
                            CAST(:step_exec_id AS uuid), 'frame-intent',
                            'ACTIVE', 'cas/e2e-23-1', :sha256
                        )
                        """
                    ),
                    {
                        "id": snapshot_id,
                        "run_id": run_id,
                        "step_exec_id": step_exec_id,
                        "sha256": "b" * 64,
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        INSERT INTO audit_ledger (
                            id, source_event_id, workspace_id, org_unit_id,
                            run_id, root_run_id, step_execution_id,
                            actor_type, actor_id, event_type, summary, trace_id
                        )
                        VALUES (
                            CAST(:id AS uuid), CAST(:src_id AS uuid),
                            CAST(:ws_id AS uuid), CAST(:org_id AS uuid),
                            CAST(:run_id AS uuid), CAST(:run_id AS uuid),
                            CAST(:step_exec_id AS uuid),
                            'HUMAN', :actor_id, 'STEP_COMMITTED', 'Snapshot committed', :trace_id
                        )
                        """
                    ),
                    {
                        "id": audit_id,
                        "src_id": source_event_id,
                        "ws_id": ws_id,
                        "org_id": org_id,
                        "run_id": run_id,
                        "step_exec_id": step_exec_id,
                        "actor_id": user_id,
                        "trace_id": "0" * 32,
                    },
                )
                await conn.execute(
                    sa.text(
                        """
                        UPDATE platform_auth_settings
                        SET auth_mode = 'SSO',
                            two_factor_mode = 'TOTP',
                            oidc_issuer_url = 'https://idp.example.test',
                            boot_epoch = CAST(:boot_epoch AS uuid)
                        WHERE singleton_key = 'GLOBAL'
                        """
                    ),
                    {"boot_epoch": old_boot_epoch},
                )

            # Seed Redis keys that must be flushed by reset_day0
            redis_client.set("help:test", "cached-help-payload")
            redis_client.set("lock:step:1", user_id)
            assert int(redis_client.dbsize()) >= 2

            # 1. `09_reset_db_first_boot.py` MUST fail explicitly when append-only rows hold
            # ON DELETE RESTRICT refs, without disabling triggers or partially deleting users.
            with pytest.raises(RuntimeError, match="ON DELETE RESTRICT"):
                await reset_first_boot_mod.reset_database_to_first_boot(engine, apply_changes=True)

            async with engine.connect() as conn:
                users_before = int(
                    (await conn.execute(sa.text("SELECT COUNT(*) FROM users"))).scalar_one()
                )
                assert users_before == 1

            # 2. `reset_day0.reset_day0_environment` truncates `public`/`dbos` CASCADE + Redis
            summary = reset_day0_mod.reset_day0_environment(
                database_url=pg_url,
                redis_url=redis_url,
            )
            assert summary["remaining_users_count"] == 0
            assert summary["redis_flushed"] is True
            assert "connector_schemes" not in summary["truncated_public_tables"]
            assert "alembic_version" not in summary["truncated_public_tables"]

            # 3. Call real `POST /api/v1/_e2e/evict-memory-caches` on `create_app()`
            evict_resp = await client.post("/api/v1/_e2e/evict-memory-caches")
            assert evict_resp.status_code == 200, evict_resp.text
            evict_payload = evict_resp.json()
            assert evict_payload["evicted"] is True
            assert len(evict_payload["cleared_caches"]) >= 1

            # Critical infra handles must survive eviction intact
            for infra_attr in (
                "db_engine",
                "session_maker",
                "http_client",
                "redis_client",
                "sse_broker",
                "dbos_uow",
                "dbos_datasource",
            ):
                assert getattr(app.state, infra_attr, None) is not None, (
                    f"{infra_attr} evicted unexpectedly"
                )

        # 4. Direct PostgreSQL 18 + Redis 7.4 assertions
        async with engine.connect() as conn:
            for table in (
                "users",
                "workflow_runs",
                "step_executions",
                "blackboard_snapshots",
                "audit_ledger",
            ):
                count_val = int(
                    (await conn.execute(sa.text(f"SELECT COUNT(*) FROM {table}"))).scalar_one()
                )
                assert count_val == 0, f"Expected 0 rows in {table}, found {count_val}"

            schemes_count = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM connector_schemes"))).scalar_one()
            )
            assert schemes_count >= 7

            packs_count = int(
                (
                    await conn.execute(sa.text("SELECT COUNT(*) FROM declarative_pack_bundles"))
                ).scalar_one()
            )
            assert packs_count >= 1

            trigger_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT t.tgname, t.tgenabled::text
                        FROM pg_trigger t
                        JOIN pg_class c ON c.oid = t.tgrelid
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public'
                          AND NOT t.tgisinternal
                          AND t.tgname IN (
                              'trg_blackboard_snapshots_append_only',
                              'prevent_audit_ledger_mutation'
                          )
                        ORDER BY t.tgname ASC
                        """
                    )
                )
            ).fetchall()
            trigger_map = {str(r[0]): str(r[1]) for r in trigger_rows}
            assert trigger_map == {
                "prevent_audit_ledger_mutation": "O",
                "trg_blackboard_snapshots_append_only": "O",
            }

            auth_row = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT auth_mode, two_factor_mode, oidc_issuer_url, boot_epoch::text
                        FROM platform_auth_settings
                        WHERE singleton_key = 'GLOBAL'
                        """
                    )
                )
            ).fetchone()
            assert auth_row is not None
            assert auth_row[0] == "LOCAL"
            assert auth_row[1] == "NONE"
            assert auth_row[2] is None
            assert UUID(str(auth_row[3])) != UUID(old_boot_epoch)

            # 5. Inspect pg_constraint ON DELETE RESTRICT refs & dbos.* runtime tables emptied
            restrict_fk_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT cl.relname, c.conname
                        FROM pg_constraint c
                        JOIN pg_class cl ON cl.oid = c.conrelid
                        WHERE c.contype = 'f' AND c.confdeltype = 'r'
                          AND c.connamespace = 'public'::regnamespace
                        """
                    )
                )
            ).fetchall()
            restrict_tables = {str(r[0]) for r in restrict_fk_rows}
            assert "blackboard_snapshots" in restrict_tables

            dbos_runtime_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'dbos'
                          AND table_type = 'BASE TABLE'
                          AND table_name NOT IN (
                              'dbos_migrations',
                              'dbos_datasource_migrations',
                              'alembic_version'
                          )
                        ORDER BY table_name ASC
                        """
                    )
                )
            ).fetchall()
            for (dbos_table,) in dbos_runtime_rows:
                dbos_cnt = int(
                    (
                        await conn.execute(sa.text(f'SELECT COUNT(*) FROM "dbos"."{dbos_table}"'))
                    ).scalar_one()
                )
                assert dbos_cnt == 0, (
                    f"Expected dbos.{dbos_table} empty after reset, got {dbos_cnt}"
                )

        # 6. Dynamic PG18 orphan table detection via information_schema.tables -> RuntimeError
        async with engine.begin() as conn:
            await conn.execute(
                sa.text("CREATE TABLE public.tmp_orphan_alembic_23_6a (id uuid PRIMARY KEY)")
            )
        try:
            with pytest.raises(RuntimeError, match="Tables Alembic orphelines"):
                await reset_first_boot_mod.reset_database_to_first_boot(engine, apply_changes=False)
        finally:
            async with engine.begin() as conn:
                await conn.execute(sa.text("DROP TABLE IF EXISTS public.tmp_orphan_alembic_23_6a"))

        clean_dry_run = await reset_first_boot_mod.reset_database_to_first_boot(
            engine, apply_changes=False
        )
        assert clean_dry_run.dry_run is True
        assert clean_dry_run.remaining_users_count == 0

        # 7. `09_reset_db_first_boot.py --apply` commits on mutable state + flushes Redis
        async with engine.begin() as conn:
            tmp_org = new_uuid7_str()
            tmp_usr = new_uuid7_str()
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO org_units (
                        id, slug, name, unit_type, lead_user_ids_jsonb, member_user_ids_jsonb
                    )
                    VALUES (
                        CAST(:id AS uuid), 'org-apply-23-6a', 'Org Apply 23.6a',
                        'ENTERPRISE', '[]'::jsonb, '[]'::jsonb
                    )
                    """
                ),
                {"id": tmp_org},
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO users (
                        id, email, display_name, auth_mode,
                        human_profile_archetype, platform_role, primary_org_unit_id
                    )
                    VALUES (
                        CAST(:id AS uuid), 'apply.23.6a@orcia.ia', 'Apply 23.6a',
                        'LOCAL', 'TECH_LEAD', 'PLATFORM_ADMIN', CAST(:org_id AS uuid)
                    )
                    """
                ),
                {"id": tmp_usr, "org_id": tmp_org},
            )
        redis_client.set("ephemeral:apply:23-6a", "1")
        committed_report = await reset_first_boot_mod.reset_database_to_first_boot(
            engine, apply_changes=True
        )
        assert committed_report.committed is True
        assert committed_report.dry_run is False
        assert committed_report.remaining_users_count == 0
        assert committed_report.deleted_rows_total >= 2
        assert int(redis_client.dbsize()) == 0
    finally:
        redis_client.close()
        await engine.dispose()
