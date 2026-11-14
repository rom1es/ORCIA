"""Story 18.2 — Datasource Webhook Ingress & 24h Staleness Reconciler Router.

Exposes:
- `POST /api/v1/webhooks/datasources/{datasource_id}`
- `POST /api/v1/workspaces/{workspace_id}/datasources/reconcile-staleness`
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Header, Path, Request

from orcia_api.dependencies import get_or_create_shared_db_engine
from orcia_api.schemas.datasource_webhooks import (
    DatasourceWebhookIngressRequest,
    DatasourceWebhookIngressResponse,
    ReconcileWorkspaceStalenessItem,
    ReconcileWorkspaceStalenessResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.bootstrap._internal.sql_datasource_freshness import (
    get_datasource_webhook_context_from_postgres18,
    record_webhook_delivery_and_outbox,
    update_datasource_freshness_state,
)
from orcia_core.bootstrap._internal.sql_workspace_datasources_queries import (
    list_workspace_datasources_from_postgres18,
)
from orcia_core.kernel.events import (
    DatasourceSyncRequested,
)
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import (
    extract_url_host,
    unpack_encrypted_secret,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    WebhookSignatureInvalidError,
)
from orcia_core.rag.source_freshness_reconciler import (
    RECONCILE_OUTCOME_NO_OP_UNCHANGED,
    evaluate_24h_freshness_probe,
    reconcile_incoming_fingerprint,
)

logger = get_logger("orcia.api.datasource_webhooks")

WEBHOOK_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(tags=["datasource-webhooks"], responses=WEBHOOK_PROBLEM_RESPONSES)


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _verify_hmac(raw_body: bytes, secret: str, signature_header: str | None) -> bool:
    if not signature_header:
        return False
    clean = signature_header.strip()
    if clean.startswith("sha256="):
        clean = clean[7:].strip()
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.lower(), clean.lower())


@router.post(
    "/api/v1/webhooks/datasources/{datasource_id}",
    response_model=DatasourceWebhookIngressResponse,
    status_code=200,
)
async def ingest_datasource_webhook(
    request: Request,
    datasource_id: Annotated[str, Path(description="Target datasource ID")],
    x_orcia_webhook_signature: Annotated[
        str | None, Header(alias="x-orcia-webhook-signature")
    ] = None,
    x_hub_signature_256: Annotated[str | None, Header(alias="x-hub-signature-256")] = None,
    x_webhook_delivery_id: Annotated[str | None, Header(alias="x-webhook-delivery-id")] = None,
) -> DatasourceWebhookIngressResponse:
    """Ingest a provider webhook with HMAC-SHA256 verification and SHA-256 short-circuit."""
    trace_id = _trace(request)
    raw_body = await request.body()
    try:
        body_json = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        req_payload = DatasourceWebhookIngressRequest.model_validate(body_json)
    except Exception as exc:
        logger.warning("Invalid JSON webhook body: %s", exc)
        req_payload = DatasourceWebhookIngressRequest(
            delivery_key=x_webhook_delivery_id or new_uuid7_str(),
            remote_fingerprint_sha256="unknown",
        )

    engine = get_or_create_shared_db_engine(request)
    ctx = await get_datasource_webhook_context_from_postgres18(engine, datasource_id=datasource_id)
    if ctx is None:
        raise ResourceNotFoundError(
            detail_override=f"Datasource '{datasource_id}' not found.",
            instance=str(request.url.path),
        )

    # Resolve webhook secret and verify HMAC-SHA256
    auth_svc = getattr(request.app.state, "auth_service", None)
    cipher = (
        getattr(auth_svc, "vault_cipher", None)
        or getattr(request.app.state, "vault_cipher", None)
        or PassthroughVaultCipher(os.environ.get("ORCIA_PASSTHROUGH_MASTER_KEY", "0" * 32))
    )
    sig_hdr = x_orcia_webhook_signature or x_hub_signature_256
    webhook_secret: str | None = None
    if ctx.webhook_secret_encrypted:
        try:
            webhook_secret = unpack_encrypted_secret(
                cipher,
                owner_id=ctx.connector_id or ctx.datasource_id,
                packed=ctx.webhook_secret_encrypted,
                scheme=ctx.connector_scheme or "git",
                host=extract_url_host(ctx.connector_base_url or ""),
            )
        except Exception as exc:
            logger.warning("Failed to decrypt webhook secret: %s", exc)
    if not webhook_secret:
        webhook_secret = os.environ.get("ORCIA_DEFAULT_WEBHOOK_SECRET")

    if (webhook_secret or sig_hdr) and (
        not webhook_secret or not _verify_hmac(raw_body, webhook_secret, sig_hdr)
    ):
        raise WebhookSignatureInvalidError(instance=str(request.url.path))

    delivery_key = x_webhook_delivery_id or req_payload.delivery_key
    outcome = reconcile_incoming_fingerprint(
        ctx.fingerprint_hash, req_payload.remote_fingerprint_sha256
    )
    delivery_id = new_uuid7_str()
    now = datetime.now(UTC)

    if outcome == RECONCILE_OUTCOME_NO_OP_UNCHANGED:
        # Short-circuit: SHA-256 unchanged -> no Outbox event published, 0 $ LLM
        inserted = await record_webhook_delivery_and_outbox(
            engine,
            delivery_id=delivery_id,
            workspace_id=ctx.workspace_id,
            datasource_id=ctx.datasource_id,
            delivery_key=delivery_key,
            provider_event=req_payload.provider_event,
            remote_fingerprint_sha256=req_payload.remote_fingerprint_sha256,
            reconcile_outcome="NO_OP_UNCHANGED",
            outbox_event=None,
        )
        await update_datasource_freshness_state(
            engine,
            datasource_id=ctx.datasource_id,
            last_probe_at=now,
        )
        return DatasourceWebhookIngressResponse(
            accepted=True,
            outcome="ALREADY_PROCESSED" if not inserted else "NO_OP_UNCHANGED",
            delivery_key=delivery_key,
            datasource_id=datasource_id,
            outbox_published=False,
            trace_id=trace_id,
        )

    # Delta sync required: publish DatasourceSyncRequested
    outbox_event = DatasourceSyncRequested.create(
        datasource_id=ctx.datasource_id,
        workspace_id=ctx.workspace_id,
        source_nature=ctx.source_nature,
        trigger_reason="WEBHOOK_PUSH",
        target_ref=req_payload.ref or ctx.target_ref,
        delivery_key=delivery_key,
        remote_fingerprint_sha256=req_payload.remote_fingerprint_sha256,
        trace_id=trace_id,
    )
    inserted = await record_webhook_delivery_and_outbox(
        engine,
        delivery_id=delivery_id,
        workspace_id=ctx.workspace_id,
        datasource_id=ctx.datasource_id,
        delivery_key=delivery_key,
        provider_event=req_payload.provider_event,
        remote_fingerprint_sha256=req_payload.remote_fingerprint_sha256,
        reconcile_outcome="DELTA_SYNC_REQUIRED",
        outbox_event=outbox_event,
    )
    if inserted:
        await update_datasource_freshness_state(
            engine,
            datasource_id=ctx.datasource_id,
            fingerprint_hash=req_payload.remote_fingerprint_sha256,
            last_sync_at=now,
            last_probe_at=now,
            freshness_status="SYNCED",
        )

    return DatasourceWebhookIngressResponse(
        accepted=True,
        outcome="ALREADY_PROCESSED" if not inserted else "DELTA_SYNC_REQUIRED",
        delivery_key=delivery_key,
        datasource_id=datasource_id,
        outbox_published=inserted,
        trace_id=trace_id,
    )


@router.post(
    "/api/v1/workspaces/{workspace_id}/datasources/reconcile-staleness",
    response_model=ReconcileWorkspaceStalenessResponse,
    status_code=200,
)
async def reconcile_workspace_staleness(
    request: Request,
    workspace_id: Annotated[str, Path(description="Target workspace ID")],
) -> ReconcileWorkspaceStalenessResponse:
    """Evaluate 24h freshness on workspace datasources and trigger delta sync if stale."""
    # RBAC guard: reject read-only observer
    hdr_mode = request.headers.get("x-orcia-access-mode", "").strip().upper()
    hdr_obs = request.headers.get("x-orcia-observer-mode", "").strip().lower()
    if hdr_mode == "READ_ONLY_OBSERVER" or hdr_obs in ("1", "true", "yes"):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))

    trace_id = _trace(request)
    engine = get_or_create_shared_db_engine(request)
    datasources = await list_workspace_datasources_from_postgres18(
        engine, workspace_id=workspace_id
    )
    now = datetime.now(UTC)
    results: list[ReconcileWorkspaceStalenessItem] = []
    stale_count = 0
    synced_count = 0

    for ds in datasources:
        last_sig_str = ds.last_probe_at_iso or ds.last_sync_at_iso or ds.created_at_iso
        last_sig: datetime | None = None
        if last_sig_str:
            try:
                last_sig = datetime.fromisoformat(last_sig_str)
            except Exception as exc:
                logger.warning("Failed to parse datasource last signal timestamp: %s", exc)
                last_sig = None

        eval_res = await evaluate_24h_freshness_probe(
            stored_hash=ds.fingerprint_hash,
            last_signal_at=last_sig,
            current_time=now,
            probe=None,
            datasource_id=ds.id,
            target_ref=ds.target_ref,
            target_scope=ds.target_scope,
        )

        if eval_res.freshness_status == "STALE":
            stale_count += 1
        else:
            synced_count += 1

        await update_datasource_freshness_state(
            engine,
            datasource_id=ds.id,
            freshness_status=eval_res.freshness_status,
            last_probe_at=now,
        )

        results.append(
            ReconcileWorkspaceStalenessItem(
                datasource_id=ds.id,
                alias=ds.alias,
                freshness_status=eval_res.freshness_status,
                outcome=eval_res.outcome,
                elapsed_hours=eval_res.elapsed_hours,
                delta_sync_needed=eval_res.delta_sync_needed,
                probed_fingerprint=eval_res.probed_fingerprint,
            )
        )

    return ReconcileWorkspaceStalenessResponse(
        workspace_id=workspace_id,
        evaluated_count=len(results),
        stale_count=stale_count,
        synced_count=synced_count,
        results=results,
        trace_id=trace_id,
    )
