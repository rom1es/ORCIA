"""WorkflowRunEntity initialization builder for `WorkflowOrchestrationSetupService`."""

from __future__ import annotations

from orcia_core.orchestration.models import (
    RecursiveRunLockManifest,
    WorkflowAsCodeDefinition,
    WorkflowRunEntity,
)


def build_initialized_run_entity(
    *,
    run_id: str,
    root_run_id: str,
    workspace_id: str,
    wf: WorkflowAsCodeDefinition,
    parent_run_id: str | None,
    parent_step_execution_id: str | None,
    nesting_depth: int,
    trigger_id: str | None,
    trigger_idempotency_key: str | None,
    user_id: str,
    execution_identity_mode: str,
    recursive_lock: RecursiveRunLockManifest,
) -> WorkflowRunEntity:
    """Construct an initialized `WorkflowRunEntity` pinned to `recursive_lock`."""
    return WorkflowRunEntity(
        id=run_id,
        run_key=f"run-{wf.uri.split('/')[-1]}-{run_id[-6:]}",
        workspace_id=workspace_id,
        workflow_def_id=wf.id,
        workflow_uri=wf.uri,
        parent_run_id=parent_run_id,
        parent_step_execution_id=parent_step_execution_id,
        root_run_id=root_run_id,
        nesting_depth=nesting_depth,
        execution_regime=wf.execution_regime,
        criticality=wf.criticality,
        trigger_id=trigger_id,
        trigger_idempotency_key=trigger_idempotency_key,
        status="INITIALIZED",
        initiated_by_user_id=user_id,
        execution_identity_mode=execution_identity_mode,  # type: ignore[arg-type]
        budget_max_usd=wf.max_cost_usd,
        run_lock=recursive_lock,
    )
