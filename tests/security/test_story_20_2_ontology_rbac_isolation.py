"""Story 20.2 — Security & RBAC isolation tests for Ontology L1–L4 & step-by-step promotions."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import OrgUnitNode, UserIdentity, WorkspaceEntity


def _build_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    svc = app.state.auth_service

    admin = UserIdentity(
        id="u-admin",
        email="admin@orcia.ia",
        display_name="Admin",
        auth_mode="LOCAL",
        human_profile_archetype="SECOPS",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="bu-a",
        roles=("PLATFORM_ADMIN",),
    )
    onto_a = UserIdentity(
        id="u-onto-a",
        email="onto.a@orcia.ia",
        display_name="Onto Lead A",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="ONTOLOGY_LEAD",
        primary_org_unit_id="bu-a",
        roles=("ONTOLOGY_LEAD",),
    )
    team_a = UserIdentity(
        id="u-team-a",
        email="team.a@orcia.ia",
        display_name="Team Lead A",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="team-a",
        roles=("TEAM_LEAD",),
    )
    contrib_a = UserIdentity(
        id="u-contrib-a",
        email="contrib.a@orcia.ia",
        display_name="Contrib A",
        auth_mode="LOCAL",
        human_profile_archetype="DEVELOPER",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="team-a",
        roles=("CONTRIBUTOR",),
    )
    observer = UserIdentity(
        id="u-obs",
        email="obs@orcia.ia",
        display_name="Observer",
        auth_mode="LOCAL",
        human_profile_archetype="EXECUTIVE",
        platform_role="OBSERVER",
        primary_org_unit_id="team-a",
        roles=("OBSERVER",),
    )
    for key, u in (
        ("admin", admin),
        ("onto_a", onto_a),
        ("team_a", team_a),
        ("contrib_a", contrib_a),
        ("obs", observer),
    ):
        svc.register_user(u)
        svc._persona_map[key] = u.id  # noqa: SLF001

    svc.evaluator.replace_org_units(
        (
            OrgUnitNode(
                id="bu-a",
                slug="bu-a",
                name="BU A",
                unit_type="BU",
                ontology_lead_user_ids=("onto.a@orcia.ia",),
            ),
            OrgUnitNode(
                id="bu-b",
                slug="bu-b",
                name="BU B",
                unit_type="BU",
                lead_user_ids=("other@orcia.ia",),
            ),
            OrgUnitNode(
                id="team-a",
                slug="team-a",
                name="Team A",
                unit_type="TEAM",
                parent_id="bu-a",
                lead_user_ids=("team.a@orcia.ia",),
                member_user_ids=("contrib.a@orcia.ia",),
            ),
        )
    )
    svc.evaluator.upsert_workspace(
        WorkspaceEntity(id="ws-a", slug="ws-a", name="WS A", owner_org_unit_id="team-a")
    )
    svc.evaluator.upsert_workspace(
        WorkspaceEntity(id="ws-b", slug="ws-b", name="WS B", owner_org_unit_id="bu-b")
    )
    return TestClient(app)


def test_cross_bu_isolation_observer_403_and_anti_level_jump_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_client(monkeypatch)

    # 1. OBSERVER rejected 403 ERR_OBSERVER_MODE_READ_ONLY on write
    r_obs = client.post(
        "/api/v1/ontology-rag/ontology/concepts",
        headers={"X-Orcia-Persona": "obs"},
        json={
            "concept_key": "c-obs",
            "canonical_term": "Obs",
            "level": "4_WORKSPACE",
            "scope_id": "ws-a",
            "definition_text": "No",
        },
    )
    assert r_obs.status_code == 403
    assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # 2. ONTOLOGY_LEAD of BU A cannot write L1 or BU B
    r_l1 = client.post(
        "/api/v1/ontology-rag/ontology/concepts",
        headers={"X-Orcia-Persona": "onto_a"},
        json={
            "concept_key": "c-l1-bad",
            "canonical_term": "L1 Bad",
            "level": "1_ENTERPRISE",
            "scope_id": "scope-global",
            "definition_text": "Forbidden",
        },
    )
    assert r_l1.status_code == 403

    r_bu_b = client.post(
        "/api/v1/ontology-rag/ontology/concepts",
        headers={"X-Orcia-Persona": "onto_a"},
        json={
            "concept_key": "c-bub-bad",
            "canonical_term": "BU B Bad",
            "level": "2_DOMAIN",
            "scope_id": "bu-b",
            "definition_text": "Forbidden",
        },
    )
    assert r_bu_b.status_code == 403

    # 3. CONTRIBUTOR creates L4 term in WS A -> cannot jump directly to L1 (422)
    r_l4 = client.post(
        "/api/v1/ontology-rag/ontology/concepts",
        headers={"X-Orcia-Persona": "contrib_a"},
        json={
            "concept_key": "c-ws-a",
            "canonical_term": "Marge Brute",
            "level": "4_WORKSPACE",
            "scope_id": "ws-a",
            "definition_text": "Marge brute locale",
        },
    )
    assert r_l4.status_code == 200

    r_jump = client.post(
        "/api/v1/ontology-rag/ontology/promotions",
        headers={"X-Orcia-Persona": "contrib_a"},
        json={"concept_key": "c-ws-a", "target_level": "1_ENTERPRISE"},
    )
    assert r_jump.status_code == 422
    assert r_jump.json()["error_code"] == "ERR_ONTOLOGY_PROMOTION_STEP_INVALID"

    # 4. Propose valid L4 -> L3; CONTRIBUTOR cannot approve L3; TEAM_LEAD A approves L3
    r_prop_l3 = client.post(
        "/api/v1/ontology-rag/ontology/promotions",
        headers={"X-Orcia-Persona": "contrib_a"},
        json={"concept_key": "c-ws-a"},
    )
    assert r_prop_l3.status_code == 200
    prop_l3_id = r_prop_l3.json()["id"]

    r_contrib_approve = client.post(
        f"/api/v1/ontology-rag/ontology/promotions/{prop_l3_id}/decide",
        headers={"X-Orcia-Persona": "contrib_a"},
        json={"decision": "APPROVE"},
    )
    assert r_contrib_approve.status_code == 403

    r_team_approve = client.post(
        f"/api/v1/ontology-rag/ontology/promotions/{prop_l3_id}/decide",
        headers={"X-Orcia-Persona": "team_a"},
        json={"decision": "APPROVE"},
    )
    assert r_team_approve.status_code == 200

    # 5. BU B proposal cannot be approved by ONTOLOGY_LEAD of BU A (403)
    r_b_term = client.post(
        "/api/v1/ontology-rag/ontology/concepts",
        headers={"X-Orcia-Persona": "admin"},
        json={
            "concept_key": "c-ws-b",
            "canonical_term": "Terme B",
            "level": "4_WORKSPACE",
            "scope_id": "ws-b",
            "definition_text": "Def B",
        },
    )
    assert r_b_term.status_code == 200
    r_prop_b = client.post(
        "/api/v1/ontology-rag/ontology/promotions",
        headers={"X-Orcia-Persona": "admin"},
        json={"concept_key": "c-ws-b"},
    )
    assert r_prop_b.status_code == 200
    r_cross_bu = client.post(
        f"/api/v1/ontology-rag/ontology/promotions/{r_prop_b.json()['id']}/decide",
        headers={"X-Orcia-Persona": "onto_a"},
        json={"decision": "APPROVE"},
    )
    assert r_cross_bu.status_code == 403

    # 6. Cross-scope concept_key overwrite/downgrade returns 409 ERR_ONTOLOGY_CONFLICT
    r_l1_seed = client.post(
        "/api/v1/ontology-rag/ontology/concepts",
        headers={"X-Orcia-Persona": "admin"},
        json={
            "concept_key": "shared-l1-key",
            "canonical_term": "Norme Groupe",
            "level": "1_ENTERPRISE",
            "scope_id": "scope-global",
            "definition_text": "Norme globale immuable",
        },
    )
    assert r_l1_seed.status_code == 200
    r_forged_key = client.post(
        "/api/v1/ontology-rag/ontology/concepts",
        headers={"X-Orcia-Persona": "contrib_a"},
        json={
            "concept_key": "shared-l1-key",
            "canonical_term": "Norme Groupe Piratée",
            "level": "4_WORKSPACE",
            "scope_id": "ws-a",
            "definition_text": "Tentative d'écrasement L1 -> L4",
        },
    )
    assert r_forged_key.status_code == 409
    assert r_forged_key.json()["error_code"] == "ERR_ONTOLOGY_CONFLICT"

    # 7. Arbitrary target_scope_id injection at promotion creation is rejected (403)
    r_forged_target = client.post(
        "/api/v1/ontology-rag/ontology/promotions",
        headers={"X-Orcia-Persona": "contrib_a"},
        json={"concept_key": "c-ws-a", "target_scope_id": "bu-b"},
    )
    assert r_forged_target.status_code == 403
    assert r_forged_target.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    # 8. GET /api/v1/ontology-rag/state filters concepts by caller read rights
    r_state_a = client.get("/api/v1/ontology-rag/state", headers={"X-Orcia-Persona": "contrib_a"})
    assert r_state_a.status_code == 200
    keys_a = {c["concept_key"] for c in r_state_a.json()["concepts"]}
    assert "c-ws-a" in keys_a
    assert "shared-l1-key" in keys_a
    assert "c-ws-b" not in keys_a

    # 9. Legacy POST /ontology/promote blocks cross-BU promotion (403)
    r_legacy_cross = client.post(
        "/api/v1/ontology-rag/ontology/promote",
        headers={"X-Orcia-Persona": "onto_a"},
        json={"proposal_key": r_prop_b.json()["proposal_key"]},
    )
    # onto_a cannot promote a proposal targeting bu-b (or 404 if not seeded into legacy gov)
    assert r_legacy_cross.status_code in (403, 404)


def test_legacy_promote_and_state_fail_closed_unauthenticated_and_cross_bu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    svc = app.state.auth_service
    svc.allow_persona_impersonation = False
    client_no_auth = TestClient(app)
    assert client_no_auth.get("/api/v1/ontology-rag/state").status_code == 401

    svc.allow_persona_impersonation = True
    onto_a = UserIdentity(
        id="u-onto-a",
        email="onto.a@orcia.ia",
        display_name="Onto A",
        auth_mode="LOCAL",
        human_profile_archetype="ARCHITECT",
        platform_role="ONTOLOGY_LEAD",
        primary_org_unit_id="bu-a",
        roles=("ONTOLOGY_LEAD",),
    )
    bu_b_lead = UserIdentity(
        id="u-bu-b",
        email="bu.b@orcia.ia",
        display_name="BU B Lead",
        auth_mode="LOCAL",
        human_profile_archetype="EXECUTIVE",
        platform_role="BU_LEAD",
        primary_org_unit_id="bu-b",
        roles=("BU_LEAD",),
    )
    svc.register_user(onto_a)
    svc.register_user(bu_b_lead)
    svc._persona_map["onto_a"] = onto_a.id  # noqa: SLF001
    svc._persona_map["bu_b"] = bu_b_lead.id  # noqa: SLF001
    svc.evaluator.replace_org_units(
        (
            OrgUnitNode(
                id="bu-a",
                slug="bu-a",
                name="BU A",
                unit_type="BU",
                ontology_lead_user_ids=("onto.a@orcia.ia",),
            ),
            OrgUnitNode(
                id="bu-b",
                slug="bu-b",
                name="BU B",
                unit_type="BU",
                lead_user_ids=("bu.b@orcia.ia",),
            ),
        )
    )
    from types import SimpleNamespace

    from orcia_api.dependencies import get_ontology_and_rag_services

    gov, _, _ = get_ontology_and_rag_services(SimpleNamespace(app=app))  # type: ignore[arg-type]
    _, prop_b = gov.extract_l4_concept(
        bu_b_lead,
        concept_key="c-l4-bu-b-legacy",
        canonical_term="Terme Legacy BU B",
        run_id="run-b",
        snapshot_id="snap-b",
        definition_text="Def B",
        target_promotion_level="2_DOMAIN",
        target_scope_id="bu-b",
    )
    r_forbid = client_no_auth.post(
        "/api/v1/ontology-rag/ontology/promote",
        headers={"X-Orcia-Persona": "onto_a"},
        json={"proposal_key": prop_b.proposal_key},
    )
    assert r_forbid.status_code == 403
