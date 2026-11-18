"""Story 22.2 (Couche Sécurité) — Root ENTERPRISE scope, observer 403 & SecretInputPayload."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import OrgUnitNode, UserIdentity, WorkspaceEntity

ROOT_ENTERPRISE_ID = "0192c4e0-0000-7000-8000-000000000001"


@pytest.mark.asyncio
async def test_story_22_2_security_guards_root_invite_observer_and_secret_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce 403 on BU_LEAD/TEAM_LEAD root invites, OBSERVER & 422 SecretInputPayload."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    initialize_app_services(app)

    svc = app.state.auth_service
    bu_lead = UserIdentity(
        id="0195f000-0000-7000-8000-000000004001",
        email="bu.lead.222@orcia.ia",
        display_name="BU Lead 22.2",
        auth_mode="LOCAL",
        human_profile_archetype="EXECUTIVE",
        platform_role="BU_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000201",
        roles=("BU_LEAD",),
    )
    team_lead = UserIdentity(
        id="0195f000-0000-7000-8000-000000004002",
        email="team.lead.222@orcia.ia",
        display_name="Team Lead 22.2",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000301",
        roles=("TEAM_LEAD",),
    )
    observer = UserIdentity(
        id="0195f000-0000-7000-8000-000000004003",
        email="observer.222@orcia.ia",
        display_name="Observer 22.2",
        auth_mode="LOCAL",
        human_profile_archetype="OBSERVER",
        platform_role="OBSERVER",
        primary_org_unit_id=ROOT_ENTERPRISE_ID,
        roles=("OBSERVER",),
    )
    for key, identity in (
        ("bulead222", bu_lead),
        ("teamlead222", team_lead),
        ("observer222", observer),
    ):
        svc.register_user(identity)
        svc._persona_map[key] = identity.id  # noqa: SLF001

    obs_token = svc.jwt_manager.issue_token_pair(
        user_id=observer.id,
        email=observer.email,
        role=observer.platform_role,
        org_unit_id=observer.primary_org_unit_id,
        archetype=observer.human_profile_archetype,
        auth_mode=observer.auth_mode,
    ).access_token

    svc.evaluator.replace_org_units(
        (
            OrgUnitNode(
                id=ROOT_ENTERPRISE_ID,
                slug="orcia-root",
                name="Plateforme Globale ORCIA",
                unit_type="ENTERPRISE",
                parent_id=None,
            ),
            OrgUnitNode(
                id="0192c4e0-0000-7000-8000-000000000201",
                slug="bu-222",
                name="BU 22.2",
                unit_type="BU",
                parent_id=ROOT_ENTERPRISE_ID,
                lead_user_ids=(bu_lead.email,),
            ),
            OrgUnitNode(
                id="0192c4e0-0000-7000-8000-000000000301",
                slug="team-222",
                name="Team 22.2",
                unit_type="TEAM",
                parent_id="0192c4e0-0000-7000-8000-000000000201",
                lead_user_ids=(team_lead.email,),
            ),
        )
    )
    ws_id = "0195f000-0000-7000-8000-000000004100"
    svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_id,
            slug="ws-sec-222",
            name="Workspace Security 22.2",
            owner_org_unit_id="0192c4e0-0000-7000-8000-000000000301",
            visibility_mode="STANDARD",
        )
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. BU_LEAD and TEAM_LEAD must get 403 when trying to invite onto root ENTERPRISE
        for persona in ("bulead222", "teamlead222"):
            r_root_deny = await client.post(
                "/api/v1/org-units/invite-user",
                headers={"X-Orcia-Persona": persona},
                json={
                    "target_org_unit_id": ROOT_ENTERPRISE_ID,
                    "email": f"denied-{persona}@orcia.ia",
                    "display_name": "Denied User",
                    "assignment_role": "CONTRIBUTOR",
                },
            )
            assert r_root_deny.status_code == 403
            assert r_root_deny.json()["error_code"] == "ERR_ORG_UNIT_SCOPE_FORBIDDEN"

        # 2. Privilege escalation (PLATFORM_ADMIN / SECOPS) remains 403 even on ENTERPRISE
        for forbidden_role in ("PLATFORM_ADMIN", "SECOPS"):
            r_esc = await client.post(
                "/api/v1/org-units/invite-user",
                headers={"X-Orcia-Persona": "karim"},
                json={
                    "target_org_unit_id": ROOT_ENTERPRISE_ID,
                    "email": f"esc-{forbidden_role.lower()}@orcia.ia",
                    "display_name": "Esc User",
                    "assignment_role": forbidden_role,
                },
            )
            assert r_esc.status_code == 403
            assert r_esc.json()["error_code"] == "ERR_PRIVILEGE_ESCALATION_FORBIDDEN"

        # 3. OBSERVER & READ_ONLY_OBSERVER rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
        for obs_headers in (
            {"Authorization": f"Bearer {obs_token}"},
            {"X-Orcia-Persona": "karim", "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
        ):
            r_waiver_obs = await client.post(
                f"/api/v1/workspaces/{ws_id}/exception-waivers",
                headers=obs_headers,
                params={"persona_key": "karim"} if "X-Orcia-Persona" in obs_headers else {},
                json={
                    "source_uri": "orcia://sources/doc.md",
                    "source_sha256": "sha256:abcdef01",
                    "conflict_rule_id": "rule-obs",
                    "norm_level": "3_WORKSPACE",
                    "dna_chain": [],
                    "reason": "Tentative observateur",
                    "ttl_days": 30,
                },
            )
            assert r_waiver_obs.status_code == 403
            assert r_waiver_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            r_invite_obs = await client.post(
                "/api/v1/org-units/invite-user",
                headers=obs_headers,
                json={
                    "target_org_unit_id": ROOT_ENTERPRISE_ID,
                    "email": "obs-invite@orcia.ia",
                    "display_name": "Obs Invite",
                    "assignment_role": "CONTRIBUTOR",
                },
            )
            assert r_invite_obs.status_code == 403
            assert r_invite_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 4. SecretInputPayload rejects legacy `value` key (422) and accepts `plaintext_value` (201)
        sp = app.state.iam_accounts_service.create_account(
            principal_id="sp-sec-222",
            display_name="SP Sec 22.2",
            account_kind="SERVICE_PRINCIPAL",
            roles=("TEAM_LEAD",),
            team_ids=(ws_id,),
        )
        r_contract = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/autonomy-contract",
            headers={"X-Orcia-Persona": "karim"},
            params={"persona_key": "karim"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "LOW_NON_CRITICAL",
                "service_principal_id": sp.id,
                "allowed_read_sources": ["catalog:read"],
                "allowed_write_actions": ["catalog:write"],
                "max_cost_per_run_usd": 5.0,
            },
        )
        assert r_contract.status_code == 201, r_contract.text

        r_bad_secret = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/triggers",
            headers={"X-Orcia-Persona": "karim"},
            params={"persona_key": "karim"},
            json={
                "trigger_type": "LOG_SINK_ALERT",
                "log_sink_service": "orcia-worker",
                "log_sink_query_text": "level:ERROR",
                "cooldown_window_seconds": 0,
                "webhook_secret": {"action": "set", "value": "legacy-secret-key"},
            },
        )
        assert r_bad_secret.status_code == 422

        r_good_secret = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/triggers",
            headers={"X-Orcia-Persona": "karim"},
            params={"persona_key": "karim"},
            json={
                "trigger_type": "LOG_SINK_ALERT",
                "log_sink_service": "orcia-worker",
                "log_sink_query_text": "level:ERROR",
                "cooldown_window_seconds": 0,
                "webhook_secret": {
                    "action": "set",
                    "plaintext_value": "valid-secret-key-222",  # pragma: allowlist secret
                },
            },
        )
        assert r_good_secret.status_code == 201, r_good_secret.text
        assert r_good_secret.json()["webhook_secret_status"]["configured"] is True
