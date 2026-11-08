"""FastAPI Router for Story 4.4: Multi-Project Jira Staged Actions, Webhooks & `/api/v1/mcp`."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

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
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_core.orchestration.mcp_server import GovernedMcpServerService
from orcia_pack_sdlc.jira_actions import MultiProjectJiraStagedActionService, StagedJiraActionItem

router = APIRouter(tags=["jira-and-mcp"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _get_jira_service(request: Request) -> MultiProjectJiraStagedActionService:
    svc: MultiProjectJiraStagedActionService | None = getattr(
        request.app.state, "jira_staged_action_service", None
    )
    if svc is None:
        svc = MultiProjectJiraStagedActionService()
        request.app.state.jira_staged_action_service = svc
    return svc


def _get_mcp_service(request: Request) -> GovernedMcpServerService:
    svc: GovernedMcpServerService | None = getattr(request.app.state, "mcp_server_service", None)
    if svc is None:
        svc = GovernedMcpServerService()
        request.app.state.mcp_server_service = svc
    return svc


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
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> JiraJqlSearchResponse:
    """Query Jira issues on the selected workspace project alias (`jira:product`, `jira:secops`)."""
    resolve_request_user(request, persona_key=persona_key)
    svc = _get_jira_service(request)
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
    workspace_id: str | None = Query(default=None, min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> StagedJiraActionListResponse:
    """List staged or executed Jira actions for F5 state rehydration."""
    resolve_request_user(request, persona_key=persona_key)
    svc = _get_jira_service(request)
    items = svc.list_staged_actions(workspace_id=workspace_id)
    return StagedJiraActionListResponse(
        actions=[_serialize_staged(item) for item in items],
        trace_id=_trace(request),
    )


@router.post(
    "/api/v1/jira/actions/stage",
    response_model=StageJiraActionResponse,
    summary="Pre-validate Jira transitions and stage action in draft_artifact_jsonb (`AD-5`)",
    responses=PROBLEM_RESPONSES,
)
async def stage_jira_workflow_action(
    payload: StageJiraActionRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> StageJiraActionResponse:
    """Validate `GET /rest/api/3/issue/{key}/transitions` and stage Jira action before Gate."""
    user = resolve_request_user(request, persona_key=persona_key)
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    svc = _get_jira_service(request)
    staged = svc.stage_action(
        workspace_id=payload.workspace_id,
        run_id=payload.run_id,
        step_execution_id=payload.step_execution_id,
        project_alias=payload.project_alias,
        action_type=payload.action_type,
        summary=payload.summary,
        issue_key=payload.issue_key,
        target_transition=payload.target_transition,
        fields_payload=payload.fields_payload,
    )
    return StageJiraActionResponse(
        staged_action=_serialize_staged(staged),
        draft_artifact_jsonb=svc.get_step_draft_artifact(payload.step_execution_id),
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
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> CommitStagedJiraActionResponse:
    """Execute staged Jira operation via `ConnectorPort.invoke` only when Gate status is `PASS`."""
    user = resolve_request_user(request, persona_key=persona_key)
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    svc = _get_jira_service(request)
    executed = svc.commit_staged_action_on_gate_pass(
        staged_action_id=payload.staged_action_id,
        gate_status=payload.gate_status,
        run_lock_sha256=payload.run_lock_sha256,
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
) -> JiraIssueUpdatedWebhookResponse:
    """Process `jira:issue_updated` (`Done`) and publish Replay event to `domain_events_outbox`."""
    svc = _get_jira_service(request)
    notif = svc.handle_issue_updated_webhook(
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
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> McpToolsListResponse:
    """Return MCP tools available in `passthrough` mode for VS Code / Cursor / Claude Code / AGY."""
    resolve_request_user(request, persona_key=persona_key)
    svc = _get_mcp_service(request)
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
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> McpToolCallResponse:
    """Execute an MCP tool call while materially blocking `human_authored_required: true` writes."""
    user = resolve_request_user(request, persona_key=persona_key)
    is_observer = user.platform_role in ("OBSERVER", "BU_DIRECTOR")
    svc = _get_mcp_service(request)
    res = svc.call_tool(
        tool_name=payload.tool_name,
        workspace_id=payload.workspace_id,
        arguments=payload.arguments,
        ide_client=payload.ide_client,
        execution_identity=payload.execution_identity,
        is_read_only_observer=is_observer,
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
