"""Unit & FastAPI conformance tests for Story 26.8 (`CONTINUE_IN_PROCESS` & Human Anchors)."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.assistant_process_launcher import AssistantProcessLauncherService
from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.errors import HumanAnchorRequiredError
from orcia_core.orchestration.seeds import build_default_orchestration_setup_service
from orcia_core.permissions import build_default_auth_and_org_service

_WS_PAY = "0192c4e0-0000-7000-8000-000000000201"


def test_prefix_step_commits_then_halts_strictly_at_first_waiting_anchor() -> None:
    """Verify domain launcher commits prefix steps and halts at the first `WAITING_*` step."""
    from orcia_core.orchestration.step_executors import _DEFAULT_AGENT_EXECUTOR
    from orcia_core.testing.cassette_llm import DeterministicCassetteLLM

    _DEFAULT_AGENT_EXECUTOR.set_llm_gateway(DeterministicCassetteLLM())
    auth = build_default_auth_and_org_service()
    marc = auth.resolve_user(persona_key="marc")
    setup_svc = build_default_orchestration_setup_service()
    yaml_text = """uri: "orcia://workflows/prefix-then-anchor-check"
title: "Prefix Then Human Anchor"
description: "Commits step-0 then pauses at step-1 WAITING_FOR_HUMAN_ANCHOR."
version: "1.0.0"
criticality: "STANDARD"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
max_cost_usd: 5.0
datasources:
  - "git://claims/core-engine@main"
steps:
  - step_key: "step-0-collect"
    title: "Collect Facts"
    step_type: "SKILL"
    skill_uri: "orcia://skills/sandbox-pytest-runner@1.0.0"
    instructions: "Gather verified context inputs."
  - step_key: "step-1-anchor"
    title: "Mandatory Human Framing"
    step_type: "AGENT"
    agent_uri: "orcia://agents/product-architect@1.0.0"
    template_key: "tpl-architecture-decision-record"
    human_authored_required: true
    requires_human_gate: true
    instructions: "Wait for signed human anchor before continuing."
    depends_on:
      - "step-0-collect"
  - step_key: "step-2-downstream"
    title: "Downstream Generation"
    step_type: "POST_ACTION_VERIFICATION"
    depends_on:
      - "step-1-anchor"
    instructions: "Runs strictly after human anchor signature."
"""
    rep = setup_svc.validate_workflow_manifest(yaml_text, workspace_id=_WS_PAY, raise_on_error=True)
    assert rep.workflow is not None
    setup_svc.register_validated_workflow(rep.workflow)

    engine = DurableOrchestrationEngine(setup_service=setup_svc)
    launcher = AssistantProcessLauncherService(setup_service=setup_svc, engine=engine)
    outcome = asyncio.run(
        launcher.launch_process_async(
            marc,
            workspace_id=_WS_PAY,
            workflow_uri="orcia://workflows/prefix-then-anchor-check",
            idempotency_token="prefix-halt-1",
        )
    )
    assert outcome.executed_step_keys == ("step-0-collect",)
    assert outcome.waiting_step_keys == ("step-1-anchor",)
    assert outcome.run_status == "WAITING_FOR_HUMAN_ARBITRATION"
    assert outcome.snapshot_count == 1

    step_1 = engine.blackboard.get_step_execution(outcome.run.id, "step-1-anchor")
    step_2 = engine.blackboard.get_step_execution(outcome.run.id, "step-2-downstream")
    assert step_1.status == "WAITING_FOR_HUMAN_ANCHOR"
    assert step_2.status == "PENDING"

    with pytest.raises(HumanAnchorRequiredError):
        asyncio.run(
            engine.execute_step_async(marc, run_id=outcome.run.id, step_key="step-1-anchor")
        )

    engine.anchors_and_arbitration.sign_human_anchor(
        marc,
        run_id=outcome.run.id,
        step_key="step-1-anchor",
        section_key="primary-anchor",
        content_text=(
            "Mandatory architectural boundary rationale signed by human reviewer >= 30 chars."
        ),
        signature_text="Signed by Marc Lead",
        author_type="HUMAN",
    )
    resumed = asyncio.run(
        launcher.resume_after_anchor_signature_async(
            marc,
            run_id=outcome.run.id,
            step_key="step-1-anchor",
        )
    )
    assert resumed is not None
    assert resumed.run_status == "COMPLETED"
    assert "step-1-anchor" in resumed.executed_step_keys
    assert "step-2-downstream" in resumed.executed_step_keys
    assert resumed.snapshot_count == 3


def test_api_continue_in_process_folder_launch_anchor_sign_and_legacy_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify HTTP routes for `/turns/{id}/approve`, `/folders/{id}/launch-process`, and removal."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    with TestClient(app) as client:
        assert client.post(
            "/api/v1/assistant/workflows/save-and-launch?persona_key=marc",
            json={"workspace_id": _WS_PAY, "manifest_yaml": "uri: orcia://workflows/x\n"},
        ).status_code in (404, 405)

        turn_res = client.post(
            "/api/v1/assistant/turns?persona_key=marc",
            json={"workspace_id": _WS_PAY, "user_prompt": "Prepare governed delivery process."},
        )
        assert turn_res.status_code == 202
        turn_id = turn_res.json()["turn_id"]

        obs_approve = client.post(
            f"/api/v1/assistant/turns/{turn_id}/approve?persona_key=claire",
            json={
                "workspace_id": _WS_PAY,
                "proposal_id": "prop-obs",
                "approved": True,
                "human_anchor_markdown": "Observer cannot mutate",
                "continue_in_process": True,
            },
        )
        assert obs_approve.status_code == 403
        assert obs_approve.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        approve_res = client.post(
            f"/api/v1/assistant/turns/{turn_id}/approve?persona_key=marc",
            json={
                "workspace_id": _WS_PAY,
                "proposal_id": "prop-268",
                "approved": True,
                "human_anchor_markdown": "Approved continuation into governed process.",
                "continue_in_process": True,
            },
        )
        assert approve_res.status_code == 200
        body = approve_res.json()
        run_id = body["run_id"]
        assert run_id
        assert body["run_status"] == "WAITING_FOR_HUMAN_ARBITRATION"
        assert body["waiting_step_keys"] == ["frame-architecture-intent"]
        assert body["executed_step_keys"] == []

        unsigned_exec = client.post(
            "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
            json={
                "run_id": run_id,
                "step_key": "frame-architecture-intent",
                "commit_immediately": True,
            },
        )
        assert unsigned_exec.status_code == 422
        assert unsigned_exec.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

        short_sign = client.post(
            "/api/v1/orchestration/runs/anchors/sign?persona_key=marc",
            json={
                "run_id": run_id,
                "step_key": "frame-architecture-intent",
                "section_key": "primary-anchor",
                "content_text": "Too short",
                "signature_text": "Marc",
                "author_type": "HUMAN",
            },
        )
        assert short_sign.status_code == 422
        assert short_sign.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

        folder_res = client.post(
            "/api/v1/assistant/folders?persona_key=marc",
            json={"workspace_id": _WS_PAY, "title": "Payments Audit Folder"},
        )
        assert folder_res.status_code == 200
        folder_id = folder_res.json()["folder_id"]

        obs_folder_launch = client.post(
            f"/api/v1/assistant/folders/{folder_id}/launch-process?persona_key=claire",
            json={"workspace_id": _WS_PAY},
        )
        assert obs_folder_launch.status_code == 403
        assert obs_folder_launch.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        folder_launch = client.post(
            f"/api/v1/assistant/folders/{folder_id}/launch-process?persona_key=marc",
            json={"workspace_id": _WS_PAY},
        )
        assert folder_launch.status_code == 200
        fl_body = folder_launch.json()
        fl_run_id = fl_body["run_id"]
        assert fl_run_id
        assert fl_body["workflow_uri"] == "orcia://pack-sdlc/workflows/ticket-to-tech-spec"
        assert fl_body["waiting_step_keys"] == ["frame-spec-human-anchor"]

        signed = client.post(
            "/api/v1/orchestration/runs/anchors/sign?persona_key=marc",
            json={
                "run_id": fl_run_id,
                "step_key": "frame-spec-human-anchor",
                "section_key": "primary-anchor",
                "content_text": (
                    "Mandatory human intent anchor approved for spec synthesis >= 30 chars."
                ),
                "signature_text": "Marc Lead Signature",
                "author_type": "HUMAN",
            },
        )
        assert signed.status_code == 200
        assert signed.json()["step_execution"]["status"] == "COMMITTED"

        blackboard = client.get(
            f"/api/v1/orchestration/runs/{fl_run_id}/blackboard?persona_key=marc"
        )
        assert blackboard.status_code == 200
        bb = blackboard.json()
        assert len(bb["active_snapshots"]) == 3
        assert [s["status"] for s in bb["step_executions"]] == [
            "COMMITTED",
            "COMMITTED",
            "COMMITTED",
        ]
