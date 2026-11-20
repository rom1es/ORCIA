"""Story 25.2 — Unit tests for read-only `/api/v1/org-units` access across all roles."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import OrgUnitNode, UserIdentity


def _build_read_access_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    svc = app.state.auth_service

    users = {
        "contrib": UserIdentity(
            id="user-contrib",
            email="contrib@orcia.ia",
            display_name="Contributeur Test",
            auth_mode="LOCAL",
            human_profile_archetype="CONTRIBUTOR",
            platform_role="CONTRIBUTOR",
            primary_org_unit_id="team-ventes",
            roles=("CONTRIBUTOR",),
        ),
        "observer": UserIdentity(
            id="user-observer",
            email="observer@orcia.ia",
            display_name="Observateur Test",
            auth_mode="LOCAL",
            human_profile_archetype="OBSERVER",
            platform_role="OBSERVER",
            primary_org_unit_id="team-ventes",
            roles=("OBSERVER",),
        ),
        "onto": UserIdentity(
            id="user-onto",
            email="onto@orcia.ia",
            display_name="Ontology Lead",
            auth_mode="LOCAL",
            human_profile_archetype="ONTOLOGY_LEAD",
            platform_role="ONTOLOGY_LEAD",
            primary_org_unit_id="bu-commerce",
            roles=("ONTOLOGY_LEAD",),
        ),
        "secops": UserIdentity(
            id="user-secops-ro",
            email="secops.ro@orcia.ia",
            display_name="SecOps Reader",
            auth_mode="LOCAL",
            human_profile_archetype="SECOPS",
            platform_role="SECOPS",
            primary_org_unit_id="bu-commerce",
            roles=("SECOPS",),
        ),
    }
    for persona_key, identity in users.items():
        svc.register_user(identity)
        svc._persona_map[persona_key] = identity.id  # noqa: SLF001

    svc.evaluator.replace_org_units(
        (
            OrgUnitNode(
                id="bu-commerce",
                slug="bu-commerce",
                name="Direction Commerciale",
                unit_type="BU",
                lead_user_ids=("martin.pecheur@orcia.ia",),
                ontology_lead_user_ids=("onto@orcia.ia",),
            ),
            OrgUnitNode(
                id="team-ventes",
                slug="team-ventes",
                name="Équipe Ventes",
                unit_type="TEAM",
                parent_id="bu-commerce",
                lead_user_ids=("pascal.lacdap@orcia.ia",),
                member_user_ids=("contrib@orcia.ia", "observer@orcia.ia"),
            ),
            OrgUnitNode(
                id="bu-finance",
                slug="bu-finance",
                name="Direction Finance",
                unit_type="BU",
                lead_user_ids=("claire.bu@orcia.io",),
            ),
        )
    )
    return TestClient(app)


@pytest.mark.parametrize("persona", ["contrib", "observer", "onto", "secops"])
def test_non_delegated_roles_read_full_org_tree_with_all_can_flags_false_and_mutations_403(
    monkeypatch: pytest.MonkeyPatch,
    persona: str,
) -> None:
    client = _build_read_access_client(monkeypatch)
    headers = {"X-Orcia-Persona": persona}

    res = client.get("/api/v1/org-units", headers=headers)
    assert res.status_code == 200, res.text
    units = {u["id"]: u for u in res.json()["org_units"]}
    assert {"bu-commerce", "team-ventes", "bu-finance"}.issubset(units.keys())

    for unit in units.values():
        assert unit["can_edit"] is False
        assert unit["can_create_child"] is False
        assert unit["can_delete"] is False
        assert unit["can_manage_members"] is False
        assert unit["can_manage_ontology_leads"] is False
        assert unit["can_invite_users"] is False

    # Every mutation remains strictly blocked in HTTP 403
    assert (
        client.post(
            "/api/v1/org-units",
            headers=headers,
            json={"name": "Unauthorized BU", "kind": "BU"},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            "/api/v1/org-units/bu-commerce",
            headers=headers,
            json={"name": "Mutated BU"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            "/api/v1/org-units/team-ventes",
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/org-units/invite-user",
            headers=headers,
            json={
                "target_org_unit_id": "team-ventes",
                "email": "unauthorized.invite@orcia.ia",
                "display_name": "Unauthorized",
                "assignment_role": "TEAM_MEMBER",
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/org-units/invite-user",
            headers=headers,
            json={
                "target_org_unit_id": "bu-commerce",
                "email": "unauthorized.onto@orcia.ia",
                "display_name": "Unauthorized Onto",
                "assignment_role": "ONTOLOGY_LEAD",
            },
        ).status_code
        == 403
    )
