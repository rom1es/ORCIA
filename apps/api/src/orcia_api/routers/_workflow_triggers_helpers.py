"""Serialization and alert-ingress helpers for Workflow Triggers router (`MAJOR-05`)."""

from __future__ import annotations

import hmac
import json
import os
from typing import Any

from fastapi import Request

from orcia_api.schemas.problem_details import ProblemDetails
from orcia_api.schemas.settings_and_studio import SecretStatusResponse
from orcia_api.schemas.workflow_triggers import (
    LogSinkAlertWebhookRequest,
    TriggerDispatchResponse,
    WorkflowTriggerResponse,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration import (
    TriggerDispatcherService,
    TriggerDispatchOutcome,
    WorkflowTriggerEntity,
)
from orcia_core.permissions.enterprise_connectors_crypto import unpack_encrypted_secret
from orcia_core.permissions.errors import (
    TriggerNotFoundError,
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


def trace_id_from_request(request: Request) -> str:
    """Resolve current W3C `trace_id` from request state or OTel context."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def parse_secret_input_spec(webhook_secret: Any | None) -> SecretInputSpec | None:
    """Convert optional HTTP `SecretUpdateInput` onto domain `SecretInputSpec`."""
    if webhook_secret is None:
        return None
    return SecretInputSpec(
        action=webhook_secret.action,
        plaintext_value=webhook_secret.plaintext_value,
    )


def serialize_trigger(t: WorkflowTriggerEntity) -> WorkflowTriggerResponse:
    """Map domain `WorkflowTriggerEntity` onto `WorkflowTriggerResponse`."""
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


def serialize_dispatch_outcome(
    res: TriggerDispatchOutcome, trace_id: str
) -> TriggerDispatchResponse:
    """Map `TriggerDispatchOutcome` onto `TriggerDispatchResponse`."""
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


async def authenticate_platform_alert_webhook(
    *,
    request: Request,
    svc: TriggerDispatcherService,
    raw_body: bytes,
    x_orcia_webhook_signature: str | None,
    x_hub_signature_256: str | None,
    x_orcia_alert_secret: str | None,
) -> tuple[WorkflowTriggerEntity, LogSinkAlertWebhookRequest]:
    """Authenticate `/api/v1/triggers/alerts` without exposing a `404` oracle."""
    path = str(request.url.path)
    sig_hdr = x_orcia_webhook_signature or x_hub_signature_256
    if not (sig_hdr or x_orcia_alert_secret):
        raise WebhookSignatureInvalidError(instance=path)

    try:
        decoded = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        body = LogSinkAlertWebhookRequest.model_validate(decoded)
    except Exception as exc:
        logger.warning("invalid_platform_alert_webhook_json", error=str(exc))
        raise ValidationDomainError(
            detail_override="Invalid alert webhook payload.",
            instance=path,
        ) from exc

    try:
        entity, enc_secret = await svc.get_trigger(body.trigger_id)
    except TriggerNotFoundError as exc:
        raise WebhookSignatureInvalidError(instance=path) from exc

    expected_secret: str | None = None
    if enc_secret:
        try:
            expected_secret = unpack_encrypted_secret(
                svc._cipher,
                owner_id=entity.id,
                packed=enc_secret,
                scheme="webhook",
                host="trigger",
            )
        except Exception as exc:
            logger.warning(
                "alert_webhook_secret_unpack_failed",
                trigger_id=entity.id,
                error=type(exc).__name__,
            )
            raise WebhookSignatureInvalidError(instance=path) from exc

    if not expected_secret:
        expected_secret = os.environ.get("ORCIA_ALERTS_WEBHOOK_SECRET", "").strip() or None
    secret_ok = bool(
        expected_secret
        and (
            verify_webhook_hmac_sha256(raw_body, expected_secret, sig_hdr)
            or (x_orcia_alert_secret and hmac.compare_digest(x_orcia_alert_secret, expected_secret))
        )
    )
    if not secret_ok:
        raise WebhookSignatureInvalidError(instance=path)
    return entity, body
