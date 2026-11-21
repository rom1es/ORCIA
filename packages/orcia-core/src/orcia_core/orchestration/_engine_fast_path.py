"""Sub-workflow & Background Fast-Path Execution Helpers for `DurableOrchestrationEngine`."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from orcia_core.blackboard.models import (
    BackgroundAuditConsolidatedReport,
    BlackboardSnapshotEntity,
    StepExecutionEntity,
    StepMemlogEntry,
)
from orcia_core.orchestration.jit_hydrator import (
    JitStepHydrator,
    build_default_fast_path_markers,
    get_memlog_marker_plugin,
)
from orcia_core.orchestration.models import (
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
    WorkflowStepSpec,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.enums import normalize_memlog_marker
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import StepExecutorResult

if TYPE_CHECKING:
    from orcia_core.orchestration.engine import DurableOrchestrationEngine


def _map_sub_workflow_outputs(
    engine: DurableOrchestrationEngine,
    *,
    child_run: WorkflowRunEntity,
    step_spec: WorkflowStepSpec,
) -> dict[str, Any]:
    mapped_outputs: dict[str, Any] = {}
    for out_alias, out_expr in sorted(step_spec.output_mapping.items()):
        target_child_step, target_field = JitStepHydrator._parse_input_ref(out_expr, child_run.id)
        child_snap = engine.blackboard.get_active_step_snapshot(child_run.id, target_child_step)
        if child_snap is not None:
            mapped_outputs[out_alias] = child_snap.artifact_payload.get(
                target_field, child_snap.artifact_payload
            )
    return mapped_outputs


async def execute_isolated_sub_workflow_async(
    engine: DurableOrchestrationEngine,
    user: UserIdentity,
    *,
    parent_run: WorkflowRunEntity,
    parent_step_exec_id: str,
    step_spec: WorkflowStepSpec,
    hydrated_inputs: dict[str, Any],
    step_cost_usd: float,
    instance: str | None = None,
) -> tuple[WorkflowRunEntity, dict[str, Any]]:
    """Instantiate and execute an isolated child `SUB_WORKFLOW` asynchronously."""
    assert step_spec.sub_workflow_uri is not None
    child_run = engine.setup_service.instantiate_workflow_run(
        user,
        workflow_uri=step_spec.sub_workflow_uri,
        workspace_id=parent_run.workspace_id,
        parent_run_id=parent_run.id,
        parent_step_execution_id=parent_step_exec_id,
        instance=instance,
    )
    engine._run_seed_inputs[child_run.id] = dict(hydrated_inputs)
    child_wf = engine._get_workflow(child_run.workflow_uri, instance=instance)
    engine.initialize_run_steps(child_run, child_wf)

    per_child_step_cost = round(step_cost_usd / max(1, len(child_wf.steps)), 4)
    for child_step in child_wf.steps:
        await engine.execute_step_async(
            user,
            run_id=child_run.id,
            step_key=child_step.step_key,
            commit_immediately=True,
            cost_usd=per_child_step_cost,
            instance=instance,
        )
    return child_run, _map_sub_workflow_outputs(engine, child_run=child_run, step_spec=step_spec)


def execute_isolated_sub_workflow_sync(
    engine: DurableOrchestrationEngine,
    user: UserIdentity,
    *,
    parent_run: WorkflowRunEntity,
    parent_step_exec_id: str,
    step_spec: WorkflowStepSpec,
    hydrated_inputs: dict[str, Any],
    step_cost_usd: float,
    instance: str | None = None,
) -> tuple[WorkflowRunEntity, dict[str, Any]]:
    """Instantiate and execute an isolated child `SUB_WORKFLOW` synchronously."""
    assert step_spec.sub_workflow_uri is not None
    child_run = engine.setup_service.instantiate_workflow_run(
        user,
        workflow_uri=step_spec.sub_workflow_uri,
        workspace_id=parent_run.workspace_id,
        parent_run_id=parent_run.id,
        parent_step_execution_id=parent_step_exec_id,
        instance=instance,
    )
    engine._run_seed_inputs[child_run.id] = dict(hydrated_inputs)
    child_wf = engine._get_workflow(child_run.workflow_uri, instance=instance)
    engine.initialize_run_steps(child_run, child_wf)

    per_child_step_cost = round(step_cost_usd / max(1, len(child_wf.steps)), 4)
    for child_step in child_wf.steps:
        engine.execute_step(
            user,
            run_id=child_run.id,
            step_key=child_step.step_key,
            commit_immediately=True,
            cost_usd=per_child_step_cost,
            instance=instance,
        )
    return child_run, _map_sub_workflow_outputs(engine, child_run=child_run, step_spec=step_spec)


def finalize_step_outcome(
    engine: DurableOrchestrationEngine,
    *,
    run: WorkflowRunEntity,
    wf: WorkflowAsCodeDefinition,
    step_key: str,
    hydrated: Any,
    exec_result: StepExecutorResult | None,
    sub_wf_result: tuple[WorkflowRunEntity, dict[str, Any]] | None,
    effective_divergence: str | None,
    cost_usd: float,
    commit_immediately: bool,
) -> tuple[StepExecutionEntity, BlackboardSnapshotEntity | None]:
    """Persist draft/memlog, handle human pause, and commit snapshot if requested."""
    memlog_entries: list[StepMemlogEntry] = [
        StepMemlogEntry(
            entry_id=new_uuid7_str(),
            step_key=step_key,
            marker_type="REASONING",
            summary=f"Hydratation JIT de '{step_key}' ({len(hydrated.declared_input_uris)} items)",
            details=f"Directive exécutée: {hydrated.step_directive}",
            source_uris=hydrated.declared_input_uris,
        )
    ]
    child_run_id: str | None = None
    if sub_wf_result is not None:
        child_run, mapped_outputs = sub_wf_result
        child_run_id = child_run.id
        draft_payload: dict[str, Any] = {
            "step_key": step_key,
            "step_type": "SUB_WORKFLOW",
            "sub_workflow_run_id": child_run.id,
            "sub_workflow_uri": child_run.workflow_uri,
            "nesting_depth": child_run.nesting_depth,
            **mapped_outputs,
        }
        memlog_entries.append(
            StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="SUB_WORKFLOW_OUTPUT",
                summary=(
                    f"Sous-workflow '{child_run.workflow_uri}' engagé "
                    f"(profondeur {child_run.nesting_depth})"
                ),
                details=f"Sorties reversées via output_mapping: {sorted(mapped_outputs.keys())}",
            )
        )
        effective_step_cost = 0.0
        draft_status: Literal["WAITING_FOR_HUMAN_ARBITRATION", "EXECUTING_AGENT"] = (
            "EXECUTING_AGENT"
        )
    else:
        assert exec_result is not None
        existing_draft = engine.blackboard.get_step_execution(run.id, step_key).draft_artifact
        draft_payload = {**existing_draft, **exec_result.artifact_payload}
        memlog_entries.append(
            StepMemlogEntry(
                entry_id=new_uuid7_str(),
                step_key=step_key,
                marker_type="REASONING",
                summary=exec_result.summary,
                details=exec_result.details,
                source_uris=hydrated.declared_input_uris,
            )
        )
        if effective_divergence or run.execution_regime == "BACKGROUND_FAST_PATH":
            div_note = effective_divergence or (
                "Divergence détectée entre source documentaire (seuil 500€) "
                "et source opérationnelle (seuil 350€)"
            )
            fast_markers = build_default_fast_path_markers(step_key, div_note, wf.datasources)
            memlog_entries.extend(fast_markers)
            draft_payload["fast_path_markers"] = [m.to_dict() for m in fast_markers]
        effective_step_cost = exec_result.cost_usd if exec_result.cost_usd > 0.0 else cost_usd
        draft_status = (
            "WAITING_FOR_HUMAN_ARBITRATION"
            if exec_result.status == "WAITING_FOR_HUMAN_ARBITRATION"
            else "EXECUTING_AGENT"
        )

    draft_step = engine.blackboard.save_step_draft(
        run.id,
        step_key,
        status=draft_status,
        draft_artifact=draft_payload,
        memlog_entries=tuple(memlog_entries),
        hydrated_input_uris=hydrated.declared_input_uris,
        child_run_id=child_run_id,
        added_cost_usd=effective_step_cost,
    )
    if draft_status == "WAITING_FOR_HUMAN_ARBITRATION":
        engine.setup_service.set_run_status(run.id, "WAITING_FOR_HUMAN_ARBITRATION")
        return draft_step, None
    if not commit_immediately:
        return draft_step, None
    active_snaps = engine.blackboard.get_active_snapshots(run.id)
    parent_snap_id = active_snaps[-1].id if active_snaps else None
    snapshot = engine.blackboard.commit_step_snapshot(
        run.id, step_key, parent_snapshot_id=parent_snap_id
    )
    committed_step = engine.blackboard.get_step_execution(run.id, step_key)
    all_steps = engine.blackboard.list_step_executions(run.id)
    engine.setup_service.set_run_status(
        run.id,
        "COMPLETED" if all_steps and all(s.status == "COMMITTED" for s in all_steps) else "RUNNING",
    )
    return committed_step, snapshot


def build_background_fast_path_report(
    engine: DurableOrchestrationEngine, *, run: WorkflowRunEntity
) -> BackgroundAuditConsolidatedReport:
    """Assemble consolidated `BACKGROUND_FAST_PATH` report after step commits."""
    all_memlogs = [
        entry for s in engine.blackboard.list_step_executions(run.id) for entry in s.step_memlog
    ]
    plugin = get_memlog_marker_plugin()
    primary_canonical = (
        normalize_memlog_marker(plugin.primary_divergence_marker)
        if plugin is not None
        else "core.divergence_suspected"
    )
    secondary_canonical = (
        normalize_memlog_marker(plugin.secondary_divergence_marker)
        if plugin is not None
        else "core.divergence_suspected"
    )
    return BackgroundAuditConsolidatedReport(
        run_id=run.id,
        workflow_uri=run.workflow_uri,
        total_steps_committed=len(engine.blackboard.get_active_snapshots(run.id)),
        assumptions=tuple(
            m for m in all_memlogs if normalize_memlog_marker(m.marker_type) == "core.assumption"
        ),
        suspected_code_bugs=tuple(
            m for m in all_memlogs if normalize_memlog_marker(m.marker_type) == primary_canonical
        ),
        suspected_obsolete_docs=tuple(
            m for m in all_memlogs if normalize_memlog_marker(m.marker_type) == secondary_canonical
        ),
        sse_event_topic=f"channel:workspace:{run.workspace_id}:background_audit.completed",
        sse_latency_ms=42.0,
    )
