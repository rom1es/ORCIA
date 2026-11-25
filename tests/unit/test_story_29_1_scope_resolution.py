"""Story 29.1 unit tests: multi-workspace autonomous runs & FinOps guards."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from tests.unit.test_epic_25_guards_and_helpers_coverage import _make_request

from orcia_api.main import create_app
from orcia_api.routers._finops_scope_guards import resolve_finops_read_scope
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService
from orcia_core.permissions import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
    build_default_auth_and_org_service,
)
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError


@pytest.mark.asyncio
async def test_autonomous_supervision_service_lists_across_authorized_workspaces() -> None:
    svc = AutonomousSupervisionService()
    ws_a = new_uuid7_str()
    ws_b = new_uuid7_str()
    ws_c = new_uuid7_str()

    await svc.register_autonomous_run(
        run_id=new_uuid7_str(),
        workspace_id=ws_a,
        workflow_id="orcia://workflows/wf-a",
        contract_id=new_uuid7_str(),
        status="RUNNING",
    )
    await svc.register_autonomous_run(
        run_id=new_uuid7_str(),
        workspace_id=ws_b,
        workflow_id="orcia://workflows/wf-b",
        contract_id=new_uuid7_str(),
        status="COMMITTED_AUTONOMOUS",
    )
    await svc.register_autonomous_run(
        run_id=new_uuid7_str(),
        workspace_id=ws_c,
        workflow_id="orcia://workflows/wf-c",
        contract_id=new_uuid7_str(),
        status="RUNNING",
    )

    items = await svc.list_autonomous_runs_for_workspaces(workspace_ids=(ws_a, ws_b))
    assert {item.workspace_id for item in items} == {ws_a, ws_b}
    assert await svc.list_autonomous_runs_for_workspaces(workspace_ids=()) == []


@pytest.mark.asyncio
async def test_get_autonomous_runs_endpoint_aggregates_authorized_workspaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    async with app.router.lifespan_context(app):
        auth_svc = app.state.auth_service
        bu_id = new_uuid7_str()
        team_a_id = new_uuid7_str()
        team_b_id = new_uuid7_str()
        ws_a = new_uuid7_str()
        ws_b = new_uuid7_str()
        ws_priv_other = new_uuid7_str()
        user_lead_id = new_uuid7_str()
        user_other_id = new_uuid7_str()

        auth_svc.evaluator.upsert_org_unit(
            OrgUnitNode(id=bu_id, slug="bu-1", name="BU 1", unit_type="BU", parent_id=None)
        )
        auth_svc.evaluator.upsert_org_unit(
            OrgUnitNode(
                id=team_a_id,
                slug="team-a",
                name="Team A",
                unit_type="TEAM",
                parent_id=bu_id,
                lead_user_ids=(user_lead_id,),
            )
        )
        auth_svc.evaluator.upsert_org_unit(
            OrgUnitNode(
                id=team_b_id, slug="team-b", name="Team B", unit_type="TEAM", parent_id=bu_id
            )
        )
        auth_svc.evaluator.upsert_workspace(
            WorkspaceEntity(
                id=ws_a,
                slug="ws-a",
                name="WS A",
                owner_org_unit_id=team_a_id,
                visibility_mode="STANDARD",
            )
        )
        auth_svc.evaluator.upsert_workspace(
            WorkspaceEntity(
                id=ws_b,
                slug="ws-b",
                name="WS B",
                owner_org_unit_id=team_b_id,
                visibility_mode="STANDARD",
            )
        )
        auth_svc.evaluator.upsert_workspace(
            WorkspaceEntity(
                id=ws_priv_other,
                slug="ws-priv",
                name="WS Priv",
                owner_org_unit_id=team_a_id,
                visibility_mode="CONFIDENTIAL_RESTRICTED",
                ui_visibility_mode="PRIVATE_USER",
                personal_owner_user_id=user_other_id,
            )
        )
        lead_user = UserIdentity(
            id=user_lead_id,
            email="lead@orcia.test",
            display_name="Lead A",
            auth_mode="LOCAL",
            human_profile_archetype="TECH_LEAD",
            platform_role="TEAM_LEAD",
            primary_org_unit_id=team_a_id,
            roles=("TEAM_LEAD",),
        )
        auth_svc.register_user(lead_user)
        auth_svc.evaluator.upsert_membership(
            WorkspaceMembershipEntity(
                id=new_uuid7_str(),
                workspace_id=ws_a,
                user_id=user_lead_id,
                role="TEAM_LEAD",
                access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            )
        )
        token = auth_svc._issue_for_user(lead_user, "LOCAL", None).access_token

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            init_res = await client.get(
                "/api/v1/autonomous-runs",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert init_res.status_code == 200
            assert init_res.json()["runs"] == []

            sup_svc: AutonomousSupervisionService = app.state.autonomous_supervision_service
            run_a = new_uuid7_str()
            run_b = new_uuid7_str()
            run_priv = new_uuid7_str()
            await sup_svc.register_autonomous_run(
                run_id=run_a,
                workspace_id=ws_a,
                workflow_id="orcia://workflows/wf-a",
                contract_id=new_uuid7_str(),
                status="RUNNING",
            )
            await sup_svc.register_autonomous_run(
                run_id=run_b,
                workspace_id=ws_b,
                workflow_id="orcia://workflows/wf-b",
                contract_id=new_uuid7_str(),
                status="RUNNING",
            )
            await sup_svc.register_autonomous_run(
                run_id=run_priv,
                workspace_id=ws_priv_other,
                workflow_id="orcia://workflows/wf-priv",
                contract_id=new_uuid7_str(),
                status="RUNNING",
            )

            res = await client.get(
                "/api/v1/autonomous-runs",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200, res.text
            payload: dict[str, Any] = res.json()
            assert payload["workspace_id"] is None
            run_ids = {r["run_id"] for r in payload["runs"]}
            assert run_a in run_ids
            assert run_b not in run_ids
            assert run_priv not in run_ids

            # Optional scope_id filter works for authorized team UUID and rejects unknown UUID
            res_team = await client.get(
                f"/api/v1/autonomous-runs?scope_id={team_a_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res_team.status_code == 200
            assert {r["run_id"] for r in res_team.json()["runs"]} == {run_a}

            res_missing = await client.get(
                f"/api/v1/autonomous-runs?scope_id={new_uuid7_str()}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res_missing.status_code == 404


@pytest.mark.asyncio
async def test_finops_scope_guard_accepts_role_bearing_team_lead_without_workspaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "orcia_api.dependencies._topology_sync.get_configured_db_engine",
        lambda _r: None,
    )
    auth_svc = build_default_auth_and_org_service()
    team_id = new_uuid7_str()
    auth_svc.evaluator.upsert_org_unit(
        OrgUnitNode(
            id=team_id, slug="team-empty", name="Team Empty", unit_type="TEAM", parent_id=None
        )
    )
    role_team_lead = UserIdentity(
        id=new_uuid7_str(),
        email="role-lead@orcia.test",
        display_name="Role Lead",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id=team_id,
        roles=("TEAM_LEAD",),
    )
    auth_svc.register_user(role_team_lead)
    req = _make_request(auth_svc=auth_svc, path="/api/v1/finops/dashboard")

    # Should not fail 403 when user carries TEAM_LEAD in roles even if workspace list is empty
    assert await resolve_finops_read_scope(req, role_team_lead, "GLOBAL", None) == ()
    assert await resolve_finops_read_scope(req, role_team_lead, "TEAM", team_id) == ()

    plain_contrib = UserIdentity(
        id=new_uuid7_str(),
        email="contrib@orcia.test",
        display_name="Contrib",
        auth_mode="LOCAL",
        human_profile_archetype="DEV",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="",
        roles=("CONTRIBUTOR",),
    )
    with pytest.raises(ScopeAccessDeniedError):
        await resolve_finops_read_scope(req, plain_contrib, "GLOBAL", None)
    with pytest.raises(ResourceNotFoundError):
        await resolve_finops_read_scope(req, role_team_lead, "TEAM", new_uuid7_str())
