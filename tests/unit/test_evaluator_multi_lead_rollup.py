"""Unit tests for multi-lead rollup, BU direct members guard, and canonical lead validation."""

from __future__ import annotations

import pytest

from orcia_core.permissions import (
    MatrixPermissionEvaluator,
    OrgUnitBuMembersForbiddenError,
    OrgUnitNode,
    OrgUnitSummary,
    OrgUnitUnknownUserError,
    UserIdentity,
    WorkspaceEntity,
    assert_bu_has_no_members,
    normalize_lead_user_ids,
)
from orcia_core.permissions.iam_accounts import (
    IamAccountsGovernanceService,
)
from orcia_core.permissions.org_user_validation import (
    KnownOrgUser,
    resolve_and_validate_org_unit_leads,
)


def test_normalize_lead_user_ids_helper() -> None:
    leads, primary = normalize_lead_user_ids(
        ["alice@orcia.local", "bob@orcia.local", "alice@orcia.local"]
    )
    assert leads == ("alice@orcia.local", "bob@orcia.local")
    assert primary == "alice@orcia.local"

    leads_single, prim_single = normalize_lead_user_ids(None, lead_user_id="charlie@orcia.local")
    assert leads_single == ("charlie@orcia.local",)
    assert prim_single == "charlie@orcia.local"

    empty_leads, empty_prim = normalize_lead_user_ids([], None)
    assert empty_leads == ()
    assert empty_prim is None


def test_org_unit_node_and_summary_sync_lead_fields() -> None:
    node = OrgUnitNode(
        id="bu-1",
        slug="direction-rh",
        name="Direction RH",
        unit_type="BU",
        lead_user_ids=("lead1@orcia.local", "lead2@orcia.local"),
    )
    assert node.lead_user_ids == ("lead1@orcia.local", "lead2@orcia.local")
    assert node.lead_user_id == "lead1@orcia.local"

    node_legacy = OrgUnitNode(
        id="bu-2",
        slug="direction-finance",
        name="Direction Finance",
        unit_type="BU",
        lead_user_id="solo@orcia.local",
    )
    assert node_legacy.lead_user_ids == ("solo@orcia.local",)
    assert node_legacy.lead_user_id == "solo@orcia.local"

    summary = OrgUnitSummary(
        id="team-1",
        slug="team-recrutement",
        name="Équipe Recrutement",
        kind="TEAM",
        lead_user_ids=("lead_a@orcia.local", "lead_b@orcia.local"),
    )
    assert summary.lead_user_ids == ("lead_a@orcia.local", "lead_b@orcia.local")
    assert summary.lead_user_id == "lead_a@orcia.local"


def test_bu_no_direct_members_guard() -> None:
    # BU with members raises 422 OrgUnitBuMembersForbiddenError
    with pytest.raises(OrgUnitBuMembersForbiddenError):
        assert_bu_has_no_members("BU", ["alice@orcia.local"])

    with pytest.raises(OrgUnitBuMembersForbiddenError):
        assert_bu_has_no_members("TRIBE", ["bob@orcia.local"])

    # BU with empty members passes
    assert_bu_has_no_members("BU", [])
    assert_bu_has_no_members("BU", None)

    # TEAM with members passes
    assert_bu_has_no_members("TEAM", ["alice@orcia.local", "bob@orcia.local"])


def test_resolve_and_validate_org_unit_leads() -> None:
    known = [
        KnownOrgUser(
            principal_id="alice@orcia.local", display_name="Alice Smith", email="alice@orcia.local"
        ),
        KnownOrgUser(
            principal_id="bob@orcia.local", display_name="Bob Jones", email="bob@orcia.local"
        ),
    ]

    leads, primary = resolve_and_validate_org_unit_leads(
        lead_user_ids=["ALICE@orcia.local", "bob@orcia.local", "alice@orcia.local"],
        lead_user_id=None,
        known_users=known,
    )
    assert leads == ("alice@orcia.local", "bob@orcia.local")
    assert primary == "alice@orcia.local"

    with pytest.raises(OrgUnitUnknownUserError):
        resolve_and_validate_org_unit_leads(
            lead_user_ids=["unknown@orcia.local"],
            lead_user_id=None,
            known_users=known,
        )


def test_matrix_evaluator_multi_lead_rollup() -> None:
    """A user co-leading two distinct BUs obtains roll-up across both BUs and all child teams."""
    bu_sales = OrgUnitNode(
        id="bu-sales",
        slug="bu-sales",
        name="Direction Ventes",
        unit_type="BU",
        lead_user_ids=("co-lead@orcia.local", "other-lead@orcia.local"),
    )
    bu_tech = OrgUnitNode(
        id="bu-tech",
        slug="bu-tech",
        name="Direction Tech",
        unit_type="BU",
        lead_user_ids=("co-lead@orcia.local",),
    )
    bu_other = OrgUnitNode(
        id="bu-other",
        slug="bu-other",
        name="Direction Autre",
        unit_type="BU",
        lead_user_ids=("stranger@orcia.local",),
    )
    team_sales_fr = OrgUnitNode(
        id="team-sales-fr",
        slug="team-sales-fr",
        name="Équipe Ventes France",
        unit_type="TEAM",
        parent_id="bu-sales",
        lead_user_ids=("teamlead@orcia.local",),
    )
    team_tech_ai = OrgUnitNode(
        id="team-tech-ai",
        slug="team-tech-ai",
        name="Équipe IA",
        unit_type="TEAM",
        parent_id="bu-tech",
        lead_user_ids=("ai-lead@orcia.local",),
    )
    team_other = OrgUnitNode(
        id="team-other",
        slug="team-other",
        name="Équipe Inaccessible",
        unit_type="TEAM",
        parent_id="bu-other",
        lead_user_ids=("stranger@orcia.local",),
    )

    ws_sales_direct = WorkspaceEntity(
        id="ws-1", slug="ws-1", name="Espace Ventes Direct", owner_org_unit_id="bu-sales"
    )
    ws_sales_child = WorkspaceEntity(
        id="ws-2", slug="ws-2", name="Espace Ventes FR", owner_org_unit_id="team-sales-fr"
    )
    ws_tech_child = WorkspaceEntity(
        id="ws-3", slug="ws-3", name="Espace IA Dev", owner_org_unit_id="team-tech-ai"
    )
    ws_other = WorkspaceEntity(
        id="ws-4", slug="ws-4", name="Espace Inaccessible", owner_org_unit_id="team-other"
    )

    evaluator = MatrixPermissionEvaluator(
        org_units=(bu_sales, bu_tech, bu_other, team_sales_fr, team_tech_ai, team_other),
        workspaces=(ws_sales_direct, ws_sales_child, ws_tech_child, ws_other),
    )

    user = UserIdentity(
        id="usr-colead",
        email="co-lead@orcia.local",
        display_name="Directeur Co-Lead",
        auth_mode="LOCAL",
        human_profile_archetype="BU_DIRECTOR",
        platform_role="BU_DIRECTOR",
        primary_org_unit_id="bu-sales",
        roles=("BU_LEAD",),
    )

    # 1. Direct workspace on led BU gives DIRECT_TEAM
    acc_direct = evaluator.resolve_workspace_access(user, "ws-1")
    assert acc_direct is not None
    assert acc_direct.access_origin == "DIRECT_TEAM"

    # 2. Child workspace in bu-sales gives ROLLUP_PARENT
    acc_child1 = evaluator.resolve_workspace_access(user, "ws-2")
    assert acc_child1 is not None
    assert acc_child1.access_origin == "ROLLUP_PARENT"

    # 3. Child workspace in bu-tech gives ROLLUP_PARENT because user is co-lead of bu-tech!
    acc_child2 = evaluator.resolve_workspace_access(user, "ws-3")
    assert acc_child2 is not None
    assert acc_child2.access_origin == "ROLLUP_PARENT"

    # 4. Workspace in bu-other is not accessible
    acc_other = evaluator.resolve_workspace_access(user, "ws-4")
    assert acc_other is None


def test_iam_accounts_service_multi_led_bus_and_local_password() -> None:
    svc = IamAccountsGovernanceService()
    account = svc.create_account(
        principal_id="lead@orcia.local",
        display_name="Multi Lead User",
        email="lead@orcia.local",
        auth_source="LOCAL_PASSWORD",
        roles=["BU_LEAD", "TEAM_LEAD"],
        led_bu_ids=["bu-1", "bu-2"],
        led_team_ids=["team-1"],
    )
    assert account.auth_source == "LOCAL_PASSWORD"
    assert account.led_bu_ids == ("bu-1", "bu-2")
    assert account.led_team_ids == ("team-1",)

    updated = svc.update_account(
        account.id,
        led_bu_ids=["bu-1"],
        led_team_ids=[],
    )
    assert updated.led_bu_ids == ("bu-1",)
    assert updated.led_team_ids == ()
