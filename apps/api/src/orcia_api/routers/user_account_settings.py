"""Story 20.3 — User Account Preferences & Personal IDE/MCP Tokens Router (PG18)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_user_preferences_and_mcp_token_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.auth_and_org import (
    McpPersonalTokenCreateRequest,
    McpPersonalTokenIssuedResponse,
    McpPersonalTokenListResponse,
    McpPersonalTokenMetadataItem,
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
)
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.user_preferences_and_mcp_tokens import ScopedMcpPersonalTokenRecord

router = APIRouter(prefix="/api/v1", tags=["user-account-settings"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _enforce_not_observer_for_mcp(request: Request, user: UserIdentity) -> None:
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()
    upper_roles = {r.strip().upper() for r in user.roles}
    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or observer_hdr in ("1", "true", "yes")
        or user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER")
        or "OBSERVER" in upper_roles
        or "READ_ONLY_OBSERVER" in upper_roles
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))


def _serialize_mcp_token_record(rec: ScopedMcpPersonalTokenRecord) -> McpPersonalTokenMetadataItem:
    return McpPersonalTokenMetadataItem(
        token_id=rec.token_id,
        user_id=rec.user_id,
        label=rec.label,
        token_prefix=rec.token_prefix,
        token_sha256=rec.token_sha256,
        expires_in_days=rec.expires_in_days,
        rpm_limit=rec.rpm_limit,
        allowed_workspace_slugs=list(rec.allowed_workspace_slugs),
        exposed_capabilities=list(rec.exposed_capabilities),
        target_kind=rec.target_kind,
        target_slug=rec.target_slug,
        mcp_endpoint_uri=rec.mcp_endpoint_uri,
        ide_json_snippet=rec.ide_json_snippet,
        revoked=rec.revoked,
        created_at_iso=rec.created_at_iso,
        expires_at_iso=rec.expires_at_iso,
        revoked_at_iso=rec.revoked_at_iso,
    )


@router.get(
    "/users/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Get current user's display, assistant & notification preferences (PG18)",
    responses=PROBLEM_RESPONSES,
)
async def get_my_preferences(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> UserPreferencesResponse:
    """Return persisted preferences for the authenticated user."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_user_preferences_and_mcp_token_service(request)
    prefs = await svc.get_preferences(user.id)
    return UserPreferencesResponse(**asdict(prefs), trace_id=_trace(request))


@router.patch(
    "/users/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Persist user preferences (`0 ms` Anti-FOUC & Assistant personalization in PG18)",
    responses=PROBLEM_RESPONSES,
)
async def patch_my_preferences(
    request: Request,
    body: UserPreferencesUpdateRequest,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> UserPreferencesResponse:
    """Upsert preferences for the authenticated user in PostgreSQL 18."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_user_preferences_and_mcp_token_service(request)
    prefs = await svc.update_preferences(
        user_id=user.id,
        theme=body.theme,
        locale=body.locale,
        default_hat=body.default_hat,
        default_assistant_hat=body.default_assistant_hat,
        assistant_tone=body.assistant_tone,
        personal_instructions=body.personal_instructions,
        auto_open_contextual_help=body.auto_open_contextual_help,
        notifications_enabled=body.notifications_enabled,
    )
    return UserPreferencesResponse(**asdict(prefs), trace_id=_trace(request))


@router.get(
    "/users/me/mcp-tokens",
    response_model=McpPersonalTokenListResponse,
    summary="List personal IDE/MCP tokens (`pat_mcp_*` SHA-256 metadata, never plaintext)",
    responses=PROBLEM_RESPONSES,
)
async def list_my_mcp_tokens(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> McpPersonalTokenListResponse:
    """List personal MCP token metadata rows strictly isolated to the authenticated user."""
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_user_preferences_and_mcp_token_service(request)
    records = await svc.list_user_mcp_tokens(user.id)
    return McpPersonalTokenListResponse(
        tokens=[_serialize_mcp_token_record(r) for r in records],
        trace_id=_trace(request),
    )


@router.post(
    "/users/me/mcp-tokens",
    response_model=McpPersonalTokenIssuedResponse,
    status_code=201,
    summary="Issue a scoped personal IDE/MCP token (`pat_mcp_*` hashed SHA-256 in PG18)",
    responses=PROBLEM_RESPONSES,
)
async def create_my_mcp_token(
    request: Request,
    body: McpPersonalTokenCreateRequest,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> McpPersonalTokenIssuedResponse:
    """Issue a `pat_mcp_*` token (plaintext returned once at creation, SHA-256 in PG18)."""
    user = resolve_request_user(request, persona_key=persona_key)
    _enforce_not_observer_for_mcp(request, user)
    svc = get_user_preferences_and_mcp_token_service(request)
    issued = await svc.issue_mcp_token(
        user_id=user.id,
        label=body.label,
        expires_in_days=body.expires_in_days,
        rpm_limit=body.rpm_limit,
        allowed_workspace_slugs=tuple(body.allowed_workspace_slugs),
        exposed_capabilities=tuple(body.exposed_capabilities),
        target_kind=body.target_kind,
        target_slug=body.target_slug,
    )
    return McpPersonalTokenIssuedResponse(
        plaintext_token=issued.plaintext_token,
        record=_serialize_mcp_token_record(issued.record),
        trace_id=_trace(request),
    )


@router.delete(
    "/users/me/mcp-tokens/{token_id}",
    response_model=McpPersonalTokenMetadataItem,
    summary="Revoke a personal IDE/MCP token owned by the authenticated user",
    responses=PROBLEM_RESPONSES,
)
async def revoke_my_mcp_token(
    request: Request,
    token_id: str,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> McpPersonalTokenMetadataItem:
    """Revoke `token_id` strictly scoped to `user.id` (`403` for `OBSERVER`, `404` otherwise)."""
    user = resolve_request_user(request, persona_key=persona_key)
    _enforce_not_observer_for_mcp(request, user)
    svc = get_user_preferences_and_mcp_token_service(request)
    revoked = await svc.revoke_mcp_token(user_id=user.id, token_id=token_id)
    return _serialize_mcp_token_record(revoked)
