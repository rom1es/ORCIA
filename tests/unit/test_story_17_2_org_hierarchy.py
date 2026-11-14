"""Story 17.2 — Unit tests for multi-level `OrgUnit` hierarchy & `/api/v1/org-units` router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions.errors import (
    OrgUnitDuplicateSlugError,
    OrgUnitHierarchyCycleError,
    OrgUnitInvalidParentKindError,
    OrgUnitNotEmptyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.models import OrgUnitNode, WorkspaceEntity
from orcia_core.permissions.org_hierarchy import (
    OrgUnitSummary,
    assert_org_unit_deletable,
    assert_unique_org_unit_slug,
    build_org_unit_summary,
    generate_new_org_unit_id,
    list_evaluator_org_unit_summaries,
    normalize_exposed_parent_id,
    normalize_member_user_ids,
    normalize_org_unit_slug,
    sort_org_unit_dicts_topologically,
    sort_org_unit_summaries_dfs,
    validate_org_unit_hierarchy,
)


def _build_in_memory_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    app.state.auth_service.evaluator.replace_org_units(())
    return TestClient(app)


def test_normalize_slug_and_members_and_uuid7() -> None:
    assert normalize_org_unit_slug(None, "Direction Produit & IA") == "direction-produit-ia"
    assert normalize_org_unit_slug("  Pôle_Data  ", "Ignored") == "p-le-data"
    with pytest.raises(ValidationDomainError):
        normalize_org_unit_slug("   ", "---")

    assert normalize_member_user_ids(None) == ()
    assert normalize_member_user_ids(
        [" alice@orcia.fr ", "", "bob@orcia.fr", "alice@orcia.fr"]
    ) == (
        "alice@orcia.fr",
        "bob@orcia.fr",
    )
    generated = generate_new_org_unit_id()
    assert len(generated) == 36 and generated[14] == "7"


def test_validate_org_unit_hierarchy_multi_level_and_errors() -> None:
    ent = OrgUnitNode(id="ent-1", slug="orcia-root", name="Root", unit_type="ENTERPRISE")
    bu_root = OrgUnitNode(
        id="bu-1", slug="dir-prod", name="Direction Produit", unit_type="BU", parent_id="ent-1"
    )
    sub_bu = OrgUnitNode(
        id="bu-2", slug="pole-ia", name="Pôle IA", unit_type="BU", parent_id="bu-1"
    )
    team_1 = OrgUnitNode(
        id="team-1", slug="eq-core", name="Équipe Core", unit_type="TEAM", parent_id="bu-2"
    )
    nodes = {u.id: u for u in (ent, bu_root, sub_bu, team_1)}

    assert normalize_exposed_parent_id("ent-1", nodes) is None
    assert normalize_exposed_parent_id("scope-global", nodes) is None
    assert normalize_exposed_parent_id("bu-1", nodes) == "bu-1"

    # Root attachment
    assert (
        validate_org_unit_hierarchy(unit_id=None, kind="BU", parent_id=None, units_by_id=nodes)
        is None
    )
    assert (
        validate_org_unit_hierarchy(
            unit_id=None, kind="BU", parent_id="scope-global", units_by_id=nodes
        )
        is None
    )
    # Sub-BU under BU (by ID or slug)
    assert (
        validate_org_unit_hierarchy(unit_id=None, kind="BU", parent_id="bu-1", units_by_id=nodes)
        == "bu-1"
    )
    assert (
        validate_org_unit_hierarchy(
            unit_id=None, kind="TEAM", parent_id="pole-ia", units_by_id=nodes
        )
        == "bu-2"
    )

    # Missing or ENTERPRISE parent -> 404
    with pytest.raises(ResourceNotFoundError):
        validate_org_unit_hierarchy(
            unit_id=None, kind="BU", parent_id="unknown-id", units_by_id=nodes
        )
    with pytest.raises(ResourceNotFoundError):
        validate_org_unit_hierarchy(unit_id=None, kind="BU", parent_id="ent-1", units_by_id=nodes)

    # BU under TEAM -> 422 OrgUnitInvalidParentKindError
    with pytest.raises(OrgUnitInvalidParentKindError):
        validate_org_unit_hierarchy(unit_id=None, kind="BU", parent_id="team-1", units_by_id=nodes)

    # Self-cycle and indirect ancestor cycle -> 422 OrgUnitHierarchyCycleError
    with pytest.raises(OrgUnitHierarchyCycleError):
        validate_org_unit_hierarchy(unit_id="bu-1", kind="BU", parent_id="bu-1", units_by_id=nodes)
    with pytest.raises(OrgUnitHierarchyCycleError):
        validate_org_unit_hierarchy(unit_id="bu-1", kind="BU", parent_id="bu-2", units_by_id=nodes)


def test_duplicate_slug_and_deletable_guards_and_dfs_sorting() -> None:
    ent = OrgUnitNode(id="ent-1", slug="orcia-root", name="Root", unit_type="ENTERPRISE")
    bu = OrgUnitNode(
        id="bu-1",
        slug="dir-tech",
        name="Direction Tech",
        unit_type="BU",
        parent_id="ent-1",
        billing_enabled=False,
        lead_user_id="cto@orcia.fr",
        member_user_ids=("dev1@orcia.fr",),
    )
    sub_bu = OrgUnitNode(
        id="bu-2", slug="pole-cloud", name="Pôle Cloud", unit_type="BU", parent_id="bu-1"
    )
    team = OrgUnitNode(
        id="team-1", slug="eq-sre", name="Équipe SRE", unit_type="TEAM", parent_id="bu-2"
    )
    nodes = {u.id: u for u in (ent, bu, sub_bu, team)}

    assert_unique_org_unit_slug("dir-tech", nodes, exclude_unit_id="bu-1")
    with pytest.raises(OrgUnitDuplicateSlugError):
        assert_unique_org_unit_slug("dir-tech", nodes)

    assert_org_unit_deletable(
        target_name="Équipe SRE", child_units_count=0, attached_workspaces_count=0
    )
    with pytest.raises(OrgUnitNotEmptyError) as exc_children:
        assert_org_unit_deletable(
            target_name="Direction Tech", child_units_count=2, attached_workspaces_count=0
        )
    assert "2 sous-unités enfants" in str(exc_children.value)

    with pytest.raises(OrgUnitNotEmptyError) as exc_both:
        assert_org_unit_deletable(
            target_name="Équipe SRE", child_units_count=1, attached_workspaces_count=2
        )
    assert "1 sous-unité enfant" in str(exc_both.value)
    assert "2 espaces de travail rattachés" in str(exc_both.value)

    summary = build_org_unit_summary(bu, nodes, attached_workspaces_count=3)
    assert summary == OrgUnitSummary(
        id="bu-1",
        slug="dir-tech",
        name="Direction Tech",
        kind="BU",
        parent_id=None,
        billing_enabled=False,
        lead_user_id="cto@orcia.fr",
        member_user_ids=("dev1@orcia.fr",),
        attached_workspaces_count=3,
    )

    dfs = list_evaluator_org_unit_summaries([team, ent, sub_bu, bu], ["team-1", "team-1"])
    assert [item.id for item in dfs] == ["bu-1", "bu-2", "team-1"]
    assert dfs[2].attached_workspaces_count == 2

    # Disconnected node fallback in sort_org_unit_summaries_dfs
    orphan = OrgUnitSummary(
        id="orphan-1", slug="orphan", name="Orphan", kind="TEAM", parent_id="missing"
    )
    assert [u.id for u in sort_org_unit_summaries_dfs([orphan])] == ["orphan-1"]

    # Topological dict sort: child listed before parent -> parent emitted first
    sorted_dicts = sort_org_unit_dicts_topologically(
        [
            {"id": "t-1", "slug": "eq-1", "level": "TEAM", "parentId": "sub-1"},
            {"id": "sub-1", "slug": "pole-1", "level": "BU", "parentId": "root-1"},
            {"id": "root-1", "slug": "dir-1", "level": "BU", "parentId": "scope-global"},
        ]
    )
    assert [d["id"] for d in sorted_dicts] == ["root-1", "sub-1", "t-1"]


def test_org_units_router_crud_hierarchy_rbac_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_in_memory_client(monkeypatch)
    admin_headers = {"X-Orcia-Persona": "karim"}

    # Initial Day-0 state is empty
    init_resp = client.get("/api/v1/org-units", headers=admin_headers)
    assert init_resp.status_code == 200
    assert init_resp.json()["org_units"] == []

    # Empty name -> 422
    empty_create = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={"name": "   ", "kind": "BU"},
    )
    assert empty_create.status_code == 422

    # Create root BU -> Sub-BU -> TEAM
    r_bu = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={
            "name": "Direction Produit",
            "kind": "BU",
            "billing_enabled": True,
            "lead_user_id": "vp@orcia.fr",
        },
    )
    assert r_bu.status_code == 200, r_bu.text
    bu_id = r_bu.json()["id"]
    assert r_bu.json()["slug"] == "direction-produit"
    assert r_bu.json()["parent_id"] is None

    r_sub = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={
            "name": "Pôle IA Générative",
            "kind": "BU",
            "parent_id": bu_id,
            "billing_enabled": False,
        },
    )
    assert r_sub.status_code == 200, r_sub.text
    sub_id = r_sub.json()["id"]
    assert r_sub.json()["parent_id"] == bu_id
    assert r_sub.json()["billing_enabled"] is False

    r_team = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={
            "name": "Équipe Core Agents",
            "kind": "TEAM",
            "parent_id": sub_id,
            "member_user_ids": ["alice@orcia.fr", "bob@orcia.fr"],
        },
    )
    assert r_team.status_code == 200, r_team.text
    team_id = r_team.json()["id"]
    assert r_team.json()["member_user_ids"] == ["alice@orcia.fr", "bob@orcia.fr"]

    # GET DFS list in evaluator mode
    listed = client.get("/api/v1/org-units", headers=admin_headers)
    assert listed.status_code == 200
    assert [u["id"] for u in listed.json()["org_units"]] == [bu_id, sub_id, team_id]

    # Duplicate slug -> 409 ERR_ORG_UNIT_DUPLICATE_SLUG
    dup = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={"name": "Autre Nom", "slug": "direction-produit", "kind": "BU"},
    )
    assert dup.status_code == 409
    assert dup.json()["error_code"] == "ERR_ORG_UNIT_DUPLICATE_SLUG"

    # Invalid parent kind (BU under TEAM) -> 422 ERR_ORG_UNIT_INVALID_PARENT_KIND
    bad_parent = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={"name": "Sous-BU Invalide", "kind": "BU", "parent_id": team_id},
    )
    assert bad_parent.status_code == 422
    assert bad_parent.json()["error_code"] == "ERR_ORG_UNIT_INVALID_PARENT_KIND"

    # PATCH cycle (reparent root BU under its child Sub-BU) -> 422 ERR_ORG_UNIT_HIERARCHY_CYCLE
    cycle = client.patch(
        f"/api/v1/org-units/{bu_id}",
        headers=admin_headers,
        json={"parent_id": sub_id},
    )
    assert cycle.status_code == 422
    assert cycle.json()["error_code"] == "ERR_ORG_UNIT_HIERARCHY_CYCLE"

    # PATCH unknown ID & empty name -> 404 / 422
    assert (
        client.patch(
            "/api/v1/org-units/unknown-unit-id",
            headers=admin_headers,
            json={"name": "Inexistant"},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/org-units/{team_id}",
            headers=admin_headers,
            json={"name": "   "},
        ).status_code
        == 422
    )

    # PATCH valid rename, reparenting, billing toggle, lead & members update
    patched = client.patch(
        f"/api/v1/org-units/{team_id}",
        headers=admin_headers,
        json={
            "name": "Équipe Core Agents & RAG",
            "parent_id": sub_id,
            "billing_enabled": False,
            "lead_user_id": "lead.rag@orcia.fr",
            "member_user_ids": ["alice@orcia.fr"],
        },
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Équipe Core Agents & RAG"
    assert patched.json()["billing_enabled"] is False
    assert patched.json()["lead_user_id"] == "lead.rag@orcia.fr"
    assert patched.json()["member_user_ids"] == ["alice@orcia.fr"]

    # RBAC & Observer mode guards -> 403
    obs_hdr = client.post(
        "/api/v1/org-units",
        headers={"X-Orcia-Persona": "karim", "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
        json={"name": "Interdit", "kind": "BU"},
    )
    assert obs_hdr.status_code == 403
    assert obs_hdr.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    obs_hat = client.delete(
        f"/api/v1/org-units/{team_id}",
        headers={"X-Orcia-Persona": "karim", "X-Orcia-Active-Hat": "OBSERVER"},
    )
    assert obs_hat.status_code == 403
    assert obs_hat.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    contrib_hat = client.patch(
        f"/api/v1/org-units/{team_id}",
        headers={"X-Orcia-Persona": "karim", "X-Orcia-Active-Hat": "CONTRIBUTOR"},
        json={"name": "Refusé Hat"},
    )
    assert contrib_hat.status_code == 403
    assert contrib_hat.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    member_persona = client.patch(
        f"/api/v1/org-units/{team_id}",
        headers={"X-Orcia-Persona": "nadia"},
        json={"name": "Refusé"},
    )
    assert member_persona.status_code == 403
    assert member_persona.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    # Non-empty deletion guard: Sub-BU has child TEAM -> 409 ERR_ORG_UNIT_NOT_EMPTY
    del_non_empty = client.delete(f"/api/v1/org-units/{sub_id}", headers=admin_headers)
    assert del_non_empty.status_code == 409
    assert del_non_empty.json()["error_code"] == "ERR_ORG_UNIT_NOT_EMPTY"

    # Attach workspace to TEAM -> deleting TEAM also returns 409 ERR_ORG_UNIT_NOT_EMPTY
    client.app.state.auth_service.evaluator.upsert_workspace(  # type: ignore[union-attr]
        WorkspaceEntity(
            id="ws-attached-1",
            slug="ws-attached",
            name="Espace Rattaché",
            owner_org_unit_id=team_id,
        )
    )
    del_ws_team = client.delete(f"/api/v1/org-units/{team_id}", headers=admin_headers)
    assert del_ws_team.status_code == 409
    assert del_ws_team.json()["error_code"] == "ERR_ORG_UNIT_NOT_EMPTY"

    # Clear workspace -> delete TEAM -> delete Sub-BU -> delete root BU
    client.app.state.auth_service.evaluator._workspaces_by_id.clear()  # type: ignore[union-attr]
    assert client.delete(f"/api/v1/org-units/{team_id}", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/v1/org-units/{sub_id}", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/v1/org-units/{bu_id}", headers=admin_headers).status_code == 200
    assert client.delete(f"/api/v1/org-units/{bu_id}", headers=admin_headers).status_code == 404
