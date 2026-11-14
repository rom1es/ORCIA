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
    OrgUnitUnknownUserError,
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
from orcia_core.permissions.org_user_validation import (
    KnownOrgUser,
    resolve_and_validate_org_unit_users,
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


def test_resolve_and_validate_org_unit_users() -> None:
    known = [
        KnownOrgUser(
            principal_id="claire.bu@orcia.io",
            display_name="Claire Delorme",
            email="claire.bu@orcia.io",
        ),
        KnownOrgUser(
            principal_id="user-karim-001",
            display_name="Karim Benali",
            email="karim.supervisor@orcia.io",
        ),
        KnownOrgUser(
            principal_id="romain.esnault@gmail.com",
            display_name="Romain Esnault",
            email="romain.esnault@gmail.com",
        ),
    ]

    # Valid lead & members matching principal_id or email case-insensitively
    lead, members = resolve_and_validate_org_unit_users(
        lead_user_id="  CLAIRE.BU@ORCIA.IO ",
        member_user_ids=[
            "karim.supervisor@orcia.io",
            "USER-KARIM-001",
            "romain.esnault@gmail.com",
        ],
        known_users=known,
    )
    assert lead == "claire.bu@orcia.io"
    # Canonical principal_id resolved, deduplicated, order preserved:
    assert members == ("user-karim-001", "romain.esnault@gmail.com")

    # None / empty lead
    lead_none, members_none = resolve_and_validate_org_unit_users(
        lead_user_id=None,
        member_user_ids=[],
        known_users=known,
    )
    assert lead_none is None
    assert members_none == ()

    # Plain first name "romain" does NOT match display_name alone -> raises OrgUnitUnknownUserError
    with pytest.raises(OrgUnitUnknownUserError) as exc_lead:
        resolve_and_validate_org_unit_users(
            lead_user_id="romain",
            member_user_ids=[],
            known_users=known,
        )
    assert exc_lead.value.error_code == "ERR_ORG_UNIT_UNKNOWN_USER"
    assert exc_lead.value.http_status == 422

    # Unknown member -> raises OrgUnitUnknownUserError
    with pytest.raises(OrgUnitUnknownUserError) as exc_member:
        resolve_and_validate_org_unit_users(
            lead_user_id=None,
            member_user_ids=["claire.bu@orcia.io", "inconnu@orcia.fr"],
            known_users=known,
        )
    assert exc_member.value.error_code == "ERR_ORG_UNIT_UNKNOWN_USER"
    assert exc_member.value.http_status == 422


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

    # Unknown lead identifier -> 422 ERR_ORG_UNIT_UNKNOWN_USER
    unknown_lead = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={"name": "BU Inconnue", "kind": "BU", "lead_user_id": "inconnu@orcia.fr"},
    )
    assert unknown_lead.status_code == 422
    assert unknown_lead.json()["error_code"] == "ERR_ORG_UNIT_UNKNOWN_USER"

    # Plain first name alone not matching principal_id/email -> 422 ERR_ORG_UNIT_UNKNOWN_USER
    plain_name_lead = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={"name": "BU Inconnue", "kind": "BU", "lead_user_id": "romain"},
    )
    assert plain_name_lead.status_code == 422
    assert plain_name_lead.json()["error_code"] == "ERR_ORG_UNIT_UNKNOWN_USER"

    # Create root BU -> Sub-BU -> TEAM
    r_bu = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={
            "name": "Direction Produit",
            "kind": "BU",
            "billing_enabled": True,
            "lead_user_id": "claire.bu@orcia.io",
        },
    )
    assert r_bu.status_code == 200, r_bu.text
    bu_id = r_bu.json()["id"]
    assert r_bu.json()["slug"] == "direction-produit"
    assert r_bu.json()["parent_id"] is None
    assert r_bu.json()["lead_user_id"] == "claire.bu@orcia.io"

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

    # Unknown member in TEAM -> 422 ERR_ORG_UNIT_UNKNOWN_USER
    unknown_member = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={
            "name": "Équipe Invalide",
            "kind": "TEAM",
            "parent_id": sub_id,
            "member_user_ids": ["nadia.dev@orcia.io", "fantome@orcia.fr"],
        },
    )
    assert unknown_member.status_code == 422
    assert unknown_member.json()["error_code"] == "ERR_ORG_UNIT_UNKNOWN_USER"

    r_team = client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={
            "name": "Équipe Core Agents",
            "kind": "TEAM",
            "parent_id": sub_id,
            "member_user_ids": ["marc.lead@orcia.io", "nadia.dev@orcia.io"],
        },
    )
    assert r_team.status_code == 200, r_team.text
    team_id = r_team.json()["id"]
    assert r_team.json()["member_user_ids"] == ["marc.lead@orcia.io", "nadia.dev@orcia.io"]

    # GET DFS list in evaluator mode & verify known_users
    listed = client.get("/api/v1/org-units", headers=admin_headers)
    assert listed.status_code == 200
    assert [u["id"] for u in listed.json()["org_units"]] == [bu_id, sub_id, team_id]
    known_pids = [u["principal_id"] for u in listed.json()["known_users"]]
    assert "claire.bu@orcia.io" in known_pids
    assert "marc.lead@orcia.io" in known_pids

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

    # PATCH unknown lead / member -> 422 ERR_ORG_UNIT_UNKNOWN_USER
    assert (
        client.patch(
            f"/api/v1/org-units/{team_id}",
            headers=admin_headers,
            json={"lead_user_id": "inconnu@orcia.fr"},
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
            "lead_user_id": "marc.lead@orcia.io",
            "member_user_ids": ["nadia.dev@orcia.io"],
        },
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Équipe Core Agents & RAG"
    assert patched.json()["billing_enabled"] is False
    assert patched.json()["lead_user_id"] == "marc.lead@orcia.io"
    assert patched.json()["member_user_ids"] == ["nadia.dev@orcia.io"]

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


def test_list_org_units_search_query_kind_and_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    client = TestClient(app)
    admin_headers = {"X-Orcia-Persona": "claire", "X-Orcia-Active-Hat": "PLATFORM_ADMIN"}

    # Create 12 BU units + 2 TEAM units
    for i in range(12):
        name = "DS3C Pôle Ingénierie" if i == 0 else f"BU Test {i + 1}"
        client.post(
            "/api/v1/org-units",
            headers=admin_headers,
            json={"name": name, "kind": "BU"},
        )
    client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={"name": "Équipe Alpha", "kind": "TEAM"},
    )
    client.post(
        "/api/v1/org-units",
        headers=admin_headers,
        json={"name": "Équipe Beta", "kind": "TEAM"},
    )

    # 1. Unfiltered returns all non-enterprise units in DFS order
    resp_all = client.get("/api/v1/org-units", headers=admin_headers)
    assert resp_all.status_code == 200
    all_units = resp_all.json()["org_units"]
    assert len(all_units) >= 14

    # 2. Filter by kind="BU" and limit=10
    resp_bu_10 = client.get("/api/v1/org-units?kind=BU&limit=10", headers=admin_headers)
    assert resp_bu_10.status_code == 200
    bu_10_units = resp_bu_10.json()["org_units"]
    assert len(bu_10_units) == 10
    assert all(u["kind"] == "BU" for u in bu_10_units)

    # 3. Filter by search query q="ds3" (case & accent insensitive)
    resp_q = client.get("/api/v1/org-units?q=ds3&kind=BU&limit=10", headers=admin_headers)
    assert resp_q.status_code == 200
    q_units = resp_q.json()["org_units"]
    assert len(q_units) == 1
    assert "DS3C" in q_units[0]["name"]


def test_search_known_org_users_route_with_nfd_null_byte_and_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    client = TestClient(app)
    admin_headers = {"X-Orcia-Persona": "claire", "X-Orcia-Active-Hat": "PLATFORM_ADMIN"}

    # 1. Unfiltered search with limit=2 -> has_more is True if > 2 users exist
    resp = client.get("/api/v1/org-units/known-users?limit=2", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert len(body["items"]) <= 2
    assert "has_more" in body

    # 2. Search with NFD accent insensitivity (e.g. "claire" or accent stripped)
    resp_search = client.get(
        "/api/v1/org-units/known-users?q=claire&limit=10",
        headers=admin_headers,
    )
    assert resp_search.status_code == 200
    search_body = resp_search.json()
    assert any(
        "claire" in u["principal_id"].lower() or "claire" in u["display_name"].lower()
        for u in search_body["items"]
    )

    # 3. Null byte \x00 cleaning
    resp_null_byte = client.get(
        "/api/v1/org-units/known-users?q=claire%00&limit=10",
        headers=admin_headers,
    )
    assert resp_null_byte.status_code == 200
    null_body = resp_null_byte.json()
    assert len(null_body["items"]) == len(search_body["items"])
