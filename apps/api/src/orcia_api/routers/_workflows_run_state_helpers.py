"""Run-state RAM/PG18 rehydration & upsert helpers for `_workflows_pending_runs` (`Story 30.3`)."""

from __future__ import annotations

from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowRunState
from orcia_core.workflows import SqlWorkflowV2RunsStore
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2


def extract_workflow_actor_slug(workflow: WorkflowDefinitionV2) -> str:
    """Derive a clean actor slug from `WorkflowDefinitionV2.global_system_prompt_or_ref`."""
    raw_ref = (workflow.global_system_prompt_or_ref or workflow.slug).strip()
    without_fragment = raw_ref.split("#", 1)[0]
    tail = without_fragment.rsplit("/", 1)[-1]
    if tail.endswith(".md"):
        tail = tail[:-3]
    return tail or workflow.slug


def remember_run_workspace(
    runs_store: dict[str, BoundedWorkflowRunState],
    run_id: str,
    workspace_id: str | None,
) -> None:
    ws_map = getattr(runs_store, "workspaces", None)
    if isinstance(ws_map, dict):
        ws_map[run_id] = workspace_id


async def persist_workflow_v2_run_state(
    sql_runs_store: SqlWorkflowV2RunsStore,
    *,
    run_state: BoundedWorkflowRunState,
    workflow: WorkflowDefinitionV2,
    workspace_id: str | None,
) -> None:
    """Upsert `BoundedWorkflowRunState` into PostgreSQL 18 `workflow_v2_runs`."""
    state_payload = run_state.model_dump(mode="json")
    if workspace_id:
        state_payload["workspace_id"] = workspace_id
    await sql_runs_store.upsert_run(
        run_id=run_state.run_id,
        workspace_id=workspace_id,
        workflow_id=run_state.workflow_id,
        workflow_slug=run_state.workflow_slug,
        workflow_title=workflow.title,
        actor_slug=extract_workflow_actor_slug(workflow),
        status=run_state.status,
        reflexive_execution_id=run_state.reflexive_execution_id,
        state_payload=state_payload,
    )


async def load_or_rehydrate_run_state(
    runs_store: dict[str, BoundedWorkflowRunState],
    sql_runs_store: SqlWorkflowV2RunsStore,
    run_id: str,
) -> tuple[BoundedWorkflowRunState | None, str | None]:
    """Load run state from RAM cache or cold PG18 `workflow_v2_runs` (`F5` survival)."""
    cached = runs_store.get(run_id)
    if cached is not None:
        ws_map = getattr(runs_store, "workspaces", None)
        if isinstance(ws_map, dict) and run_id in ws_map:
            return cached, ws_map[run_id]
        raw_fallback = await sql_runs_store.get_run(run_id)
        if raw_fallback is not None:
            ws_raw = raw_fallback.get("workspace_id")
            ws_id = str(ws_raw).strip() if isinstance(ws_raw, str) and ws_raw.strip() else None
            remember_run_workspace(runs_store, run_id, ws_id)
            return cached, ws_id
        return cached, None
    raw = await sql_runs_store.get_run(run_id)
    if raw is None:
        return None, None
    ws_raw = raw.get("workspace_id")
    ws_id = str(ws_raw).strip() if isinstance(ws_raw, str) and ws_raw.strip() else None
    clean_payload = {k: v for k, v in raw.items() if k != "workspace_id"}
    restored = BoundedWorkflowRunState.model_validate(clean_payload)
    runs_store[run_id] = restored
    remember_run_workspace(runs_store, run_id, ws_id)
    return restored, ws_id


__all__ = [
    "extract_workflow_actor_slug",
    "load_or_rehydrate_run_state",
    "persist_workflow_v2_run_state",
    "remember_run_workspace",
]
