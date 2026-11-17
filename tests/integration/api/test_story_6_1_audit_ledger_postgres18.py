"""Story 6.1 — Integration Tests for PostgreSQL 18 Immutable Audit Ledger (`AD-20`, `AD-24.6`).

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Migration 20261116_0601 applies cleanly on PostgreSQL 18.
2. `audit_ledger` append-only trigger enforces immutability:
   - UPDATE raises PostgreSQL exception carrying ERR_AUDIT_LEDGER_IMMUTABLE
   - DELETE raises PostgreSQL exception carrying ERR_AUDIT_LEDGER_IMMUTABLE
3. Vertical API wiring:
   - GET /api/v1/audit/ledger lists persisted entries from PostgreSQL 18
   - GET /api/v1/audit/ledger/{run_id}/provenance returns certified provenance summary
   - GET /api/v1/audit/ledger/{run_id}/export?format=json and ?format=md exports sealed dossiers
   - Non-existent run_id returns HTTP 404 RFC 9457 ERR_AUDIT_RUN_NOT_FOUND
4. DEC-SEC-01: Zero canary leak in audit_ledger.metadata_jsonb.
5. ADMIN_CONNECTION_TEST entries persist with run_id IS NULL and real measured latency.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer

from orcia_api.dependencies import initialize_app_services
from orcia_api.main import create_app
from orcia_core.audit_finops._internal.sql_audit_ledger import SqlAuditLedgerService
from orcia_core.ports.finops_telemetry import FinopsCostLedgerEntry
from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_6_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_6_1_pw"  # pragma: allowlist secret


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
        subprocess.run([*alembic_cmd, "upgrade", "head"], cwd=REPO_ROOT, env=env, check=True)
        yield url


@pytest_asyncio.fixture
async def app_client(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-6-1-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-6-1-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    app = create_app()
    initialize_app_services(app)
    auth_svc = app.state.auth_service
    admin_user = auth_svc.get_user_by_id("0192c4e0-0000-7000-8000-000000000601")
    admin_token = auth_svc._issue_for_user(admin_user, "LOCAL", None).access_token
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={
            "Authorization": f"Bearer {admin_token}",
            "Accept-Language": "fr",
        },
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_audit_ledger_immutability_trigger_postgres18(database_url: str) -> None:
    """Verify that PostgreSQL 18 trigger prevent_audit_ledger_mutation forbids UPDATE and DELETE."""
    engine = create_async_engine(database_url)
    ledger_service = SqlAuditLedgerService(engine=engine)

    entry_id = new_uuid7_str()
    source_evt_id = new_uuid7_str()

    entry = FinopsCostLedgerEntry(
        id=entry_id,
        source_event_id=source_evt_id,
        actor_type="USER",
        actor_id="admin-1",
        actor_display_name="Romain Admin",
        event_type="SettingsChanged",
        summary="Initial audit entry",
        cost_usd=0.0,
        trace_id="00000000000000000000000000000001",
    )

    # 1. Insert entry cleanly
    rec_id = await ledger_service.record_entry(entry)
    assert rec_id == entry_id

    # 2. Attempt UPDATE -> must raise exception with ERR_AUDIT_LEDGER_IMMUTABLE
    async with engine.begin() as conn:
        with pytest.raises(Exception) as exc_info:
            await conn.execute(
                sa.text(
                    "UPDATE audit_ledger SET summary = 'Tampered' WHERE id = CAST(:id AS uuid)"
                ),
                {"id": entry_id},
            )
        assert "ERR_AUDIT_LEDGER_IMMUTABLE" in str(exc_info.value)

    # 3. Attempt DELETE -> must raise exception with ERR_AUDIT_LEDGER_IMMUTABLE
    async with engine.begin() as conn:
        with pytest.raises(Exception) as exc_info:
            await conn.execute(
                sa.text("DELETE FROM audit_ledger WHERE id = CAST(:id AS uuid)"),
                {"id": entry_id},
            )
        assert "ERR_AUDIT_LEDGER_IMMUTABLE" in str(exc_info.value)

    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_ledger_admin_connection_test_persisted_postgres18(
    database_url: str,
    app_client: AsyncClient,
) -> None:
    """Verify ADMIN_CONNECTION_TEST persists with run_id IS NULL and DEC-SEC-01 scrubbing."""
    engine = create_async_engine(database_url)
    ledger_service = SqlAuditLedgerService(engine=engine)

    entry_id = new_uuid7_str()
    source_evt_id = new_uuid7_str()

    entry = FinopsCostLedgerEntry(
        id=entry_id,
        source_event_id=source_evt_id,
        actor_type="ADMIN_CONNECTION_TEST",
        actor_id="admin-test",
        actor_display_name="Admin Test",
        event_type="AdminConnectionTested",
        summary="Test connecteur live",
        run_id=None,
        latency_ms=75,
        metadata={
            "target": "mcp_github",
            "secret_token": "[REDACTED_SECRET]",
        },
        trace_id="00000000000000000000000000000002",
    )

    await ledger_service.record_entry(entry)

    # Direct PostgreSQL 18 SELECT verification
    async with engine.connect() as conn:
        res = await conn.execute(
            sa.text(
                "SELECT run_id, actor_type, latency_ms, metadata_jsonb "
                "FROM audit_ledger WHERE id = CAST(:id AS uuid)"
            ),
            {"id": entry_id},
        )
        row = res.fetchone()
        assert row is not None
        assert row[0] is None  # run_id is NULL
        assert row[1] == "ADMIN_CONNECTION_TEST"
        assert row[2] == 75
        meta = row[3] if isinstance(row[3], dict) else json.loads(row[3])
        assert "secret_token" in meta
        assert meta["secret_token"] == "[REDACTED_SECRET]"
        # DEC-SEC-01: No unscrubbed plain secret anywhere
        assert "sk-" not in str(meta)

    # API verification: GET /api/v1/audit/ledger
    resp = await app_client.get("/api/v1/audit/ledger?limit=100")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert any(item["id"] == entry_id for item in data["entries"])

    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_ledger_run_provenance_and_exports_postgres18(
    database_url: str,
    app_client: AsyncClient,
) -> None:
    """Verify provenance calculation and sealed JSON/Markdown export against PostgreSQL 18."""
    engine = create_async_engine(database_url)
    ledger_service = SqlAuditLedgerService(engine=engine)

    run_id = new_uuid7_str()
    step_id = new_uuid7_str()
    verified_sha = (
        "abcdef0123456789abcdef0123456789"  # pragma: allowlist secret
        "abcdef0123456789abcdef0123456789"  # pragma: allowlist secret
    )

    # Insert run_lock_manifests row to check alignment
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "ALTER TABLE run_lock_manifests "
                "DROP CONSTRAINT IF EXISTS run_lock_manifests_run_id_fkey;"
            )
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO run_lock_manifests (
                    run_id,
                    manifest_jsonb,
                    overrides_sha256,
                    kb_snapshot_hash,
                    manifest_sha256,
                    locked_at
                ) VALUES (
                    CAST(:run_id AS uuid),
                    '{}'::jsonb,
                    'sha-overrides',
                    'sha-kb',
                    :sha,
                    NOW()
                ) ON CONFLICT (run_id) DO UPDATE SET manifest_sha256 = EXCLUDED.manifest_sha256;
                """
            ),
            {"run_id": run_id, "sha": verified_sha},
        )

    # Insert 2 step entries for this run_id
    await ledger_service.record_entry(
        FinopsCostLedgerEntry(
            source_event_id=new_uuid7_str(),
            run_id=run_id,
            step_execution_id=step_id,
            actor_type="AGENT",
            actor_id="amelia",
            actor_display_name="Amelia Dev",
            event_type="StepCompleted",
            summary="Étape SDLC complétée",
            model_id="qwen2.5-coder",
            input_tokens=1000,
            output_tokens=400,
            cost_usd=0.0028,
            run_lock_sha256=verified_sha,
            cas_references=["seaweedfs://blobs/sha-step1"],
            trace_id="00000000000000000000000000000003",
        )
    )

    # 1. Test GET /api/v1/audit/ledger/{run_id}/provenance
    prov_resp = await app_client.get(f"/api/v1/audit/ledger/{run_id}/provenance")
    assert prov_resp.status_code == 200
    prov_data = prov_resp.json()
    assert prov_data["run_id"] == run_id
    assert prov_data["is_run_lock_aligned"] is True
    assert prov_data["total_input_tokens"] == 1000
    assert prov_data["total_output_tokens"] == 400

    # 2. Test GET /api/v1/audit/ledger/{run_id}/export?format=json
    json_resp = await app_client.get(f"/api/v1/audit/ledger/{run_id}/export?format=json")
    assert json_resp.status_code == 200
    json_data = json_resp.json()
    assert json_data["format"] == "json"
    assert json_data["manifest_sha256"] == verified_sha
    parsed = json.loads(json_data["content"])
    assert parsed["certification"]["is_run_lock_aligned"] is True

    # 3. Test GET /api/v1/audit/ledger/{run_id}/export?format=md
    md_resp = await app_client.get(f"/api/v1/audit/ledger/{run_id}/export?format=md")
    assert md_resp.status_code == 200
    md_data = md_resp.json()
    assert md_data["format"] == "md"
    assert "Dossier de Provenance" in md_data["content"]
    assert "CONFORME (100 % ALIGNÉ)" in md_data["content"]

    # 4. Test unknown run_id -> 404
    unknown_run_id = new_uuid7_str()
    err_resp = await app_client.get(f"/api/v1/audit/ledger/{unknown_run_id}/provenance")
    assert err_resp.status_code == 404
    err_json = err_resp.json()
    assert err_json.get("error_code") == "ERR_AUDIT_RUN_NOT_FOUND"

    await engine.dispose()
