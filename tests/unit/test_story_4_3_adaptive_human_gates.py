"""Unit & API contract tests for Story 4.3: Adaptive Human Gates & Chunked Validation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.gates import (
    AdaptiveHumanGateService,
    HumanGateNotFoundError,
    RubberStampingGuardTriggeredError,
    UnapprovedChunksRemainingError,
    compute_sampling_bucket,
)


def test_adaptive_human_gate_policies_auto_pass_and_exceptions() -> None:
    """Verify `risk_or_exception_based`, `mandatory_full`, and `sampling` policies (`AD-11`)."""
    service = AdaptiveHumanGateService()

    # 1. risk_or_exception_based auto-passes when all 5 conditions hold
    auto_eval = service.evaluate_human_gate(
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-1",
        step_key="step-spec",
        policy="risk_or_exception_based",
        artifact_payload={
            "sections": [{"chunk_key": "s1", "title": "Intro", "content": "Conforme aux axiomes."}]
        },
        deterministic_status="PASS",
        agentic_score=0.91,
        ontology_conflicts=0,
        stale_warnings=0,
    )
    assert auto_eval.status == "PASS"
    assert auto_eval.auto_passed is True
    assert auto_eval.outbox_event_id is not None
    assert all(c.status == "APPROVED" for c in auto_eval.chunks)

    # 2. risk_or_exception_based requires human review if human_authored_required=True
    human_req_eval = service.evaluate_human_gate(
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-2",
        step_key="step-anchor",
        policy="risk_or_exception_based",
        artifact_payload={
            "sections": [
                {
                    "chunk_key": "s1",
                    "title": "Ancre Humaine",
                    "content": "Décision d'architecture critique.",
                    "human_authored_required": True,
                }
            ]
        },
        deterministic_status="PASS",
        agentic_score=0.95,
        ontology_conflicts=0,
        stale_warnings=0,
    )
    assert human_req_eval.status == "PENDING_HUMAN_REVIEW"
    assert human_req_eval.auto_passed is False

    # 3. mandatory_full always requires human review even when score is 0.99
    mandatory_eval = service.evaluate_human_gate(
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-3",
        step_key="step-mandatory",
        policy="mandatory_full",
        artifact_payload={"content": "## Section A\nTexte A\n## Section B\nTexte B"},
        deterministic_status="PASS",
        agentic_score=0.99,
    )
    assert mandatory_eval.status == "PENDING_HUMAN_REVIEW"
    assert len(mandatory_eval.chunks) == 2

    # 4. sampling policy uses deterministic bucket or explicit override
    bucket = compute_sampling_bucket("run-1", "step-4")
    assert 0 <= bucket < 100
    sampled_hit = service.evaluate_human_gate(
        workspace_id="ws-1",
        run_id="run-1",
        step_execution_id="step-4",
        step_key="step-sampled",
        policy="sampling",
        artifact_payload={"content": "Section unique"},
        sampling_override=True,
    )
    assert sampled_hit.status == "PENDING_HUMAN_REVIEW"


def test_chunked_validation_and_anti_rubber_stamping_guard() -> None:
    """Verify chunk decisions (`APPROVE`, `CO_EDIT`, `CHALLENGE`) & <15s guard on >1,000 words."""
    service = AdaptiveHumanGateService()
    large_text_1 = " ".join(["architecture"] * 600)
    large_text_2 = " ".join(["securite"] * 600)

    record = service.evaluate_human_gate(
        workspace_id="ws-1",
        run_id="run-2",
        step_execution_id="step-large",
        step_key="step-arch",
        policy="mandatory_full",
        artifact_payload={
            "sections": [
                {"chunk_key": "sec-1", "title": "1. Architecture", "content": large_text_1},
                {"chunk_key": "sec-2", "title": "2. Sécurité", "content": large_text_2},
            ]
        },
    )
    assert record.total_word_count == 1200

    # Attempting to finalize while chunks are PENDING fails with UnapprovedChunksRemainingError
    with pytest.raises(UnapprovedChunksRemainingError):
        service.finalize_human_gate(
            record.id,
            reviewer_user_id="user-helene",
            review_duration_ms=20000,
        )

    # Approve chunk 1 and co-edit chunk 2 (creates SHA-256 signature)
    c1 = service.decide_chunk(record.id, "sec-1", action="APPROVE", reviewer_user_id="user-helene")
    assert c1.status == "APPROVED"

    c2 = service.decide_chunk(
        record.id,
        "sec-2",
        action="CO_EDIT",
        reviewer_user_id="user-helene",
        co_edited_content=large_text_2 + " amendé par Hélène",
    )
    assert c2.status == "CO_EDITED"
    assert c2.human_anchor_signature_id is not None
    assert c2.human_anchor_sha256 is not None

    # Still blocked until Block 4 (Retained Hypotheses) is inspected
    with pytest.raises(UnapprovedChunksRemainingError):
        service.finalize_human_gate(
            record.id,
            reviewer_user_id="user-helene",
            review_duration_ms=20000,
        )

    service.inspect_briefing_hypotheses(record.id, reviewer_user_id="user-helene")

    # Fast approval (< 15 000 ms on > 1 000 words) without explicit confirmation triggers guard
    with pytest.raises(RubberStampingGuardTriggeredError):
        service.finalize_human_gate(
            record.id,
            reviewer_user_id="user-helene",
            review_duration_ms=4200,
            explicit_hypotheses_confirmation=False,
        )

    # Confirming hypotheses explicitly allows finalization and records fast_approval_warning=True
    finalized = service.finalize_human_gate(
        record.id,
        reviewer_user_id="user-helene",
        review_duration_ms=4200,
        explicit_hypotheses_confirmation=True,
    )
    assert finalized.status == "PASS"
    assert finalized.fast_approval_warning is True
    assert finalized.outbox_event_id is not None

    with pytest.raises(HumanGateNotFoundError):
        service.get_evaluation("non-existent-gate")


def test_api_human_gates_endpoints_and_alembic_0018() -> None:
    """Verify FastAPI Human Gate endpoints, observer guard (`HTTP 403`), and migration 0018."""
    app = create_app()
    client = TestClient(app)
    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    words_600 = " ".join(["validation"] * 600)

    eval_resp = client.post(
        "/api/v1/gates/human/evaluate?persona_key=marc",
        json={
            "workspace_id": ws_id,
            "run_id": "run-api-4-3",
            "step_execution_id": "step-api-4-3",
            "step_key": "step-prd",
            "policy": "mandatory_full",
            "artifact_payload": {
                "sections": [
                    {"chunk_key": "c1", "title": "Section 1", "content": words_600},
                    {"chunk_key": "c2", "title": "Section 2", "content": words_600},
                ]
            },
        },
    )
    assert eval_resp.status_code == 200, eval_resp.text
    gate_id = eval_resp.json()["evaluation"]["id"]

    # Unapproved chunks -> HTTP 422 ERR_UNAPPROVED_CHUNKS_REMAINING
    unapproved_resp = client.post(
        f"/api/v1/gates/human/{gate_id}/finalize?persona_key=marc",
        json={"review_duration_ms": 20000},
    )
    assert unapproved_resp.status_code == 422
    assert unapproved_resp.json()["error_code"] == "ERR_UNAPPROVED_CHUNKS_REMAINING"

    # Decide chunks & inspect hypotheses
    assert (
        client.post(
            f"/api/v1/gates/human/{gate_id}/chunks/c1/decide?persona_key=marc",
            json={"action": "APPROVE"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/gates/human/{gate_id}/chunks/c2/decide?persona_key=marc",
            json={"action": "CO_EDIT", "co_edited_content": words_600 + " signé"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/gates/human/{gate_id}/inspect-hypotheses?persona_key=marc"
        ).status_code
        == 200
    )

    # < 15s on > 1,000 words without confirmation -> 422 ERR_RUBBER_STAMPING_GUARD_TRIGGERED
    guard_resp = client.post(
        f"/api/v1/gates/human/{gate_id}/finalize?persona_key=marc",
        json={"review_duration_ms": 5000, "explicit_hypotheses_confirmation": False},
    )
    assert guard_resp.status_code == 422
    assert guard_resp.json()["error_code"] == "ERR_RUBBER_STAMPING_GUARD_TRIGGERED"

    # With explicit confirmation -> HTTP 200 PASS + fast_approval_warning=True
    pass_resp = client.post(
        f"/api/v1/gates/human/{gate_id}/finalize?persona_key=marc",
        json={"review_duration_ms": 5000, "explicit_hypotheses_confirmation": True},
    )
    assert pass_resp.status_code == 200
    assert pass_resp.json()["evaluation"]["status"] == "PASS"
    assert pass_resp.json()["evaluation"]["fast_approval_warning"] is True

    list_resp = client.get(f"/api/v1/gates/human/evaluations?workspace_id={ws_id}&persona_key=marc")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["evaluations"]) >= 1
    assert list_resp.json()["evaluations"][-1]["id"] == gate_id

    # READ_ONLY_OBSERVER blocked with HTTP 403 ERR_OBSERVER_MODE_READ_ONLY
    obs_resp = client.post(
        f"/api/v1/gates/human/{gate_id}/finalize?persona_key=claire",
        json={"review_duration_ms": 20000, "explicit_hypotheses_confirmation": True},
    )
    assert obs_resp.status_code == 403
    assert obs_resp.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # Verify Alembic migration 0018_story_4_3_chunk_approvals.py upgrade() and downgrade()
    mig_path = Path("infra/migrations/versions/0018_story_4_3_chunk_approvals.py")
    spec = importlib.util.spec_from_file_location("mig_0018", mig_path)
    assert spec is not None and spec.loader is not None
    mig_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig_mod)
    assert mig_mod.revision == "0018_story_4_3"
    assert mig_mod.down_revision == "0017_story_4_1"
    mock_op = MagicMock()
    mig_mod.op = mock_op
    mig_mod.upgrade()
    mig_mod.downgrade()
    assert mock_op.execute.call_count == 4
