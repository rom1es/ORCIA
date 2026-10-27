"""Layer 1 Unit Tests for Story 3.2: Durable Orchestration Engine, JIT Hydrator & Blackboard."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.domain.exceptions import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.orchestration import (
    JitStepHydrator,
    build_default_orchestration_setup_service,
)
from orcia_core.permissions.models import UserIdentity
from orcia_worker.step_runner import execute_step_runner_job


def _lead_user() -> UserIdentity:
    return UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000603",
        email="marc.lead@orcia.io",
        display_name="Marc",
        auth_mode="HYBRID",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )


def _observer_user() -> UserIdentity:
    return UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000699",
        email="obs@orcia.io",
        display_name="Observer",
        auth_mode="LOCAL",
        human_profile_archetype="PM_BUSINESS",
        platform_role="OBSERVER",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )


def test_jit_step_hydrator_zero_future_leakage_and_draft_vs_snapshot_separation() -> None:
    """Verify JitStepHydrator (AD-13) and draft vs committed snapshot separation (AD-2)."""
    svc = build_default_orchestration_setup_service()
    lead = _lead_user()
    root_run = svc.runs[0]
    wf = svc.engine._get_workflow(root_run.workflow_uri)

    # 1. Step 1 hydration: 0 future step instructions leaked
    ctx1 = JitStepHydrator.hydrate_step(
        run=root_run,
        workflow=wf,
        step_key="frame-architecture-intent",
        blackboard=svc.engine.blackboard,
    )
    assert ctx1.future_step_instructions_leaked == 0
    assert ctx1.undeclared_artifacts_leaked == 0
    assert "Observer le puits de logs" not in ctx1.step_directive

    # 2. Hydrating Step 2 BEFORE Step 1 is committed raises ResourceNotFoundError
    with pytest.raises(ResourceNotFoundError):
        JitStepHydrator.hydrate_step(
            run=root_run,
            workflow=wf,
            step_key="delegate-remediation-subworkflow",
            blackboard=svc.engine.blackboard,
        )

    # 3. Execute Step 1 with commit_immediately=False -> draft written, 0 snapshot in blackboard
    draft_step, snap_none = svc.engine.execute_step(
        lead,
        run_id=root_run.id,
        step_key="frame-architecture-intent",
        commit_immediately=False,
    )
    assert snap_none is None
    assert draft_step.status == "EXECUTING_AGENT"
    assert draft_step.draft_cas_key is not None
    assert len(svc.engine.blackboard.get_active_snapshots(root_run.id)) == 0

    # 4. Commit Step 1 -> immutable snapshot created in blackboard_snapshots
    snap1 = svc.engine.blackboard.commit_step_snapshot(root_run.id, "frame-architecture-intent")
    assert snap1.branch_status == "ACTIVE"
    assert len(svc.engine.blackboard.get_active_snapshots(root_run.id)) == 1

    # 5. Any attempt to mutate or delete a committed snapshot raises ValidationDomainError
    with pytest.raises(ValidationDomainError) as append_exc:
        svc.engine.blackboard.mutate_or_delete_snapshot(snap1.id)
    assert "ERR_BLACKBOARD_APPEND_ONLY_VIOLATION" in str(append_exc.value)


def test_bounded_feedback_retries_and_isolated_sub_workflow_execution() -> None:
    """Verify bounded retries (max_agent_retries), SUB_WORKFLOW isolation, and shared budget."""
    svc = build_default_orchestration_setup_service()
    lead = _lead_user()
    root_run = svc.runs[0]

    # Bounded retry loop up to max_agent_retries (3)
    for attempt in range(1, 4):
        retried = svc.engine.blackboard.record_bounded_retry(
            root_run.id,
            "frame-architecture-intent",
            feedback_reason=f"Auto-correction #{attempt}",
        )
        assert retried.attempt_count == attempt
        assert retried.status == "EXECUTING_AGENT"

    # 4th retry exceeds max_agent_retries=3 -> escalates to WAITING_FOR_HUMAN_ARBITRATION
    with pytest.raises(ValidationDomainError):
        svc.engine.blackboard.record_bounded_retry(
            root_run.id,
            "frame-architecture-intent",
            feedback_reason="Dépassement max_agent_retries",
        )
    escalated = svc.engine.blackboard.get_step_execution(root_run.id, "frame-architecture-intent")
    assert escalated.status == "WAITING_FOR_HUMAN_ARBITRATION"

    # Execute Step 1 then Step 2 (SUB_WORKFLOW) -> spawns isolated child & grandchild runs
    svc.engine.execute_step(
        lead,
        run_id=root_run.id,
        step_key="frame-architecture-intent",
        commit_immediately=True,
    )
    step2, snap2 = svc.engine.execute_step(
        lead,
        run_id=root_run.id,
        step_key="delegate-remediation-subworkflow",
        commit_immediately=True,
    )
    assert step2.child_run_id is not None
    assert snap2 is not None
    assert "verified_patch" in snap2.artifact_payload

    # Lexical isolation: child run snapshots do NOT appear in root_run's active snapshots
    root_snaps = svc.engine.blackboard.get_active_snapshots(root_run.id)
    child_snaps = svc.engine.blackboard.get_active_snapshots(step2.child_run_id)
    assert len(root_snaps) == 2
    assert len(child_snaps) == 3
    assert {s.run_id for s in root_snaps} == {root_run.id}
    assert {s.run_id for s in child_snaps} == {step2.child_run_id}

    # Shared root_run_id budget enforcement
    with pytest.raises(ValidationDomainError) as budget_exc:
        svc.engine.execute_step(
            lead,
            run_id=root_run.id,
            step_key="post-deploy-verification",
            cost_usd=999.0,
        )
    assert "Plafond budgétaire root_run_id" in str(budget_exc.value)


def test_background_fast_path_audit_worker_idempotency_and_rest_routes() -> None:
    """Verify BACKGROUND_FAST_PATH markers, idempotent Dramatiq step_runner, and REST routes."""
    svc = build_default_orchestration_setup_service()
    observer = _observer_user()
    root_run = svc.runs[0]

    with pytest.raises(ObserverModeReadOnlyError):
        svc.engine.execute_step(
            observer,
            run_id=root_run.id,
            step_key="frame-architecture-intent",
        )

    # Idempotent Dramatiq step_runner job
    res1 = execute_step_runner_job(
        run_id=root_run.id,
        step_key="frame-architecture-intent",
        trace_id="0123456789abcdef0123456789abcdef",
        orchestration_service=svc,
    )
    assert res1.already_committed is False
    assert res1.snapshot_id is not None

    res2 = execute_step_runner_job(
        run_id=root_run.id,
        step_key="frame-architecture-intent",
        trace_id="0123456789abcdef0123456789abcdef",
        orchestration_service=svc,
    )
    assert res2.already_committed is True
    assert res2.snapshot_id == res1.snapshot_id

    # FastAPI endpoints for Story 3.2
    client = TestClient(create_app())
    state_res = client.get("/api/v1/orchestration/state?persona_key=marc")
    assert state_res.status_code == 200
    api_run_id = state_res.json()["runs"][0]["id"]

    hydrate_res = client.post(
        "/api/v1/orchestration/runs/steps/hydrate?persona_key=marc",
        json={"run_id": api_run_id, "step_key": "frame-architecture-intent"},
    )
    assert hydrate_res.status_code == 200
    assert hydrate_res.json()["hydrated_context"]["future_step_instructions_leaked"] == 0

    exec_res = client.post(
        "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
        json={
            "run_id": api_run_id,
            "step_key": "frame-architecture-intent",
            "commit_immediately": True,
        },
    )
    assert exec_res.status_code == 200
    assert exec_res.json()["step_execution"]["status"] == "COMMITTED"

    audit_res = client.post(
        "/api/v1/orchestration/runs/fast-path-audit?persona_key=marc",
        json={"run_id": api_run_id},
    )
    assert audit_res.status_code == 200
    report = audit_res.json()["report"]
    assert report["total_steps_committed"] == 3
    assert len(report["assumptions"]) >= 1
    assert len(report["suspected_code_bugs"]) >= 1
    assert len(report["suspected_obsolete_docs"]) >= 1
    assert report["sse_latency_ms"] < 500.0

    bb_res = client.get(f"/api/v1/orchestration/runs/{api_run_id}/blackboard?persona_key=marc")
    assert bb_res.status_code == 200
    assert len(bb_res.json()["active_snapshots"]) == 3
