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

from orcia_api.dependencies import initialize_app_services
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
    """Verify processes CTE anti-Cartesian, BU recursive filter, and override + outbox on PG18."""
    engine = create_async_engine(database_url)

    run_id = new_uuid7_str()
    step_id = new_uuid7_str()
    karim_id = "0192c4e0-0000-7000-8000-000000000601"
    user_id = "0192c4e0-0000-7000-8000-000000000603"
    ws_id = new_uuid7_str()
    wf_id = new_uuid7_str()
    bu_id = new_uuid7_str()

    # 1. Insert org tree (ENTERPRISE -> BU), karim/marc users, workspace, paused run & ledger rows
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
                "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                "VALUES (CAST(:id AS uuid), 'bu-finops-test', 'Direction FinOps', 'BU', :parent)"
            ),
            {"id": bu_id, "parent": root_ou},
        )
        for uid, email, name, role in (
            (karim_id, "karim.benali@orcia.io", "Karim Benali", "PLATFORM_ADMIN"),
            (user_id, "marc.lead@orcia.io", "Marc Lead", "TEAM_LEAD"),
        ):
            await conn.execute(
                sa.text(
                    "INSERT INTO users ("
                    "  id, email, display_name, auth_mode, human_profile_archetype, "
                    "  platform_role, primary_org_unit_id, is_active"
                    ") VALUES ("
                    "  CAST(:id AS uuid), :email, :name, 'LOCAL', 'TECH_LEAD', "
                    "  :role, CAST(:ou_id AS uuid), TRUE"
                    ") ON CONFLICT (id) DO NOTHING"
                ),
                {"id": uid, "email": email, "name": name, "role": role, "ou_id": str(root_ou)},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, name, slug, owner_org_unit_id) "
                "VALUES (CAST(:id AS uuid), 'FinOps Workspace', 'ws-finops', CAST(:ou_id AS uuid)) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": ws_id, "ou_id": bu_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions (id, uri, version, sha256, workspace_id) "
                "VALUES (CAST(:id AS uuid), 'orcia://wf/paused-review@v1', '1.0.0', 'sha-002', "
                "        CAST(:ws_id AS uuid)) "
                "ON CONFLICT DO NOTHING"
            ),
            {"id": wf_id, "ws_id": ws_id},
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
        # Seed 2 audit_ledger entries + 2 gate_evaluations on same run (ZERO Cartesian check)
        for idx, cost in ((1, "2.500000"), (2, "1.500000")):
            await conn.execute(
                sa.text(
                    "INSERT INTO audit_ledger ("
                    "  id, source_event_id, workspace_id, scope_path, run_id, actor_type, "
                    "  actor_id, event_type, summary, cost_usd, cost_source, trace_id"
                    ") VALUES ("
                    "  CAST(:id AS uuid), CAST(:src AS uuid), CAST(:ws_id AS uuid), "
                    "  :scope_path, CAST(:run_id AS uuid), 'AGENT', 'orcia-agent', "
                    "  'StepCompleted', :summary, :cost, 'INTERNAL_VERIFIED', :trace"
                    ")"
                ),
                {
                    "id": new_uuid7_str(),
                    "src": new_uuid7_str(),
                    "ws_id": ws_id,
                    "scope_path": f"WORKSPACE:{ws_id}",
                    "run_id": run_id,
                    "summary": f"Step {idx}",
                    "cost": Decimal(cost),
                    "trace": f"trace-6-2-{idx}",
                },
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO gate_evaluations ("
                    "  id, workspace_id, run_id, step_execution_id, step_key, gate_type, "
                    "  status, score, pattern_drift_passed, review_duration_ms"
                    ") VALUES ("
                    "  CAST(:id AS uuid), CAST(:ws_id AS uuid), CAST(:run_id AS uuid), "
                    "  CAST(:step_id AS uuid), :sk, 'HUMAN', 'PASS', 1.0, TRUE, 30000"
                    ")"
                ),
                {
                    "id": new_uuid7_str(),
                    "ws_id": ws_id,
                    "run_id": run_id,
                    "step_id": step_id,
                    "sk": f"gate-{idx}",
                },
            )

    # 1b. BLOCKING-01: GET /finops/dashboard?scope_type=BU returns exact non-Cartesian sums
    bu_dash_resp = await app_client.get(f"/api/v1/finops/dashboard?scope_type=BU&scope_id={bu_id}")
    assert bu_dash_resp.status_code == 200, bu_dash_resp.text
    bu_dash = bu_dash_resp.json()
    assert len(bu_dash["processes"]) >= 1
    proc = next(p for p in bu_dash["processes"] if p["workflow_id"] == wf_id)
    assert proc["workflow_title"] == "paused-review@v1"
    assert proc["runs_count"] == 1
    assert proc["paused_runs_count"] == 1
    assert proc["sample_paused_run_id"] == run_id
    assert proc["paused_reason"] == "BUDGET"
    assert proc["has_declared_baseline"] is False
    # Exact sum (2.50 + 1.50 = 4.00 USD * 0.92 = 3.68 EUR), NOT multiplied by 2 gate evaluations!
    assert abs(proc["run_cost_eur"] - round(4.0 * 0.92, 4)) < 0.01

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
    # - domain_events_outbox + audit_ledger BudgetOverrideApproved created (BLOCKING-04)
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

        outbox_count = (
            await conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM domain_events_outbox "
                    "WHERE event_type = 'BudgetOverrideApproved' AND run_id = CAST(:run_id AS uuid)"
                ),
                {"run_id": run_id},
            )
        ).scalar_one()
        assert outbox_count >= 1

        ledger_ov_count = (
            await conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM audit_ledger "
                    "WHERE event_type = 'BudgetOverrideApproved' AND run_id = CAST(:run_id AS uuid)"
                ),
                {"run_id": run_id},
            )
        ).scalar_one()
        assert ledger_ov_count >= 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_finops_observer_mode_and_idor_forbidden_403(
    database_url: str,
    app_client: AsyncClient,
) -> None:
    """Verify READ_ONLY_OBSERVER -> 403 and unauthorized contributor IDOR -> 403 (`BLOCKING-05`)."""
    budget_payload = {
        "scope_type": "GLOBAL",
        "scope_id": None,
        "monthly_budget_usd": 100.0,
        "warning_threshold_pct": 80,
        "hard_stop_pct": 100,
    }
    resp = await app_client.put(
        "/api/v1/finops/budgets",
        json=budget_payload,
        headers={"X-Orcia-Active-Hat": "READ_ONLY_OBSERVER"},
    )
    assert resp.status_code == 403
    problem = resp.json()
    assert problem["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # Non-admin contributor token cannot mutate GLOBAL budget (BLOCKING-05)
    from orcia_api.dependencies import initialize_app_services
    from orcia_api.main import create_app

    app = create_app()
    initialize_app_services(app)
    auth_svc = app.state.auth_service
    contrib = auth_svc.get_user_by_id("0192c4e0-0000-7000-8000-000000000605")
    contrib_token = auth_svc._issue_for_user(contrib, "LOCAL", None).access_token
    resp_idor = await app_client.put(
        "/api/v1/finops/budgets",
        json=budget_payload,
        headers={"Authorization": f"Bearer {contrib_token}"},
    )
    assert resp_idor.status_code == 403


@pytest.mark.asyncio
async def test_finops_global_baselines_workspace_isolation_postgres18(
    database_url: str,
    app_client: AsyncClient,
) -> None:
    """Verify restricted caller on ?scope_type=GLOBAL only sees own baselines (RES-02)."""
    import json

    from orcia_core.permissions.models import UserIdentity

    engine = create_async_engine(database_url)
    org_a = new_uuid7_str()
    org_b = new_uuid7_str()
    ws_a = new_uuid7_str()
    ws_b = new_uuid7_str()
    user_a_id = new_uuid7_str()
    wf_a = new_uuid7_str()
    wf_b = new_uuid7_str()

    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type, member_user_ids_jsonb) VALUES "
                "(CAST(:oa AS uuid), 'team-fin-a', 'Team Fin A', 'TEAM', CAST(:ma AS jsonb)), "
                "(CAST(:ob AS uuid), 'team-fin-b', 'Team Fin B', 'TEAM', '[]'::jsonb)"
            ),
            {"oa": org_a, "ob": org_b, "ma": json.dumps([user_a_id])},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO users ("
                "  id, email, display_name, auth_mode, human_profile_archetype, "
                "  platform_role, primary_org_unit_id, is_active"
                ") VALUES ("
                "  CAST(:uid AS uuid), 'alice.fin@orcia.fr', 'Alice A', 'LOCAL', 'TECH_LEAD', "
                "  'CONTRIBUTOR', CAST(:oa AS uuid), TRUE"
                ")"
            ),
            {"uid": user_a_id, "oa": org_a},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id) VALUES "
                "(CAST(:wa AS uuid), 'ws-fin-a', 'WS Fin A', CAST(:oa AS uuid)), "
                "(CAST(:wb AS uuid), 'ws-fin-b', 'WS Fin B', CAST(:ob AS uuid))"
            ),
            {"wa": ws_a, "oa": org_a, "wb": ws_b, "ob": org_b},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions (id, uri, version, sha256, workspace_id) VALUES "
                "(CAST(:wfa AS uuid), 'orcia://wf/fin-a', '1.0.0', 'sha-fa', CAST(:wa AS uuid)), "
                "(CAST(:wfb AS uuid), 'orcia://wf/fin-b', '1.0.0', 'sha-fb', CAST(:wb AS uuid))"
            ),
            {"wfa": wf_a, "wa": ws_a, "wfb": wf_b, "wb": ws_b},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO finops_workflow_baselines ("
                "  id, workflow_definition_id, scope_id, manual_time_minutes, "
                "  manual_cost_usd, target_ttm_reduction_pct"
                ") VALUES "
                "(CAST(:ba AS uuid), CAST(:wfa AS uuid), CAST(:wa AS uuid), 100, 120.0, 20), "
                "(CAST(:bb AS uuid), CAST(:wfb AS uuid), CAST(:wb AS uuid), 200, 240.0, 30)"
            ),
            {
                "ba": new_uuid7_str(),
                "wfa": wf_a,
                "wa": ws_a,
                "bb": new_uuid7_str(),
                "wfb": wf_b,
                "wb": ws_b,
            },
        )

    app = app_client._transport.app  # type: ignore[attr-defined]
    auth_svc = app.state.auth_service
    user_a = UserIdentity(
        id=user_a_id,
        email="alice.fin@orcia.fr",
        display_name="Alice A",
        auth_mode="LOCAL",
        platform_role="CONTRIBUTOR",
        roles=("CONTRIBUTOR",),
        primary_org_unit_id=org_a,
        human_profile_archetype="TECH_LEAD",
    )
    auth_svc.register_user(user_a)
    token_a = auth_svc._issue_for_user(user_a, "LOCAL", None).access_token

    resp = await app_client.get(
        "/api/v1/finops/dashboard?scope_type=GLOBAL",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200, resp.text
    baselines = resp.json()["baselines"]
    baseline_wf_ids = {b["workflow_definition_id"] for b in baselines}
    assert wf_a in baseline_wf_ids
    assert wf_b not in baseline_wf_ids, f"Cross-workspace baseline leaked: {baselines}"

    await engine.dispose()
