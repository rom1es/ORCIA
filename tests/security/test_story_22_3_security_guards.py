"""Story 22.3 (Couche Sécurité) — OBSERVER 403 & CONFIDENTIAL_RESTRICTED isolation."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import OrgUnitNode, UserIdentity, WorkspaceEntity


@pytest.mark.asyncio
async def test_story_22_3_observer_read_only_and_confidential_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce 403 ERR_OBSERVER_MODE_READ_ONLY & CONFIDENTIAL_RESTRICTED isolation."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    initialize_app_services(app)

    auth_svc = app.state.auth_service
    obs_user = UserIdentity(
        id="0195f000-0000-7000-8000-000000007099",
        email="observer.223@orcia.ia",
        display_name="Observateur 22.3",
        auth_mode="LOCAL",
        human_profile_archetype="OBSERVER",
        platform_role="OBSERVER",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000001",
        roles=("OBSERVER",),
    )
    auth_svc.register_user(obs_user)
    obs_token = auth_svc.jwt_manager.issue_token_pair(
        user_id=obs_user.id,
        email=obs_user.email,
        role=obs_user.platform_role,
        org_unit_id=obs_user.primary_org_unit_id,
        archetype=obs_user.human_profile_archetype,
        auth_mode=obs_user.auth_mode,
    ).access_token

    team = OrgUnitNode(
        id="0192c4e0-0000-7000-8000-000000000301",
        slug="sec-223-team",
        name="Équipe Sécurité 22.3",
        unit_type="TEAM",
        parent_id="0192c4e0-0000-7000-8000-000000000001",
    )
    ws_std = WorkspaceEntity(
        id="0195f000-0000-7000-8000-000000007001",
        slug="ws-std-223",
        name="Workspace Standard 22.3",
        owner_org_unit_id=team.id,
        visibility_mode="STANDARD",
    )
    ws_conf = WorkspaceEntity(
        id="0195f000-0000-7000-8000-000000007002",
        slug="ws-conf-223",
        name="Workspace Confidential 22.3",
        owner_org_unit_id=team.id,
        visibility_mode="CONFIDENTIAL_RESTRICTED",
    )
    auth_svc.evaluator.replace_org_units(
        (
            OrgUnitNode(
                id="0192c4e0-0000-7000-8000-000000000001",
                slug="global",
                name="Global",
                unit_type="GLOBAL",
            ),
            team,
        )
    )
    auth_svc.evaluator.upsert_workspace(ws_std)
    auth_svc.evaluator.upsert_workspace(ws_conf)

    # Seed notification in standard and confidential workspaces
    notif_std = app.state.notification_service.create_notification(
        workspace_id=ws_std.id,
        target_team_id=team.id,
        target_user_id=None,
        run_id="0195f000-0000-7000-8000-000000007101",
        step_execution_id="0195f000-0000-7000-8000-000000007201",
        step_key="sec-step-1",
        notification_type="HUMAN_ARBITRATION",
        scope_kind="TEAM",
        title="Arbitrage Standard",
        summary="Détail standard",
    )
    app.state.notification_service.create_notification(
        workspace_id=ws_conf.id,
        target_team_id=team.id,
        target_user_id=None,
        run_id="0195f000-0000-7000-8000-000000007102",
        step_execution_id="0195f000-0000-7000-8000-000000007202",
        step_key="sec-step-conf",
        notification_type="HUMAN_ARBITRATION",
        scope_kind="TEAM",
        title="Arbitrage Confidentiel",
        summary="Détail confidentiel",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. OBSERVER JWT & READ_ONLY_OBSERVER header -> 403 ERR_OBSERVER_MODE_READ_ONLY
        for obs_params, obs_headers in (
            ({}, {"Authorization": f"Bearer {obs_token}"}),
            ({"persona_key": "karim"}, {"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"}),
        ):
            r_folder_obs = await client.post(
                "/api/v1/assistant/folders",
                params=obs_params,
                headers=obs_headers,
                json={"workspace_id": ws_std.id, "title": "Dossier Observateur"},
            )
            assert r_folder_obs.status_code == 403
            assert r_folder_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
            assert r_folder_obs.headers["content-type"].startswith("application/problem+json")

            r_claim_obs = await client.post(
                f"/api/v1/tasks/{notif_std.id}/claim",
                params=obs_params,
                headers=obs_headers,
                json={"workspace_id": ws_std.id, "ttl_seconds": 900, "force": False},
            )
            assert r_claim_obs.status_code == 403
            assert r_claim_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            r_broker_obs = await client.post(
                "/api/v1/permissions/broker/check-access",
                params=obs_params,
                headers=obs_headers,
                json={
                    "target_uri": "git://gitlab.internal/platform/infra-core",
                    "workspace_id": ws_std.id,
                    "raise_on_denied": False,
                },
            )
            assert r_broker_obs.status_code == 403
            assert r_broker_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 2. CONFIDENTIAL_RESTRICTED isolation on folders & workspace notifications
        r_conf_folder_write = await client.post(
            "/api/v1/assistant/folders",
            params={"persona_key": "karim"},
            json={"workspace_id": ws_conf.id, "title": "Intrusion Confidentielle"},
        )
        assert r_conf_folder_write.status_code == 403
        assert r_conf_folder_write.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        r_conf_folder_read = await client.get(
            f"/api/v1/assistant/workspaces/{ws_conf.id}/overview",
            params={"persona_key": "karim"},
        )
        assert r_conf_folder_read.status_code == 403
        assert r_conf_folder_read.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        r_conf_inbox = await client.get(
            "/api/v1/inbox/notifications",
            params={"workspace_id": ws_conf.id, "persona_key": "karim"},
        )
        assert r_conf_inbox.status_code == 403
        assert r_conf_inbox.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        r_conf_broker = await client.get(
            "/api/v1/permissions/broker/state",
            params={"workspace_id": ws_conf.id, "persona_key": "karim"},
        )
        assert r_conf_broker.status_code == 403
        assert r_conf_broker.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"
