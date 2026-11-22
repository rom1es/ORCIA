"""API Composition Root wiring for durable Assistant DBOS + PG18 processes (`Story 26.8`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.dependencies import (
    get_assistant_process_launcher_service,
    get_auth_service,
    get_orchestration_service,
)
from orcia_api.routers._assistant_dbos_backend import ApiDbosProcessBackendAdapter
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.schemas.assistant_citations_and_folders import LaunchProcessFromFolderResponse
from orcia_core.orchestration import WorkflowRunEntity
from orcia_core.orchestration.assistant_process_launcher import (
    AssistantProcessLauncherService,
    DurableProcessExecutionSnapshot,
    LaunchedProcessOutcome,
)
from orcia_core.orchestration.seeds import ensure_folder_pilot_workflow_registered
from orcia_core.permissions.models import UserIdentity


def resolve_assistant_process_launcher(request: Request) -> AssistantProcessLauncherService:
    """Resolve `AssistantProcessLauncherService` wired to `ApiDbosProcessBackendAdapter`."""
    launcher = get_assistant_process_launcher_service(request)
    setup_svc = get_orchestration_service(request)
    engine = setup_svc.engine
    request.app.state.orchestration_engine = engine
    launcher.set_durable_backend(
        ApiDbosProcessBackendAdapter(request=request, setup_service=setup_svc, engine=engine)
    )
    return launcher


async def launch_assistant_process_from_api(
    request: Request,
    *,
    user: UserIdentity,
    workspace_id: str,
    workflow_uri: str | None,
    idempotency_token: str,
    seed_inputs: dict[str, Any] | None = None,
    trace_id: str = "0" * 32,
) -> LaunchedProcessOutcome:
    """Sync workspace topology from PG18 and launch a durable assistant process run."""
    await sync_evaluator_topology_from_pg(request, get_auth_service(request))
    ensure_folder_pilot_workflow_registered(
        get_orchestration_service(request), workflow_uri=workflow_uri
    )
    launcher = resolve_assistant_process_launcher(request)
    return await launcher.launch_process_async(
        user,
        workspace_id=workspace_id,
        workflow_uri=workflow_uri,
        idempotency_token=idempotency_token,
        seed_inputs=seed_inputs,
        trace_id=trace_id,
        instance=str(request.url.path),
    )


async def resume_assistant_process_after_anchor(
    request: Request,
    *,
    user: UserIdentity,
    run: WorkflowRunEntity,
    step_key: str,
    signature_id: str,
    trace_id: str,
) -> DurableProcessExecutionSnapshot | None:
    """Resume a paused assistant-launched process once its human anchor has been signed."""
    is_assistant_process = run.trigger_id == "assistant-process" or (
        run.trigger_idempotency_key or ""
    ).startswith("assistant-process:")
    if not is_assistant_process:
        return None
    launcher = resolve_assistant_process_launcher(request)
    return await launcher.resume_after_anchor_signature_async(
        user,
        run_id=run.id,
        step_key=step_key,
        signature_id=signature_id,
        trace_id=trace_id,
        instance=str(request.url.path),
    )


async def launch_folder_process_response(
    request: Request,
    *,
    user: UserIdentity,
    prep: Any,
) -> LaunchProcessFromFolderResponse:
    """Launch a durable DBOS process from a prepared folder contract and serialize response."""
    trace_id = str(getattr(getattr(request, "state", None), "trace_id", "") or "0" * 32)
    outcome = await launch_assistant_process_from_api(
        request,
        user=user,
        workspace_id=prep.workspace_id,
        workflow_uri=prep.workflow_uri,
        idempotency_token=f"folder:{prep.folder_id}:{prep.workflow_uri}",
        seed_inputs=dict(prep.prefilled_contract_inputs),
        trace_id=trace_id,
    )
    return LaunchProcessFromFolderResponse(
        folder_id=prep.folder_id,
        workspace_id=prep.workspace_id,
        workflow_uri=outcome.workflow_uri,
        initiated_by_user_id=prep.initiated_by_user_id,
        passthrough_identity=prep.passthrough_identity,
        prefilled_contract_inputs=prep.prefilled_contract_inputs,
        run_id=outcome.run.id,
        run_status=outcome.run_status,
        dbos_workflow_id=outcome.dbos_workflow_id,
        waiting_step_keys=list(outcome.waiting_step_keys),
        executed_step_keys=list(outcome.executed_step_keys),
        snapshot_count=outcome.snapshot_count,
    )


__all__ = [
    "ApiDbosProcessBackendAdapter",
    "launch_assistant_process_from_api",
    "launch_folder_process_response",
    "resolve_assistant_process_launcher",
    "resume_assistant_process_after_anchor",
]
