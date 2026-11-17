"""Workflow Triggers CRUD, Manual Fire, Webhook Ingress & Alert Fallback (`Story 7.2`, `AD-18`)."""

from __future__ import annotations

import hmac
import json
import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Path, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_trigger_dispatcher_service,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_api.schemas.settings_and_studio import SecretStatusResponse
from orcia_api.schemas.workflow_triggers import (
    CreateWorkflowTriggerRequest,
    DeleteWorkflowTriggerResponse,
    FireManualTriggerRequest,
    LogSinkAlertWebhookRequest,
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
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration import (
    CreateTriggerCommand,
    TriggerDispatcherService,
    TriggerDispatchOutcome,
    UpdateTriggerCommand,
    WorkflowTriggerEntity,
)
from orcia_core.permissions import AuthAndOrganizationService, UserIdentity
from orcia_core.permissions.enterprise_connectors_crypto import unpack_encrypted_secret
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ValidationDomainError,
    WebhookSignatureInvalidError,
)
from orcia_core.permissions.secret_hint import SecretInputSpec
from orcia_core.permissions.webhook_security import verify_webhook_hmac_sha256

logger = get_logger("orcia.api.workflow_triggers")

TRIGGER_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    503: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(tags=["workflow-triggers"], responses=TRIGGER_PROBLEM_RESPONSES)


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _enforce_not_observer(
    request: Request,
    user: UserIdentity,
    auth_svc: AuthAndOrganizationService,
    workspace_id: str,
) -> None:
    instance = str(request.url.path)
    if (
        request.headers.get("X-Orcia-Access-Mode", "").strip().upper() == "READ_ONLY_OBSERVER"
        or user.platform_role == "OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=instance)
    ws_access = auth_svc.evaluator.resolve_workspace_access(user, workspace_id)
    if ws_access is not None and ws_access.access_mode == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)


def _serialize_trigger(t: WorkflowTriggerEntity) -> WorkflowTriggerResponse:
    return WorkflowTriggerResponse(
        id=t.id,
        trigger_key=t.trigger_key,
        workspace_id=t.workspace_id,
        workflow_id=t.workflow_id,
        trigger_type=t.trigger_type,
        contract_id=t.contract_id,
        cron_expr=t.cron_expr,
        cooldown_window_seconds=t.cooldown_window_seconds,
        service_principal_id=t.service_principal_id,
        max_runs_per_hour=t.max_runs_per_hour,
        max_daily_cost_usd=t.max_daily_cost_usd,
        max_consecutive_failures=t.max_consecutive_failures,
        consecutive_failures=t.consecutive_failures,
        status=t.status,
        auto_help_on_publish=t.auto_help_on_publish,
        last_fired_at_iso=t.last_fired_at_iso,
        log_sink_service=t.log_sink_service,
        log_sink_query_text=t.log_sink_query_text,
        outbox_event_filter=t.outbox_event_filter,
        webhook_secret_status=SecretStatusResponse(
            configured=t.webhook_secret_configured,
            fingerprint=t.webhook_secret_fingerprint,
            masked_hint=t.webhook_secret_masked_hint,
            updated_at=t.webhook_secret_updated_at or "",
            updated_by=t.webhook_secret_updated_by or "",
        ),
    )


def _serialize_dispatch(res: TriggerDispatchOutcome, trace_id: str) -> TriggerDispatchResponse:
    return TriggerDispatchResponse(
        dispatched=res.dispatched,
        outcome=res.outcome,
        trigger_id=res.trigger_id,
        idempotency_key=res.idempotency_key,
        dbos_workflow_id=res.dbos_workflow_id,
        run_id=res.run_id,
        attempts=res.attempts,
        reason=res.reason,
        trace_id=trace_id,
    )


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
    del user
    items = await svc.list_triggers(workspace_id=workspace_id, workflow_id=workflow_id)
    return WorkflowTriggerListResponse(
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        items=[_serialize_trigger(t) for t in items],
        trace_id=_trace(request),
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
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
) -> WorkflowTriggerResponse:
    _enforce_not_observer(request, user, auth_svc, workspace_id)
    secret_spec = (
        SecretInputSpec(
            action=body.webhook_secret.action,
            plaintext_value=body.webhook_secret.plaintext_value,
        )
        if body.webhook_secret is not None
        else None
    )
    created = await svc.create_trigger(
        CreateTriggerCommand(
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            trigger_type=body.trigger_type,
            trigger_key=body.trigger_key,
            cron_expr=body.cron_expr,
            cooldown_window_seconds=body.cooldown_window_seconds,
            max_runs_per_hour=body.max_runs_per_hour,
            max_daily_cost_usd=body.max_daily_cost_usd,
            max_consecutive_failures=body.max_consecutive_failures,
            auto_help_on_publish=body.auto_help_on_publish,
            webhook_secret=secret_spec,
            log_sink_service=body.log_sink_service,
            log_sink_query_text=body.log_sink_query_text,
            outbox_event_filter=body.outbox_event_filter,
            status=body.status,
            actor_id=user.id,
        )
    )
    return _serialize_trigger(created)


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
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
) -> WorkflowTriggerResponse:
    del workflow_id
    _enforce_not_observer(request, user, auth_svc, workspace_id)
    secret_spec = (
        SecretInputSpec(
            action=body.webhook_secret.action,
            plaintext_value=body.webhook_secret.plaintext_value,
        )
        if body.webhook_secret is not None
        else None
    )
    updated = await svc.update_trigger(
        workspace_id=workspace_id,
        trigger_id=trigger_id,
        cmd=UpdateTriggerCommand(
            status=body.status,
            cron_expr=body.cron_expr,
            cooldown_window_seconds=body.cooldown_window_seconds,
            max_runs_per_hour=body.max_runs_per_hour,
            max_daily_cost_usd=body.max_daily_cost_usd,
            max_consecutive_failures=body.max_consecutive_failures,
            auto_help_on_publish=body.auto_help_on_publish,
            webhook_secret=secret_spec,
            log_sink_service=body.log_sink_service,
            log_sink_query_text=body.log_sink_query_text,
            outbox_event_filter=body.outbox_event_filter,
            actor_id=user.id,
        ),
    )
    return _serialize_trigger(updated)


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
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
) -> DeleteWorkflowTriggerResponse:
    del workflow_id
    _enforce_not_observer(request, user, auth_svc, workspace_id)
    await svc.delete_trigger(workspace_id=workspace_id, trigger_id=trigger_id)
    return DeleteWorkflowTriggerResponse(deleted_id=trigger_id, trace_id=_trace(request))


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
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
) -> TriggerDispatchResponse:
    del workflow_id
    _enforce_not_observer(request, user, auth_svc, workspace_id)
    idem_key = (body.idempotency_key or "").strip() or f"manual:{new_uuid7_str()}"
    outcome = await svc.dispatch_trigger(
        trigger_id=trigger_id,
        idempotency_key=idem_key,
        headers=dict(request.headers),
        payload=body.payload,
        trace_id=_trace(request),
    )
    return _serialize_dispatch(outcome, _trace(request))


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
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
) -> WorkflowTriggerResponse:
    del workflow_id
    _enforce_not_observer(request, user, auth_svc, workspace_id)
    reset = await svc.reset_circuit(workspace_id=workspace_id, trigger_id=trigger_id)
    return _serialize_trigger(reset)


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
    trace_id = _trace(request)
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
        trigger_id=trigger_id,
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
    return _serialize_dispatch(outcome, trace_id)


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
    trace_id = _trace(request)
    raw_body = await request.body()
    try:
        decoded = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        body = LogSinkAlertWebhookRequest.model_validate(decoded)
    except Exception as exc:
        logger.warning("invalid_platform_alert_webhook_json", error=str(exc))
        raise ValidationDomainError(
            detail_override="Invalid alert webhook payload.",
            instance=str(request.url.path),
        ) from exc
    entity, enc_secret = await svc.get_trigger(body.trigger_id)
    expected_secret: str | None = None
    if enc_secret:
        expected_secret = unpack_encrypted_secret(
            svc._cipher, owner_id=entity.id, packed=enc_secret, scheme="webhook", host="trigger"
        )
    if not expected_secret:
        expected_secret = os.environ.get("ORCIA_ALERTS_WEBHOOK_SECRET", "").strip() or None
    sig_hdr = x_orcia_webhook_signature or x_hub_signature_256
    secret_ok = bool(
        expected_secret
        and (
            verify_webhook_hmac_sha256(raw_body, expected_secret, sig_hdr)
            or (x_orcia_alert_secret and hmac.compare_digest(x_orcia_alert_secret, expected_secret))
        )
    )
    if not secret_ok:
        raise WebhookSignatureInvalidError(instance=str(request.url.path))
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
    return _serialize_dispatch(outcome, trace_id)
