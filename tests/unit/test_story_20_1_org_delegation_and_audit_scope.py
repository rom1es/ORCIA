"""Story 20.1 — Unit tests for org delegation, 7th role `ONTOLOGY_LEAD`, and scoped audit."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.audit_finops import AuditLedgerFilterParams
from orcia_core.audit_finops._internal.sql_audit_ledger_mappers import (
    build_audit_ledger_where,
    parse_row_to_entry,
)
from orcia_core.permissions import (
    DEFAULT_ROLE_PERMISSION_MATRIX,
    VALID_IAM_ROLES,
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    assert_can_create_org_unit,
    assert_can_delete_org_unit,
    assert_can_update_org_unit,
    compute_managed_org_scope,
    compute_org_unit_capabilities,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    OrgUnitScopeForbiddenError,
    ValidationDomainError,
)
from orcia_core.permissions.role_matrix import iter_scope_prefixes, normalize_scope_path


def _setup_delegated_client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, dict[str, str]]:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    svc = app.state.auth_service

    martin = UserIdentity(
        id="user-martin",
        email="martin.pecheur@orcia.ia",
        display_name="Martin Pecheur",
        auth_mode="LOCAL",
        human_profile_archetype="EXECUTIVE",
        platform_role="BU_LEAD",
        primary_org_unit_id="bu-commerce",
        roles=("BU_LEAD",),
    )
    pascal = UserIdentity(
        id="user-pascal",
        email="pascal.lacdap@orcia.ia",
        display_name="Pascal Lacdap",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="team-ventes",
        roles=("TEAM_LEAD",),
    )
    secops = UserIdentity(
        id="user-secops",
        email="secops@orcia.ia",
        display_name="SecOps Officer",
        auth_mode="LOCAL",
        human_profile_archetype="SECOPS",
        platform_role="SECOPS",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
        roles=("SECOPS",),
    )
    for persona_key, ident in (("martin", martin), ("pascal", pascal), ("secops", secops)):
        svc.register_user(ident)
        svc._persona_map[persona_key] = ident.id  # noqa: SLF001

    bu_comm = OrgUnitNode(
        id="bu-commerce",
        slug="bu-commerce",
        name="Direction Commerciale",
        unit_type="BU",
        parent_id=None,
        lead_user_id="martin.pecheur@orcia.ia",
        lead_user_ids=("martin.pecheur@orcia.ia",),
        ontology_lead_user_ids=(),
    )
    sub_bu = OrgUnitNode(
        id="sub-bu-emea",
        slug="sub-bu-emea",
        name="Pôle EMEA",
        unit_type="BU",
        parent_id="bu-commerce",
        lead_user_ids=(),
    )
    team_ventes = OrgUnitNode(
        id="team-ventes",
        slug="team-ventes",
        name="Équipe Ventes Enterprise",
        unit_type="TEAM",
        parent_id="bu-commerce",
        lead_user_id="pascal.lacdap@orcia.ia",
        lead_user_ids=("pascal.lacdap@orcia.ia",),
        member_user_ids=("nadia.dev@orcia.io",),
    )
    bu_finance = OrgUnitNode(
        id="bu-finance",
        slug="bu-finance",
        name="Direction Finance",
        unit_type="BU",
        parent_id=None,
        lead_user_ids=("claire.bu@orcia.io",),
    )
    svc.evaluator.replace_org_units((bu_comm, sub_bu, team_ventes, bu_finance))
    svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id="0192c4e0-0000-7000-8000-000000000901",
            slug="ws-ventes",
            name="Workspace Ventes",
            owner_org_unit_id="team-ventes",
            visibility_mode="SHARED_WORKSPACE",
        )
    )
    svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id="0192c4e0-0000-7000-8000-000000000902",
            slug="ws-finance",
            name="Workspace Finance",
            owner_org_unit_id="bu-finance",
            visibility_mode="SHARED_WORKSPACE",
        )
    )

    ids = {
        "bu_commerce": "bu-commerce",
        "sub_bu": "sub-bu-emea",
        "team_ventes": "team-ventes",
        "bu_finance": "bu-finance",
    }
    return TestClient(app), ids


def test_ontology_lead_seventh_role_and_bu_only_node_normalization() -> None:
    assert "ONTOLOGY_LEAD" in VALID_IAM_ROLES
    assert len(VALID_IAM_ROLES) == 7
    onto_entry = DEFAULT_ROLE_PERMISSION_MATRIX["ONTOLOGY_LEAD"]
    assert onto_entry.natural_scope == "BU"
    assert "grant" in onto_entry.resource_permissions["glossary_promotions"]

    team = OrgUnitNode(
        id="t-1",
        slug="t-1",
        name="Team",
        unit_type="TEAM",
        ontology_lead_user_ids=("someone@orcia.ia",),
    )
    assert team.ontology_lead_user_ids == ()


def test_bu_lead_delegation_capabilities_anti_eviction_and_root_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, ids = _setup_delegated_client(monkeypatch)
    martin_headers = {"X-Orcia-Persona": "martin"}

    # 1. GET /org-units returns the full org tree to all authenticated users (Story 25.2)
    #    with computed can_* flags (False on bu-finance outside Martin's subtree)
    res_list = client.get("/api/v1/org-units", headers=martin_headers)
    assert res_list.status_code == 200
    units = {u["id"]: u for u in res_list.json()["org_units"]}
    assert set(units.keys()) == {"bu-commerce", "sub-bu-emea", "team-ventes", "bu-finance"}
    assert units["bu-finance"]["can_edit"] is False
    assert units["bu-finance"]["can_create_child"] is False
    assert units["bu-finance"]["can_delete"] is False
    assert units["bu-finance"]["can_manage_members"] is False
    assert units["bu-finance"]["can_manage_ontology_leads"] is False
    assert units["bu-finance"]["can_invite_users"] is False

    assert units["bu-commerce"]["can_edit"] is True
    assert units["bu-commerce"]["can_create_child"] is True
    assert units["bu-commerce"]["can_delete"] is False
    assert units["bu-commerce"]["can_manage_ontology_leads"] is True
    assert units["bu-commerce"]["can_invite_users"] is True
    assert units["sub-bu-emea"]["can_delete"] is True
    assert units["team-ventes"]["can_delete"] is True

    # 2. Cannot delete his root BU -> 403 ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN
    del_root = client.delete(f"/api/v1/org-units/{ids['bu_commerce']}", headers=martin_headers)
    assert del_root.status_code == 403
    assert del_root.json()["error_code"] == "ERR_ORG_UNIT_ROOT_DELETE_FORBIDDEN"

    # 3. Cannot create orphan root BU -> 403 ERR_ORG_UNIT_SCOPE_FORBIDDEN
    orphan_post = client.post(
        "/api/v1/org-units",
        headers=martin_headers,
        json={"name": "Orphan BU", "kind": "BU"},
    )
    assert orphan_post.status_code == 403
    assert orphan_post.json()["error_code"] == "ERR_ORG_UNIT_SCOPE_FORBIDDEN"

    # 4. Can create TEAM under governed sub-BU & delete it cleanly
    child_post = client.post(
        "/api/v1/org-units",
        headers=martin_headers,
        json={"name": "Équipe Grands Comptes", "kind": "TEAM", "parent_id": ids["sub_bu"]},
    )
    assert child_post.status_code == 200, child_post.text
    child_id = child_post.json()["id"]
    assert client.delete(f"/api/v1/org-units/{child_id}", headers=martin_headers).status_code == 200

    # 5. Anti-eviction: sole lead of root BU cannot empty lead_user_ids -> 422
    self_evict = client.patch(
        f"/api/v1/org-units/{ids['bu_commerce']}",
        headers=martin_headers,
        json={"lead_user_ids": []},
    )
    assert self_evict.status_code == 422
    assert self_evict.json()["error_code"] == "ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN"

    # 6. Parent BU lead CAN intervene to replace sole lead of child team -> 200
    child_reassigned = client.patch(
        f"/api/v1/org-units/{ids['team_ventes']}",
        headers=martin_headers,
        json={"lead_user_ids": ["nadia.dev@orcia.io"]},
    )
    assert child_reassigned.status_code == 200

    # 7. Assigning ontology_lead_user_ids on BU succeeds; on TEAM raises 422
    onto_bu = client.patch(
        f"/api/v1/org-units/{ids['bu_commerce']}",
        headers=martin_headers,
        json={"ontology_lead_user_ids": ["claire.bu@orcia.io"]},
    )
    assert onto_bu.status_code == 200
    assert onto_bu.json()["ontology_lead_user_ids"] == ["claire.bu@orcia.io"]

    onto_team = client.patch(
        f"/api/v1/org-units/{ids['team_ventes']}",
        headers=martin_headers,
        json={"ontology_lead_user_ids": ["claire.bu@orcia.io"]},
    )
    assert onto_team.status_code == 422


def test_team_lead_pascal_lacdap_delegation_and_field_restrictions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, ids = _setup_delegated_client(monkeypatch)
    pascal_headers = {"X-Orcia-Persona": "pascal"}

    # 1. GET /org-units shows full org tree with parent BU & non-delegated units read-only
    #    and own team editable
    res_list = client.get("/api/v1/org-units", headers=pascal_headers)
    assert res_list.status_code == 200
    units = {u["id"]: u for u in res_list.json()["org_units"]}
    assert set(units.keys()) == {"bu-commerce", "sub-bu-emea", "team-ventes", "bu-finance"}
    for readonly_id in ("bu-commerce", "sub-bu-emea", "bu-finance"):
        assert units[readonly_id]["can_edit"] is False
        assert units[readonly_id]["can_create_child"] is False
        assert units[readonly_id]["can_delete"] is False
        assert units[readonly_id]["can_manage_members"] is False
        assert units[readonly_id]["can_manage_ontology_leads"] is False
        assert units[readonly_id]["can_invite_users"] is False

    assert units["team-ventes"]["can_edit"] is True
    assert units["team-ventes"]["can_manage_members"] is True
    assert units["team-ventes"]["can_delete"] is False
    assert units["team-ventes"]["can_create_child"] is False
    assert units["team-ventes"]["can_invite_users"] is False

    # 2. Cannot create or delete units -> 403
    assert (
        client.post(
            "/api/v1/org-units",
            headers=pascal_headers,
            json={"name": "Nouvelle", "kind": "TEAM", "parent_id": ids["bu_commerce"]},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/v1/org-units/{ids['team_ventes']}", headers=pascal_headers).status_code
        == 403
    )

    # 3. Cannot change parent_id or billing_enabled on own team -> 403
    assert (
        client.patch(
            f"/api/v1/org-units/{ids['team_ventes']}",
            headers=pascal_headers,
            json={"billing_enabled": False},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/v1/org-units/{ids['team_ventes']}",
            headers=pascal_headers,
            json={"parent_id": ids["sub_bu"]},
        ).status_code
        == 403
    )

    # 4. Cannot self-evict when sole lead of team -> 422 ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN
    self_remove = client.patch(
        f"/api/v1/org-units/{ids['team_ventes']}",
        headers=pascal_headers,
        json={"lead_user_ids": ["nadia.dev@orcia.io"]},
    )
    assert self_remove.status_code == 422
    assert self_remove.json()["error_code"] == "ERR_ORG_UNIT_LAST_LEAD_REMOVAL_FORBIDDEN"

    # 5. Can rename own team & update members -> 200
    ok_patch = client.patch(
        f"/api/v1/org-units/{ids['team_ventes']}",
        headers=pascal_headers,
        json={"name": "Équipe Ventes Key Accounts", "member_user_ids": ["nadia.dev@orcia.io"]},
    )
    assert ok_patch.status_code == 200
    assert ok_patch.json()["name"] == "Équipe Ventes Key Accounts"


def test_bu_lead_scoped_invitation_provisions_temp_password_and_attaches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, ids = _setup_delegated_client(monkeypatch)
    martin_headers = {"X-Orcia-Persona": "martin"}

    resp = client.post(
        "/api/v1/org-units/invite-user",
        headers=martin_headers,
        json={
            "target_org_unit_id": ids["bu_commerce"],
            "email": "camille.onto@orcia.ia",
            "display_name": "Camille Onto",
            "assignment_role": "ONTOLOGY_LEAD",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["effective_roles"] == ["ONTOLOGY_LEAD"]
    assert body["must_change_password"] is True
    assert isinstance(body["temporary_password"], str)
    assert len(body["temporary_password"]) >= 12
    assert "camille.onto@orcia.ia" in body["org_unit"]["ontology_lead_user_ids"]

    # Newly invited user is immediately resolvable in auth_service
    resolved = client.app.state.auth_service.get_user_by_id(body["account_id"])  # type: ignore[union-attr]
    assert resolved.email == "camille.onto@orcia.ia"

    # Invite TEAM_MEMBER onto child team
    team_invite = client.post(
        "/api/v1/org-units/invite-user",
        headers=martin_headers,
        json={
            "target_org_unit_id": ids["team_ventes"],
            "email": "julie.member@orcia.ia",
            "display_name": "Julie Member",
            "assignment_role": "TEAM_MEMBER",
        },
    )
    assert team_invite.status_code == 200, team_invite.text
    assert team_invite.json()["effective_roles"] == ["CONTRIBUTOR"]
    assert "julie.member@orcia.ia" in team_invite.json()["org_unit"]["member_user_ids"]


def test_audit_ledger_where_clause_for_scoped_org_units_and_empty_tuples() -> None:
    where_scoped, params_scoped = build_audit_ledger_where(
        AuditLedgerFilterParams(
            allowed_workspace_ids=("0192c4e0-0000-7000-8000-000000000901",),
            allowed_org_unit_ids=("0192c4e0-0000-7000-8000-000000000102",),
            include_null_workspace=False,
        )
    )
    assert "workspace_id = ANY(:allowed_ws_ids)" in where_scoped
    assert "(workspace_id IS NULL AND org_unit_id = ANY(:allowed_ou_ids))" in where_scoped
    assert "allowed_ws_ids" in params_scoped
    assert "allowed_ou_ids" in params_scoped

    where_empty, _ = build_audit_ledger_where(
        AuditLedgerFilterParams(
            allowed_workspace_ids=(),
            allowed_org_unit_ids=(),
            include_null_workspace=False,
        )
    )
    assert "FALSE" in where_empty

    # Verify domain compute_org_unit_capabilities observer lock
    obs = UserIdentity(
        id="obs",
        email="obs@orcia.ia",
        display_name="Obs",
        auth_mode="LOCAL",
        human_profile_archetype="OBSERVER",
        platform_role="OBSERVER",
        primary_org_unit_id="bu-commerce",
    )
    node = OrgUnitNode(id="bu-commerce", slug="bu", name="BU", unit_type="BU")
    scope = compute_managed_org_scope(obs, (node,))
    caps = compute_org_unit_capabilities(obs, node, scope, is_observer=True)
    assert caps.can_edit is False and caps.can_invite_users is False


def test_org_delegation_edge_branches_and_audit_mappers_coverage() -> None:
    obs = UserIdentity(
        id="obs",
        email="obs@orcia.ia",
        display_name="Obs",
        auth_mode="LOCAL",
        human_profile_archetype="OBSERVER",
        platform_role="OBSERVER",
        primary_org_unit_id="bu-root",
    )
    bu_root = OrgUnitNode(
        id="bu-root", slug="bu-root", name="Root", unit_type="BU", lead_user_ids=("bu@orcia.ia",)
    )
    bu_sub = OrgUnitNode(
        id="bu-sub", slug="bu-sub", name="Sub", unit_type="BU", parent_id="bu-root"
    )
    team = OrgUnitNode(
        id="team-1",
        slug="team-1",
        name="Team 1",
        unit_type="TEAM",
        parent_id="bu-root",
        lead_user_ids=("tl@orcia.ia",),
    )
    other_bu = OrgUnitNode(id="bu-other", slug="bu-other", name="Other", unit_type="BU")
    units = (bu_root, bu_sub, team, other_bu)

    with pytest.raises(ObserverModeReadOnlyError):
        assert_can_create_org_unit(obs, parent_id="bu-root", org_units=units)
    with pytest.raises(ObserverModeReadOnlyError):
        assert_can_update_org_unit(
            obs,
            target=bu_root,
            parent_id_provided=False,
            next_parent_id=None,
            billing_enabled_provided=False,
            next_billing_enabled=True,
            lead_user_ids_provided=False,
            next_lead_user_ids=(),
            ontology_lead_user_ids_provided=False,
            next_ontology_lead_user_ids=(),
            org_units=units,
        )
    with pytest.raises(ObserverModeReadOnlyError):
        assert_can_delete_org_unit(obs, target=bu_sub, org_units=units)

    bu_lead = UserIdentity(
        id="bu@orcia.ia",
        email="bu@orcia.ia",
        display_name="BU",
        auth_mode="LOCAL",
        human_profile_archetype="EXECUTIVE",
        platform_role="BU_LEAD",
        primary_org_unit_id="bu-root",
        roles=("BU_LEAD",),
    )
    with pytest.raises(OrgUnitScopeForbiddenError):
        assert_can_update_org_unit(
            bu_lead,
            target=bu_root,
            parent_id_provided=True,
            next_parent_id="bu-other",
            billing_enabled_provided=False,
            next_billing_enabled=True,
            lead_user_ids_provided=False,
            next_lead_user_ids=(),
            ontology_lead_user_ids_provided=False,
            next_ontology_lead_user_ids=(),
            org_units=units,
        )
    with pytest.raises(OrgUnitScopeForbiddenError):
        assert_can_update_org_unit(
            bu_lead,
            target=bu_sub,
            parent_id_provided=True,
            next_parent_id="bu-other",
            billing_enabled_provided=False,
            next_billing_enabled=True,
            lead_user_ids_provided=False,
            next_lead_user_ids=(),
            ontology_lead_user_ids_provided=False,
            next_ontology_lead_user_ids=(),
            org_units=units,
        )

    team_lead = UserIdentity(
        id="tl@orcia.ia",
        email="tl@orcia.ia",
        display_name="TL",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="team-1",
        roles=("TEAM_LEAD",),
    )
    with pytest.raises(OrgUnitScopeForbiddenError):
        assert_can_update_org_unit(
            team_lead,
            target=team,
            parent_id_provided=False,
            next_parent_id="bu-root",
            billing_enabled_provided=False,
            next_billing_enabled=True,
            lead_user_ids_provided=False,
            next_lead_user_ids=(),
            ontology_lead_user_ids_provided=True,
            next_ontology_lead_user_ids=("onto@orcia.ia",),
            org_units=units,
        )

    where_global, params_global = build_audit_ledger_where(
        AuditLedgerFilterParams(
            scope_path="bu:bu-root",
            allowed_workspace_ids=("0192c4e0-0000-7000-8000-000000000901",),
            include_null_workspace=True,
        )
    )
    assert "workspace_id IS NULL" in where_global
    assert params_global["scope_path"] == "bu:bu-root"

    entry = parse_row_to_entry(
        {
            "id": "e1",
            "source_event_id": "se1",
            "actor_type": "USER",
            "actor_id": "u1",
            "event_type": "ORG_UNIT_CREATED",
            "summary": "OK",
            "trace_id": "t1",
            "cas_references_jsonb": "{bad-json",
            "metadata_jsonb": "{bad-json",
        }
    )
    assert entry.cas_references == []
    assert entry.metadata == {}

    entry_none = parse_row_to_entry(
        {
            "id": "e2",
            "source_event_id": "se2",
            "actor_type": "USER",
            "actor_id": "u1",
            "event_type": "ORG_UNIT_CREATED",
            "summary": "OK",
            "trace_id": "t2",
            "cas_references_jsonb": None,
            "metadata_jsonb": None,
        }
    )
    assert entry_none.cas_references == []

    with pytest.raises(ValidationDomainError):
        normalize_scope_path("   ")
    assert iter_scope_prefixes("bu:corp/team:ops/ws:alpha") == [
        "bu:corp/team:ops",
        "bu:corp/team:ops/ws:alpha",
    ]


@pytest.mark.asyncio
async def test_enforce_audit_read_access_unions_governed_bu_and_external_led_team() -> None:
    from types import SimpleNamespace

    from orcia_api.routers._finops_auth_guards import enforce_audit_read_access
    from orcia_core.permissions import build_default_auth_and_org_service
    from orcia_core.permissions.models import OrgUnitNode, UserIdentity, WorkspaceEntity

    auth_svc = build_default_auth_and_org_service()
    hybrid_user = UserIdentity(
        id="u-hybrid",
        email="hybrid.lead@orcia.ia",
        display_name="Hybrid Lead",
        auth_mode="LOCAL",
        human_profile_archetype="EXECUTIVE",
        platform_role="BU_LEAD",
        primary_org_unit_id="bu-a",
        roles=("BU_LEAD", "TEAM_LEAD"),
    )
    auth_svc.register_user(hybrid_user)
    auth_svc.evaluator.replace_org_units(
        (
            OrgUnitNode(
                id="bu-a",
                slug="bu-a",
                name="BU A",
                unit_type="BU",
                lead_user_ids=("hybrid.lead@orcia.ia",),
            ),
            OrgUnitNode(
                id="team-a1",
                slug="team-a1",
                name="Team A1",
                unit_type="TEAM",
                parent_id="bu-a",
            ),
            OrgUnitNode(
                id="bu-c",
                slug="bu-c",
                name="BU C",
                unit_type="BU",
                lead_user_ids=("other@orcia.ia",),
            ),
            OrgUnitNode(
                id="team-ext",
                slug="team-ext",
                name="External Team B",
                unit_type="TEAM",
                parent_id="bu-c",
                lead_user_ids=("hybrid.lead@orcia.ia",),
            ),
        )
    )
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(id="ws-a1", slug="ws-a1", name="WS A1", owner_org_unit_id="team-a1")
    )
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(id="ws-ext", slug="ws-ext", name="WS Ext", owner_org_unit_id="team-ext")
    )
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(id="ws-c", slug="ws-c", name="WS C", owner_org_unit_id="bu-c")
    )

    fake_request = SimpleNamespace(
        url=SimpleNamespace(path="/api/v1/audit/ledger"),
        app=SimpleNamespace(state=SimpleNamespace(auth_service=auth_svc, db_engine=None)),
    )
    scope = await enforce_audit_read_access(fake_request, hybrid_user)  # type: ignore[arg-type]
    assert scope.allowed_org_unit_ids is not None
    assert set(scope.allowed_org_unit_ids) == {"bu-a", "team-a1", "team-ext"}
    assert "bu-c" not in scope.allowed_org_unit_ids
    assert scope.allowed_workspace_ids is not None
    assert {"ws-a1", "ws-ext"}.issubset(set(scope.allowed_workspace_ids))
    assert "ws-c" not in scope.allowed_workspace_ids
