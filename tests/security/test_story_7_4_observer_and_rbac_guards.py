"""Security & Red-Team Tests for Story 7.4 — Observer 403 & Cross-Workspace RBAC Guards."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.dependencies import get_autonomous_supervision_service, initialize_app_services
from orcia_api.main import create_app


@pytest.mark.asyncio
async def test_story_7_4_observer_mode_and_rbac_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce 403 ERR_OBSERVER_MODE_READ_ONLY & cross-workspace RBAC denial on Story 7.4."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    initialize_app_services(app)
    ws_id = "0195f000-0000-7000-8000-000000000301"
    other_ws_id = "0195f000-0000-7000-8000-000000000399"
    run_id = "0195f000-0000-7000-8000-000000007450"

    from starlette.requests import Request

    dummy_req = Request({"type": "http", "app": app, "headers": [], "path": "/"})
    sup_svc = get_autonomous_supervision_service(dummy_req)
    await sup_svc.register_autonomous_run(
        run_id=run_id,
        workspace_id=ws_id,
        workflow_id="orcia://pack-sdlc/workflows/help-sync",
        contract_id="0195f000-0000-7000-8000-000000007401",
        status="COMMITTED_AUTONOMOUS",
        trigger_id="0195f000-0000-7000-8000-000000007402",
        trigger_label="Mise à jour nocturne",
        force_post_hoc_sample=True,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path, payload in (
            (f"/api/v1/runs/{run_id}/emergency-stop", {"reason": "test", "suspend_trigger": True}),
            (f"/api/v1/runs/{run_id}/invalidate-and-restore", {"comment": "rollback"}),
            (f"/api/v1/runs/{run_id}/post-hoc-review", {"decision": "VALIDATED"}),
        ):
            r_obs = await client.post(
                path,
                headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
                params={"persona_key": "partenaire"},
                json=payload,
            )
            assert r_obs.status_code == 403
            assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
            assert r_obs.headers["content-type"].startswith("application/problem+json")

        # Cross-workspace denial: unknown/ungranted workspace on list
        r_cross = await client.get(
            f"/api/v1/workspaces/{other_ws_id}/autonomous-runs",
            params={"persona_key": "dev"},
        )
        assert r_cross.status_code in (403, 404)

        # Authorized lead can execute emergency stop
        r_stop = await client.post(
            f"/api/v1/runs/{run_id}/emergency-stop",
            params={"persona_key": "marc"},
            json={"reason": "Dérive détectée", "suspend_trigger": True},
        )
        assert r_stop.status_code == 200
        assert r_stop.json()["status"] == "KILL_SWITCH_STOPPED"
        assert r_stop.json()["trigger_suspended"] is True
