"""Helper routines for preparing workflow step inputs and executor contexts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from orcia_core.blackboard.models import (
    BackgroundAuditConsolidatedReport,
    StepExecutionEntity,
    StepExecutionStatus,
)
from orcia_core.orchestration._engine_fast_path import build_background_fast_path_report
from orcia_core.orchestration.errors import ResourceNotFoundError, ValidationDomainError
from orcia_core.orchestration.human_anchors_and_arbitration import AuthorIdentityType
from orcia_core.orchestration.jit_hydrator import JitStepHydrator
from orcia_core.orchestration.models import (
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
    WorkflowStepSpec,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import StepExecutorContext, get_registered_step_executor

if TYPE_CHECKING:
    from orcia_core.orchestration.engine import DurableOrchestrationEngine


def initialize_run_steps_helper(
    engine: DurableOrchestrationEngine,
    run: WorkflowRunEntity,
    workflow: WorkflowAsCodeDefinition,
    *,
    initialize_anchored_as_waiting: bool = False,
) -> tuple[StepExecutionEntity, ...]:
    """Initialize `StepExecutionEntity` rows in topological order if not already created."""
    existing = engine.blackboard.list_step_executions(run.id)
    if existing:
        if initialize_anchored_as_waiting:
            updated_steps: list[StepExecutionEntity] = []
            specs_by_key = {s.step_key: s for s in workflow.steps}
            for step_exec in existing:
                spec = specs_by_key.get(step_exec.step_key)
                if (
                    spec is not None
                    and spec.human_authored_required
                    and step_exec.status == "PENDING"
                    and not engine.anchors_and_arbitration.get_step_anchors(
                        run.id, step_exec.step_key
                    )
                ):
                    draft = engine.blackboard.save_step_draft(
                        run.id,
                        step_exec.step_key,
                        status="WAITING_FOR_HUMAN_ANCHOR",
                        draft_artifact=step_exec.draft_artifact,
                    )
                    updated_steps.append(draft)
                else:
                    updated_steps.append(step_exec)
            return tuple(updated_steps)
        return existing
    created: list[StepExecutionEntity] = []
    for idx, step in enumerate(workflow.steps):
        initial_status: StepExecutionStatus = (
            "WAITING_FOR_HUMAN_ANCHOR"
            if (initialize_anchored_as_waiting and step.human_authored_required)
            else "PENDING"
        )
        step_exec = StepExecutionEntity(
            id=new_uuid7_str(),
            step_execution_key=f"stepexec-{run.id[-6:]}-{step.step_key}",
            run_id=run.id,
            step_key=step.step_key,
            step_index=idx,
            step_type=step.step_type,
            execution_mode=run.execution_regime,
            status=initial_status,
            attempt_count=0,
            max_agent_retries=step.max_agent_retries,
        )
        engine.blackboard.register_step_execution(step_exec)
        created.append(step_exec)
    return tuple(created)


def prepare_step_inputs(
    engine: DurableOrchestrationEngine,
    user: UserIdentity,
    *,
    run_id: str,
    step_key: str,
    divergence_note: str | None,
    cost_usd: float,
    require_human_anchor: bool,
    author_type: AuthorIdentityType,
    instance: str | None,
    legacy_kwargs: dict[str, Any],
) -> tuple[
    WorkflowRunEntity,
    WorkflowRunEntity,
    WorkflowAsCodeDefinition,
    WorkflowStepSpec,
    Any,
    float,
    str | None,
]:
    """Validate permissions, root budget, anchors, and hydrate inputs for a workflow step."""
    legacy_div = legacy_kwargs.get("divergence_hint") or next(
        (v for k, v in legacy_kwargs.items() if "divergence" in k and isinstance(v, str)),
        None,
    )
    effective_divergence = divergence_note or legacy_div
    run = engine._get_run(run_id, instance=instance)
    engine.setup_service._enforce_mutation_guard(user, run.workspace_id, instance=instance)
    wf = engine._get_workflow(run.workflow_uri, instance=instance)
    engine.initialize_run_steps(run, wf)

    root_run = engine._get_run(run.root_run_id, instance=instance)
    current_root_cost = engine.get_root_accumulated_cost(root_run.id)
    if current_root_cost + cost_usd > root_run.budget_max_usd:
        raise ValidationDomainError(
            detail_code="ERR_ROOT_BUDGET_EXCEEDED",
            detail_params={
                "root_run_id": root_run.id,
                "spent": f"{current_root_cost + cost_usd:.2f}",
                "max_usd": f"{root_run.budget_max_usd:.2f}",
            },
            instance=instance,
        )
    step_spec = next((s for s in wf.steps if s.step_key == step_key), None)
    if step_spec is None:
        raise ResourceNotFoundError(
            detail_code="ERR_STEP_NOT_FOUND",
            detail_params={"step_key": step_key},
            instance=instance,
        )
    engine.anchors_and_arbitration.enforce_step_anchor_if_required(
        run,
        step_spec,
        require_human_anchor=require_human_anchor,
        author_type=author_type,
        instance=instance,
    )
    hydrated = JitStepHydrator.hydrate_step(
        run=run,
        workflow=wf,
        step_key=step_key,
        blackboard=engine.blackboard,
        seed_inputs=engine._run_seed_inputs.get(run.id),
    )
    return run, root_run, wf, step_spec, hydrated, current_root_cost, effective_divergence


def build_step_exec_ctx(
    *,
    run: WorkflowRunEntity,
    root_run: WorkflowRunEntity,
    wf: WorkflowAsCodeDefinition,
    step_spec: WorkflowStepSpec,
    hydrated: Any,
    current_root_cost: float,
    human_decision: str | None,
    executor_metadata: dict[str, Any] | None,
    instance: str | None,
) -> tuple[Any, StepExecutorContext]:
    """Resolve the registered `StepExecutorPort` plugin and assemble its execution context."""
    executor = get_registered_step_executor(step_spec.step_type)
    if executor is None:
        raise ValidationDomainError(
            detail_code="ERR_STEP_EXECUTOR_NOT_FOUND",
            detail_params={"step_type": step_spec.step_type},
            instance=instance,
        )
    meta = dict(executor_metadata or {})
    if human_decision is not None:
        meta["human_decision"] = human_decision
    ctx = StepExecutorContext(
        run_id=run.id,
        root_run_id=root_run.id,
        workspace_id=run.workspace_id,
        workflow_uri=wf.uri,
        step_key=step_spec.step_key,
        step_title=step_spec.title,
        step_type=step_spec.step_type,
        execution_regime=run.execution_regime,
        directive=hydrated.step_directive,
        declared_input_uris=hydrated.declared_input_uris,
        resolved_inputs=hydrated.resolved_inputs,
        datasources=wf.datasources,
        agent_uri=step_spec.agent_uri,
        skill_uri=step_spec.skill_uri,
        sub_workflow_uri=step_spec.sub_workflow_uri,
        max_agent_retries=step_spec.max_agent_retries,
        budget_remaining_usd=max(0.0, root_run.budget_max_usd - current_root_cost),
        idempotency_key=f"idem:{run.id}:{step_spec.step_key}",
        metadata=meta,
    )
    return executor, ctx


async def run_background_fast_path_audit_async_helper(
    engine: DurableOrchestrationEngine,
    user: UserIdentity,
    *,
    run_id: str,
    divergence_note: str,
    instance: str | None = None,
) -> BackgroundAuditConsolidatedReport:
    """Async execution of all steps of `run_id` in `BACKGROUND_FAST_PATH` (`UJ-10`)."""
    run = engine._get_run(run_id, instance=instance)
    wf = engine._get_workflow(run.workflow_uri, instance=instance)
    engine.initialize_run_steps(run, wf)
    for step in wf.steps:
        await engine.execute_step_async(
            user,
            run_id=run.id,
            step_key=step.step_key,
            commit_immediately=True,
            divergence_note=divergence_note,
            cost_usd=0.2,
            instance=instance,
        )
    return build_background_fast_path_report(engine, run=run)


def run_background_fast_path_audit_sync_helper(
    engine: DurableOrchestrationEngine,
    user: UserIdentity,
    *,
    run_id: str,
    divergence_note: str,
    instance: str | None = None,
) -> BackgroundAuditConsolidatedReport:
    """Sync execution of all steps of `run_id` in `BACKGROUND_FAST_PATH` (`UJ-10`)."""
    run = engine._get_run(run_id, instance=instance)
    wf = engine._get_workflow(run.workflow_uri, instance=instance)
    engine.initialize_run_steps(run, wf)
    for step in wf.steps:
        engine.execute_step(
            user,
            run_id=run.id,
            step_key=step.step_key,
            commit_immediately=True,
            divergence_note=divergence_note,
            cost_usd=0.2,
            instance=instance,
        )
    return build_background_fast_path_report(engine, run=run)


def compute_root_accumulated_cost(engine: DurableOrchestrationEngine, root_run_id: str) -> float:
    """Compute total accumulated cost across `root_run_id` and all nested child runs."""
    total = 0.0
    for r in engine.setup_service.runs:
        if r.root_run_id == root_run_id:
            for s in engine.blackboard.list_step_executions(r.id):
                total += s.cost_usd
    return round(total, 4)


def resolve_engine_run(
    engine: DurableOrchestrationEngine, run_id: str, *, instance: str | None = None
) -> WorkflowRunEntity:
    """Lookup `run_id` inside engine setup service or raise `ResourceNotFoundError`."""
    if run := next((r for r in engine.setup_service.runs if r.id == run_id), None):
        return run
    raise ResourceNotFoundError(
        detail_override=f"Workflow Run '{run_id}' introuvable.", instance=instance
    )


def resolve_engine_workflow(
    engine: DurableOrchestrationEngine, uri: str, *, instance: str | None = None
) -> WorkflowAsCodeDefinition:
    """Lookup workflow definition by URI or raise `ResourceNotFoundError`."""
    if wf := next((w for w in engine.setup_service.workflows if w.uri == uri), None):
        return wf
    raise ResourceNotFoundError(detail_override=f"Workflow '{uri}' introuvable.", instance=instance)
