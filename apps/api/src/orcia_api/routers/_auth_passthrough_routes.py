"""Passthrough credential route extracted from `auth.py` for volumetric clarity."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_auth_service
from orcia_api.schemas.auth_and_org import (
    PassthroughSecretMetadataResponse,
    PassthroughSecretStoreRequest,
)
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter()


@router.post(
    "/passthrough-credentials",
    response_model=PassthroughSecretMetadataResponse,
    summary="Encrypt and store a user Passthrough credential in AES-256-GCM (NFR-SEC-4)",
)
async def store_passthrough_credential(
    payload: PassthroughSecretStoreRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> PassthroughSecretMetadataResponse:
    """Store a Passthrough token encrypted with AES-256-GCM and per-user HKDF key."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    user = svc.resolve_user(
        persona_key=persona_key,
        bearer_token=request.headers.get("Authorization"),
    )
    record = svc.store_passthrough_credential(
        user,
        connector_scheme=payload.connector_scheme,
        target_host=payload.target_host,
        plaintext_secret=payload.plaintext_secret,
        instance=str(request.url.path),
    )
    broker_svc = getattr(request.app.state, "permission_broker_service", None)
    if broker_svc is not None:
        broker_svc.register_passthrough_credential(record)
    return PassthroughSecretMetadataResponse(
        id=record.id,
        user_id=record.user_id,
        connector_scheme=record.connector_scheme,
        target_host=record.target_host,
        key_version=record.key_version,
        encrypted_at_rest=True,
        trace_id=trace_id,
    )
