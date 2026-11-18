"""Workflow Triggers CRUD, Manual Fire, Webhook Ingress & Alert Fallback (`Story 7.2`, `AD-18`)."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Request

from orcia_api.dependencies import get_trigger_dispatcher_service
from orcia_api.routers._finops_auth_guards import (
    enforce_workspace_governed_mutation,
    resolve_finops_read_scope,
)
from orcia_api.routers._finops_scope_guards import validate_uuid
from orcia_api.routers._workflow_triggers_helpers import (
    TRIGGER_PROBLEM_RESPONSES,
    authenticate_platform_alert_webhook,
    parse_secret_input_spec,
    serialize_dispatch_outcome,
    serialize_trigger,
    trace_id_from_request,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.workflow_triggers import (
    CreateWorkflowTriggerRequest,
    DeleteWorkflowTriggerResponse,
    FireManualTriggerRequest,
    TriggerDispatchResponse,
    UpdateWorkflowTriggerRequest,
    WorkflowTriggerListResponse,
    WorkflowTriggerResponse,
    WorkflowTriggerWebhookRequest,
)
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.fingerprint import (
    compute_error_fingerprint_sha256,
    extract_top_frame,
)
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration import (
    CreateTriggerCommand,
    TriggerDispatcherService,
    UpdateTriggerCommand,
)
from orcia_core.permissions import UserIdentity
from orcia_core.permissions.errors import TriggerNotFoundError

logger = get_logger("orcia.api.workflow_triggers")

router = APIRouter(tags=["workflow-triggers"], responses=TRIGGER_PROBLEM_RESPONSES)


@router.get(
    "/api/v1/workspaces/{workspace_id}/workflows/{workflow_id:path}/triggers",
    response_model=WorkflowTriggerListResponse,
)
async def list_workflow_triggers(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[TriggerDispatcherService, Depends(get_trigger_dispatcher_service)],
) -> WorkflowTriggerListResponse:
    ws_uuid = validate_uuid(workspace_id, "workspace_id")
    await resolve_finops_read_scope(request, user, "WORKSPACE", ws_uuid)
    items = await svc.list_triggers(workspace_id=ws_uuid, workflow_id=workflow_id)
    return WorkflowTriggerListResponse(
        workspace_id=ws_uuid,
        workflow_id=workflow_id,
        items=[serialize_trigger(t) for t in items],
        trace_id=trace_id_from_request(request),
    )


@router.post(
    "/api/v1/workspaces/{workspace_id}/workflows/{workflow_id:path}/triggers",
    response_model=WorkflowTriggerResponse,
    status_code=201,
)
async def create_workflow_trigger(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    body: CreateWorkflowTriggerRequest,
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[TriggerDispatcherService, Depends(get_trigger_dispatcher_service)],
) -> WorkflowTriggerResponse:
    ws_uuid = validate_uuid(workspace_id, "workspace_id")
    await enforce_workspace_governed_mutation(request, user, ws_uuid)
    created = await svc.create_trigger(
        CreateTriggerCommand(
            workspace_id=ws_uuid,
            workflow_id=workflow_id,
            trigger_type=body.trigger_type,
            trigger_key=body.trigger_key,
            cron_expr=body.cron_expr,
            cooldown_window_seconds=body.cooldown_window_seconds,
            max_runs_per_hour=body.max_runs_per_hour,
            max_daily_cost_usd=body.max_daily_cost_usd,
            max_consecutive_failures=body.max_consecutive_failures,
            auto_help_on_publish=body.auto_help_on_publish,
            webhook_secret=parse_secret_input_spec(body.webhook_secret),
            log_sink_service=body.log_sink_service,
            log_sink_query_text=body.log_sink_query_text,
            outbox_event_filter=body.outbox_event_filter,
            status=body.status,
            actor_id=user.id,
        )
    )
    return serialize_trigger(created)


@router.patch(
    "/api/v1/workspaces/{workspace_id}/workflows/{workflow_id:path}/triggers/{trigger_id}",
    response_model=WorkflowTriggerResponse,
)
async def update_workflow_trigger(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    trigger_id: Annotated[str, Path(min_length=1)],
    body: UpdateWorkflowTriggerRequest,
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[TriggerDispatcherService, Depends(get_trigger_dispatcher_service)],
) -> WorkflowTriggerResponse:
    del workflow_id
    ws_uuid = validate_uuid(workspace_id, "workspace_id")
    await enforce_workspace_governed_mutation(request, user, ws_uuid)
    updated = await svc.update_trigger(
        workspace_id=ws_uuid,
        trigger_id=trigger_id,
        cmd=UpdateTriggerCommand(
            status=body.status,
            cron_expr=body.cron_expr,
            cooldown_window_seconds=body.cooldown_window_seconds,
            max_runs_per_hour=body.max_runs_per_hour,
            max_daily_cost_usd=body.max_daily_cost_usd,
            max_consecutive_failures=body.max_consecutive_failures,
            auto_help_on_publish=body.auto_help_on_publish,
            webhook_secret=parse_secret_input_spec(body.webhook_secret),
            log_sink_service=body.log_sink_service,
            log_sink_query_text=body.log_sink_query_text,
            outbox_event_filter=body.outbox_event_filter,
            actor_id=user.id,
        ),
    )
    return serialize_trigger(updated)


@router.delete(
    "/api/v1/workspaces/{workspace_id}/workflows/{workflow_id:path}/triggers/{trigger_id}",
    response_model=DeleteWorkflowTriggerResponse,
)
async def delete_workflow_trigger(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    trigger_id: Annotated[str, Path(min_length=1)],
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[TriggerDispatcherService, Depends(get_trigger_dispatcher_service)],
) -> DeleteWorkflowTriggerResponse:
    del workflow_id
    ws_uuid = validate_uuid(workspace_id, "workspace_id")
    await enforce_workspace_governed_mutation(request, user, ws_uuid)
    await svc.delete_trigger(workspace_id=ws_uuid, trigger_id=trigger_id)
    return DeleteWorkflowTriggerResponse(
        deleted_id=trigger_id, trace_id=trace_id_from_request(request)
    )


@router.post(
    "/api/v1/workspaces/{workspace_id}/workflows/{workflow_id:path}/triggers/{trigger_id}/fire",
    response_model=TriggerDispatchResponse,
    status_code=201,
)
async def fire_manual_workflow_trigger(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    trigger_id: Annotated[str, Path(min_length=1)],
    body: FireManualTriggerRequest,
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[TriggerDispatcherService, Depends(get_trigger_dispatcher_service)],
) -> TriggerDispatchResponse:
    del workflow_id
    ws_uuid = validate_uuid(workspace_id, "workspace_id")
    await enforce_workspace_governed_mutation(request, user, ws_uuid)
    entity, _ = await svc.get_trigger(trigger_id)
    if entity.workspace_id != ws_uuid:
        raise TriggerNotFoundError(instance=str(request.url.path))
    idem_key = (body.idempotency_key or "").strip() or f"manual:{new_uuid7_str()}"
    trace_id = trace_id_from_request(request)
    outcome = await svc.dispatch_trigger(
        trigger_id=trigger_id,
        idempotency_key=idem_key,
        headers=dict(request.headers),
        payload=body.payload,
        trace_id=trace_id,
    )
    return serialize_dispatch_outcome(outcome, trace_id)


@router.post(
    "/api/v1/workspaces/{workspace_id}/workflows/{workflow_id:path}/triggers/{trigger_id}/reset-circuit",
    response_model=WorkflowTriggerResponse,
)
async def reset_workflow_trigger_circuit(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    trigger_id: Annotated[str, Path(min_length=1)],
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[TriggerDispatcherService, Depends(get_trigger_dispatcher_service)],
) -> WorkflowTriggerResponse:
    del workflow_id
    ws_uuid = validate_uuid(workspace_id, "workspace_id")
    await enforce_workspace_governed_mutation(request, user, ws_uuid)
    reset = await svc.reset_circuit(workspace_id=ws_uuid, trigger_id=trigger_id)
    return serialize_trigger(reset)


@router.post("/api/v1/webhooks/triggers/{trigger_id}", response_model=TriggerDispatchResponse)
async def ingest_workflow_trigger_webhook(
    request: Request,
    trigger_id: Annotated[str, Path(min_length=1)],
    svc: Annotated[TriggerDispatcherService, Depends(get_trigger_dispatcher_service)],
    x_orcia_webhook_signature: Annotated[
        str | None, Header(alias="x-orcia-webhook-signature")
    ] = None,
    x_hub_signature_256: Annotated[str | None, Header(alias="x-hub-signature-256")] = None,
    x_webhook_delivery_id: Annotated[str | None, Header(alias="x-webhook-delivery-id")] = None,
) -> TriggerDispatchResponse:
    """Ingest external webhook with shared HMAC verification, deduplication & Self-Trigger Guard."""
    trace_id = trace_id_from_request(request)
    trigger_uuid = validate_uuid(trigger_id, "trigger_id")
    raw_body = await request.body()
    try:
        decoded = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        req_payload = WorkflowTriggerWebhookRequest.model_validate(decoded)
    except Exception as exc:
        logger.warning("invalid_workflow_trigger_webhook_json", error=str(exc))
        req_payload = WorkflowTriggerWebhookRequest(delivery_key=x_webhook_delivery_id)
    delivery_key = (
        x_webhook_delivery_id or req_payload.delivery_key or ""
    ).strip() or new_uuid7_str()
    sig_hdr = x_orcia_webhook_signature or x_hub_signature_256
    entity, is_new = await svc.verify_webhook_request(
        trigger_id=trigger_uuid,
        raw_body=raw_body,
        signature_header=sig_hdr,
        delivery_key=delivery_key,
    )
    if not is_new:
        return TriggerDispatchResponse(
            dispatched=False,
            outcome="DUPLICATE_SUPPRESSED",
            trigger_id=entity.id,
            idempotency_key=delivery_key,
            dbos_workflow_id=f"{entity.id}:{delivery_key}",
            reason="Duplicate webhook delivery suppressed",
            trace_id=trace_id,
        )
    outcome = await svc.dispatch_trigger(
        trigger_id=entity.id,
        idempotency_key=delivery_key,
        headers=dict(request.headers),
        payload=req_payload.model_dump(),
        trace_id=trace_id,
    )
    return serialize_dispatch_outcome(outcome, trace_id)


@router.post("/api/v1/triggers/alerts", response_model=TriggerDispatchResponse)
async def ingest_platform_log_alert_fallback(
    request: Request,
    svc: Annotated[TriggerDispatcherService, Depends(get_trigger_dispatcher_service)],
    x_orcia_webhook_signature: Annotated[
        str | None, Header(alias="x-orcia-webhook-signature")
    ] = None,
    x_hub_signature_256: Annotated[str | None, Header(alias="x-hub-signature-256")] = None,
    x_orcia_alert_secret: Annotated[str | None, Header(alias="x-orcia-alert-secret")] = None,
) -> TriggerDispatchResponse:
    """Platform log-sink alert fallback webhook (`AD-23.5`) protected by HMAC or alert secret."""
    trace_id = trace_id_from_request(request)
    raw_body = await request.body()
    entity, body = await authenticate_platform_alert_webhook(
        request=request,
        svc=svc,
        raw_body=raw_body,
        x_orcia_webhook_signature=x_orcia_webhook_signature,
        x_hub_signature_256=x_hub_signature_256,
        x_orcia_alert_secret=x_orcia_alert_secret,
    )
    fp = compute_error_fingerprint_sha256(
        body.service, body.exception_type, extract_top_frame(body.traceback or body.message)
    )
    idem_key = (body.delivery_key or "").strip() or f"alert:{fp}"
    outcome = await svc.dispatch_trigger(
        trigger_id=entity.id,
        idempotency_key=idem_key,
        headers=dict(request.headers),
        payload=body.model_dump(),
        trace_id=trace_id,
    )
    return serialize_dispatch_outcome(outcome, trace_id)
