"""Security & Red-Team Tests for Story 7.1 — Confinement, Observer Guard & Zero Secret Leak."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.main import create_app


@pytest.mark.asyncio
async def test_story_7_1_observer_blocked_escalation_rejected_and_zero_secret_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce 403 OBSERVER, 403 privilege escalation, 422 HIGH_CRITICAL & 0 canary leak."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    other_ws_id = "0192c4e0-0000-7000-8000-000000000203"
    wf_id = "wf-sec-autonomy"
    sp_obs = app.state.iam_accounts_service.create_account(
        principal_id="sp-readonly",
        display_name="SP Lecture Seule",
        account_kind="SERVICE_PRINCIPAL",
        roles=("OBSERVER",),
        team_ids=(ws_id,),
    )
    sp_lead = app.state.iam_accounts_service.create_account(
        principal_id="sp-lead",
        display_name="SP Équipe",
        account_kind="SERVICE_PRINCIPAL",
        roles=("TEAM_LEAD",),
        team_ids=(ws_id,),
    )

    canary = "sk-live-" + "ORCIA_CANARY_STORY_7_1_TOP_SECRET_KEY"  # pragma: allowlist secret
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. READ_ONLY_OBSERVER rejected 403 ERR_OBSERVER_MODE_READ_ONLY
        r_obs = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
            params={"persona_key": "partenaire"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "STANDARD",
                "service_principal_id": sp_lead.id,
                "allowed_write_actions": ["catalog:write"],
                "max_cost_per_run_usd": 5.0,
            },
        )
        assert r_obs.status_code == 403
        assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 2. Privilege escalation rejected 403 ERR_CONTRACT_PRIVILEGE_ESCALATION (SP OBSERVER)
        r_esc = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "marc"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "STANDARD",
                "service_principal_id": sp_obs.id,
                "allowed_write_actions": ["catalog:create"],
                "max_cost_per_run_usd": 5.0,
            },
        )
        assert r_esc.status_code == 403
        assert r_esc.json()["error_code"] == "ERR_CONTRACT_PRIVILEGE_ESCALATION"

        # 3. HIGH_CRITICAL rejected 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE
        r_crit = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "marc"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "HIGH_CRITICAL",
                "service_principal_id": sp_lead.id,
                "allowed_write_actions": ["catalog:write"],
                "max_cost_per_run_usd": 5.0,
            },
        )
        assert r_crit.status_code == 422
        assert r_crit.json()["error_code"] == "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE"

        # 4. Sign valid contract and run autonomous execution with canary in payload -> 0 leak
        r_sign = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "marc"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "LOW_NON_CRITICAL",
                "service_principal_id": sp_lead.id,
                "allowed_read_sources": ["catalog:read"],
                "allowed_write_actions": ["help_article:publish"],
                "max_cost_per_run_usd": 5.0,
            },
        )
        assert r_sign.status_code == 201
        assert canary not in json.dumps(r_sign.json())

        r_run = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/runs/autonomous",
            params={"persona_key": "marc"},
            json={
                "criticality": "LOW_NON_CRITICAL",
                "actions": [
                    {
                        "action_key": "help_article:publish",
                        "scheme": "catalog",
                        "payload": {"api_key": canary, "title": "Aide"},
                    }
                ],
            },
        )
        assert r_run.status_code == 201
        assert r_run.json()["status"] == "COMMITTED_AUTONOMOUS"
        assert canary not in r_run.text

        # 5. Cross-team / confidential IDOR & non-governor contributor denied (403)
        r_idor = await client.get(
            f"/api/v1/workspaces/{other_ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "partenaire"},
        )
        assert r_idor.status_code == 403

        r_contrib = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "nadia"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "STANDARD",
                "service_principal_id": sp_lead.id,
                "allowed_write_actions": ["catalog:write"],
                "max_cost_per_run_usd": 5.0,
            },
        )
        assert r_contrib.status_code == 403
