"""FastAPI Router for Assistant Workflow-as-Code Launch (`FR-11`, `Story 26.8`)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_assistant_service
from orcia_api.dependencies._assistant_guards import enforce_assistant_workspace_guard
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.assistant import (
    AssistantSaveAndLaunchRequest,
    AssistantSaveAndLaunchResponse,
)

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant-agent"])


@router.post(
    "/workflows/save-and-launch",
    response_model=AssistantSaveAndLaunchResponse,
    summary="Save a composed Workflow-as-Code manifest in the Workspace and launch its real run",
    responses=PROBLEM_RESPONSES,
)
async def assistant_save_and_launch_workflow(
    payload: AssistantSaveAndLaunchRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> AssistantSaveAndLaunchResponse:
    """Register and execute a composed workflow via `orcia.step_executors` (`FR-11`, `UJ-10`)."""
    user = resolve_request_user(request, persona_key=persona_key)
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    result = await get_assistant_service(request).save_and_launch_workflow_async(
        user,
        workspace_id=payload.workspace_id,
        manifest_yaml=payload.manifest_yaml,
    )
    return AssistantSaveAndLaunchResponse(
        workflow_uri=result.workflow_uri,
        version=result.version,
        run_id=result.run_id,
        execution_regime=result.execution_regime,
        run_status=result.run_status,
        executed_step_keys=list(result.executed_step_keys),
        snapshot_count=result.snapshot_count,
    )
