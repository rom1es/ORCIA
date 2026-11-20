"""FastAPI Router for Multi-Project Jira Staged Actions, Webhooks & `/api/v1/mcp`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import get_jira_staged_action_service, get_mcp_server_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.jira_and_mcp import (
    CommitStagedJiraActionRequest,
    CommitStagedJiraActionResponse,
    JiraIssueUpdatedWebhookRequest,
    JiraIssueUpdatedWebhookResponse,
    JiraJqlSearchRequest,
    JiraJqlSearchResponse,
    McpToolCallRequest,
    McpToolCallResponse,
    McpToolDescriptorSchema,
    McpToolsListResponse,
    StagedJiraActionItemSchema,
    StagedJiraActionListResponse,
    StageJiraActionRequest,
    StageJiraActionResponse,
)
from orcia_connectors.jira_actions import MultiProjectJiraStagedActionService, StagedJiraActionItem
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_core.orchestration.mcp_server import GovernedMcpServerService

router = APIRouter(tags=["jira-and-mcp"])

JiraSvcDep = Annotated[MultiProjectJiraStagedActionService, Depends(get_jira_staged_action_service)]
McpSvcDep = Annotated[GovernedMcpServerService, Depends(get_mcp_server_service)]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_staged(item: StagedJiraActionItem) -> StagedJiraActionItemSchema:
    return StagedJiraActionItemSchema(
        staged_action_id=item.staged_action_id,
        workspace_id=item.workspace_id,
        run_id=item.run_id,
        step_execution_id=item.step_execution_id,
        project_alias=item.project_alias,
        project_key=item.project_key,
        action_type=item.action_type,
        issue_key=item.issue_key,
        summary=item.summary,
        target_transition=item.target_transition,
        fields_payload=item.fields_payload,
        status=item.status,
        idempotency_key=item.idempotency_key,
        provenance_run_lock_uri=item.provenance_run_lock_uri,
        provenance_run_lock_sha256=item.provenance_run_lock_sha256,
        executed_issue_key=item.executed_issue_key,
        replayed_from_cache=item.replayed_from_cache,
    )


@router.post(
    "/api/v1/jira/jql/search",
    response_model=JiraJqlSearchResponse,
    summary="Search workspace Jira projects in real time via JQL (`FR-24`)",
    responses=PROBLEM_RESPONSES,
)
async def search_workspace_jira_jql(
    payload: JiraJqlSearchRequest,
    request: Request,
    svc: JiraSvcDep,
    persona_key: PersonaQuery = None,
) -> JiraJqlSearchResponse:
    """Query Jira issues on the selected workspace project alias (`jira:product`, `jira:secops`)."""
    resolve_request_user(request, persona_key=persona_key)
    project_key = svc.resolve_project_key(payload.project_alias)
    issues = svc.search_jql(
        workspace_id=payload.workspace_id,
        project_alias=payload.project_alias,
        jql=payload.jql,
    )
    return JiraJqlSearchResponse(
        workspace_id=payload.workspace_id,
        project_alias=payload.project_alias,
        project_key=project_key,
        issues=issues,
        trace_id=_trace(request),
    )


@router.get(
    "/api/v1/jira/actions/staged",
    response_model=StagedJiraActionListResponse,
    summary="List staged and executed Jira workflow actions (`Story 4.4`, `AD-5`)",
    responses=PROBLEM_RESPONSES,
)
async def list_staged_jira_actions(
    request: Request,
    svc: JiraSvcDep,
    workspace_id: Annotated[str | None, Query(min_length=1, max_length=128)] = None,
    persona_key: PersonaQuery = None,
) -> StagedJiraActionListResponse:
    """List staged or executed Jira actions from PostgreSQL 18 for F5 rehydration."""
    resolve_request_user(request, persona_key=persona_key)
    items = await svc.list_staged_actions_async(workspace_id=workspace_id)
    return StagedJiraActionListResponse(
        actions=[_serialize_staged(item) for item in items],
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/jira/actions/stage",
    response_model=StageJiraActionResponse,
    summary="Pre-validate Jira transitions and stage action in PG18 (`AD-5`)",
    responses=PROBLEM_RESPONSES,
)
async def stage_jira_workflow_action(
    payload: StageJiraActionRequest,
    request: Request,
    svc: JiraSvcDep,
    persona_key: PersonaQuery = None,
) -> StageJiraActionResponse:
    """Validate `GET /rest/api/3/issue/{key}/transitions` and persist staged Jira action in PG18."""
    user = resolve_request_user(request, persona_key=persona_key)
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    staged = await svc.stage_action_async(
        workspace_id=payload.workspace_id,
        run_id=payload.run_id,
        step_execution_id=payload.step_execution_id,
        project_alias=payload.project_alias,
        action_type=payload.action_type,
        summary=payload.summary,
        issue_key=payload.issue_key,
        target_transition=payload.target_transition,
        fields_payload=payload.fields_payload,
        staged_by=user.id,
    )
    return StageJiraActionResponse(
        staged_action=_serialize_staged(staged),
        draft_artifact_jsonb=await svc.get_step_draft_artifact_async(payload.step_execution_id),
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/jira/actions/commit",
    response_model=CommitStagedJiraActionResponse,
    summary="Execute a staged Jira action on Gate pass with `run-lock.json` provenance (`AD-5`)",
    responses=PROBLEM_RESPONSES,
)
async def commit_staged_jira_action(
    payload: CommitStagedJiraActionRequest,
    request: Request,
    svc: JiraSvcDep,
    persona_key: PersonaQuery = None,
) -> CommitStagedJiraActionResponse:
    """Execute staged Jira operation via `ConnectorPort.invoke` only when Gate status is `PASS`."""
    user = resolve_request_user(request, persona_key=persona_key)
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    executed = await svc.commit_staged_action_on_gate_pass_async(
        staged_action_id=payload.staged_action_id,
        gate_status=payload.gate_status,
        run_lock_sha256=payload.run_lock_sha256,
        approved_by=user.id,
    )
    return CommitStagedJiraActionResponse(
        executed_action=_serialize_staged(executed),
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/webhooks/jira/issue-updated",
    response_model=JiraIssueUpdatedWebhookResponse,
    summary="Receive `jira:issue_updated` webhook and wake up paused run in < 500ms (`FR-16`)",
    responses=PROBLEM_RESPONSES,
)
async def handle_jira_issue_updated_webhook_route(
    payload: JiraIssueUpdatedWebhookRequest,
    request: Request,
    svc: JiraSvcDep,
) -> JiraIssueUpdatedWebhookResponse:
    """Process `jira:issue_updated` (`Done`) and publish Replay event to `domain_events_outbox`."""
    notif = await svc.handle_issue_updated_webhook_async(
        webhook_event=payload.webhook_event,
        issue_key=payload.issue_key,
        new_status=payload.new_status,
        workspace_id=payload.workspace_id,
        run_id=payload.run_id,
        step_execution_id=payload.step_execution_id,
    )
    return JiraIssueUpdatedWebhookResponse(
        webhook_event=notif.webhook_event,
        issue_key=notif.issue_key,
        project_key=notif.project_key,
        new_status=notif.new_status,
        workspace_id=notif.workspace_id,
        run_id=notif.run_id,
        step_execution_id=notif.step_execution_id,
        replay_triggered=notif.replay_triggered,
        outbox_event_id=notif.outbox_event_id,
        sse_channel=notif.sse_channel,
        processing_ms=notif.processing_ms,
        trace_id=_trace(request),
    )


@router.get(
    "/api/v1/mcp/tools",
    response_model=McpToolsListResponse,
    summary="List governed MCP tools exposed to external IDEs (`/api/v1/mcp`, `AR-7`)",
    responses=PROBLEM_RESPONSES,
)
async def list_governed_mcp_tools(
    request: Request,
    svc: McpSvcDep,
    persona_key: PersonaQuery = None,
) -> McpToolsListResponse:
    """Return MCP tools available in `passthrough` mode for VS Code / Cursor / Claude Code / AGY."""
    resolve_request_user(request, persona_key=persona_key)
    return McpToolsListResponse(
        tools=[
            McpToolDescriptorSchema(
                name=t.name,
                description=t.description,
                mode=t.mode,
                passthrough_required=t.passthrough_required,
                blocks_human_authored_sections=t.blocks_human_authored_sections,
            )
            for t in svc.list_tools()
        ],
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/mcp/call",
    response_model=McpToolCallResponse,
    summary="Invoke a governed MCP tool in `passthrough` mode (`/api/v1/mcp`, `FR-24`, `AD-3`)",
    responses=PROBLEM_RESPONSES,
)
async def call_governed_mcp_tool(
    payload: McpToolCallRequest,
    request: Request,
    svc: McpSvcDep,
    persona_key: PersonaQuery = None,
) -> McpToolCallResponse:
    """Execute an MCP tool call while materially blocking `human_authored_required: true` writes."""
    user = resolve_request_user(request, persona_key=persona_key)
    is_observer = user.platform_role in ("OBSERVER", "BU_DIRECTOR")
    res = await svc.call_tool_async(
        tool_name=payload.tool_name,
        workspace_id=payload.workspace_id,
        arguments=payload.arguments,
        ide_client=payload.ide_client,
        execution_identity=payload.execution_identity,
        is_read_only_observer=is_observer,
        proposed_by=user.id,
        instance=str(request.url.path),
    )
    return McpToolCallResponse(
        tool_name=res.tool_name,
        ide_client=res.ide_client,
        execution_identity=res.execution_identity,
        workspace_id=res.workspace_id,
        status=res.status,
        data=res.data,
        trace_id=_trace(request),
    )
