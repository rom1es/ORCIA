"""Real Composition Root vertical integration tests (`HTTP -> PG18 + Redis 7.4`).

Proves `BLOCKING-01`, `BLOCKING-03`, `BLOCKING-05` & `MAJOR-01` WITHOUT manual
`app.state.*` injection:
1. `create_app()` + `app_lifespan` automatically initializes `db_engine`, `session_maker`,
   `redis_client`, `RedisSseBrokerAdapter`, `EnvelopeVaultSecretProvider`, and
   `autonomous_executor` solely from `DATABASE_URL` & `REDIS_URL`.
2. Firing a `MANUAL_AUTONOMOUS` trigger executes `execute_autonomous_contract_run`,
   persists `HELP_ARTICLE` (`catalog_items`) & updates `workflow_runs.status`, and leaves
   `domain_events_outbox` rows as `'PENDING'` for Outbox relay.
3. `RedisSseBrokerAdapter` bridges Pub/Sub events across separate broker instances.
4. `POST /api/v1/runs/{run_id}/invalidate-and-restore` restores `@v(N-1)` in PG18,
   flushes Redis `help:route:*`, and `GET /api/v1/help/resolve` serves `@v(N-1)`.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
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
from orcia_core.catalog.contextual_help import build_help_redis_cache_key
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.orchestration import RedisSseBrokerAdapter

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_epic7_comp_root"
DB_USER = "orcia"
DB_PASSWORD = "orcia_comp_root_pw"  # pragma: allowlist secret


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
            [*alembic_cmd, "downgrade", "20261117_0704"],
            [*alembic_cmd, "upgrade", "head"],
        ):
            res = subprocess.run(args, cwd=REPO_ROOT, env=env, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Alembic {args} failed:\n{res.stdout}\n{res.stderr}")
        yield pg_url, redis_url


@pytest_asyncio.fixture
async def real_lifespan_client(
    pg_and_redis_urls: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, object, str, str]]:
    pg_url, redis_url = pg_and_redis_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")

    app = create_app()
    # ZERO manual app.state.db_engine / app.state.redis_client injection!
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client, app, pg_url, redis_url


@pytest.mark.asyncio
async def test_composition_root_real_pg18_redis_pubsub_and_help_rollback(
    real_lifespan_client: tuple[AsyncClient, object, str, str],
) -> None:
    """Verify full Composition Root wiring without manual `app.state` injection."""
    client, app, pg_url, redis_url = real_lifespan_client
    assert getattr(app.state, "db_engine", None) is not None  # type: ignore[attr-defined]
    assert getattr(app.state, "session_maker", None) is not None  # type: ignore[attr-defined]
    assert getattr(app.state, "redis_client", None) is not None  # type: ignore[attr-defined]
    assert isinstance(
        getattr(app.state, "sse_broker", None),  # type: ignore[attr-defined]
        RedisSseBrokerAdapter,
    )

    org_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    sp_id = new_uuid7_str()
    wf_id = "orcia://pack-docs/workflows/generate-and-attach-help"
    article_id = "help.comp-root.processes"
    res_id_fr = f"{article_id}-fr"

    engine = create_async_engine(pg_url)
    worker_redis = aioredis.from_url(redis_url, decode_responses=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type, lead_user_id) "
                    "VALUES (CAST(:oid AS uuid), 'org-comp-root', 'Org CR', 'ENTERPRISE', "
                    "CAST('0192c4e0-0000-7000-8000-000000000603' AS uuid))"
                ),
                {"oid": org_id},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                    "VALUES (CAST(:wid AS uuid), 'ws-comp-root', 'WS CR', CAST(:oid AS uuid), "
                    "'STANDARD')"
                ),
                {"wid": ws_id, "oid": org_id},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO iam_accounts (id, principal_id, display_name, email, "
                    "account_kind, auth_source, roles_jsonb, team_ids_jsonb, status) VALUES ("
                    "CAST(:id AS uuid), 'sp-comp-root', 'SP CR', NULL, 'SERVICE_PRINCIPAL', "
                    "'SERVICE_TOKEN', '[\"TEAM_LEAD\"]'::jsonb, CAST(:teams AS jsonb), 'ACTIVE')"
                ),
                {"id": sp_id, "teams": json.dumps([ws_id])},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO catalog_items ("
                    "id, resource_id, uri, title, description, resource_type, source_format, "
                    "version, sha256, cas_key, visibility_scope, owner_org_unit_id, "
                    "item_type, metadata_jsonb) VALUES ("
                    "CAST(:id AS uuid), :res_id, :uri, 'Guide Initial', 'Base', 'template', "
                    "'ORCIA', '1.0.0', :sha, :cas, 'PUBLISHED_ORG', CAST(:oid AS uuid), "
                    "'HELP_ARTICLE', CAST(:meta AS jsonb))"
                ),
                {
                    "id": new_uuid7_str(),
                    "res_id": res_id_fr,
                    "uri": f"orcia://packs/core/help/{article_id}/fr",
                    "sha": "1" * 64,
                    "cas": "cas/" + "1" * 64,
                    "oid": org_id,
                    "meta": json.dumps(
                        {
                            "lang": "fr",
                            "pack_name": "core",
                            "layer": "BASE",
                            "bound_routes": ["/processes"],
                            "summary_what_for": "Résumé @v1.0.0",
                            "markdown_body": "# Guide Initial",
                        }
                    ),
                },
            )

        # 1. Sign contract + create trigger + fire trigger via real Composition Root
        r_sign = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "marc"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "STANDARD",
                "service_principal_id": sp_id,
                "allowed_read_sources": ["catalog:read"],
                "allowed_write_actions": ["catalog:help.attach"],
                "max_cost_per_run_usd": 5.0,
                "post_hoc_sampling_rate": 0.15,
            },
        )
        assert r_sign.status_code == 201

        r_trig = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/triggers",
            params={"persona_key": "marc"},
            json={"trigger_type": "MANUAL_AUTONOMOUS"},
        )
        assert r_trig.status_code == 201
        trig_id = r_trig.json()["id"]

        r_fire = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/triggers/{trig_id}/fire",
            params={"persona_key": "marc"},
            json={
                "idempotency_key": "comp-root-fire-1",
                "payload": {
                    "article_id": article_id,
                    "article_slug": "comp-root-processes",
                    "version": "1.0.1",
                    "pack_slug": "core",
                    "title_fr": "Guide Auto @v1.0.1",
                    "title_en": "Auto Guide @v1.0.1",
                    "bound_routes": ["/processes"],
                    "purpose_fr": "Objectif mis à jour.",
                    "purpose_en": "Updated purpose.",
                    "steps_fr": ["Étape 1"],
                    "steps_en": ["Step 1"],
                    "faq_fr": ["FAQ 1"],
                    "faq_en": ["FAQ 1"],
                    "force_post_hoc_sample": True,
                },
            },
        )
        assert r_fire.status_code == 201
        fire_body = r_fire.json()
        assert fire_body["dispatched"] is True
        run_id = fire_body["run_id"]
        assert run_id is not None

        # Verify Outbox rows stay PENDING & run/help persisted in PG18
        async with engine.connect() as conn:
            run_status = (
                await conn.execute(
                    sa.text("SELECT status FROM workflow_runs WHERE id = CAST(:rid AS uuid)"),
                    {"rid": run_id},
                )
            ).scalar()
            assert run_status == "COMMITTED_AUTONOMOUS"

            outbox_statuses = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT status FROM domain_events_outbox "
                            "WHERE event_type IN ('AutonomousContractSigned', 'TriggerFired')"
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert "PENDING" in outbox_statuses

            help_ver = (
                await conn.execute(
                    sa.text(
                        "SELECT version, metadata_jsonb->>'previous_version' "
                        "FROM catalog_items WHERE resource_id = :rid"
                    ),
                    {"rid": res_id_fr},
                )
            ).fetchone()
            assert help_ver is not None
            assert help_ver[0] == "1.0.1"
            assert help_ver[1] == "1.0.0"

        # 2. Resolve contextual help -> reads @v1.0.1 from PG18 & warms Redis
        r_help_1 = await client.get(
            "/api/v1/help/resolve",
            params={"route": "/processes", "pack": "orcia-core", "lang": "fr"},
        )
        assert r_help_1.status_code == 200
        assert r_help_1.json()["active_article"]["version"] == "1.0.1"
        assert r_help_1.json()["previous_version_available"] is True

        # 3. Cross-process Redis Pub/Sub SSE test (worker broker -> API broker)
        received: list[str] = []
        unsub = app.state.sse_broker.subscribe(  # type: ignore[attr-defined]
            lambda env: received.append(env.event_name),
            workspace_id=ws_id,
        )
        try:
            worker_broker = RedisSseBrokerAdapter(redis_client=worker_redis)
            await worker_broker.publish_async(
                workspace_id=ws_id,
                event_name="autonomous.worker.ping",
                run_id=run_id,
                step_execution_id=run_id,
                payload={"ok": True},
            )
            for _ in range(25):
                if "autonomous.worker.ping" in received:
                    break
                await asyncio.sleep(0.05)
            assert "autonomous.worker.ping" in received
        finally:
            unsub()

        # 4. Invalidate & restore @v(N-1) -> PG18 becomes 1.0.0 & Redis cache invalidated
        r_rb = await client.post(
            f"/api/v1/runs/{run_id}/invalidate-and-restore",
            params={"persona_key": "marc"},
            json={"comment": "Rollback E2E", "help_resource_id": res_id_fr},
        )
        assert r_rb.status_code == 200
        assert r_rb.json()["restored_version"] == "1.0.0"

        cache_key = build_help_redis_cache_key("/processes", "core", "fr")
        assert await worker_redis.get(cache_key) is None

        r_help_2 = await client.get(
            "/api/v1/help/resolve",
            params={"route": "/processes", "pack": "core", "lang": "fr"},
        )
        assert r_help_2.status_code == 200
        assert r_help_2.json()["active_article"]["version"] == "1.0.0"
        assert r_help_2.json()["cache_hit"] is False
    finally:
        await worker_redis.aclose()
        await engine.dispose()
