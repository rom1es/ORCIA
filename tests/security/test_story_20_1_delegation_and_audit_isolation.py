"""Story 20.1 — Security & anti-escalation tests for delegation, IAM lockout, and audit scope."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import OrgUnitNode, UserIdentity


def _build_security_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
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
    secops_only = UserIdentity(
        id="user-rssi",
        email="rssi.only@orcia.ia",
        display_name="RSSI SecOps",
        auth_mode="LOCAL",
        human_profile_archetype="SECOPS",
        platform_role="SECOPS",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
        roles=("SECOPS",),
    )
    for k, u in (("martin", martin), ("pascal", pascal), ("rssi", secops_only)):
        svc.register_user(u)
        svc._persona_map[k] = u.id  # noqa: SLF001

    svc.evaluator.replace_org_units(
        (
            OrgUnitNode(
                id="bu-commerce",
                slug="bu-commerce",
                name="Direction Commerciale",
                unit_type="BU",
                lead_user_ids=("martin.pecheur@orcia.ia",),
            ),
            OrgUnitNode(
                id="team-ventes",
                slug="team-ventes",
                name="Équipe Ventes",
                unit_type="TEAM",
                parent_id="bu-commerce",
                lead_user_ids=("pascal.lacdap@orcia.ia",),
            ),
            OrgUnitNode(
                id="bu-other",
                slug="bu-other",
                name="Direction Concurrente",
                unit_type="BU",
                lead_user_ids=("claire.bu@orcia.io",),
            ),
        )
    )
    return TestClient(app)


def test_forbid_privilege_escalation_on_org_unit_invite_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_security_client(monkeypatch)
    for forbidden_role in ("PLATFORM_ADMIN", "SECOPS"):
        res = client.post(
            "/api/v1/org-units/invite-user",
            headers={"X-Orcia-Persona": "martin"},
            json={
                "target_org_unit_id": "bu-commerce",
                "email": f"escalade-{forbidden_role.lower()}@orcia.ia",
                "display_name": "Escalade Test",
                "assignment_role": forbidden_role,
            },
        )
        assert res.status_code == 403
        assert res.json()["error_code"] == "ERR_PRIVILEGE_ESCALATION_FORBIDDEN"


def test_cross_bu_and_team_lead_invitation_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _build_security_client(monkeypatch)

    # BU_LEAD Martin cannot invite, create, patch, or delete on bu-other
    assert (
        client.post(
            "/api/v1/org-units/invite-user",
            headers={"X-Orcia-Persona": "martin"},
            json={
                "target_org_unit_id": "bu-other",
                "email": "crossbu@orcia.ia",
                "display_name": "Cross BU",
                "assignment_role": "BU_LEAD",
            },
        ).status_code
        == 403
    )
    assert (
        client.patch(
            "/api/v1/org-units/bu-other",
            headers={"X-Orcia-Persona": "martin"},
            json={"name": "Hijacked BU"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            "/api/v1/org-units/bu-other", headers={"X-Orcia-Persona": "martin"}
        ).status_code
        == 403
    )

    # TEAM_LEAD Pascal cannot invite users
    inv_team_lead = client.post(
        "/api/v1/org-units/invite-user",
        headers={"X-Orcia-Persona": "pascal"},
        json={
            "target_org_unit_id": "team-ventes",
            "email": "pascal.invite@orcia.ia",
            "display_name": "Blocked",
            "assignment_role": "TEAM_MEMBER",
        },
    )
    assert inv_team_lead.status_code == 403
    assert inv_team_lead.json()["error_code"] == "ERR_ORG_UNIT_SCOPE_FORBIDDEN"


def test_iam_accounts_mutations_locked_from_bu_team_leads_and_secops_anti_escalation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _build_security_client(monkeypatch)

    # Seed Day-0 admin via GET (PLATFORM_ADMIN & SECOPS allowed; others -> 403)
    list_res = client.get("/api/v1/settings/iam/accounts", headers={"X-Orcia-Persona": "karim"})
    assert list_res.status_code == 200
    day0_admin = list_res.json()["accounts"][0]
    rssi_list = client.get("/api/v1/settings/iam/accounts", headers={"X-Orcia-Persona": "rssi"})
    assert rssi_list.status_code == 200
    for forbidden_persona in ("martin", "pascal", "nadia"):
        forb_res = client.get(
            "/api/v1/settings/iam/accounts", headers={"X-Orcia-Persona": forbidden_persona}
        )
        assert forb_res.status_code == 403
        assert forb_res.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"
    obs_list = client.get(
        "/api/v1/settings/iam/accounts",
        headers={"X-Orcia-Persona": "karim", "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
    )
    assert obs_list.status_code == 403

    # BU_LEAD & TEAM_LEAD cannot touch /api/v1/settings/iam/accounts mutations
    for persona in ("martin", "pascal", "nadia"):
        res = client.post(
            "/api/v1/settings/iam/accounts",
            headers={"X-Orcia-Persona": persona},
            json={
                "principal_id": f"blocked-{persona}@orcia.ia",
                "display_name": "Blocked",
                "email": f"blocked-{persona}@orcia.ia",
                "account_kind": "HUMAN",
                "roles": ["CONTRIBUTOR"],
            },
        )
        assert res.status_code == 403
        assert res.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

    # SECOPS without PLATFORM_ADMIN cannot create PLATFORM_ADMIN or alter/delete PLATFORM_ADMIN
    secops_grant_admin = client.post(
        "/api/v1/settings/iam/accounts",
        headers={"X-Orcia-Persona": "rssi"},
        json={
            "principal_id": "rouge-admin@orcia.ia",
            "display_name": "Rogue Admin",
            "email": "rouge-admin@orcia.ia",
            "account_kind": "HUMAN",
            "roles": ["PLATFORM_ADMIN"],
        },
    )
    assert secops_grant_admin.status_code == 403
    assert secops_grant_admin.json()["error_code"] == "ERR_PRIVILEGE_ESCALATION_FORBIDDEN"

    secops_del_admin = client.delete(
        f"/api/v1/settings/iam/accounts/{day0_admin['id']}",
        headers={"X-Orcia-Persona": "rssi"},
    )
    assert secops_del_admin.status_code == 403
    assert secops_del_admin.json()["error_code"] == "ERR_PRIVILEGE_ESCALATION_FORBIDDEN"

    # SECOPS CAN create a normal CONTRIBUTOR account
    secops_ok = client.post(
        "/api/v1/settings/iam/accounts",
        headers={"X-Orcia-Persona": "rssi"},
        json={
            "principal_id": "secops.analyst@orcia.ia",
            "display_name": "Analyst",
            "email": "secops.analyst@orcia.ia",
            "account_kind": "HUMAN",
            "roles": ["CONTRIBUTOR"],
        },
    )
    assert secops_ok.status_code == 200
