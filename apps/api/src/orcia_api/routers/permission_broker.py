"""Permission Broker, Passthrough vs Service Principal Guard & Jira Request Router (Story 1.4)."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_permission_broker_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.permission_broker import (
    PermissionBrokerPolicyItem,
    PermissionBrokerStateResponse,
    PermissionBrokerTicketItem,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionPolicyImportMarkdownRequest,
    PermissionPolicyImportMarkdownResponse,
    PermissionTicketActionRequest,
    PermissionTicketActionResponse,
)
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions import (
    PermissionBrokerPolicy,
    PermissionBrokerTicket,
)

router = APIRouter(prefix="/api/v1/permissions/broker", tags=["permission-broker"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_policy(policy: PermissionBrokerPolicy) -> PermissionBrokerPolicyItem:
    return PermissionBrokerPolicyItem(
        id=policy.id,
        policy_key=policy.policy_key,
        uri_pattern=policy.uri_pattern,
        connector_scheme=policy.connector_scheme,
        required_role=policy.required_role,
        approver_team=policy.approver_team,
        request_url_template=policy.request_url_template,
        sla_hours=policy.sla_hours,
        procedure_markdown=policy.procedure_markdown,
        service_principal_allowed=policy.service_principal_allowed,
        approved_by_admin_id=policy.approved_by_admin_id,
        human_anchor_author_id=policy.human_anchor_author_id,
        human_anchor_signature=policy.human_anchor_signature,
        freshness_ttl_days=policy.freshness_ttl_days,
    )


def _serialize_ticket(ticket: PermissionBrokerTicket) -> PermissionBrokerTicketItem:
    return PermissionBrokerTicketItem(
        id=ticket.id,
        ticket_key=ticket.ticket_key,
        workspace_id=ticket.workspace_id,
        requester_user_id=ticket.requester_user_id,
        policy_id=ticket.policy_id,
        step_key=ticket.step_key,
        step_number=ticket.step_number,
        step_state=ticket.step_state,
        status=ticket.status,
        target_uri=ticket.target_uri,
        connector_scheme=ticket.connector_scheme,
        execution_identity=ticket.execution_identity,
        upstream_http_status=ticket.upstream_http_status,
        required_role=ticket.required_role,
        approver_team=ticket.approver_team,
        sla_hours=ticket.sla_hours,
        jira_request_url=ticket.jira_request_url,
        permission_broker_hint=ticket.permission_broker_hint,
        procedure_markdown=ticket.procedure_markdown,
    )


@router.get(
    "/state",
    response_model=PermissionBrokerStateResponse,
    summary="List Permission Broker KB policies and blocked/paused/replayed step tickets",
    responses=PROBLEM_RESPONSES,
)
async def get_permission_broker_state(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
    workspace_id: str | None = Query(default=None, min_length=1, max_length=128),
) -> PermissionBrokerStateResponse:
    """Return all Permission Broker KB policies and step denial tickets for `workspace_id`."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_permission_broker_service(request)
    return PermissionBrokerStateResponse(
        policies=[_serialize_policy(p) for p in svc.list_policies()],
        tickets=[
            _serialize_ticket(t)
            for t in svc.list_tickets(
                workspace_id=workspace_id, user=user, instance=str(request.url.path)
            )
        ],
        trace_id=_trace(request),
    )


@router.post(
    "/policies/import-markdown",
    response_model=PermissionPolicyImportMarkdownResponse,
    summary="Import a Permission Knowledge Base Markdown policy with YAML frontmatter",
    responses=PROBLEM_RESPONSES,
)
async def import_permission_policy_markdown(
    payload: PermissionPolicyImportMarkdownRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> PermissionPolicyImportMarkdownResponse:
    """Parse and upsert a Permission KB policy (`READ_ONLY_OBSERVER` rejected with HTTP 403)."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_permission_broker_service(request)
    policy = svc.import_policy_markdown(
        user,
        payload.markdown_text,
        policy_key=payload.policy_key,
        workspace_id=payload.workspace_id,
        instance=str(request.url.path),
    )
    return PermissionPolicyImportMarkdownResponse(
        policy=_serialize_policy(policy),
        trace_id=_trace(request),
    )


@router.post(
    "/check-access",
    response_model=PermissionCheckResponse,
    summary="Check connector execution (`passthrough` vs `service_principal`) or intercept 401/403",
    responses=PROBLEM_RESPONSES,
)
async def check_or_intercept_connector_access(
    payload: PermissionCheckRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> PermissionCheckResponse:
    """Execute governed connector access check with anti-Confused Deputy and Jira KB brokering."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_permission_broker_service(request)
    outcome = svc.check_or_intercept_access(
        user,
        target_uri=payload.target_uri,
        execution_identity=payload.execution_identity,
        step_key=payload.step_key,
        step_number=payload.step_number,
        workspace_id=payload.workspace_id,
        resource_id=payload.resource_id,
        simulated_upstream_status=payload.simulated_upstream_status,
        granted_external_roles=tuple(payload.granted_external_roles),
        raise_on_denied=payload.raise_on_denied,
        instance=str(request.url.path),
    )
    return PermissionCheckResponse(
        allowed=outcome.allowed,
        status=outcome.status,
        execution_identity=outcome.execution_identity,
        target_uri=outcome.target_uri,
        connector_scheme=outcome.connector_scheme,
        policy=_serialize_policy(outcome.policy),
        ticket=_serialize_ticket(outcome.ticket) if outcome.ticket is not None else None,
        permission_broker_hint=outcome.permission_broker_hint,
        trace_id=_trace(request),
    )


@router.post(
    "/tickets/{ticket_id}/action",
    response_model=PermissionTicketActionResponse,
    summary="Pause or replay a blocked Permission Broker step (`Replay Step N`, FR-22)",
    responses=PROBLEM_RESPONSES,
)
async def apply_permission_ticket_action(
    payload: PermissionTicketActionRequest,
    request: Request,
    ticket_id: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> PermissionTicketActionResponse:
    """Transition `ticket_id` to `PAUSED` or `REPLAYED` (`READ_ONLY_OBSERVER` rejected)."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_permission_broker_service(request)
    updated = svc.apply_ticket_action(
        user,
        ticket_id,
        payload.action,
        workspace_id=payload.workspace_id,
        instance=str(request.url.path),
    )
    return PermissionTicketActionResponse(
        ticket=_serialize_ticket(updated),
        trace_id=_trace(request),
    )
