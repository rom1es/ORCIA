"""Story 7.4 — Vertical Integration Tests (`HTTP -> PG18 + Redis 7.4`, `AD-17`)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer
try:
    from testcontainers.community.redis import RedisContainer
except ImportError:
    from testcontainers.redis import RedisContainer

from orcia_api.main import create_app
from orcia_core.audit_finops.post_hoc_audit import PostHocAuditService
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_7_4"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_7_4_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg_and_redis_urls() -> Iterator[tuple[str, str]]:
    with (
        PostgresContainer(
            "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        ) as pg,
        RedisContainer("redis:7.4.2-alpine") as redis_c,
    ):
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_url = f"redis://127.0.0.1:{redis_c.get_exposed_port(6379)}/0"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        alembic_cmd = [alembic_bin, "-c", "infra/migrations/alembic.ini"]
        for args in (
            [*alembic_cmd, "upgrade", "head"],
            [*alembic_cmd, "downgrade", "20261117_0702"],
            [*alembic_cmd, "upgrade", "head"],
        ):
            res = subprocess.run(args, cwd=REPO_ROOT, env=env, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(
                    f"Alembic {args} failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                )
        yield pg_url, redis_url


@pytest_asyncio.fixture
async def app_client(
    pg_and_redis_urls: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, str, str]]:
    pg_url, redis_url = pg_and_redis_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")

    app = create_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client, pg_url, redis_url


@pytest.mark.asyncio
async def test_story_7_4_supervision_kill_switch_rollback_redis_and_finops_pg18(
    app_client: tuple[AsyncClient, str, str],
) -> None:
    """Verify HTTP -> PG18 + Redis for emergency stop, `@v(N-1)` restore, SM-A1..A3 & DB reset."""
    client, pg_url, redis_url = app_client
    org_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    sp_id = new_uuid7_str()
    wf_def_id = new_uuid7_str()
    wf_uri = "orcia://pack-sdlc/workflows/help-sync-7-4"
    help_cat_id = new_uuid7_str()
    help_res_id = "help-processes-guide-7-4"
    run_running_id = new_uuid7_str()
    run_committed_id = new_uuid7_str()
    run_interactive_id = new_uuid7_str()
    audit_id = new_uuid7_str()

    engine = create_async_engine(pg_url)
    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type, lead_user_id) "
                    "VALUES (CAST(:oid AS uuid), 'org-7-4', 'Org 7.4', 'ENTERPRISE', "
                    "CAST('0192c4e0-0000-7000-8000-000000000603' AS uuid))"
                ),
                {"oid": org_id},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                    "VALUES (CAST(:wid AS uuid), 'ws-7-4', 'WS 7.4', "
                    "CAST(:oid AS uuid), 'STANDARD')"
                ),
                {"wid": ws_id, "oid": org_id},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO iam_accounts (id, principal_id, display_name, email, "
                    "account_kind, auth_source, roles_jsonb, team_ids_jsonb, status) VALUES ("
                    "CAST(:id AS uuid), 'sp-7-4', 'SP 7.4', NULL, 'SERVICE_PRINCIPAL', "
                    "'SERVICE_TOKEN', '[\"TEAM_LEAD\"]'::jsonb, CAST(:teams AS jsonb), 'ACTIVE')"
                ),
                {"id": sp_id, "teams": json.dumps([ws_id])},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workflow_definitions "
                    "(id, workspace_id, uri, version, source_format, sha256) "
                    "VALUES (CAST(:id AS uuid), CAST(:wid AS uuid), :uri, '1.0.0', 'ORCIA', :sha)"
                ),
                {"id": wf_def_id, "wid": ws_id, "uri": wf_uri, "sha": "3" * 64},
            )
            help_meta = json.dumps(
                {
                    "lang": "fr",
                    "pack_name": "core",
                    "bound_routes": ["/processes"],
                    "previous_version": "1.0.0",
                    "previous_sha256": "1" * 64,
                    "previous_cas_key": "cas/" + "1" * 64,
                    "is_autonomous_generated": True,
                    "autonomous_run_id": run_committed_id,
                }
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO catalog_items ("
                    "id, resource_id, uri, title, description, resource_type, source_format, "
                    "version, sha256, cas_key, visibility_scope, owner_org_unit_id, "
                    "item_type, metadata_jsonb) VALUES ("
                    "CAST(:id AS uuid), :res_id, 'orcia://help/fr/processes-7-4', 'Guide Auto', "
                    "'Auto', 'template', 'ORCIA', '1.1.0', :sha, :cas, 'SHARED_WORKSPACE', "
                    "CAST(:oid AS uuid), 'HELP_ARTICLE', CAST(:meta AS jsonb))"
                ),
                {
                    "id": help_cat_id,
                    "res_id": help_res_id,
                    "sha": "2" * 64,
                    "cas": "cas/" + "2" * 64,
                    "oid": org_id,
                    "meta": help_meta,
                },
            )

        # Sign contract + create trigger via HTTP
        r_contract = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_def_id}/autonomy-contract",
            params={"persona_key": "marc"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "STANDARD",
                "service_principal_id": sp_id,
                "allowed_read_sources": ["catalog:read"],
                "allowed_write_actions": ["catalog:write"],
                "max_cost_per_run_usd": 5.0,
                "post_hoc_sampling_rate": 0.15,
            },
        )
        assert r_contract.status_code == 201
        contract_id = r_contract.json()["id"]

        r_trig = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_def_id}/triggers",
            params={"persona_key": "marc"},
            json={"trigger_type": "MANUAL_AUTONOMOUS"},
        )
        assert r_trig.status_code == 201
        trig_id = r_trig.json()["id"]

        async with engine.begin() as conn:
            for rid, regime, status in (
                (run_running_id, "AUTONOMOUS_CONTRACT", "RUNNING"),
                (run_committed_id, "AUTONOMOUS_CONTRACT", "COMMITTED_AUTONOMOUS"),
                (run_interactive_id, "INTERACTIVE_COACHING", "COMPLETED"),
            ):
                await conn.execute(
                    sa.text(
                        "INSERT INTO workflow_runs ("
                        "id, run_key, workspace_id, workflow_def_id, root_run_id, "
                        "execution_regime, criticality, trigger_id, status) VALUES ("
                        "CAST(:rid AS uuid), :rkey, CAST(:wid AS uuid), CAST(:wfd AS uuid), "
                        "CAST(:rid AS uuid), :regime, 'STANDARD', CAST(:tid AS uuid), :status)"
                    ),
                    {
                        "rid": rid,
                        "rkey": f"rk-{rid}",
                        "wid": ws_id,
                        "wfd": wf_def_id,
                        "regime": regime,
                        "tid": trig_id if regime == "AUTONOMOUS_CONTRACT" else None,
                        "status": status,
                    },
                )
            await conn.execute(
                sa.text(
                    "INSERT INTO autonomous_post_hoc_audits ("
                    "id, run_id, workspace_id, contract_id, review_status) VALUES ("
                    "CAST(:aid AS uuid), CAST(:rid AS uuid), CAST(:wid AS uuid), "
                    "CAST(:cid AS uuid), 'PENDING_SAMPLE')"
                ),
                {"aid": audit_id, "rid": run_committed_id, "wid": ws_id, "cid": contract_id},
            )

        # Prime Redis help cache key
        redis_key = "help:route:/processes:core:fr"
        await redis_client.set(redis_key, json.dumps({"version": "1.1.0"}), ex=3600)
        assert await redis_client.get(redis_key) is not None

        # 1. List workspace autonomous runs excludes interactive run
        r_list = await client.get(
            f"/api/v1/workspaces/{ws_id}/autonomous-runs",
            params={"persona_key": "karim"},
        )
        assert r_list.status_code == 200
        listed_ids = {item["run_id"] for item in r_list.json()["runs"]}
        assert listed_ids == {run_running_id, run_committed_id}

        # 2. Emergency Stop -> PG18 KILL_SWITCH_STOPPED + trigger CIRCUIT_OPEN + Outbox
        r_stop = await client.post(
            f"/api/v1/runs/{run_running_id}/emergency-stop",
            params={"persona_key": "karim"},
            json={"reason": "Dérive constatée", "suspend_trigger": True},
        )
        assert r_stop.status_code == 200
        assert r_stop.json()["status"] == "KILL_SWITCH_STOPPED"
        assert r_stop.json()["trigger_suspended"] is True

        # 2b. Verify cognitive-impact lists pending post-hoc sample before rollback
        r_cog_before = await client.get(
            "/api/v1/finops/cognitive-impact",
            params={"scope_type": "WORKSPACE", "scope_id": ws_id, "persona_key": "karim"},
        )
        assert r_cog_before.status_code == 200
        assert len(r_cog_before.json()["autonomous_governance"]["pending_samples"]) == 1

        # 3. Invalidate & Restore @v(N-1) (auto-discovers help_resource_id + Redis flush)
        r_rb = await client.post(
            f"/api/v1/runs/{run_committed_id}/invalidate-and-restore",
            params={"persona_key": "karim"},
            json={"comment": "Contenu erroné"},
        )
        assert r_rb.status_code == 200
        assert r_rb.json()["status"] == "ROLLED_BACK"
        assert r_rb.json()["restored_version"] == "1.0.0"
        assert await redis_client.get(redis_key) is None

        async with engine.connect() as conn:
            stop_status = (
                await conn.execute(
                    sa.text("SELECT status FROM workflow_runs WHERE id = CAST(:id AS uuid)"),
                    {"id": run_running_id},
                )
            ).scalar()
            trig_status = (
                await conn.execute(
                    sa.text("SELECT status FROM workflow_triggers WHERE id = CAST(:id AS uuid)"),
                    {"id": trig_id},
                )
            ).scalar()
            rb_status = (
                await conn.execute(
                    sa.text("SELECT status FROM workflow_runs WHERE id = CAST(:id AS uuid)"),
                    {"id": run_committed_id},
                )
            ).scalar()
            audit_status = (
                await conn.execute(
                    sa.text(
                        "SELECT review_status FROM autonomous_post_hoc_audits "
                        "WHERE run_id = CAST(:id AS uuid)"
                    ),
                    {"id": run_committed_id},
                )
            ).scalar()
            cat_ver = (
                await conn.execute(
                    sa.text("SELECT version FROM catalog_items WHERE resource_id = :res_id"),
                    {"res_id": help_res_id},
                )
            ).scalar()
            outbox_cnt = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM domain_events_outbox "
                        "WHERE event_type IN "
                        "('KillSwitchActivated', 'AutonomousArtifactRolledBack')"
                    )
                )
            ).scalar()
            assert stop_status == "KILL_SWITCH_STOPPED"
            assert trig_status == "CIRCUIT_OPEN"
            assert rb_status == "ROLLED_BACK"
            assert audit_status == "INVALIDATED_ROLLED_BACK"
            assert cat_ver == "1.0.0"
            assert int(outbox_cnt or 0) == 2

        # 3b. Exercise PG18 post-hoc sampling insert + VALIDATED review + step kill-switch check
        post_hoc_pg = PostHocAuditService(engine=engine)
        sampled_pg = await post_hoc_pg.maybe_sample_committed_run(
            run_id=run_running_id,
            workspace_id=ws_id,
            contract_id=contract_id,
            workflow_id=wf_uri,
            force_select=True,
        )
        assert sampled_pg is not None
        r_val = await client.post(
            f"/api/v1/runs/{run_running_id}/post-hoc-review",
            params={"persona_key": "karim"},
            json={"decision": "VALIDATED", "comment": "Conforme PG18"},
        )
        assert r_val.status_code == 200
        assert r_val.json()["review_status"] == "VALIDATED"
        sup_pg = AutonomousSupervisionService(engine=engine)
        assert await sup_pg.is_run_stopped(run_running_id) is True
        assert await sup_pg.is_run_stopped(new_uuid7_str()) is False
        assert len(await sup_pg.list_autonomous_runs(workspace_id=ws_id)) >= 2
        # Unsampled run review hits insert-on-review SQL branch
        unsampled_run_id = new_uuid7_str()
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO workflow_runs ("
                    "id, run_key, workspace_id, workflow_def_id, root_run_id, "
                    "execution_regime, criticality, trigger_id, status) VALUES ("
                    "CAST(:rid AS uuid), :rkey, CAST(:wid AS uuid), CAST(:wfd AS uuid), "
                    "CAST(:rid AS uuid), 'AUTONOMOUS_CONTRACT', 'STANDARD', "
                    "CAST(:tid AS uuid), 'COMMITTED_AUTONOMOUS')"
                ),
                {
                    "rid": unsampled_run_id,
                    "rkey": f"rk-{unsampled_run_id}",
                    "wid": ws_id,
                    "wfd": wf_def_id,
                    "tid": trig_id,
                },
            )
        rec_unsampled = await post_hoc_pg.record_review(
            run_id=unsampled_run_id,
            decision="VALIDATED",
            reviewer_user_id=new_uuid7_str(),
            workspace_id=ws_id,
            contract_id=contract_id,
        )
        assert rec_unsampled is not None
        assert rec_unsampled.review_status == "VALIDATED"

        # 4. FinOps cognitive-impact computes SM-A1..A3 in SQL & isolates SM-C1/C2
        r_cog = await client.get(
            "/api/v1/finops/cognitive-impact",
            params={"scope_type": "WORKSPACE", "scope_id": ws_id, "persona_key": "karim"},
        )
        assert r_cog.status_code == 200
        gov = r_cog.json()["autonomous_governance"]
        assert gov["total_autonomous_runs"] == 3
        assert gov["killed_runs_count"] == 1
        assert gov["invalidated_samples_count"] == 1
        assert gov["invalidation_alert"] is True

        # 5. Verify 09_reset_db_first_boot.py clears autonomous_post_hoc_audits cleanly
        reset_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
        spec = spec_from_file_location("reset_db_first_boot", reset_path)
        assert spec and spec.loader
        mod = module_from_spec(spec)
        sys.modules["reset_db_first_boot"] = mod
        spec.loader.exec_module(mod)
        report = await mod.reset_database_to_first_boot(engine, apply_changes=True)
        assert report.committed is True
        async with engine.connect() as conn:
            rem_audits = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM autonomous_post_hoc_audits"))
            ).scalar()
            assert int(rem_audits or 0) == 0
    finally:
        await redis_client.aclose()
        await engine.dispose()
