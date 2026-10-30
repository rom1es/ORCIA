"""Tests for Story 5.2: Unified 4-Tab Workspace Control Center, `RunAccessGuard` & `⌘K` Palette.

Covers:
1. Multi-level scope consolidation (`GLOBAL | BU | TEAM | WORKSPACE`) across the 4 fractal tabs:
   - Tab 1 (`contributor_runs` vs `observer_runs`)
   - Tab 2 (`datasources` + 5-step `guidance_steps`)
   - Tab 3 (`workflow_overrides` 4-layer inspector)
   - Tab 4 (`org_units` + `workspaces_governance` with `RUN | BUILD | MIGRATION` lifecycle)
2. `CONFIDENTIAL_RESTRICTED` visibility: `PLATFORM_ADMIN` retains technical/FinOps roll-up while
   `blackboard_payload_masked=True` hides business payloads; non-member `BU_DIRECTOR` is excluded.
3. `RunAccessGuard` ($O(1)$): rejects `READ_ONLY_OBSERVER` with `403 ERR_OBSERVER_MODE_READ_ONLY`
   and rejects peer-claimed steps with `HTTP 409 ERR_STEP_ALREADY_CLAIMED_BY_PEER`.
4. `⌘K` Command Palette (`< 1 s`) and FastAPI endpoints `/api/v1/control-center/*`.
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.control_center import ControlCenterOverviewService
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    StepAlreadyClaimedByPeerError,
)
from orcia_core.orchestration.notifications_and_claims import (
    UnifiedNotificationAndClaimService,
)
from orcia_core.permissions import build_default_auth_and_org_service


def test_control_center_overview_scopes_and_confidential_restricted_masking() -> None:
    """Verify 4-tab rollup across GLOBAL/BU/TEAM/WORKSPACE and CONFIDENTIAL_RESTRICTED masking."""
    auth_svc = build_default_auth_and_org_service()
    notif_svc = UnifiedNotificationAndClaimService()
    cc_svc = ControlCenterOverviewService(
        evaluator=auth_svc.evaluator,
        notification_service=notif_svc,
    )

    karim = auth_svc.resolve_user(persona_key="karim")  # PLATFORM_ADMIN
    claire = auth_svc.resolve_user(persona_key="claire")  # BU_DIRECTOR (READ_ONLY_OBSERVER)
    marc = auth_svc.resolve_user(persona_key="marc")  # TEAM_LEAD on Workspace 1

    # 1. PLATFORM_ADMIN on GLOBAL sees CONFIDENTIAL_RESTRICTED Workspace 3 FinOps, payload masked
    ov_karim = cc_svc.build_overview(karim, scope_type="GLOBAL")
    ws3_gov = next(
        g
        for g in ov_karim.workspaces_governance
        if g.workspace_id == "0192c4e0-0000-7000-8000-000000000203"
    )
    assert ws3_gov.visibility_mode == "CONFIDENTIAL_RESTRICTED"
    assert ws3_gov.finops_cost_usd is not None and ws3_gov.finops_cost_usd > 0
    assert ws3_gov.blackboard_payload_masked is True
    run_703 = next(r for r in ov_karim.observer_runs if r.run_id.endswith("0703"))
    assert run_703.blackboard_payload_masked is True
    assert "CONFIDENTIAL_RESTRICTED" in run_703.blackboard_summary

    # 2. BU_DIRECTOR (claire) on GLOBAL is in READ_ONLY_OBSERVER mode with observer banner
    ov_claire = cc_svc.build_overview(claire, scope_type="GLOBAL")
    assert ov_claire.viewer_access_mode == "READ_ONLY_OBSERVER"
    assert ov_claire.observer_banner_fr is not None
    assert "Mode Consultation Seule" in ov_claire.observer_banner_fr
    assert len(ov_claire.guidance_steps) == 5
    assert len(ov_claire.workflow_overrides) >= 1

    # 3. TEAM_LEAD (marc) on WORKSPACE 1 has CONTRIBUTOR_ACTION_REQUIRED & can switch lifecycle
    ov_marc = cc_svc.build_overview(
        marc,
        scope_type="WORKSPACE",
        scope_id="0192c4e0-0000-7000-8000-000000000201",
    )
    assert ov_marc.viewer_access_mode == "CONTRIBUTOR_ACTION_REQUIRED"
    assert len(ov_marc.contributor_runs) == 1

    updated_gov = cc_svc.set_workspace_lifecycle_phase(
        marc,
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        lifecycle_phase="MIGRATION",
    )
    assert updated_gov.lifecycle_phase == "MIGRATION"
    assert "cartographie-dependances-existant" in updated_gov.suggested_workflows


def test_run_access_guard_and_command_palette_sub_second() -> None:
    """Verify O(1) RunAccessGuard (403 Observer / 409 Peer Claim) and < 1s Command Palette."""
    auth_svc = build_default_auth_and_org_service()
    notif_svc = UnifiedNotificationAndClaimService()
    cc_svc = ControlCenterOverviewService(
        evaluator=auth_svc.evaluator,
        notification_service=notif_svc,
    )

    claire = auth_svc.resolve_user(persona_key="claire")  # BU_DIRECTOR
    marc = auth_svc.resolve_user(persona_key="marc")  # TEAM_LEAD
    nadia = auth_svc.resolve_user(persona_key="nadia")  # CONTRIBUTOR

    run_id = "0195f000-0000-7000-8000-000000000701"
    step_id = "0195f000-0000-7000-8000-000000000801"

    # Observer is rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
    with pytest.raises(ObserverModeReadOnlyError) as obs_exc:
        cc_svc.enforce_run_mutation_guard(claire, run_id=run_id, step_execution_id=step_id)
    assert obs_exc.value.error_code == "ERR_OBSERVER_MODE_READ_ONLY"

    # Nadia claims the step -> Marc is rejected with 409 ERR_STEP_ALREADY_CLAIMED_BY_PEER
    notif_svc.claim_by_step_execution(
        nadia,
        run_id=run_id,
        step_execution_id=step_id,
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
    )
    with pytest.raises(StepAlreadyClaimedByPeerError) as peer_exc:
        cc_svc.enforce_run_mutation_guard(marc, run_id=run_id, step_execution_id=step_id)
    assert peer_exc.value.error_code == "ERR_STEP_ALREADY_CLAIMED_BY_PEER"

    # Nadia (lock holder) passes RunAccessGuard
    allowed_run = cc_svc.enforce_run_mutation_guard(nadia, run_id=run_id, step_execution_id=step_id)
    assert allowed_run.run_id == run_id

    # Command palette search completes in < 1s
    t0 = time.perf_counter()
    results = cc_svc.search_command_palette(marc, query="701")
    elapsed_s = time.perf_counter() - t0
    assert elapsed_s < 1.0
    assert any(item.entry_id.endswith("0701") for item in results)


def test_story_5_2_control_center_http_endpoints() -> None:
    """Verify FastAPI `/api/v1/control-center/*` endpoints and RFC 9457 error responses."""
    app = create_app()
    with TestClient(app) as client:
        # 1. Overview for Marc (TEAM_LEAD)
        res_ov = client.get("/api/v1/control-center/overview?scope_type=GLOBAL&persona_key=marc")
        assert res_ov.status_code == 200
        data = res_ov.json()
        assert len(data["guidance_steps"]) == 5
        assert len(data["contributor_runs"]) >= 1

        # 2. Lifecycle update as Marc succeeds
        ws1_id = "0192c4e0-0000-7000-8000-000000000201"
        res_lc = client.patch(
            f"/api/v1/control-center/workspaces/{ws1_id}/lifecycle?persona_key=marc",
            json={"lifecycle_phase": "RUN"},
        )
        assert res_lc.status_code == 200
        assert res_lc.json()["lifecycle_phase"] == "RUN"

        # 3. Lifecycle update as Observer (claire) fails with 403 ERR_OBSERVER_MODE_READ_ONLY
        res_lc_obs = client.patch(
            f"/api/v1/control-center/workspaces/{ws1_id}/lifecycle?persona_key=claire",
            json={"lifecycle_phase": "BUILD"},
        )
        assert res_lc_obs.status_code == 403
        assert res_lc_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 4. RunAccessGuard endpoint check
        run_id = "0195f000-0000-7000-8000-000000000701"
        step_id = "0195f000-0000-7000-8000-000000000801"
        res_guard_obs = client.post(
            f"/api/v1/control-center/runs/{run_id}/steps/{step_id}/mutate-check?persona_key=claire",
            json={"action": "approve_gate"},
        )
        assert res_guard_obs.status_code == 403
        assert res_guard_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        res_guard_ok = client.post(
            f"/api/v1/control-center/runs/{run_id}/steps/{step_id}/mutate-check?persona_key=marc",
            json={"action": "approve_gate"},
        )
        assert res_guard_ok.status_code == 200
        assert res_guard_ok.json()["allowed"] is True

        # 5. Command Palette endpoint
        res_cmd = client.get("/api/v1/control-center/command-palette?q=g%20w&persona_key=marc")
        assert res_cmd.status_code == 200
        assert any(item["shortcut"] == "g w" for item in res_cmd.json()["items"])
