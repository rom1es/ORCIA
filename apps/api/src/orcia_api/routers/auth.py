"""Bi-Mode Authentication Router (`/api/v1/auth/*`, AD-6, NFR-SEC-4)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request, Response

from orcia_core.domain.exceptions import InvalidCredentialsError, OrciaDomainError
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions import (
    REFRESH_TOKEN_TTL_SECONDS,
    AuthAndOrganizationService,
    SessionTokenPair,
    UserIdentity,
    WorkspaceAccessSummary,
    build_default_auth_and_org_service,
)
from orcia_core.schemas.auth_and_org import (
    AuthTokenResponse,
    LocalLoginRequest,
    LogoutResponse,
    OidcLoginRequest,
    OrgUnitTreeItem,
    PassthroughSecretMetadataResponse,
    PassthroughSecretStoreRequest,
    UserMeResponse,
    WorkspaceDatasourceItem,
    WorkspaceSummaryItem,
)
from orcia_core.schemas.problem_details import ProblemDetails

REFRESH_COOKIE_NAME: str = "orcia_refresh_token"

PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

_DEFAULT_AUTH_SERVICE = build_default_auth_and_org_service()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_auth_service(request: Request) -> AuthAndOrganizationService:
    """Return the active `AuthAndOrganizationService` attached to `app.state` or default."""
    svc: AuthAndOrganizationService | None = getattr(request.app.state, "auth_service", None)
    return svc if svc is not None else _DEFAULT_AUTH_SERVICE


def resolve_request_user(request: Request, persona_key: str | None = None) -> UserIdentity:
    """Resolve authenticated `UserIdentity` from `Authorization: Bearer ...` or `persona_key`."""
    svc = get_auth_service(request)
    return svc.resolve_user(
        persona_key=persona_key, bearer_token=request.headers.get("Authorization")
    )


def serialize_workspace_summary(item: WorkspaceAccessSummary) -> WorkspaceSummaryItem:
    """Convert domain `WorkspaceAccessSummary` into Pydantic `WorkspaceSummaryItem`."""
    ws = item.workspace
    return WorkspaceSummaryItem(
        id=ws.id,
        slug=ws.slug,
        name=ws.name,
        owner_org_unit_id=ws.owner_org_unit_id,
        visibility_mode=ws.visibility_mode,
        effective_role=item.effective_role,
        access_mode=item.access_mode,
        access_origin=item.access_origin,
        finops_cost_usd=ws.finops_cost_usd if item.finops_visible else None,
        datasources=[
            WorkspaceDatasourceItem(
                id=ds.id,
                workspace_id=ds.workspace_id,
                alias=ds.alias,
                scheme=ds.scheme,
                uri=ds.uri,
                role=ds.role,
                execution_identity=ds.execution_identity,
                freshness_ttl_days=ds.freshness_ttl_days,
            )
            for ds in ws.datasources
        ],
    )


def _issue_auth_response(
    response: Response, user: UserIdentity, tokens: SessionTokenPair, trace_id: str
) -> AuthTokenResponse:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=tokens.refresh_token,
        max_age=REFRESH_TOKEN_TTL_SECONDS,
        path="/api/v1/auth",
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return AuthTokenResponse(
        access_token=tokens.access_token,
        expires_in_seconds=tokens.expires_in_seconds,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        platform_role=user.platform_role,
        human_profile_archetype=user.human_profile_archetype,
        primary_org_unit_id=user.primary_org_unit_id,
        trace_id=trace_id,
    )


@router.post(
    "/login/local",
    response_model=AuthTokenResponse,
    summary="Authenticate via Local Argon2id password and optional RFC 6238 TOTP MFA",
    responses=PROBLEM_RESPONSES,
)
async def login_local(
    payload: LocalLoginRequest, request: Request, response: Response
) -> AuthTokenResponse:
    """Authenticate local user, issue 15-min JWT, and set HttpOnly refresh cookie."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    user, tokens = svc.login_local(payload.email, payload.password, totp_code=payload.totp_code)
    return _issue_auth_response(response, user, tokens, trace_id)


@router.post(
    "/login/oidc",
    response_model=AuthTokenResponse,
    summary="Authenticate via Enterprise SSO OIDC / OAuth 2.1 subject claim",
    responses=PROBLEM_RESPONSES,
)
async def login_oidc(
    payload: OidcLoginRequest, request: Request, response: Response
) -> AuthTokenResponse:
    """Authenticate OIDC user, issue 15-min JWT, and set HttpOnly refresh cookie."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    user, tokens = svc.login_oidc(payload.oidc_subject, email=payload.email)
    return _issue_auth_response(response, user, tokens, trace_id)


@router.post(
    "/refresh",
    response_model=AuthTokenResponse,
    summary="Rotate HttpOnly refresh token and issue a fresh 15-minute access JWT",
    responses=PROBLEM_RESPONSES,
)
async def refresh_session(request: Request, response: Response) -> AuthTokenResponse:
    """Rotate refresh token (revoking previous `jti` in Redis/memory) and issue new JWT."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    raw_refresh = request.headers.get("X-Refresh-Token") or request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise InvalidCredentialsError(instance=str(request.url.path))
    user, tokens = svc.refresh_session(raw_refresh)
    return _issue_auth_response(response, user, tokens, trace_id)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Revoke active session tokens and clear HttpOnly refresh cookie",
    responses=PROBLEM_RESPONSES,
)
async def logout_session(request: Request, response: Response) -> LogoutResponse:
    """Revoke refresh and/or access token `jti` and clear cookie."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    raw_refresh = request.headers.get("X-Refresh-Token") or request.cookies.get(REFRESH_COOKIE_NAME)
    auth_header = request.headers.get("Authorization")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/v1/auth")
    if not raw_refresh and not auth_header:
        raise InvalidCredentialsError(instance=str(request.url.path))

    errors: list[OrciaDomainError] = []
    revoked_any = False
    if raw_refresh:
        try:
            svc.revoke_token(raw_refresh, expected_type="refresh")
            revoked_any = True
        except OrciaDomainError as exc:
            errors.append(exc)
    if auth_header:
        raw_access = auth_header.removeprefix("Bearer ").removeprefix("bearer ").strip()
        try:
            svc.revoke_token(raw_access, expected_type="access")
            revoked_any = True
        except OrciaDomainError as exc:
            errors.append(exc)

    if not revoked_any and errors:
        raise errors[0]
    return LogoutResponse(revoked=True, trace_id=trace_id)


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get authenticated Human Profile, OrgUnit tree, and accessible Multi-Source Workspaces",
    responses=PROBLEM_RESPONSES,
)
async def get_current_user_me(
    request: Request,
    persona_key: str | None = Query(
        default=None,
        min_length=1,
        max_length=64,
        description="Optional persona key (`karim`, `claire`, `marc`, `nadia`, `partenaire`).",
    ),
) -> UserMeResponse:
    """Return full Human Profile, OrgUnit tree, accessible Workspaces, and RBAC module flags."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    user = resolve_request_user(request, persona_key=persona_key)
    accessible = svc.evaluator.resolve_accessible_workspaces(user)
    finops_total = svc.evaluator.compute_finops_rollup_usd(user)
    modules_map = svc.evaluator.evaluate_module_permissions(user)

    return UserMeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        auth_mode=user.auth_mode,
        human_profile_archetype=user.human_profile_archetype,
        platform_role=user.platform_role,
        primary_org_unit_id=user.primary_org_unit_id,
        totp_enabled=user.totp_enabled,
        transverse_groups=list(user.transverse_groups),
        org_units=[
            OrgUnitTreeItem(
                id=u.id, slug=u.slug, name=u.name, unit_type=u.unit_type, parent_id=u.parent_id
            )
            for u in svc.evaluator.org_units
        ],
        workspaces=[serialize_workspace_summary(item) for item in accessible],
        consolidated_finops_usd=finops_total,
        modules=modules_map,
        trace_id=trace_id,
    )


@router.post(
    "/passthrough-credentials",
    response_model=PassthroughSecretMetadataResponse,
    summary="Encrypt and store a user Passthrough credential in AES-256-GCM (NFR-SEC-4)",
    responses=PROBLEM_RESPONSES,
)
async def store_passthrough_credential(
    payload: PassthroughSecretStoreRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> PassthroughSecretMetadataResponse:
    """Store a Passthrough token encrypted with AES-256-GCM and per-user HKDF key."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    user = resolve_request_user(request, persona_key=persona_key)
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
