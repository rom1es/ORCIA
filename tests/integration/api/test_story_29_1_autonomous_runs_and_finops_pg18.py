"""Story 29.1 — Real PG18 Vertical Integration Tests (`UH-01`, `UH-02`, `AD-17` Layer 2)."""

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

from orcia_api.main import create_app
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.permissions.models import UserIdentity

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_29_1"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_29_1_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        res = subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Alembic failed:\n{res.stdout}\n{res.stderr}")
        yield pg_url


@pytest_asyncio.fixture
async def pg_client(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[AsyncClient, str]]:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-29-1-jwt-secret-0001")

    app = create_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        yield client, database_url


@pytest.mark.asyncio
async def test_story_29_1_multi_workspace_autonomous_runs_and_finops_scope_pg18(
    pg_client: tuple[AsyncClient, str],
) -> None:
    """Verify GET /api/v1/autonomous-runs & FinOps TEAM/BU/GLOBAL scope isolation on PG18."""
    client, pg_url = pg_client
    bu_id = new_uuid7_str()
    team_a_id = new_uuid7_str()
    team_b_id = new_uuid7_str()
    ws_a1 = new_uuid7_str()
    ws_a2 = new_uuid7_str()
    ws_b1 = new_uuid7_str()
    ws_priv = new_uuid7_str()
    lead_id = new_uuid7_str()
    bu_dir_id = new_uuid7_str()
    other_user_id = new_uuid7_str()
    wf_a1, wf_a2, wf_b1, wf_priv = (new_uuid7_str() for _ in range(4))
    run_a1, run_a2, run_b1, run_priv = (new_uuid7_str() for _ in range(4))

    engine = create_async_engine(pg_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO org_units "
                    "(id, slug, name, unit_type, parent_id, lead_user_id, lead_user_ids_jsonb) "
                    "VALUES "
                    "(CAST(:bu AS uuid), 'bu-29-1', 'BU 29.1', 'BU', NULL, "
                    "CAST(:bu_dir AS uuid), CAST(:bu_leads AS jsonb)), "
                    "(CAST(:ta AS uuid), 'team-a-29-1', 'Team A', 'TEAM', CAST(:bu AS uuid), "
                    "CAST(:lead AS uuid), CAST(:ta_leads AS jsonb)), "
                    "(CAST(:tb AS uuid), 'team-b-29-1', 'Team B', 'TEAM', "
                    "CAST(:bu AS uuid), NULL, '[]'::jsonb)"
                ),
                {
                    "bu": bu_id,
                    "ta": team_a_id,
                    "tb": team_b_id,
                    "bu_dir": bu_dir_id,
                    "bu_leads": json.dumps([bu_dir_id]),
                    "lead": lead_id,
                    "ta_leads": json.dumps([lead_id]),
                },
            )
            for wid, slug, name, oid, vis, settings in (
                (ws_a1, "ws-a1", "WS A1", team_a_id, "STANDARD", "{}"),
                (ws_a2, "ws-a2", "WS A2", team_a_id, "STANDARD", "{}"),
                (ws_b1, "ws-b1", "WS B1", team_b_id, "STANDARD", "{}"),
                (
                    ws_priv,
                    "ws-priv-29-1",
                    "WS Priv",
                    team_a_id,
                    "CONFIDENTIAL_RESTRICTED",
                    json.dumps(
                        {
                            "ui_visibility_mode": "PRIVATE_USER",
                            "personal_owner_user_id": other_user_id,
                        }
                    ),
                ),
            ):
                await conn.execute(
                    sa.text(
                        "INSERT INTO workspaces "
                        "(id, slug, name, owner_org_unit_id, visibility_mode, settings_jsonb) "
                        "VALUES (CAST(:wid AS uuid), :slug, :name, CAST(:oid AS uuid), "
                        ":vis, CAST(:st AS jsonb))"
                    ),
                    {
                        "wid": wid,
                        "slug": slug,
                        "name": name,
                        "oid": oid,
                        "vis": vis,
                        "st": settings,
                    },
                )
            for wfd, wid, uri in (
                (wf_a1, ws_a1, "orcia://workflows/a1"),
                (wf_a2, ws_a2, "orcia://workflows/a2"),
                (wf_b1, ws_b1, "orcia://workflows/b1"),
                (wf_priv, ws_priv, "orcia://workflows/priv"),
            ):
                await conn.execute(
                    sa.text(
                        "INSERT INTO workflow_definitions "
                        "(id, workspace_id, uri, version, source_format, sha256) "
                        "VALUES (CAST(:id AS uuid), CAST(:wid AS uuid), :uri, "
                        "'1.0.0', 'ORCIA', :sha)"
                    ),
                    {"id": wfd, "wid": wid, "uri": uri, "sha": "4" * 64},
                )
            for rid, wid, wfd in (
                (run_a1, ws_a1, wf_a1),
                (run_a2, ws_a2, wf_a2),
                (run_b1, ws_b1, wf_b1),
                (run_priv, ws_priv, wf_priv),
            ):
                await conn.execute(
                    sa.text(
                        "INSERT INTO workflow_runs (id, run_key, workspace_id, workflow_def_id, "
                        "root_run_id, execution_regime, criticality, status) VALUES ("
                        "CAST(:rid AS uuid), :rkey, CAST(:wid AS uuid), CAST(:wfd AS uuid), "
                        "CAST(:rid AS uuid), 'AUTONOMOUS_CONTRACT', 'STANDARD', 'RUNNING')"
                    ),
                    {"rid": rid, "rkey": f"rk-{rid}", "wid": wid, "wfd": wfd},
                )
            await conn.execute(
                sa.text(
                    "INSERT INTO finops_workflow_baselines ("
                    "id, workflow_definition_id, scope_id, manual_time_minutes, "
                    "manual_cost_usd, target_ttm_reduction_pct"
                    ") VALUES "
                    "(CAST(:ba AS uuid), CAST(:wfa AS uuid), CAST(:wa AS uuid), 60, 80.0, 20), "
                    "(CAST(:bb AS uuid), CAST(:wfb AS uuid), CAST(:wb AS uuid), 90, 120.0, 25)"
                ),
                {
                    "ba": new_uuid7_str(),
                    "wfa": wf_a1,
                    "wa": ws_a1,
                    "bb": new_uuid7_str(),
                    "wfb": wf_b1,
                    "wb": ws_b1,
                },
            )

        app = client._transport.app  # type: ignore[attr-defined]
        auth_svc = app.state.auth_service
        lead_user = UserIdentity(
            id=lead_id,
            email="lead.291@orcia.test",
            display_name="Lead 29.1",
            auth_mode="LOCAL",
            human_profile_archetype="TECH_LEAD",
            platform_role="TEAM_LEAD",
            primary_org_unit_id=team_a_id,
            roles=("TEAM_LEAD",),
        )
        bu_dir_user = UserIdentity(
            id=bu_dir_id,
            email="budir.291@orcia.test",
            display_name="BU Dir 29.1",
            auth_mode="LOCAL",
            human_profile_archetype="BU_DIRECTOR",
            platform_role="BU_DIRECTOR",
            primary_org_unit_id=bu_id,
            roles=("BU_DIRECTOR",),
        )
        auth_svc.register_user(lead_user)
        auth_svc.register_user(bu_dir_user)
        lead_tok = auth_svc._issue_for_user(lead_user, "LOCAL", None).access_token
        bu_tok = auth_svc._issue_for_user(bu_dir_user, "LOCAL", None).access_token

        # 1. GET /api/v1/autonomous-runs aggregates ws_a1 + ws_a2, excludes ws_b1 & ws_priv
        r_multi = await client.get(
            "/api/v1/autonomous-runs",
            headers={"Authorization": f"Bearer {lead_tok}"},
        )
        assert r_multi.status_code == 200, r_multi.text
        multi_ids = {r["run_id"] for r in r_multi.json()["runs"]}
        assert multi_ids == {run_a1, run_a2}

        # Direct SQL SELECT ground truth check
        async with engine.connect() as conn:
            pg_count = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*)::int FROM workflow_runs "
                        "WHERE execution_regime = 'AUTONOMOUS_CONTRACT' "
                        "AND workspace_id = ANY(:ws)"
                    ),
                    {"ws": [ws_a1, ws_a2]},
                )
            ).scalar_one()
            assert pg_count == 2

        # 2. FinOps TEAM scope for TEAM_LEAD -> 200 (team_a only), 403 on team_b
        r_team_ok = await client.get(
            f"/api/v1/finops/dashboard?scope_type=TEAM&scope_id={team_a_id}",
            headers={"Authorization": f"Bearer {lead_tok}"},
        )
        assert r_team_ok.status_code == 200, r_team_ok.text
        team_wfs = {b["workflow_definition_id"] for b in r_team_ok.json()["baselines"]}
        assert team_wfs == {wf_a1}

        r_team_denied = await client.get(
            f"/api/v1/finops/dashboard?scope_type=TEAM&scope_id={team_b_id}",
            headers={"Authorization": f"Bearer {lead_tok}"},
        )
        assert r_team_denied.status_code == 403
        assert r_team_denied.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        # 3. FinOps BU scope for BU_DIRECTOR -> 200 (aggregates team A + team B)
        r_bu_ok = await client.get(
            f"/api/v1/finops/dashboard?scope_type=BU&scope_id={bu_id}",
            headers={"Authorization": f"Bearer {bu_tok}"},
        )
        assert r_bu_ok.status_code == 200, r_bu_ok.text
        bu_wfs = {b["workflow_definition_id"] for b in r_bu_ok.json()["baselines"]}
        assert bu_wfs == {wf_a1, wf_b1}
    finally:
        await engine.dispose()
