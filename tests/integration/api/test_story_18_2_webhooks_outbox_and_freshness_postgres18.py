"""Story 18.2 — Vertical HTTP -> PostgreSQL 18 Integration Tests for Webhooks & Outbox Freshness.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic `20261114_1802` (`upgrade head` -> `downgrade 20261114_1801` -> `upgrade head`).
2. Webhook HMAC-SHA256 signature enforcement (`401 ERR_WEBHOOK_SIGNATURE_INVALID`).
3. Successful webhook delivery:
   - SELECT verification in `datasource_webhook_deliveries`.
   - SELECT verification in `domain_events_outbox` (`DatasourceSyncRequested`).
4. Idempotent duplicate delivery (`ALREADY_PROCESSED`, no duplicate Outbox row).
5. Differential SHA-256 short-circuit (`NO_OP_UNCHANGED`, zero Outbox row).
6. 24h staleness reconciliation (`reconcile-staleness` -> `STALE` in PostgreSQL 18).
7. Observer mode read-only guard (`403 ERR_OBSERVER_MODE_READ_ONLY`).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import pack_encrypted_secret

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_18_2"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_18_2_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
        url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        alembic_cmd = [alembic_bin, "-c", "infra/migrations/alembic.ini"]
        # Verify upgrade -> downgrade -> upgrade idempotency of revision 20261114_1802
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        subprocess.run(
            [*alembic_cmd, "downgrade", "20261114_1801"], cwd=REPO_ROOT, env=env, check=True
        )
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest.fixture
def app_client_factory(database_url: str, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-18-2-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-18-2-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)
    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.main import create_app

    cipher = PassthroughVaultCipher("orcia-story-18-2-vault-key-0001")

    def _build_client() -> tuple[AsyncClient, PassthroughVaultCipher]:
        app = create_app()
        initialize_app_services(app)
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        return client, cipher

    return _build_client


@pytest.mark.asyncio
async def test_story_18_2_webhooks_outbox_and_freshness_postgres18(
    database_url: str,
    app_client_factory,  # type: ignore[no-untyped-def]
) -> None:
    client, cipher = app_client_factory()
    engine = create_async_engine(database_url)

    ws_id = str(UUID(new_uuid7_str()))
    conn_id = str(UUID(new_uuid7_str()))
    ds_id = str(UUID(new_uuid7_str()))
    plain_secret = "secret-webhook-story-18-2"  # pragma: allowlist secret
    packed_secret = pack_encrypted_secret(
        cipher,
        owner_id=conn_id,
        plaintext=plain_secret,
        scheme="GITLAB",
        host="gitlab.internal",
    )

    # 1. Seed database with org unit, workspace, connector and datasource
    async with engine.begin() as conn:
        res = await conn.execute(sa.text("SELECT id FROM org_units LIMIT 1;"))
        row = res.fetchone()
        ou_id = row[0] if row else UUID(new_uuid7_str())
        if not row:
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type) "
                    "VALUES (:id, 'ou-18-2', 'OU 18-2', 'TEAM') "
                    "ON CONFLICT (id) DO NOTHING;"
                ),
                {"id": ou_id},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (:id, :slug, :name, :ou_id, 'STANDARD') "
                "ON CONFLICT (id) DO NOTHING;"
            ),
            {
                "id": UUID(ws_id),
                "slug": f"ws-{ws_id[:8]}",
                "name": "Workspace 18.2 Test",
                "ou_id": ou_id,
            },
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO enterprise_connectors (
                    id, connector_kind, name, base_url, auth_mode, enabled, webhook_secret_encrypted
                ) VALUES (
                    CAST(:id AS uuid), 'GITLAB', 'GitLab Enterprise',
                    'https://gitlab.internal', 'PERSONAL_ACCESS_TOKEN', true, :enc_sec
                ) ON CONFLICT (id) DO NOTHING;
                """
            ),
            {"id": conn_id, "enc_sec": packed_secret},
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspace_datasources (
                    id, workspace_id, alias, scheme, uri, role, connector_id,
                    source_nature, sync_mode, target_ref, freshness_status, fingerprint_hash
                ) VALUES (
                    CAST(:id AS uuid), CAST(:ws_id AS uuid), 'repo-core', 'git',
                    'git://gitlab.internal/core.git', 'DOCUMENT', CAST(:conn_id AS uuid),
                    'SOURCE_CODE', 'WEBHOOK_PUSH', 'main', 'PENDING_INITIAL_SYNC', NULL
                ) ON CONFLICT (id) DO NOTHING;
                """
            ),
            {"id": ds_id, "ws_id": ws_id, "conn_id": conn_id},
        )

    # 2. Webhook HMAC signature rejection test
    payload_1 = {
        "delivery_key": "del-001",
        "provider_event": "push",
        "remote_fingerprint_sha256": (
            "1111111111111111111111111111111111111111111111111111111111111111"
        ),
        "ref": "refs/heads/main",
    }
    raw_body_1 = json.dumps(payload_1).encode("utf-8")

    # Invalid signature -> 401
    bad_resp = await client.post(
        f"/api/v1/webhooks/datasources/{ds_id}",
        content=raw_body_1,
        headers={"Content-Type": "application/json", "X-Orcia-Webhook-Signature": "sha256=invalid"},
    )
    assert bad_resp.status_code == 401
    prob = bad_resp.json()
    assert prob["error_code"] == "ERR_WEBHOOK_SIGNATURE_INVALID"

    # 3. Valid signature -> 200 DELTA_SYNC_REQUIRED & Outbox published
    valid_hmac_1 = hmac.new(plain_secret.encode(), raw_body_1, hashlib.sha256).hexdigest()
    ok_resp_1 = await client.post(
        f"/api/v1/webhooks/datasources/{ds_id}",
        content=raw_body_1,
        headers={
            "Content-Type": "application/json",
            "X-Orcia-Webhook-Signature": f"sha256={valid_hmac_1}",
            "X-Webhook-Delivery-Id": "del-001",
        },
    )
    assert ok_resp_1.status_code == 200
    data_1 = ok_resp_1.json()
    assert data_1["accepted"] is True
    assert data_1["outcome"] == "DELTA_SYNC_REQUIRED"
    assert data_1["outbox_published"] is True

    # Direct PostgreSQL 18 SELECT verification
    async with engine.connect() as conn:
        deliv = await conn.execute(
            sa.text(
                "SELECT delivery_key, reconcile_outcome "
                "FROM datasource_webhook_deliveries "
                "WHERE datasource_id = CAST(:id AS uuid)"
            ),
            {"id": ds_id},
        )
        deliv_row = deliv.fetchone()
        assert deliv_row is not None
        assert deliv_row[0] == "del-001"
        assert deliv_row[1] == "DELTA_SYNC_REQUIRED"

        outbox = await conn.execute(
            sa.text(
                "SELECT event_type, aggregate_id "
                "FROM domain_events_outbox "
                "WHERE event_type = 'DatasourceSyncRequested' AND aggregate_id = :id"
            ),
            {"id": ds_id},
        )
        outbox_row = outbox.fetchone()
        assert outbox_row is not None
        assert outbox_row[0] == "DatasourceSyncRequested"

    # 4. Duplicate delivery key -> ALREADY_PROCESSED and no duplicate Outbox row
    dup_resp = await client.post(
        f"/api/v1/webhooks/datasources/{ds_id}",
        content=raw_body_1,
        headers={
            "Content-Type": "application/json",
            "X-Orcia-Webhook-Signature": f"sha256={valid_hmac_1}",
            "X-Webhook-Delivery-Id": "del-001",
        },
    )
    assert dup_resp.status_code == 200
    assert dup_resp.json()["outcome"] == "ALREADY_PROCESSED"
    assert dup_resp.json()["outbox_published"] is False

    # 5. Differential SHA-256 short-circuit: identical hash -> NO_OP_UNCHANGED & 0 Outbox row
    payload_2 = {
        "delivery_key": "del-002",
        "provider_event": "push",
        "remote_fingerprint_sha256": (
            "1111111111111111111111111111111111111111111111111111111111111111"
        ),
        "ref": "refs/heads/main",
    }
    raw_body_2 = json.dumps(payload_2).encode("utf-8")
    valid_hmac_2 = hmac.new(plain_secret.encode(), raw_body_2, hashlib.sha256).hexdigest()

    noop_resp = await client.post(
        f"/api/v1/webhooks/datasources/{ds_id}",
        content=raw_body_2,
        headers={
            "Content-Type": "application/json",
            "X-Orcia-Webhook-Signature": valid_hmac_2,
            "X-Webhook-Delivery-Id": "del-002",
        },
    )
    assert noop_resp.status_code == 200
    assert noop_resp.json()["outcome"] == "NO_OP_UNCHANGED"
    assert noop_resp.json()["outbox_published"] is False

    # 6. Staleness reconciliation: backfill last_probe_at to 30h ago -> evaluate to STALE
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                UPDATE workspace_datasources
                SET last_probe_at = NOW() - INTERVAL '30 hours',
                    last_sync_at = NOW() - INTERVAL '30 hours',
                    freshness_status = 'SYNCED'
                WHERE id = CAST(:id AS uuid);
                """
            ),
            {"id": ds_id},
        )

    # Observer mode guard -> 403
    obs_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/datasources/reconcile-staleness",
        headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
    )
    assert obs_resp.status_code == 403
    assert obs_resp.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # Lead user reconciliation -> 200 & STALE in PostgreSQL 18
    rec_resp = await client.post(
        f"/api/v1/workspaces/{ws_id}/datasources/reconcile-staleness",
        headers={"X-Orcia-Persona": "karim"},
    )
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert rec_data["evaluated_count"] >= 1
    assert rec_data["stale_count"] >= 1

    async with engine.connect() as conn:
        ds_check = await conn.execute(
            sa.text(
                "SELECT freshness_status FROM workspace_datasources WHERE id = CAST(:id AS uuid)"
            ),
            {"id": ds_id},
        )
        assert ds_check.scalar_one() == "STALE"
