"""Workflow Save-and-Launch Helpers extracted from `assistant_agent_synthesis.py`."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration.assistant_agent_models import SavedAndLaunchedWorkflowResult
from orcia_core.permissions.models import UserIdentity


async def execute_saved_and_launched_workflow_async(
    setup: Any,
    engine: Any,
    user: UserIdentity,
    *,
    workspace_id: str,
    manifest_yaml: str,
) -> SavedAndLaunchedWorkflowResult:
    """Async register composed YAML workflow and run steps without blocking event loop."""
    if setup is None or engine is None:
        raise RuntimeError(
            "WorkflowOrchestrationSetupService and DurableOrchestrationEngine are required."
        )
    definition = setup.register_workflow_manifest(user, manifest_yaml, workspace_id=workspace_id)
    run = setup.instantiate_workflow_run(
        user, workflow_uri=definition.uri, workspace_id=workspace_id
    )
    engine.initialize_run_steps(run, definition)
    executed_keys: list[str] = []
    for step in definition.steps:
        await engine.execute_step_async(
            user, run_id=run.id, step_key=step.step_key, commit_immediately=True
        )
        executed_keys.append(step.step_key)
    active_snaps = engine.blackboard.get_active_snapshots(run.id)
    updated_run = next((r for r in setup.runs if r.id == run.id), None)
    return SavedAndLaunchedWorkflowResult(
        workflow_uri=definition.uri,
        version=definition.version,
        run_id=run.id,
        execution_regime=definition.execution_regime,
        run_status=str(updated_run.status if updated_run is not None else "COMPLETED"),
        executed_step_keys=tuple(executed_keys),
        snapshot_count=len(active_snaps),
    )


def execute_saved_and_launched_workflow(
    setup: Any,
    engine: Any,
    user: UserIdentity,
    *,
    workspace_id: str,
    manifest_yaml: str,
) -> SavedAndLaunchedWorkflowResult:
    """Sync register composed YAML workflow in Workspace and run it through Durable engine."""
    if setup is None or engine is None:
        raise RuntimeError(
            "WorkflowOrchestrationSetupService and DurableOrchestrationEngine are required."
        )
    definition = setup.register_workflow_manifest(user, manifest_yaml, workspace_id=workspace_id)
    run = setup.instantiate_workflow_run(
        user, workflow_uri=definition.uri, workspace_id=workspace_id
    )
    engine.initialize_run_steps(run, definition)
    executed_keys: list[str] = []
    for step in definition.steps:
        engine.execute_step(user, run_id=run.id, step_key=step.step_key, commit_immediately=True)
        executed_keys.append(step.step_key)
    active_snaps = engine.blackboard.get_active_snapshots(run.id)
    updated_run = next((r for r in setup.runs if r.id == run.id), None)
    return SavedAndLaunchedWorkflowResult(
        workflow_uri=definition.uri,
        version=definition.version,
        run_id=run.id,
        execution_regime=definition.execution_regime,
        run_status=str(updated_run.status if updated_run is not None else "COMPLETED"),
        executed_step_keys=tuple(executed_keys),
        snapshot_count=len(active_snaps),
    )
