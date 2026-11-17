"""Security & Red-Team Tests for Story 7.2 — HMAC 401, Observer 403 & Zero Secret Leak."""

from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.main import create_app
from orcia_core.permissions import compute_webhook_hmac_sha256


@pytest.mark.asyncio
async def test_story_7_2_hmac_rejection_observer_guard_and_zero_secret_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce 401 ERR_WEBHOOK_SIGNATURE_INVALID, 403 OBSERVER, and 0 canary leak."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    ws_id = "0195f000-0000-7000-8000-000000000301"
    wf_id = "wf-sec-triggers"
    sp = app.state.iam_accounts_service.create_account(
        principal_id="sp-triggers-sec",
        display_name="SP Triggers",
        account_kind="SERVICE_PRINCIPAL",
        roles=("TEAM_LEAD",),
        team_ids=(ws_id,),
    )
    canary_secret = "whsec-canary-story-7-2-top-secret"  # pragma: allowlist secret

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Observer blocked 403 on trigger creation
        r_obs = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/triggers",
            headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
            params={"persona_key": "partenaire"},
            json={"trigger_type": "MANUAL_AUTONOMOUS"},
        )
        assert r_obs.status_code == 403
        assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 2. Sign contract & create WEBHOOK trigger with canary secret
        r_sign = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/autonomy-contract",
            params={"persona_key": "marc"},
            json={
                "workflow_version": "1.0.0",
                "criticality": "LOW_NON_CRITICAL",
                "service_principal_id": sp.id,
                "allowed_read_sources": ["catalog:read"],
                "allowed_write_actions": ["catalog:write"],
                "max_cost_per_run_usd": 5.0,
            },
        )
        assert r_sign.status_code == 201

        r_create = await client.post(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/triggers",
            params={"persona_key": "marc"},
            json={
                "trigger_type": "WEBHOOK",
                "webhook_secret": {"action": "set", "plaintext_value": canary_secret},
            },
        )
        assert r_create.status_code == 201
        trig_id = r_create.json()["id"]
        assert canary_secret not in json.dumps(r_create.json())
        assert r_create.json()["webhook_secret_status"]["configured"] is True

        # GET list never leaks canary secret
        r_list = await client.get(
            f"/api/v1/workspaces/{ws_id}/workflows/{wf_id}/triggers",
            params={"persona_key": "marc"},
        )
        assert r_list.status_code == 200
        assert canary_secret not in json.dumps(r_list.json())

        # 3. Missing or invalid HMAC signature rejected 401
        raw_body = json.dumps({"delivery_key": "sec-1"}).encode()
        r_bad_sig = await client.post(
            f"/api/v1/webhooks/triggers/{trig_id}",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Orcia-Webhook-Signature": "sha256=" + "f" * 64,
            },
        )
        assert r_bad_sig.status_code == 401
        assert r_bad_sig.json()["error_code"] == "ERR_WEBHOOK_SIGNATURE_INVALID"

        # 4. Unsigned / bad signature on /api/v1/triggers/alerts rejected 401
        r_bad_alert = await client.post(
            "/api/v1/triggers/alerts",
            json={"trigger_id": trig_id, "service": "api", "message": "err"},
        )
        assert r_bad_alert.status_code == 401
        assert r_bad_alert.json()["error_code"] == "ERR_WEBHOOK_SIGNATURE_INVALID"

        # 5. Valid HMAC signature succeeds and leaks zero canary
        good_sig = compute_webhook_hmac_sha256(raw_body, canary_secret)
        r_good = await client.post(
            f"/api/v1/webhooks/triggers/{trig_id}",
            content=raw_body,
            headers={"Content-Type": "application/json", "X-Orcia-Webhook-Signature": good_sig},
        )
        assert r_good.status_code == 200
        assert r_good.json()["dispatched"] is True
        assert canary_secret not in json.dumps(r_good.json())
