"""Unit tests for orchestration governance, adaptive human gates, and kill-switch rollback guard."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from orcia_connectors.jira_actions import MultiProjectJiraStagedActionService
from orcia_core.gates._internal._sql_gate_mappers import row_to_gate_entity, row_to_human_record
from orcia_core.gates.deterministic import DeterministicGateService
from orcia_core.gates.errors import (
    RubberStampingGuardTriggeredError,
    UnapprovedChunksRemainingError,
)
from orcia_core.gates.models import DeterministicGateInput
from orcia_core.orchestration import (
    build_default_orchestration_setup_service,
    register_default_step_executors,
)
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions.models import UserIdentity
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.ids import new_uuid7_str


def _make_admin_user() -> UserIdentity:
    return UserIdentity(
        id="0195f000-0000-7000-8000-000000000201",
        email="lead.arch@orcia.ia",
        display_name="Lead Architecture",
        auth_mode="LOCAL",
        human_profile_archetype="LEAD_DEV_ARCH",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000001",
        roles=("PLATFORM_ADMIN",),
    )


@pytest.mark.asyncio
async def test_autonomous_supervision_preserves_kill_switch_after_emergency_stop_and_rollback() -> (
    None
):
    """Emergency stop followed by invalidate_and_restore keeps `KILL_SWITCH_STOPPED` intact."""
    svc = AutonomousSupervisionService()
    run_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    contract_id = new_uuid7_str()
    actor_id = new_uuid7_str()

    await svc.register_autonomous_run(
        run_id=run_id,
        workspace_id=ws_id,
        workflow_id="wf-01-qualification-prd",
        contract_id=contract_id,
        status="COMMITTED_AUTONOMOUS",
        cost_usd=Decimal("0.040000"),
        force_post_hoc_sample=True,
    )
    stop_outcome = await svc.emergency_stop(
        run_id=run_id,
        actor_user_id=actor_id,
        reason="Arrêt immédiat opérateur",
        suspend_trigger=False,
    )
    assert stop_outcome.status == "KILL_SWITCH_STOPPED"
    assert await svc.is_run_stopped(run_id) is True

    rollback_outcome = await svc.invalidate_and_restore(
        run_id=run_id,
        actor_user_id=actor_id,
        comment="Restauration artefact @v(N-1) sans lever l'arrêt d'urgence",
    )
    assert rollback_outcome.status == "KILL_SWITCH_STOPPED"
    runs = await svc.list_autonomous_runs(workspace_id=ws_id)
    assert len(runs) == 1
    assert runs[0].run_status == "KILL_SWITCH_STOPPED"
    assert runs[0].post_hoc_status == "INVALIDATED_ROLLED_BACK"


def test_human_anchor_upstream_challenge_run_lock_and_append_only_replay() -> None:
    """Verify run-lock stability, human anchor SHA-256, upstream challenge & append-only replay."""
    register_default_step_executors(llm_gateway=DeterministicCassetteLLM())
    auth_svc = build_default_auth_and_org_service(seed_reference_personas=True)
    orch_svc = build_default_orchestration_setup_service(evaluator=auth_svc.evaluator)
    admin = _make_admin_user()
    ws_id = "0192c4e0-0000-7000-8000-000000000201"

    run = orch_svc.instantiate_workflow_run(
        admin,
        workflow_uri="orcia://workflows/claims-engineering-delivery",
        workspace_id=ws_id,
    )
    assert run.run_lock.manifest_sha256
    assert run.run_lock.workflow_sha256
    wf = orch_svc.engine._get_workflow(run.workflow_uri)
    orch_svc.engine.initialize_run_steps(run, wf)

    sig = orch_svc.engine.anchors_and_arbitration.sign_human_anchor(
        admin,
        run_id=run.id,
        step_key="frame-architecture-intent",
        section_key="human_architecture_intent",
        content_text=(
            "Isolation hexagonale stricte entre domaine métier, ports et adaptateurs PG18."
        ),
        signature_text="Lead Architecture",
        author_type="HUMAN",
    )
    assert sig.char_length >= 30
    assert len(sig.content_sha256) == 64

    _, snap_before = orch_svc.engine.execute_step(
        admin,
        run_id=run.id,
        step_key="frame-architecture-intent",
        commit_immediately=True,
        require_human_anchor=True,
    )
    assert snap_before is not None

    preview = orch_svc.engine.challenge_and_replay.preview_upstream_challenge(
        run_id=run.id,
        challenger_step_key="delegate-remediation-subworkflow",
        target_upstream_step_key="frame-architecture-intent",
        challenged_section_key="human_architecture_intent",
        challenge_reason="Contrainte partenaire v3 imposant une fenêtre maximale de 15 minutes.",
        target_profile_archetype="PM_BUSINESS",
    )
    assert "frame-architecture-intent" in preview.invalidated_downstream_step_keys

    challenge, _ = orch_svc.engine.challenge_and_replay.submit_upstream_challenge(
        admin,
        run_id=run.id,
        challenger_step_key="delegate-remediation-subworkflow",
        target_upstream_step_key="frame-architecture-intent",
        challenged_section_key="human_architecture_intent",
        challenge_reason="Contrainte partenaire v3 imposant une fenêtre maximale de 15 minutes.",
        target_profile_archetype="PM_BUSINESS",
    )
    assert challenge.status == "OPEN"

    replay_res = orch_svc.engine.challenge_and_replay.replay_from_step(
        admin,
        run_id=run.id,
        step_key="frame-architecture-intent",
    )
    assert replay_res.run_lock_sha256 == run.run_lock.manifest_sha256
    assert snap_before.id in replay_res.superseded_snapshot_ids
    assert len(replay_res.new_active_snapshot_ids) >= 1

    all_snapshots = orch_svc.engine.blackboard.list_all_snapshots(run.id)
    assert len(all_snapshots) >= 2
    assert orch_svc.engine.blackboard.get_effective_branch_status(snap_before.id) == "SUPERSEDED"
    active_ids = {s.id for s in orch_svc.engine.blackboard.get_active_snapshots(run.id)}
    assert snap_before.id not in active_ids
    for active_id in replay_res.new_active_snapshot_ids:
        assert active_id in active_ids
        assert orch_svc.engine.blackboard.get_effective_branch_status(active_id) == "ACTIVE"


def test_adaptive_human_gate_fast_approval_guard_and_jira_staged_execution() -> None:
    """Verify chunked approval, <15s anti-rubber-stamping guard, and Jira Staged execution."""
    det_service = DeterministicGateService()
    human_service = det_service.human_service
    ws_id = new_uuid7_str()
    run_id = new_uuid7_str()
    step_id = new_uuid7_str()
    reviewer_id = new_uuid7_str()

    det_eval = det_service.evaluate_deterministic_gate(
        DeterministicGateInput(
            workspace_id=ws_id,
            run_id=run_id,
            step_execution_id=step_id,
            step_key="step-architecture-gate",
            artifact_payload={"summary": "Contrat OpenAPI validé."},
            required_sections=("summary",),
        )
    )
    assert det_eval.status == "PASS"

    large_text = " ".join(["conformite"] * 600)
    record = human_service.evaluate_human_gate(
        workspace_id=ws_id,
        run_id=run_id,
        step_execution_id=step_id,
        step_key="step-architecture-gate",
        policy="mandatory_full",
        artifact_payload={
            "sections": [
                {"chunk_key": "sec-1", "title": "Architecture", "content": large_text},
                {"chunk_key": "sec-2", "title": "Sécurité", "content": large_text},
            ]
        },
    )
    assert record.status == "PENDING_HUMAN_REVIEW"
    assert record.total_word_count > 1000

    with pytest.raises(UnapprovedChunksRemainingError):
        human_service.finalize_human_gate(
            record.id,
            reviewer_user_id=reviewer_id,
            review_duration_ms=20000,
            explicit_hypotheses_confirmation=False,
        )

    human_service.inspect_briefing_hypotheses(record.id, reviewer_user_id=reviewer_id)
    human_service.decide_chunk(record.id, "sec-1", action="APPROVE", reviewer_user_id=reviewer_id)
    co_edited = human_service.decide_chunk(
        record.id,
        "sec-2",
        action="CO_EDIT",
        reviewer_user_id=reviewer_id,
        co_edited_content=f"{large_text} verifie",
    )
    assert co_edited.status == "CO_EDITED"
    assert co_edited.human_anchor_sha256 is not None

    with pytest.raises(RubberStampingGuardTriggeredError):
        human_service.finalize_human_gate(
            record.id,
            reviewer_user_id=reviewer_id,
            review_duration_ms=3200,
            explicit_hypotheses_confirmation=False,
        )

    finalized = human_service.finalize_human_gate(
        record.id,
        reviewer_user_id=reviewer_id,
        review_duration_ms=3200,
        explicit_hypotheses_confirmation=True,
    )
    assert finalized.status == "PASS"
    assert finalized.fast_approval_warning is True

    jira_service = MultiProjectJiraStagedActionService()
    staged = jira_service.stage_action(
        workspace_id=ws_id,
        run_id=run_id,
        step_execution_id=step_id,
        project_alias="jira:product",
        action_type="transition_issue",
        issue_key="PAYBUILD-101",
        target_transition="Submit for Review",
        summary="Soumettre PAYBUILD-101 après PASS de Gate",
        fields_payload={"pr_url": "https://git.orcia.local/pr/101"},
    )
    assert staged.status == "STAGED"
    executed = jira_service.commit_staged_action_on_gate_pass(
        staged_action_id=staged.staged_action_id,
        gate_status=finalized.status,
        run_lock_sha256="sha256:runlock-verified",
    )
    assert executed.status == "EXECUTED"

    # Markdown ## splitting, risk_or_exception_based auto-pass, sampling & CHALLENGE path
    auto_pass = human_service.evaluate_human_gate(
        workspace_id=ws_id,
        run_id=run_id,
        step_execution_id=step_id,
        step_key="step-auto",
        policy="risk_or_exception_based",
        artifact_payload={"content": "## Résumé\nContenu validé.\n## Détails\nConforme."},
        deterministic_status="PASS",
        agentic_score=0.95,
    )
    assert auto_pass.status == "PASS"
    assert auto_pass.auto_passed is True

    sampled = human_service.evaluate_human_gate(
        workspace_id=ws_id,
        run_id=run_id,
        step_execution_id=step_id,
        step_key="step-sampled",
        policy="sampling",
        artifact_payload={"content": "## Section A\nÀ revoir."},
        sampling_override=True,
    )
    assert sampled.status == "PENDING_HUMAN_REVIEW"
    challenged = human_service.decide_chunk(
        sampled.id,
        "section-1",
        action="CHALLENGE",
        reviewer_user_id=reviewer_id,
        challenge_reason="Contradiction amont",
    )
    assert challenged.status == "CHALLENGED"
    assert sampled.status == "FAIL"


def test_sql_gate_row_mappers_preserve_metadata_and_chunk_hashes() -> None:
    """Verify PG18 row mappers reconstruct GateEvaluationEntity and HumanGateEvaluationRecord."""
    gate_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    run_id = new_uuid7_str()
    step_id = new_uuid7_str()
    now = datetime.now(UTC)

    det_row = {
        "id": gate_id,
        "workspace_id": ws_id,
        "run_id": run_id,
        "step_execution_id": step_id,
        "step_key": "step-arch",
        "gate_type": "DETERMINISTIC",
        "sandbox_tier": "TIER_1_WASM",
        "status": "FAIL",
        "score": 0.2,
        "schema_validation_passed": False,
        "ontology_axioms_passed": True,
        "pattern_drift_passed": False,
        "pattern_drift_findings_jsonb": json.dumps(
            [
                {
                    "rule_id": "DRIFT-01",
                    "forbidden_symbol": "requests",
                    "severity": "HIGH",
                    "message": "Forbidden sync client",
                }
            ]
        ),
        "lens_findings_jsonb": "[]",
        "briefing_4blocks_jsonb": json.dumps(
            {
                "_det_meta": {
                    "missing_sections": ["security"],
                    "violated_axioms": [],
                    "sandbox_exit_code": 1,
                    "sandbox_stderr": "drift",
                }
            }
        ),
        "evaluator_model_id": None,
        "duration_ms": 12,
        "review_duration_ms": 0,
        "fast_approval_warning": False,
        "outbox_event_id": None,
        "evaluated_at": now,
    }
    entity = row_to_gate_entity(det_row)
    assert entity.status == "FAIL"
    assert entity.missing_sections == ("security",)
    assert entity.pattern_drift_findings[0].forbidden_symbol == "requests"
    assert entity.sandbox_exit_code == 1

    human_row = {
        "id": gate_id,
        "workspace_id": ws_id,
        "run_id": run_id,
        "step_execution_id": step_id,
        "step_key": "step-arch",
        "status": "PASS",
        "score": 1.0,
        "schema_validation_passed": True,
        "ontology_axioms_passed": True,
        "briefing_4blocks_jsonb": json.dumps(
            {
                "_human_gate_meta": {
                    "policy": "mandatory_full",
                    "auto_passed": False,
                    "deterministic_status": "PASS",
                    "agentic_score": 0.94,
                    "ontology_conflicts": 0,
                    "stale_warnings": 0,
                    "total_word_count": 1200,
                    "hypotheses_block_inspected": True,
                    "reviewer_user_id": "user-1",
                    "chunk_sha256_map": {"sec-1": "a" * 64},
                }
            }
        ),
        "review_duration_ms": 3200,
        "fast_approval_warning": True,
        "outbox_event_id": None,
        "evaluated_at": now,
    }
    chunk_rows = [
        {
            "id": new_uuid7_str(),
            "gate_evaluation_id": gate_id,
            "workspace_id": ws_id,
            "run_id": run_id,
            "step_execution_id": step_id,
            "chunk_key": "sec-1",
            "section_title": "Section 1",
            "section_index": 0,
            "content_markdown": "Contenu co-édité",
            "word_count": 1200,
            "human_authored_required": True,
            "status": "CO_EDITED",
            "reviewer_user_id": "user-1",
            "human_anchor_signature_id": new_uuid7_str(),
            "challenge_reason": None,
            "reviewed_at": now,
        }
    ]
    human_record = row_to_human_record(human_row, chunk_rows)
    assert human_record.fast_approval_warning is True
    assert human_record.hypotheses_block_inspected is True
    assert human_record.chunks[0].status == "CO_EDITED"
    assert human_record.chunks[0].human_anchor_sha256 == "a" * 64


def test_gate_parent_uuid_coercion() -> None:
    """Verify deterministic UUID coercion for gate workspace/run identifiers."""
    from orcia_core.gates._internal._sql_gate_parents import coerce_gate_uuid

    assert coerce_gate_uuid(None) != coerce_gate_uuid(" ")
    assert coerce_gate_uuid("ws-custom-slug") == coerce_gate_uuid("ws-custom-slug")


@pytest.mark.asyncio
async def test_orchestration_sql_hydration_fallbacks_and_error_resilience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify UOW fallback resolution and resilient hydration when PG18 reads fail."""
    from types import SimpleNamespace

    from starlette.requests import Request

    from orcia_api.routers._orchestration_sql_hydration import (
        hydrate_orchestration_runs_from_sql,
        hydrate_run_from_sql_if_missing,
        resolve_optional_dbos_uow,
    )

    app_empty = SimpleNamespace(state=SimpleNamespace())
    req_empty = Request({"type": "http", "app": app_empty, "headers": [], "path": "/"})
    assert resolve_optional_dbos_uow(req_empty) is None

    auth_svc = build_default_auth_and_org_service(seed_reference_personas=False)
    orch_svc = build_default_orchestration_setup_service(evaluator=auth_svc.evaluator)
    await hydrate_orchestration_runs_from_sql(req_empty, orch_svc)

    app_ds = SimpleNamespace(
        state=SimpleNamespace(dbos_datasource=SimpleNamespace(engine=object()))
    )
    req_ds = Request({"type": "http", "app": app_ds, "headers": [], "path": "/"})
    assert resolve_optional_dbos_uow(req_ds) is not None

    app_eng = SimpleNamespace(state=SimpleNamespace(db_engine=object(), session_maker=None))
    req_eng = Request({"type": "http", "app": app_eng, "headers": [], "path": "/"})
    assert resolve_optional_dbos_uow(req_eng) is not None

    async def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("pg-offline")

    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.list_workflow_runs_with_locks_sql", _boom
    )
    await hydrate_orchestration_runs_from_sql(req_ds, orch_svc)
    await hydrate_run_from_sql_if_missing(req_ds, orch_svc, new_uuid7_str())

    async def _empty_runs(*_args: Any, **_kwargs: Any) -> tuple[Any, ...]:
        return ()

    monkeypatch.setattr(
        "orcia_api.routers._orchestration_sql_hydration.list_workflow_runs_with_locks_sql",
        _empty_runs,
    )
    await hydrate_run_from_sql_if_missing(req_ds, orch_svc, new_uuid7_str())
