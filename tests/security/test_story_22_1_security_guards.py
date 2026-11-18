"""Story 22.1 (Couche Sécurité) — UUID validation, OBSERVER 403 & CONFIDENTIAL isolation."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import OrgUnitNode, UserIdentity, WorkspaceEntity


@pytest.mark.asyncio
async def test_story_22_1_security_guards_uuid_observer_and_confidential_isolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject 'ws-1' (422), enforce 403 ERR_OBSERVER_MODE_READ_ONLY & isolate CONFIDENTIAL."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    initialize_app_services(app)

    auth_svc = app.state.auth_service
    obs_user = UserIdentity(
        id="0195f000-0000-7000-8000-000000003099",
        email="observer.sec@orcia.ia",
        display_name="Observateur Sécurité",
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
        slug="sec-team",
        name="Équipe Sécurité",
        unit_type="TEAM",
        parent_id="0192c4e0-0000-7000-8000-000000000001",
    )
    ws_std = WorkspaceEntity(
        id="0195f000-0000-7000-8000-000000003001",
        slug="sec-standard",
        name="Standard Sec",
        owner_org_unit_id=team.id,
        visibility_mode="STANDARD",
    )
    ws_conf = WorkspaceEntity(
        id="0195f000-0000-7000-8000-000000003002",
        slug="sec-confidential",
        name="Confidential Sec",
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Legacy synthetic key 'ws-1' must be rejected with HTTP 422 on UUID-typed endpoints
        r_dna = await client.post(
            "/api/v1/workspaces/ws-1/dna-mechanisms/compile",
            params={"persona_key": "karim"},
            json={
                "rule_id": "rule-1",
                "directive_title": "Conformité",
                "norm_title": "Norme",
                "natural_language_rule_fr": "Le champ code est requis.",
                "target_json_schema": {"type": "object"},
                "required_field": "code",
                "regex_pattern": "^[A-Z]+$",
                "passing_test_payload": {"code": "ABC"},
                "failing_test_payload": {"code": "123"},
            },
        )
        assert r_dna.status_code == 422

        # 2. Real OBSERVER JWT & READ_ONLY_OBSERVER header -> 403 ERR_OBSERVER_MODE_READ_ONLY
        for obs_params, obs_headers in (
            ({}, {"Authorization": f"Bearer {obs_token}"}),
            ({"persona_key": "karim"}, {"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"}),
        ):
            r_ws_create = await client.post(
                "/api/v1/workspaces",
                params=obs_params,
                headers=obs_headers,
                json={
                    "name": "Tentative Observateur",
                    "slug": "tentative-obs",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_ws_create.status_code == 403
            assert r_ws_create.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
            assert r_ws_create.headers["content-type"].startswith("application/problem+json")

            r_gate = await client.post(
                "/api/v1/gates/deterministic/evaluate",
                params=obs_params,
                headers=obs_headers,
                json={
                    "workspace_id": ws_std.id,
                    "run_id": "0195f000-0000-7000-8000-000000009010",
                    "step_execution_id": "0195f000-0000-7000-8000-000000009011",
                    "step_key": "check",
                    "artifact_payload": {"artifact": "ok"},
                },
            )
            assert r_gate.status_code == 403
            assert r_gate.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 3. CONFIDENTIAL_RESTRICTED without delegation remains isolated from PLATFORM_ADMIN
        r_list = await client.get("/api/v1/workspaces", params={"persona_key": "karim"})
        assert r_list.status_code == 200
        listed_ids = {item["id"] for item in r_list.json()["workspaces"]}
        assert ws_std.id in listed_ids
        assert ws_conf.id not in listed_ids

        r_conf_mut = await client.post(
            f"/api/v1/workspaces/{ws_conf.id}/mutations/check",
            params={"persona_key": "karim"},
        )
        assert r_conf_mut.status_code == 403
        assert r_conf_mut.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"
