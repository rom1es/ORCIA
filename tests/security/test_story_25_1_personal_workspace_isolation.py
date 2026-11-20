"""Story 25.1 Security Isolation Tests for Personal Workspaces (`PRIVATE_USER`)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)

ROOT_OU_ID = "0192c4e0-0000-7000-8000-000000000001"
WS_PERSONAL_A_ID = "0195f000-0000-7000-8000-00000000a001"
WS_PERSONAL_B_ID = "0195f000-0000-7000-8000-00000000b002"


def _build_isolation_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TestClient, dict[str, dict[str, str]]]:
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    svc = app.state.auth_service

    user_a = UserIdentity(
        id="0195f000-0000-7000-8000-0000000000a1",
        email="alice.owner@orcia.ia",
        display_name="Alice Owner",
        auth_mode="LOCAL",
        human_profile_archetype="CONTRIBUTOR",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id=ROOT_OU_ID,
        roles=("CONTRIBUTOR",),
    )
    admin_b = UserIdentity(
        id="0195f000-0000-7000-8000-0000000000b2",
        email="bob.platform.admin@orcia.ia",
        display_name="Bob Platform Admin",
        auth_mode="LOCAL",
        human_profile_archetype="PLATFORM_ADMIN",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id=ROOT_OU_ID,
        roles=("PLATFORM_ADMIN", "SECOPS"),
    )
    secops_c = UserIdentity(
        id="0195f000-0000-7000-8000-0000000000c3",
        email="claire.secops@orcia.ia",
        display_name="Claire SecOps",
        auth_mode="LOCAL",
        human_profile_archetype="SECOPS",
        platform_role="SECOPS",
        primary_org_unit_id=ROOT_OU_ID,
        roles=("SECOPS",),
    )
    headers_by_key: dict[str, dict[str, str]] = {}
    for key, u in (("alice", user_a), ("bob", admin_b), ("claire", secops_c)):
        svc.register_user(u)
        tokens = svc.jwt_manager.issue_token_pair(
            user_id=u.id,
            email=u.email,
            role=u.platform_role,
            org_unit_id=u.primary_org_unit_id,
            archetype=u.human_profile_archetype,
            auth_mode="LOCAL",
        )
        headers_by_key[key] = {"Authorization": f"Bearer {tokens.access_token}"}

    svc.evaluator.upsert_org_unit(
        OrgUnitNode(
            id=ROOT_OU_ID,
            slug="orcia-root",
            name="ORCIA Root Organization",
            unit_type="ENTERPRISE",
            parent_id=None,
        )
    )
    svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=WS_PERSONAL_A_ID,
            slug=f"personal-{user_a.id}",
            name="Espace personnel — Alice Owner",
            owner_org_unit_id=ROOT_OU_ID,
            visibility_mode="CONFIDENTIAL_RESTRICTED",
            personal_owner_user_id=user_a.id,
            ui_visibility_mode="PRIVATE_USER",
        )
    )
    svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=WS_PERSONAL_B_ID,
            slug=f"personal-{admin_b.id}",
            name="Espace personnel — Bob Platform Admin",
            owner_org_unit_id=ROOT_OU_ID,
            visibility_mode="CONFIDENTIAL_RESTRICTED",
            personal_owner_user_id=admin_b.id,
            ui_visibility_mode="PRIVATE_USER",
        )
    )
    svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="0195f000-0000-7000-8000-00000000f001",
            workspace_id=WS_PERSONAL_A_ID,
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            user_id=user_a.id,
        )
    )
    return TestClient(app), headers_by_key


def test_platform_admin_and_secops_cannot_access_other_users_personal_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, auth_headers = _build_isolation_client(monkeypatch)

    # Owner Alice can access and pass mutation guard on her own personal workspace
    r_alice_ws = client.get("/api/v1/workspaces", headers=auth_headers["alice"])
    assert r_alice_ws.status_code == 200
    alice_ws_by_id = {w["id"]: w for w in r_alice_ws.json()["workspaces"]}
    assert WS_PERSONAL_A_ID in alice_ws_by_id
    assert WS_PERSONAL_B_ID not in alice_ws_by_id
    assert alice_ws_by_id[WS_PERSONAL_A_ID]["is_personal"] is True
    assert alice_ws_by_id[WS_PERSONAL_A_ID]["visibility_mode"] == "PRIVATE_USER"

    r_alice_check = client.post(
        f"/api/v1/workspaces/{WS_PERSONAL_A_ID}/mutations/check",
        headers=auth_headers["alice"],
    )
    assert r_alice_check.status_code == 200

    # PLATFORM_ADMIN Bob and SECOPS Claire NEVER see Alice's personal workspace in /workspaces
    for persona in ("bob", "claire"):
        r_list = client.get("/api/v1/workspaces", headers=auth_headers[persona])
        assert r_list.status_code == 200
        returned_ids = {w["id"] for w in r_list.json()["workspaces"]}
        assert WS_PERSONAL_A_ID not in returned_ids

        # Direct access by ID to Alice's personal workspace MUST return 403 or 404
        r_mut = client.post(
            f"/api/v1/workspaces/{WS_PERSONAL_A_ID}/mutations/check",
            headers=auth_headers[persona],
        )
        assert r_mut.status_code in (403, 404), r_mut.text

        r_overview = client.get(
            f"/api/v1/assistant/workspaces/{WS_PERSONAL_A_ID}/overview",
            headers=auth_headers[persona],
        )
        assert r_overview.status_code in (403, 404), r_overview.text
