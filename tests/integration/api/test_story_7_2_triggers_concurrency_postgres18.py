"""Story 7.2 — Concurrent Vertical Integration Tests (`HTTP -> PG18 + Redis 7.4`, `AD-17`)."""

from __future__ import annotations

import asyncio
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

from orcia_api.dependencies import initialize_app_services
from orcia_api.main import create_app
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.permissions import compute_webhook_hmac_sha256

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_7_2"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_7_2_pw"  # pragma: allowlist secret


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
            [*alembic_cmd, "downgrade", "-1"],
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
) -> AsyncIterator[tuple[AsyncClient, str]]:
    pg_url, redis_url = pg_and_redis_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv(
        "ORCIA_ALERTS_WEBHOOK_SECRET",
        "alert-fallback-sec",  # pragma: allowlist secret
    )

    app = create_app()
    initialize_app_services(app)
    engine = create_async_engine(pg_url)
    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    app.state.db_engine = engine
    app.state.redis_client = redis_client
    for svc_attr in ("audit_ledger_service", "finops_accounting_service"):
        svc = getattr(app.state, svc_attr, None)
        if svc is not None:
            svc._engine = engine

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, pg_url

    await redis_client.aclose()
    await engine.dispose()


@pytest.mark.asyncio
async def test_story_7_2_concurrent_webhook_dedup_self_trigger_and_reset_boot(
    app_client: tuple[AsyncClient, str],
) -> None:
    """Verify concurrent webhook burst creates 1 run, Self-Trigger Guard & DB reset."""
    client, pg_url = app_client
    ws_id = "0195f000-0000-7000-8000-000000000301"
    org_id = "0195f000-0000-7000-8000-000000000101"
    sp_id = new_uuid7_str()
    wf_id = "wf-01-qualification-prd"
    webhook_secret = "whsec-pg18-concurrency-secret"  # pragma: allowlist secret

    engine = create_async_engine(pg_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type, lead_user_id) "
                    "VALUES (CAST(:oid AS uuid), 'org-7-2', 'Org 7.2', 'ENTERPRISE', "
                    "CAST('0192c4e0-0000-7000-8000-000000000603' AS uuid)) "
                    "ON CONFLICT (id) DO UPDATE SET lead_user_id = EXCLUDED.lead_user_id"
                ),
                {"oid": org_id},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                    "VALUES (CAST(:wid AS uuid), 'ws-7-2', 'WS 7.2', CAST(:oid AS uuid), "
                    "'STANDARD') ON CONFLICT (id) DO NOTHING"
                ),
                {"wid": ws_id, "oid": org_id},
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO iam_accounts (id, principal_id, display_name, email, "
                    "account_kind, auth_source, roles_jsonb, team_ids_jsonb, status) VALUES ("
                    "CAST(:id AS uuid), 'sp-7-2', 'SP 7.2', NULL, 'SERVICE_PRINCIPAL', "
                    "'SERVICE_TOKEN', '[\"TEAM_LEAD\"]'::jsonb, CAST(:teams AS jsonb), 'ACTIVE') "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": sp_id, "teams": json.dumps([ws_id])},
            )

        r_sign = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "marc"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "STANDARD",
                "service_principal_id": sp_id,
                "allowed_read_sources": ["catalog:read"],
                "allowed_write_actions": ["catalog:write"],
                "max_cost_per_run_usd": 5.0,
            },
        )
        assert r_sign.status_code == 201

        r_create = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/triggers",
            params={"persona_key": "marc"},
            json={
                "trigger_type": "WEBHOOK",
                "webhook_secret": {
                    "action": "set",
                    "plaintext_value": webhook_secret,
                },
            },
        )
        assert r_create.status_code == 201
        trig_id = r_create.json()["id"]
        assert webhook_secret not in json.dumps(r_create.json())

        # Concurrent burst of 6 identical webhook deliveries
        raw_body = json.dumps({"delivery_key": "burst-key-1", "event_name": "push"}).encode()
        sig = compute_webhook_hmac_sha256(raw_body, webhook_secret)
        responses = await asyncio.gather(
            *[
                client.post(
                    f"/api/v1/webhooks/triggers/{trig_id}",
                    content=raw_body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Orcia-Webhook-Signature": sig,
                        "X-Webhook-Delivery-Id": "burst-key-1",
                    },
                )
                for _ in range(6)
            ]
        )
        assert all(r.status_code == 200 for r in responses)
        dispatched_count = sum(1 for r in responses if r.json()["dispatched"] is True)
        assert dispatched_count == 1

        async with engine.connect() as conn:
            run_cnt = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM workflow_runs WHERE trigger_id = CAST(:tid AS uuid)"
                    ),
                    {"tid": trig_id},
                )
            ).scalar()
            deliv_cnt = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM trigger_webhook_deliveries "
                        "WHERE trigger_id = CAST(:tid AS uuid)"
                    ),
                    {"tid": trig_id},
                )
            ).scalar()
            assert int(run_cnt or 0) == 1
            assert int(deliv_cnt or 0) == 1

        # Self-Trigger Guard on webhook with X-Orcia-Origin-Run-Id
        loop_body = json.dumps({"delivery_key": "loop-key-1"}).encode()
        loop_sig = compute_webhook_hmac_sha256(loop_body, webhook_secret)
        r_loop = await client.post(
            f"/api/v1/webhooks/triggers/{trig_id}",
            content=loop_body,
            headers={
                "Content-Type": "application/json",
                "X-Orcia-Webhook-Signature": loop_sig,
                "X-Orcia-Origin-Run-Id": "0195f000-0000-7000-8000-000000009999",
            },
        )
        assert r_loop.status_code == 200
        assert r_loop.json()["outcome"] == "SELF_TRIGGER_BLOCKED"

        async with engine.connect() as conn:
            blocked_evt = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM domain_events_outbox "
                        "WHERE event_type = 'SelfTriggerBlocked' AND aggregate_id = :tid"
                    ),
                    {"tid": trig_id},
                )
            ).scalar()
            assert int(blocked_evt or 0) == 1

        # Platform alert fallback endpoint (AD-23.5)
        alert_body = json.dumps(
            {
                "trigger_id": trig_id,
                "service": "api",
                "exception_type": "TimeoutError",
                "message": "Upstream timeout",
                "delivery_key": "alert-key-1",
            }
        ).encode()
        alert_sig = compute_webhook_hmac_sha256(alert_body, webhook_secret)
        r_alert = await client.post(
            "/api/v1/triggers/alerts",
            content=alert_body,
            headers={"Content-Type": "application/json", "X-Orcia-Webhook-Signature": alert_sig},
        )
        assert r_alert.status_code == 200
        assert r_alert.json()["dispatched"] is True

        # Verify 09_reset_db_first_boot.py clears trigger_webhook_deliveries -> workflow_triggers
        reset_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
        spec = spec_from_file_location("reset_db_first_boot", reset_path)
        assert spec and spec.loader
        mod = module_from_spec(spec)
        sys.modules["reset_db_first_boot"] = mod
        spec.loader.exec_module(mod)
        report = await mod.reset_database_to_first_boot(engine, apply_changes=True)
        assert report.committed is True
        async with engine.connect() as conn:
            rem_trigs = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_triggers"))
            ).scalar()
            rem_delivs = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM trigger_webhook_deliveries"))
            ).scalar()
            assert int(rem_trigs or 0) == 0
            assert int(rem_delivs or 0) == 0
    finally:
        await engine.dispose()
