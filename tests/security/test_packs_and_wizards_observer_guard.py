"""Security tests enforcing 403 ERR_OBSERVER_MODE_READ_ONLY on packs & wizards mutations."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.dependencies import initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import UserIdentity


@pytest.mark.asyncio
async def test_observer_mode_and_observer_jwt_rejected_on_packs_and_wizards_mutations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce HTTP 403 ERR_OBSERVER_MODE_READ_ONLY on all declarative pack & wizard mutations."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    initialize_app_services(app)

    auth_svc = app.state.auth_service
    obs_user = UserIdentity(
        id="0195f000-0000-7000-8000-000000009099",
        email="observer.wizards@orcia.ia",
        display_name="Observateur Packs & Wizards",
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

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create an initial wizard session as legitimate non-observer user
        r_start = await client.post(
            "/api/v1/wizards/sessions",
            json={
                "actor_persona": "marc",
                "wizard_type": "sdlc_tech_lead",
                "scope_id": "0195f000-0000-7000-8000-000000000301",
            },
        )
        assert r_start.status_code == 200, r_start.text
        session_id = r_start.json()["id"]

        mutation_targets: list[tuple[str, dict[str, object] | None]] = [
            ("/api/v1/packs/export/ws-observer-check?pack_id=orcia-pack-sdlc", None),
            (
                "/api/v1/wizards/sessions",
                {
                    "actor_persona": "marc",
                    "wizard_type": "sdlc_tech_lead",
                    "scope_id": "0195f000-0000-7000-8000-000000000301",
                },
            ),
            (
                f"/api/v1/wizards/sessions/{session_id}/steps",
                {
                    "actor_persona": "marc",
                    "step_index": 1,
                    "step_payload": {"org_unit_name": "Observer Blocked"},
                },
            ),
            (
                f"/api/v1/wizards/sessions/{session_id}/step-back",
                {
                    "actor_persona": "marc",
                    "step_index": 2,
                    "step_payload": {"workspace_name": "Observer Blocked"},
                },
            ),
            ("/api/v1/wizards/demo-workspace?actor_persona=marc", None),
        ]

        for path, body in mutation_targets:
            # 1. Explicit READ_ONLY_OBSERVER header
            resp_hdr = await client.post(
                path,
                headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                json=body,
            )
            assert resp_hdr.status_code == 403, f"{path} (header): {resp_hdr.text}"
            assert resp_hdr.headers["content-type"].startswith("application/problem+json")
            assert resp_hdr.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            # 2. Real OBSERVER JWT Bearer token
            resp_jwt = await client.post(
                path,
                headers={"Authorization": f"Bearer {obs_token}"},
                json=body,
            )
            assert resp_jwt.status_code == 403, f"{path} (JWT): {resp_jwt.text}"
            assert resp_jwt.headers["content-type"].startswith("application/problem+json")
            assert resp_jwt.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
