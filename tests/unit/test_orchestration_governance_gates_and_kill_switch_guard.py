"""Unit tests for orchestration governance, adaptive human gates, and kill-switch rollback guard."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
from orcia_core.orchestration._internal._sql_autonomous_rollback import (
    restore_help_article_and_rollback_run_sql,
)
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions.models import UserIdentity
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.events import DomainEvent
from orcia_kernel.ids import new_uuid7_str


class _FakeMappingResult:
    def __init__(self, *, first_row: dict[str, Any] | None = None, scalar: Any = None) -> None:
        self._first = first_row
        self._scalar = scalar

    def mappings(self) -> _FakeMappingResult:
        return self

    def first(self) -> dict[str, Any] | None:
        return self._first

    def scalar_one_or_none(self) -> Any:
        return self._scalar

    def scalar(self) -> Any:
        return self._scalar


class _FakeKillSwitchConn:
    """Fake AsyncConnection simulating a `workflow_runs` row locked at `KILL_SWITCH_STOPPED`."""

    def __init__(self, *, run_id: str, workspace_id: str, contract_id: str) -> None:
        self.run_id = run_id
        self.workspace_id = workspace_id
        self.contract_id = contract_id
        self.executed_sql: list[str] = []

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeMappingResult:
        sql_text = str(stmt)
        self.executed_sql.append(sql_text)
        _ = params
        if "UPDATE workflow_runs" in sql_text:
            # Guard `AND status <> 'KILL_SWITCH_STOPPED'` prevents mutating KILL_SWITCH_STOPPED
            return _FakeMappingResult(first_row=None)
        if "SELECT id::text AS run_id" in sql_text and "FROM workflow_runs" in sql_text:
            return _FakeMappingResult(
                first_row={
                    "run_id": self.run_id,
                    "workspace_id": self.workspace_id,
                    "status": "KILL_SWITCH_STOPPED",
                }
            )
        if "FROM autonomy_contracts" in sql_text:
            return _FakeMappingResult(scalar=self.contract_id)
        if "FROM catalog_items" in sql_text and "HELP_ARTICLE" in sql_text:
            return _FakeMappingResult(
                first_row={
                    "resource_id": "help-processes-guide",
                    "version": "2.0.0",
                    "sha256": "b" * 64,
                    "cas_key": "cas/b",
                    "metadata_jsonb": {
                        "previous_version": "1.0.0",
                        "previous_sha256": "a" * 64,
                        "previous_cas_key": "cas/a",
                        "lang": "fr",
                        "pack_name": "core",
                        "bound_routes": ["/processes"],
                    },
                }
            )
        return _FakeMappingResult()


class _FakeAsyncEngine:
    def __init__(self, conn: _FakeKillSwitchConn) -> None:
        self._conn = conn

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[_FakeKillSwitchConn]:
        yield self._conn


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
async def test_kill_switch_stopped_status_preserved_during_sql_rollback() -> None:
    """Post-hoc rollback SQL must never overwrite `KILL_SWITCH_STOPPED` in `workflow_runs`."""
    run_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    contract_id = new_uuid7_str()
    conn = _FakeKillSwitchConn(run_id=run_id, workspace_id=ws_id, contract_id=contract_id)
    engine = _FakeAsyncEngine(conn)
    evt = DomainEvent(
        event_id=new_uuid7_str(),
        event_type="AutonomousArtifactRolledBack",
        aggregate_type="WorkflowRun",
        aggregate_id=run_id,
        run_id=run_id,
        workspace_id=ws_id,
        payload={"run_id": run_id, "restored_version": "1.0.0"},
        trace_id="0" * 32,
    )

    result = await restore_help_article_and_rollback_run_sql(
        engine,  # type: ignore[arg-type]
        run_id=run_id,
        reviewer_user_id=new_uuid7_str(),
        comment="Invalidation post-hoc après arrêt d'urgence",
        help_resource_id="help-processes-guide",
        contract_id=contract_id,
        event=evt,
    )

    assert result is not None
    assert result["status"] == "KILL_SWITCH_STOPPED"
    assert result["restored_version"] == "1.0.0"
    assert result["invalidated_redis_keys"]
    update_stmts = [s for s in conn.executed_sql if "UPDATE workflow_runs" in s]
    assert len(update_stmts) == 1
    assert "status <> 'KILL_SWITCH_STOPPED'" in update_stmts[0]
    audit_stmts = [s for s in conn.executed_sql if "INSERT INTO autonomous_post_hoc_audits" in s]
    assert len(audit_stmts) == 1

    invalid_res = await restore_help_article_and_rollback_run_sql(
        engine,  # type: ignore[arg-type]
        run_id="not-a-uuid",
        reviewer_user_id=new_uuid7_str(),
        comment=None,
        help_resource_id=None,
        contract_id=None,
        event=evt,
    )
    assert invalid_res is None


@pytest.mark.asyncio
async def test_sql_rollback_normal_run_updates_status_and_resolves_help_article() -> None:
    """Normal rollback without kill-switch transitions to ROLLED_BACK and resolves catalog item."""
    run_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    contract_id = new_uuid7_str()

    class _NormalRollbackConn(_FakeKillSwitchConn):
        async def execute(
            self, stmt: Any, params: dict[str, Any] | None = None
        ) -> _FakeMappingResult:
            sql_text = str(stmt)
            self.executed_sql.append(sql_text)
            _ = params
            if "UPDATE workflow_runs" in sql_text:
                return _FakeMappingResult(
                    first_row={
                        "run_id": self.run_id,
                        "workspace_id": self.workspace_id,
                        "status": "ROLLED_BACK",
                    }
                )
            if "SELECT resource_id" in sql_text and "FROM catalog_items" in sql_text:
                return _FakeMappingResult(scalar="help-auto-1")
            if "FROM autonomy_contracts" in sql_text:
                return _FakeMappingResult(scalar=None)
            return await super().execute(stmt, params)

    conn = _NormalRollbackConn(run_id=run_id, workspace_id=ws_id, contract_id=contract_id)
    engine = _FakeAsyncEngine(conn)
    evt = DomainEvent(
        event_id=new_uuid7_str(),
        event_type="AutonomousArtifactRolledBack",
        aggregate_type="WorkflowRun",
        aggregate_id=run_id,
        run_id=run_id,
        workspace_id=ws_id,
        payload={"run_id": run_id, "restored_version": "1.0.0"},
        trace_id="0" * 32,
    )
    res = await restore_help_article_and_rollback_run_sql(
        engine,  # type: ignore[arg-type]
        run_id=run_id,
        reviewer_user_id=new_uuid7_str(),
        comment="Rollback standard",
        help_resource_id=None,
        contract_id=None,
        event=evt,
    )
    assert res is not None
    assert res["status"] == "ROLLED_BACK"
    assert res["help_resource_id"] == "help-auto-1"


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


@pytest.mark.asyncio
async def test_gate_parent_resolution_edge_cases_and_signature_guards() -> None:
    """Verify UUID coercion, empty-DB parent creation, and short-chunk signature guards."""
    from orcia_core.gates._internal._sql_gate_parents import (
        coerce_gate_uuid,
        ensure_chunk_anchor_signature,
        ensure_gate_parents,
        resolve_gate_user_id,
    )

    assert coerce_gate_uuid(None) != coerce_gate_uuid(" ")
    assert coerce_gate_uuid("ws-custom-slug") == coerce_gate_uuid("ws-custom-slug")

    class _EmptyParentConn:
        def __init__(self) -> None:
            self.org_inserted = False
            self.wf_inserted = False

        async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> Any:
            _ = params
            sql = str(stmt)

            class _Res:
                def __init__(self, first_val: Any = None, scalar_val: Any = None) -> None:
                    self._first = first_val
                    self._scalar = scalar_val

                def first(self) -> Any:
                    return self._first

                def scalar_one_or_none(self) -> Any:
                    return self._scalar

                def scalar_one(self) -> Any:
                    return self._scalar

            if "INSERT INTO org_units" in sql:
                self.org_inserted = True
            elif "FROM org_units" in sql:
                val = "0192c4e0-0000-7000-8000-000000000101" if self.org_inserted else None
                return _Res(scalar_val=val)
            elif "INSERT INTO workflow_definitions" in sql:
                self.wf_inserted = True
            elif "FROM workflow_definitions" in sql:
                val = ("0195f000-0000-7000-8000-000000000602",) if self.wf_inserted else None
                return _Res(first_val=val, scalar_val=val[0] if val else None)
            elif "SELECT id::text FROM step_executions WHERE id =" in sql:
                return _Res(scalar_val=None)
            elif "SELECT id::text FROM step_executions" in sql:
                return _Res(scalar_val=new_uuid7_str())
            return _Res(first_val=None, scalar_val=None)

    conn = _EmptyParentConn()
    assert await resolve_gate_user_id(conn, "  ") is None  # type: ignore[arg-type]
    ws_id, run_id, step_id = await ensure_gate_parents(
        conn,  # type: ignore[arg-type]
        workspace_id="ws-non-uuid",
        run_id="run-non-uuid",
        step_execution_id="step-non-uuid",
        step_key="step-arch",
    )
    assert ws_id and run_id and step_id
    assert (
        await ensure_chunk_anchor_signature(
            conn,  # type: ignore[arg-type]
            signature_id=None,
            workspace_id=ws_id,
            run_id=run_id,
            step_execution_id=step_id,
            step_key="step-arch",
            chunk_key="sec-1",
            content_markdown="Trop court",
            content_sha256=None,
            reviewer_user_id=None,
        )
        is None
    )
    assert (
        await ensure_chunk_anchor_signature(
            conn,  # type: ignore[arg-type]
            signature_id="sig-short",
            workspace_id=ws_id,
            run_id=run_id,
            step_execution_id=step_id,
            step_key="step-arch",
            chunk_key="sec-1",
            content_markdown="Trop court",
            content_sha256=None,
            reviewer_user_id=None,
        )
        is None
    )
    assert (
        await ensure_chunk_anchor_signature(
            conn,  # type: ignore[arg-type]
            signature_id="sig-no-user",
            workspace_id=ws_id,
            run_id=run_id,
            step_execution_id=step_id,
            step_key="step-arch",
            chunk_key="sec-1",
            content_markdown="Contenu suffisamment long dépassant largement trente caractères.",
            content_sha256=None,
            reviewer_user_id="unknown-user",
        )
        is None
    )


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
