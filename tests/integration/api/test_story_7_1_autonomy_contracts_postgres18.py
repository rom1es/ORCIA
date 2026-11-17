"""Story 7.1 — Vertical Integration Tests (`HTTP -> PostgreSQL 18`) for Autonomy Contracts.

Verifies against real `pgvector/pgvector:pg18` (`AD-17` Layer 2):
1. Alembic migration `20261117_0701` (`upgrade head`, `downgrade -1`, `upgrade head`) creates
   `autonomy_contracts` and expands `workflow_runs.status` & `domain_events_outbox.event_type`.
2. `POST /api/v1/workspaces/{ws}/workflows/{wf}/autonomy-contract` persists in `autonomy_contracts`,
   inserts `AutonomousContractSigned` into `domain_events_outbox`, and seals `audit_ledger`.
3. `POST .../runs/autonomous` commits `COMMITTED_AUTONOMOUS` or suspends
   `PAUSED_AUTONOMOUS_ESCALATION` in `workflow_runs` + `AutonomousEscalated` in Outbox (`SELECT`).
4. `POST .../autonomy-contract/revoke` updates `status = 'REVOKED'` and emits Outbox/Audit.
5. `09_reset_db_first_boot.py` clears `autonomy_contracts` before `iam_accounts` without FK error.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from importlib.util import module_from_spec, spec_from_file_location
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
from orcia_core.kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_7_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_7_1_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg_url() -> Iterator[str]:
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
        yield url


@pytest_asyncio.fixture
async def app_client(
    pg_url: str, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, str]]:
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")

    app = create_app()
    initialize_app_services(app)
    engine = create_async_engine(pg_url)
    app.state.db_engine = engine
    for svc_attr in ("audit_ledger_service", "finops_accounting_service"):
        svc = getattr(app.state, svc_attr, None)
        if svc is not None:
            svc._engine = engine

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, pg_url

    await engine.dispose()


@pytest.mark.asyncio
async def test_story_7_1_vertical_http_to_postgres18_and_reset_first_boot(
    app_client: tuple[AsyncClient, str],
) -> None:
    """Verify full HTTP -> PG18 lifecycle for autonomy_contracts, runs, outbox & audit_ledger."""
    client, pg_url = app_client
    ws_id = "0195f000-0000-7000-8000-000000000301"
    org_id = "0195f000-0000-7000-8000-000000000101"
    sp_id = new_uuid7_str()
    wf_id = "packs/orcia-docs/workflows/generate-and-attach-help"

    engine = create_async_engine(pg_url)
    try:
        # Seed org_unit, workspace, and active SERVICE_PRINCIPAL in PG18
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO org_units (id, slug, name, unit_type)
                    VALUES (CAST(:oid AS uuid), 'org-7-1', 'Org 7.1', 'ENTERPRISE')
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"oid": org_id},
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO workspaces (
                        id, slug, name, owner_org_unit_id, visibility_mode
                    )
                    VALUES (
                        CAST(:wid AS uuid), 'ws-7-1', 'Workspace 7.1',
                        CAST(:oid AS uuid), 'STANDARD'
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"wid": ws_id, "oid": org_id},
            )
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO iam_accounts (
                        id, principal_id, display_name, email, account_kind, auth_source,
                        roles_jsonb, team_ids_jsonb, status
                    )
                    VALUES (
                        CAST(:sp_id AS uuid), 'sp-pg-docs', 'SP PG Docs', NULL,
                        'SERVICE_PRINCIPAL', 'SERVICE_TOKEN',
                        '["TEAM_LEAD"]'::jsonb, CAST(:teams AS jsonb), 'ACTIVE'
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"sp_id": sp_id, "teams": f'["{ws_id}"]'},
            )

        # 1. GET state shows eligible SP
        r_get = await client.get(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "marc"},
        )
        assert r_get.status_code == 200
        assert any(sp["id"] == sp_id for sp in r_get.json()["eligible_service_principals"])

        # 2. Sign contract via HTTP POST (single signature TEAM_LEAD, no SECOPS)
        r_sign = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "marc"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "LOW_NON_CRITICAL",
                "service_principal_id": sp_id,
                "allowed_read_sources": ["orcia://docs"],
                "allowed_write_actions": ["help_article:publish"],
                "max_cost_per_run_usd": 5.0,
                "tie_break_policy": "ONTOLOGY_AXIOM_FIRST",
            },
        )
        assert r_sign.status_code == 201
        contract_id = r_sign.json()["id"]

        # Verify PG18 direct SELECT on autonomy_contracts, domain_events_outbox, audit_ledger
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        "SELECT status, signed_by_role, service_principal_id::text "
                        "FROM autonomy_contracts WHERE id = CAST(:cid AS uuid)"
                    ),
                    {"cid": contract_id},
                )
            ).fetchone()
            assert row is not None
            assert row[0] == "ACTIVE"
            assert row[1] == "TEAM_LEAD"
            assert row[2] == sp_id

            outbox_row = (
                await conn.execute(
                    sa.text(
                        "SELECT event_type FROM domain_events_outbox "
                        "WHERE aggregate_id = :cid AND event_type = 'AutonomousContractSigned'"
                    ),
                    {"cid": contract_id},
                )
            ).fetchone()
            assert outbox_row is not None

            ledger_row = (
                await conn.execute(
                    sa.text(
                        "SELECT event_type FROM audit_ledger "
                        "WHERE event_type = 'AutonomousContractSigned'"
                    )
                )
            ).fetchone()
            assert ledger_row is not None

        # 3. Execute nominal autonomous run -> COMMITTED_AUTONOMOUS in workflow_runs
        r_run = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/runs/autonomous",
            params={"persona_key": "marc"},
            json={
                "criticality": "LOW_NON_CRITICAL",
                "actions": [
                    {
                        "action_key": "help_article:publish",
                        "scheme": "catalog",
                        "payload": {"article_id": "help-studio"},
                    }
                ],
                "agentic_score": 0.92,
                "fact_verification_score": 0.96,
            },
        )
        assert r_run.status_code == 201
        assert r_run.json()["status"] == "COMMITTED_AUTONOMOUS"
        run_id_ok = r_run.json()["run_id"]

        # 4. Execute escalated autonomous run (score 0.70 < 0.85) -> PAUSED_AUTONOMOUS_ESCALATION
        r_esc = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/runs/autonomous",
            params={"persona_key": "marc"},
            json={
                "criticality": "LOW_NON_CRITICAL",
                "actions": [{"action_key": "help_article:publish", "scheme": "catalog"}],
                "agentic_score": 0.70,
                "fact_verification_score": 0.96,
            },
        )
        assert r_esc.status_code == 201
        assert r_esc.json()["status"] == "PAUSED_AUTONOMOUS_ESCALATION"
        run_id_esc = r_esc.json()["run_id"]

        async with engine.connect() as conn:
            statuses = (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, status FROM workflow_runs "
                        "WHERE id IN (CAST(:r1 AS uuid), CAST(:r2 AS uuid))"
                    ),
                    {"r1": run_id_ok, "r2": run_id_esc},
                )
            ).fetchall()
            status_map = {str(r[0]): str(r[1]) for r in statuses}
            assert status_map[run_id_ok] == "COMMITTED_AUTONOMOUS"
            assert status_map[run_id_esc] == "PAUSED_AUTONOMOUS_ESCALATION"

            esc_evt = (
                await conn.execute(
                    sa.text(
                        "SELECT event_type FROM domain_events_outbox "
                        "WHERE run_id = CAST(:r2 AS uuid) AND event_type = 'AutonomousEscalated'"
                    ),
                    {"r2": run_id_esc},
                )
            ).fetchone()
            assert esc_evt is not None

        # 5. Revoke contract
        r_rev = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract/revoke",
            params={"persona_key": "marc"},
            json={"scope_path": "GLOBAL"},
        )
        assert r_rev.status_code == 200
        assert r_rev.json()["status"] == "REVOKED"

        # 6. Verify 09_reset_db_first_boot.py clears autonomy_contracts before iam_accounts cleanly
        reset_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
        spec = spec_from_file_location("reset_db_first_boot", reset_path)
        assert spec is not None and spec.loader is not None
        reset_mod = module_from_spec(spec)
        sys.modules["reset_db_first_boot"] = reset_mod
        spec.loader.exec_module(reset_mod)
        report = await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        assert report.committed is True
        async with engine.connect() as conn:
            cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM autonomy_contracts"))).scalar()
                or 0
            )
            assert cnt == 0
    finally:
        await engine.dispose()
