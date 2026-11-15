"""Session maintenance routes (`/session`, `/refresh`, `/logout`, `/change-password`, `/me`)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Query, Request, Response

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.routers._auth_pg_helpers import (
    REFRESH_COOKIE_NAME,
    execute_change_password,
    hydrate_user_identity_from_pg,
    rehydrate_user_from_pg_by_id,
    serialize_workspace_summary,
)
from orcia_api.routers._auth_policy_runtime import trace_id_for
from orcia_api.routers._auth_token_issuer import (
    PROBLEM_RESPONSES,
    resolve_request_user,
    serialize_auth_token_response,
)
from orcia_api.schemas.auth_and_org import (
    AuthTokenResponse,
    LogoutResponse,
    OrgUnitTreeItem,
    UserMeResponse,
)
from orcia_api.schemas.auth_policy import AuthSessionBootstrapResponse
from orcia_api.schemas.iam_password_models import (
    ChangePasswordRequest,
    ChangePasswordResponse,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import AuthAndOrganizationService
from orcia_core.permissions.errors import (
    InvalidCredentialsError,
    OrciaDomainError,
    ResourceNotFoundError,
)

logger = get_logger("orcia.api.auth.session")
router = APIRouter()


def _pg_enabled() -> bool:
    return os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1"


async def _rotate_refresh_and_hydrate(
    request: Request,
    response: Response,
    *,
    raw_refresh: str,
    trace_id: str,
    svc: AuthAndOrganizationService,
) -> AuthTokenResponse:
    """Shared refresh rotation + optional PostgreSQL identity enrichment."""
    claims = svc.verify_refresh_token_claims(raw_refresh)
    if not svc.has_user_in_memory(claims.sub) and _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            await rehydrate_user_from_pg_by_id(engine, svc, claims.sub, auth_mode=claims.auth_mode)
        except Exception as exc:
            logger.warning("auth_refresh_pg_pre_hydration_failed", error_type=type(exc).__name__)

    user, tokens = svc.refresh_session(raw_refresh)
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            user = await hydrate_user_identity_from_pg(engine, user, svc=svc)
        except ResourceNotFoundError:
            raise
        except Exception as exc:
            logger.warning("auth_refresh_pg_hydration_failed", error_type=type(exc).__name__)
    return serialize_auth_token_response(response, user, tokens, trace_id, request)


@router.get(
    "/session",
    response_model=AuthSessionBootstrapResponse,
    summary="Bootstrap browser session without 401 noise when anonymous or cookie stale",
    responses=PROBLEM_RESPONSES,
)
async def get_session_bootstrap(
    request: Request, response: Response
) -> AuthSessionBootstrapResponse:
    """Return `{authenticated: false, session: null}` with HTTP 200 when unauthenticated."""
    trace_id = trace_id_for(request)
    raw_refresh = request.headers.get("X-Refresh-Token") or request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        return AuthSessionBootstrapResponse(authenticated=False, session=None, trace_id=trace_id)

    svc = get_auth_service(request)
    try:
        token_response = await _rotate_refresh_and_hydrate(
            request, response, raw_refresh=raw_refresh, trace_id=trace_id, svc=svc
        )
        return AuthSessionBootstrapResponse(
            authenticated=True,
            session=token_response,
            trace_id=trace_id,
        )
    except OrciaDomainError as exc:
        response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/v1/auth")
        logger.info("auth.session_bootstrap_cleared_stale_cookie", error_code=exc.error_code)
        return AuthSessionBootstrapResponse(authenticated=False, session=None, trace_id=trace_id)


@router.post(
    "/refresh",
    response_model=AuthTokenResponse,
    summary="Rotate HttpOnly refresh token and issue a fresh 15-minute access JWT",
    responses=PROBLEM_RESPONSES,
)
async def refresh_session(request: Request, response: Response) -> AuthTokenResponse:
    """Rotate refresh token (revoking previous `jti` in Redis/memory) and issue new JWT."""
    trace_id = trace_id_for(request)
    svc = get_auth_service(request)
    raw_refresh = request.headers.get("X-Refresh-Token") or request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise InvalidCredentialsError(instance=str(request.url.path))
    return await _rotate_refresh_and_hydrate(
        request, response, raw_refresh=raw_refresh, trace_id=trace_id, svc=svc
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Revoke active session tokens and clear HttpOnly refresh cookie",
    responses=PROBLEM_RESPONSES,
)
async def logout_session(request: Request, response: Response) -> LogoutResponse:
    """Revoke refresh and/or access token `jti` and clear cookie."""
    trace_id = trace_id_for(request)
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


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Change authenticated user password, enforcing policy and clearing temporary flag",
    responses=PROBLEM_RESPONSES,
)
async def change_password(
    payload: ChangePasswordRequest, request: Request
) -> ChangePasswordResponse:
    """Validate current password, verify policy, update PG and memory session."""
    svc = get_auth_service(request)
    engine = get_or_create_shared_db_engine(request) if _pg_enabled() else None
    return await execute_change_password(
        request,
        current_password=payload.current_password,
        new_password=payload.new_password,
        trace_id=trace_id_for(request),
        svc=svc,
        engine=engine,
    )


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
        description="Optional persona key for development impersonation.",
    ),
) -> UserMeResponse:
    """Return full Human Profile, OrgUnit tree, accessible Workspaces, and RBAC module flags."""
    svc = get_auth_service(request)
    user = resolve_request_user(request, persona_key=persona_key)
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            user = await hydrate_user_identity_from_pg(engine, user)
        except Exception as exc:
            logger.warning("auth_refresh_pg_hydration_failed", error_type=type(exc).__name__)
    accessible = svc.evaluator.resolve_accessible_workspaces(user)
    finops_total = svc.evaluator.compute_finops_rollup_usd(user)
    modules_map = svc.evaluator.evaluate_module_permissions(user, has_workspaces=bool(accessible))

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
        roles=list(user.roles),
        must_change_password=user.must_change_password,
        org_units=[
            OrgUnitTreeItem(
                id=u.id, slug=u.slug, name=u.name, unit_type=u.unit_type, parent_id=u.parent_id
            )
            for u in svc.evaluator.org_units
        ],
        workspaces=[serialize_workspace_summary(item) for item in accessible],
        consolidated_finops_usd=finops_total,
        modules=modules_map,
        trace_id=trace_id_for(request),
    )
