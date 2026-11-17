"""Story 6.2 — Integration Tests for FinOps Accounting, Baselines & Pauses on PostgreSQL 18.

Verifies against a real `pgvector/pgvector:pg18` testcontainer:
1. Alembic migration 20261116_0602 applies cleanly on PostgreSQL 18.
2. Vertical API wiring & database persistence:
   - PUT /api/v1/finops/budgets persists NUMERIC(12, 6) in finops_scope_budgets (SELECT PG18).
   - PUT /api/v1/finops/baselines persists baseline in finops_workflow_baselines (SELECT PG18).
   - GET /api/v1/finops/dashboard consolidates overview, processes, tiers, budgets, and baselines.
   - PAUSED_BUDGET_EXCEEDED run resumption via POST /api/v1/runs/{run_id}/budget-override:
     persists finops_budget_overrides and unpauses workflow_runs and step_executions to RUNNING.
3. Observer role restriction:
   - Mutations return HTTP 403 ERR_OBSERVER_MODE_READ_ONLY when executed by READ_ONLY_OBSERVER.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer

from orcia_api.main import create_app
from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_6_2"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_6_2_pw"  # pragma: allowlist secret


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
        res = subprocess.run(
            [*alembic_cmd, "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(
                f"Alembic upgrade head failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            )
        yield url


@pytest_asyncio.fixture
async def app_client(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-6-2-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-6-2-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={
            "X-Orcia-Active-Hat": "PLATFORM_ADMIN",
            "Accept-Language": "fr",
        },
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_finops_dashboard_and_scope_budgets_postgres18(
    database_url: str,
    app_client: AsyncClient,
) -> None:
    """Verify PUT budgets, PUT baselines, and GET dashboard on real PostgreSQL 18."""
    engine = create_async_engine(database_url)

    # 1. Configure Global Scope Budget via HTTP API
    budget_payload = {
        "scope_type": "GLOBAL",
        "scope_id": None,
        "monthly_budget_usd": 350.0,
        "warning_threshold_pct": 80,
        "hard_stop_pct": 100,
    }
    resp_budget = await app_client.put("/api/v1/finops/budgets", json=budget_payload)
    assert resp_budget.status_code == 200, resp_budget.text
    budget_data = resp_budget.json()
    assert budget_data["scope_type"] == "GLOBAL"
    assert budget_data["monthly_budget_usd"] == 350.0

    # 2. SELECT directly on PostgreSQL 18 table finops_scope_budgets
    async with engine.connect() as conn:
        res = await conn.execute(
            sa.text(
                "SELECT scope_type, monthly_budget_usd, warning_threshold_pct, hard_stop_pct "
                "FROM finops_scope_budgets WHERE scope_type = 'GLOBAL' AND scope_id IS NULL"
            )
        )
        row = res.fetchone()
        assert row is not None
        assert row[0] == "GLOBAL"
        assert Decimal(str(row[1])) == Decimal("350.000000")
        assert row[2] == 80
        assert row[3] == 100

    # 3. Configure Baseline for a workflow
    wf_def_id = new_uuid7_str()
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions (id, uri, version, sha256) "
                "VALUES (CAST(:id AS uuid), 'orcia://wf/review@v1', '1.0.0', 'sha-001') "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": wf_def_id},
        )

    baseline_payload = {
        "workflow_definition_id": wf_def_id,
        "scope_id": None,
        "manual_time_minutes": 180,
        "manual_cost_usd": 225.0,
        "target_ttm_reduction_pct": 30,
    }
    resp_baseline = await app_client.put("/api/v1/finops/baselines", json=baseline_payload)
    assert resp_baseline.status_code == 200, resp_baseline.text

    # 4. SELECT directly on PostgreSQL 18 table finops_workflow_baselines
    async with engine.connect() as conn:
        res = await conn.execute(
            sa.text(
                "SELECT workflow_definition_id, manual_time_minutes, manual_cost_usd, "
                "target_ttm_reduction_pct FROM finops_workflow_baselines "
                "WHERE workflow_definition_id = CAST(:id AS uuid)"
            ),
            {"id": wf_def_id},
        )
        row_base = res.fetchone()
        assert row_base is not None
        assert str(row_base[0]) == wf_def_id
        assert row_base[1] == 180
        assert Decimal(str(row_base[2])) == Decimal("225.000000")
        assert row_base[3] == 30

    # 5. Fetch Dashboard GET /api/v1/finops/dashboard
    resp_dash = await app_client.get("/api/v1/finops/dashboard?scope_type=GLOBAL")
    assert resp_dash.status_code == 200, resp_dash.text
    dash_json = resp_dash.json()
    assert "overview" in dash_json
    assert "processes" in dash_json
    assert "tiers" in dash_json
    assert "scope_budgets" in dash_json
    assert any(b["scope_type"] == "GLOBAL" for b in dash_json["scope_budgets"])
    assert any(b["workflow_definition_id"] == wf_def_id for b in dash_json["baselines"])

    await engine.dispose()


@pytest.mark.asyncio
async def test_finops_run_pause_and_budget_override_postgres18(
    database_url: str,
    app_client: AsyncClient,
) -> None:
    """Verify run budget override unpauses run and step_execution in PostgreSQL 18."""
    engine = create_async_engine(database_url)

    run_id = new_uuid7_str()
    step_id = new_uuid7_str()
    user_id = "0192c4e0-0000-7000-8000-000000000603"
    ws_id = new_uuid7_str()
    wf_id = new_uuid7_str()

    # 1. Insert root_ou, user, workspace, and a paused run + step execution in PostgreSQL 18
    async with engine.begin() as conn:
        root_ou = (
            await conn.execute(
                sa.text("SELECT id FROM org_units WHERE unit_type = 'ENTERPRISE' LIMIT 1")
            )
        ).scalar()
        if root_ou is None:
            root_ou = UUID(new_uuid7_str())
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                    "VALUES (:id, 'orcia-ent-test', 'ORCIA Enterprise', 'ENTERPRISE', NULL)"
                ),
                {"id": root_ou},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO users ("
                "  id, email, display_name, auth_mode, human_profile_archetype, "
                "  platform_role, primary_org_unit_id, is_active"
                ") VALUES ("
                "  CAST(:id AS uuid), 'marc.lead@orcia.io', 'Marc Lead', 'LOCAL', 'TECH_LEAD', "
                "  'PLATFORM_ADMIN', CAST(:ou_id AS uuid), TRUE"
                ") ON CONFLICT (id) DO NOTHING"
            ),
            {"id": user_id, "ou_id": str(root_ou)},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, name, slug, owner_org_unit_id) "
                "VALUES (CAST(:id AS uuid), 'FinOps Workspace', 'ws-finops', CAST(:ou_id AS uuid)) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": ws_id, "ou_id": str(root_ou)},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions (id, uri, version, sha256) "
                "VALUES (CAST(:id AS uuid), 'orcia://wf/paused@v1', '1.0.0', 'sha-002') "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": wf_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_runs ("
                "  id, run_key, workspace_id, workflow_def_id, root_run_id, status, budget_max_usd"
                ") VALUES ("
                "  CAST(:id AS uuid), 'run-paused-audit', CAST(:ws_id AS uuid), "
                "  CAST(:wf_id AS uuid), CAST(:id AS uuid), 'PAUSED_BUDGET_EXCEEDED', 10.0"
                ")"
            ),
            {"id": run_id, "ws_id": ws_id, "wf_id": wf_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO step_executions ("
                "  id, step_execution_key, run_id, step_key, step_index, "
                "  step_type, status, attempt_count"
                ") VALUES ("
                "  CAST(:step_id AS uuid), 'step-exec-paused', CAST(:run_id AS uuid), "
                "  'step-1', 1, 'AGENT', 'PAUSED_BUDGET_EXCEEDED', 1"
                ")"
            ),
            {"step_id": step_id, "run_id": run_id},
        )

    # 2. Call POST /api/v1/runs/{run_id}/budget-override to grant an extension
    override_payload = {
        "override_amount_usd": 75.0,
        "reason": "Comitologie sprint urgent - extension autorisée",
        "workspace_id": ws_id,
    }
    resp_override = await app_client.post(
        f"/api/v1/runs/{run_id}/budget-override",
        json=override_payload,
    )
    assert resp_override.status_code == 200, resp_override.text
    override_json = resp_override.json()
    assert override_json["override_amount_usd"] == 75.0
    assert override_json["new_run_status"] == "RUNNING"

    # 3. SELECT directly on PostgreSQL 18 to verify:
    # - finops_budget_overrides audit record created
    # - workflow_runs.status updated to RUNNING
    # - step_executions.status updated to PENDING
    async with engine.connect() as conn:
        res_ov = await conn.execute(
            sa.text(
                "SELECT run_id, override_amount_usd, reason FROM finops_budget_overrides "
                "WHERE run_id = CAST(:run_id AS uuid)"
            ),
            {"run_id": run_id},
        )
        row_ov = res_ov.fetchone()
        assert row_ov is not None
        assert Decimal(str(row_ov[1])) == Decimal("75.000000")
        assert "Comitologie" in row_ov[2]

        res_run = await conn.execute(
            sa.text("SELECT status FROM workflow_runs WHERE id = CAST(:run_id AS uuid)"),
            {"run_id": run_id},
        )
        assert res_run.scalar_one() == "RUNNING"

        res_step = await conn.execute(
            sa.text("SELECT status FROM step_executions WHERE id = CAST(:step_id AS uuid)"),
            {"step_id": step_id},
        )
        assert res_step.scalar_one() == "PENDING"

    await engine.dispose()


@pytest.mark.asyncio
async def test_finops_observer_mode_mutation_forbidden_403(
    app_client: AsyncClient,
) -> None:
    """Verify that READ_ONLY_OBSERVER is rejected with HTTP 403 ERR_OBSERVER_MODE_READ_ONLY."""
    budget_payload = {
        "scope_type": "GLOBAL",
        "scope_id": None,
        "monthly_budget_usd": 100.0,
        "warning_threshold_pct": 80,
        "hard_stop_pct": 100,
    }
    # Mutating with READ_ONLY_OBSERVER role
    resp = await app_client.put(
        "/api/v1/finops/budgets",
        json=budget_payload,
        headers={"X-Orcia-Active-Hat": "READ_ONLY_OBSERVER"},
    )
    assert resp.status_code == 403
    problem = resp.json()
    assert problem["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
