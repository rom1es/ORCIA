"""Unit tests for `bounded_workflow_v2`, HITL signals, and `SqlWorkflowDefinitionsV2Store`.

Validates:
- `SqlWorkflowDefinitionsV2Store` memory fallback, SQL session path, and `strict_sql` mode.
- `run_bounded_workflow_v2` in `EXTERNAL_DELEGATED_GATE` and multi-step `NATIVE_ORCIA` HITL modes.
- `apply_hitl_signal_to_run` across `WAITING_EXTERNAL_GATE`, `WAITING_SUBSTEP_HITL` (`AMEND_DIFF`,
  `REJECT_RETRY_SUBSTEP`, `APPROVE` with `write_preview_required`), `SUSPEND_SLA`, and
  `REJECT_AND_LOOP` (both `DETERMINISTIC_DBOS` and `NON_DETERMINISTIC` goal re-entry).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from orcia_connectors.bounded_workflow_v2 import (
    HitlSignalPayload,
    apply_hitl_signal_to_run,
    run_bounded_workflow_v2,
    run_bounded_workflow_v2_async,
)
from orcia_core.agents.reflexive_schemas import ProcessOrchestrationType
from orcia_core.storage.claim_check import ClaimCheckStorageService
from orcia_core.workflows import SqlWorkflowDefinitionsV2Store
from orcia_core.workflows.schemas_v2 import (
    DeterministicSubStepSpec,
    ExecutionMode,
    WorkflowDefinitionV2,
    WorkflowLifecycleStatus,
)


async def test_sql_workflow_definitions_v2_store_session_and_fallback_paths() -> None:
    """Verify `SqlWorkflowDefinitionsV2Store` memory fallback, SQL session path, and strict mode."""
    rows_storage: list[tuple[str]] = []
    fail_mode = False

    class _FakeResult:
        def __init__(self, rows: list[tuple[str]]) -> None:
            self._rows = rows

        def fetchall(self) -> list[tuple[str]]:
            return list(self._rows)

    class _FakeSession:
        async def __aenter__(self) -> _FakeSession:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def execute(self, _stmt: object, params: dict[str, Any] | None = None) -> _FakeResult:
            if fail_mode:
                raise RuntimeError("simulated_sql_outage")
            if params and "spec_jsonb" in params:
                rows_storage.clear()
                rows_storage.append((str(params["spec_jsonb"]),))
            return _FakeResult(rows_storage)

        async def commit(self) -> None:
            return None

    wf = WorkflowDefinitionV2(
        id="wf-mem-01",
        slug="wf-mem-01",
        title="Processus memoire",
        version="1.1.0-draft",
        status=WorkflowLifecycleStatus.DRAFT,
        pack_id="orcia-pack-docs",
        orchestration_type=ProcessOrchestrationType.NON_DETERMINISTIC,
        reflexive_objective="Objectif test",
        allowed_delegate_agents=["redacteur-documentation-orcia"],
    )

    store_mem = SqlWorkflowDefinitionsV2Store(session_maker=None)
    await store_mem.upsert_workflow(wf)
    assert len(await store_mem.list_persisted_workflows()) == 1

    store_sql = SqlWorkflowDefinitionsV2Store(
        session_maker=lambda: _FakeSession()  # type: ignore[arg-type,return-value]
    )
    await store_sql.upsert_workflow(wf)
    persisted = await store_sql.list_persisted_workflows()
    assert len(persisted) == 1
    assert json.loads(rows_storage[0][0])["orchestration_type"] == "non_deterministic"

    fail_mode = True
    assert len(await store_sql.list_persisted_workflows()) == 1

    strict_store = SqlWorkflowDefinitionsV2Store(
        session_maker=lambda: _FakeSession(),  # type: ignore[arg-type,return-value]
        strict_sql=True,
    )
    with pytest.raises(RuntimeError, match="simulated_sql_outage"):
        await strict_store.upsert_workflow(wf)
    with pytest.raises(RuntimeError, match="simulated_sql_outage"):
        await strict_store.list_persisted_workflows()


async def test_bounded_workflow_hitl_signals_external_gate_and_return_loops() -> None:
    """Verify external gate, multi-step HITL, write-preview token, SLA suspend, and return loops."""
    storage = ClaimCheckStorageService()

    # 1. External delegated gate + WAITING_EXTERNAL_GATE -> WAITING_FINAL_ANCHOR -> APPROVE
    ext_wf = WorkflowDefinitionV2(
        id="wf-ext",
        slug="wf-ext",
        title="Processus Externe",
        pack_id="pack-demo",
        execution_mode=ExecutionMode.EXTERNAL_DELEGATED_GATE,
    )
    ext_state = run_bounded_workflow_v2(ext_wf, run_id="run-ext-1", storage=storage)
    assert ext_state.status == "WAITING_EXTERNAL_GATE"
    ext_state = apply_hitl_signal_to_run(
        ext_wf,
        ext_state,
        HitlSignalPayload(action="APPROVE", actor_id="marc"),
        storage=storage,
    )
    assert ext_state.status == "WAITING_FINAL_ANCHOR"
    ext_state = apply_hitl_signal_to_run(
        ext_wf,
        ext_state,
        HitlSignalPayload(action="APPROVE", actor_id="marc"),
        storage=storage,
    )
    assert ext_state.status == "COMPLETED_APPROVED"

    # 2. Multi-step NATIVE_ORCIA HITL: REJECT_RETRY_SUBSTEP, AMEND_DIFF + write_preview, SUSPEND_SLA
    native_wf = WorkflowDefinitionV2(
        id="wf-hitl",
        slug="wf-hitl",
        title="Processus Jalons HITL",
        pack_id="pack-demo",
        sub_steps=[
            DeterministicSubStepSpec(
                id="s1",
                name="Etape 1",
                short_label="E1",
                trigger_condition_label="Start",
                role_description="R1",
                instruction_prompt_or_ref="p1",
                output_description="O1",
                requires_human_checkpoint=True,
                write_preview_required=True,
                checkpoint_label="CP1",
            ),
            DeterministicSubStepSpec(
                id="s2",
                name="Etape 2",
                short_label="E2",
                trigger_condition_label="Apres E1",
                role_description="R2",
                instruction_prompt_or_ref="p2",
                output_description="O2",
                requires_human_checkpoint=False,
                checkpoint_label="CP2",
            ),
        ],
    )
    state = await run_bounded_workflow_v2_async(
        native_wf,
        run_id="run-hitl-1",
        auto_approve_checkpoints=False,
        storage=storage,
    )
    assert state.status == "WAITING_SUBSTEP_HITL"

    # Retry substep 1
    state = apply_hitl_signal_to_run(
        native_wf,
        state,
        HitlSignalPayload(
            action="REJECT_RETRY_SUBSTEP",
            actor_id="marc",
            correction_remarks="Ajouter plus de details",
        ),
        storage=storage,
    )
    assert state.iteration == 2

    # Amend diff on substep 1 (advances to substep 2)
    state = apply_hitl_signal_to_run(
        native_wf,
        state,
        HitlSignalPayload(
            action="AMEND_DIFF",
            actor_id="marc",
            amended_markdown="# Amendement\n\nContenu corrige.",
        ),
        storage=storage,
    )
    assert state.current_sub_step_index == 1
    assert state.status == "WAITING_SUBSTEP_HITL"

    # Approve substep 2 -> WAITING_FINAL_ANCHOR -> AMEND_DIFF on final anchor
    state = apply_hitl_signal_to_run(
        native_wf,
        state,
        HitlSignalPayload(action="APPROVE", actor_id="marc"),
        storage=storage,
    )
    assert state.status == "WAITING_FINAL_ANCHOR"

    state_am = apply_hitl_signal_to_run(
        native_wf,
        state.model_copy(deep=True),
        HitlSignalPayload(
            action="AMEND_DIFF",
            actor_id="marc",
            amended_markdown="# Final\n\nLivrable amende.",
        ),
        storage=storage,
    )
    assert state_am.status == "COMPLETED_APPROVED"

    state_sla = apply_hitl_signal_to_run(
        native_wf,
        state.model_copy(deep=True),
        HitlSignalPayload(action="SUSPEND_SLA", actor_id="marc", correction_remarks="Attente info"),
        storage=storage,
    )
    assert state_sla.status == "SLA_SUSPENDED"

    # REJECT_AND_LOOP on milestone-driven vs goal-driven state
    state_loop_ms = apply_hitl_signal_to_run(
        native_wf,
        state.model_copy(deep=True),
        HitlSignalPayload(
            action="REJECT_AND_LOOP",
            actor_id="marc",
            target_step_num="01",
            target_sub_step_id="s1",
            correction_remarks="Revoir cadrage",
        ),
        storage=storage,
    )
    assert state_loop_ms.status == "RETURN_LOOP_TRIGGERED"
    assert len(state_loop_ms.sub_step_records) >= 3

    goal_state = state.model_copy(deep=True)
    goal_state.orchestration_type = ProcessOrchestrationType.NON_DETERMINISTIC
    state_loop_goal = apply_hitl_signal_to_run(
        native_wf,
        goal_state,
        HitlSignalPayload(
            action="REJECT_AND_LOOP",
            actor_id="marc",
            correction_remarks="Approfondir la synthese",
        ),
        storage=storage,
    )
    assert state_loop_goal.status == "RETURN_LOOP_TRIGGERED"
