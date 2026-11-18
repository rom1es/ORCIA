"""Exclusive Authentication Router (`/api/v1/auth/*`, AD-6, NFR-SEC-4)."""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter, Request, Response

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._auth_2fa_helpers import (
    authenticate_pg_local_with_policy,
    execute_resend_login_2fa,
    execute_verify_login_2fa,
)
from orcia_api.routers._auth_oidc_helpers import (
    execute_oidc_authorize,
    execute_oidc_callback,
)
from orcia_api.routers._auth_passthrough_routes import router as passthrough_router
from orcia_api.routers._auth_pg_helpers import (
    serialize_workspace_summary as serialize_workspace_summary,
)
from orcia_api.routers._auth_policy_runtime import (
    resolve_auth_policy_runtime,
    serialize_public_auth_config,
    trace_id_for,
)
from orcia_api.routers._auth_session_routes import router as session_router
from orcia_api.routers._auth_token_issuer import (
    PROBLEM_RESPONSES as PROBLEM_RESPONSES,
)
from orcia_api.routers._auth_token_issuer import (
    issue_completed_auth_response,
    serialize_auth_token_response,
    user_identity_from_candidate,
)
from orcia_api.routers._auth_token_issuer import (
    resolve_request_user as resolve_request_user,
)
from orcia_api.schemas.auth_and_org import (
    AuthTokenResponse,
    LocalLoginRequest,
    OidcLoginRequest,
)
from orcia_api.schemas.auth_policy import (
    OidcAuthorizeUrlResponse,
    OidcCallbackExchangeRequest,
    PublicAuthConfigResponse,
    ResendLoginTwoFactorRequest,
    ResendLoginTwoFactorResponse,
    VerifyLoginTwoFactorRequest,
)
from orcia_core.bootstrap import load_auth_candidate_by_oidc_from_postgres18
from orcia_core.observability.logging import get_logger
from orcia_core.permissions.errors import (
    InvalidCredentialsError,
    InvalidOrExpiredLoginChallengeError,
    LocalAuthDisabledByPolicyError,
    SsoAuthDisabledByPolicyError,
)

logger = get_logger("orcia.api.auth")

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
router.include_router(passthrough_router)
router.include_router(session_router)


def _pg_enabled() -> bool:
    from orcia_api.dependencies._core_providers import is_pg_runtime_active

    return is_pg_runtime_active()


@router.get(
    "/public-config",
    response_model=PublicAuthConfigResponse,
    summary="Read anonymous platform login mode, 2FA policy, and boot_epoch (zero secrets)",
    responses=PROBLEM_RESPONSES,
)
async def get_public_auth_config(request: Request) -> PublicAuthConfigResponse:
    """Expose public authentication mode and `boot_epoch` for `/login` bootstrapping."""
    state, _, _ = await resolve_auth_policy_runtime(request)
    return serialize_public_auth_config(state, trace_id=trace_id_for(request))


@router.post(
    "/login/local",
    response_model=AuthTokenResponse,
    summary="Authenticate via Local Argon2id password and configured 2FA (`NONE|EMAIL_OTP|TOTP`)",
    responses=PROBLEM_RESPONSES,
)
async def login_local(
    payload: LocalLoginRequest, request: Request, response: Response
) -> AuthTokenResponse:
    """Authenticate local user or start step-2 `EMAIL_OTP` / `TOTP` / `TOTP_ENROLL` challenge."""
    trace_id = trace_id_for(request)
    svc = get_auth_service(request)
    policy, strict_exclusive, engine = await resolve_auth_policy_runtime(request)
    if strict_exclusive and policy.auth_mode != "LOCAL":
        raise LocalAuthDisabledByPolicyError(instance=str(request.url.path))

    if engine is not None:
        async with engine.begin() as conn:
            users_count = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM users"))).scalar() or 0
            )
        if users_count > 0 or not svc.list_personas():
            return await authenticate_pg_local_with_policy(
                engine=engine,
                request=request,
                response=response,
                svc=svc,
                policy=policy,
                email=payload.email,
                password=payload.password,
                totp_code=payload.totp_code,
                trace_id=trace_id,
            )

    user, tokens = svc.login_local(payload.email, payload.password, totp_code=payload.totp_code)
    return serialize_auth_token_response(response, user, tokens, trace_id, request)


@router.post(
    "/login/verify-2fa",
    response_model=AuthTokenResponse,
    summary="Verify 6-digit `EMAIL_OTP`, `TOTP`, or `TOTP_ENROLL` step-2 login code",
    responses=PROBLEM_RESPONSES,
)
async def verify_login_two_factor(
    payload: VerifyLoginTwoFactorRequest, request: Request, response: Response
) -> AuthTokenResponse:
    """Consume single-use login challenge and issue final JWT session tokens."""
    trace_id = trace_id_for(request)
    svc = get_auth_service(request)
    policy, strict_exclusive, engine = await resolve_auth_policy_runtime(request)
    if strict_exclusive and policy.auth_mode != "LOCAL":
        raise LocalAuthDisabledByPolicyError(instance=str(request.url.path))
    if engine is None:
        raise InvalidOrExpiredLoginChallengeError(instance=str(request.url.path))
    return await execute_verify_login_2fa(
        engine=engine,
        request=request,
        response=response,
        svc=svc,
        challenge_token=payload.challenge_token,
        code=payload.code,
        trace_id=trace_id,
    )


@router.post(
    "/login/resend-2fa",
    response_model=ResendLoginTwoFactorResponse,
    summary="Regenerate and resend a 6-digit `EMAIL_OTP` verification code",
    responses=PROBLEM_RESPONSES,
)
async def resend_login_two_factor(
    payload: ResendLoginTwoFactorRequest, request: Request
) -> ResendLoginTwoFactorResponse:
    """Dispatch a fresh 6-digit code over the active `SMTP_MAIL` connector."""
    trace_id = trace_id_for(request)
    svc = get_auth_service(request)
    policy, strict_exclusive, engine = await resolve_auth_policy_runtime(request)
    if strict_exclusive and policy.auth_mode != "LOCAL":
        raise LocalAuthDisabledByPolicyError(instance=str(request.url.path))
    if engine is None:
        raise InvalidOrExpiredLoginChallengeError(instance=str(request.url.path))
    return await execute_resend_login_2fa(
        engine=engine,
        request=request,
        svc=svc,
        challenge_token=payload.challenge_token,
        trace_id=trace_id,
    )


@router.get(
    "/oidc/authorize",
    response_model=OidcAuthorizeUrlResponse,
    summary="Generate Enterprise SSO OIDC Authorization Code redirect URL",
    responses=PROBLEM_RESPONSES,
)
async def oidc_authorize(request: Request, response: Response) -> OidcAuthorizeUrlResponse:
    """Initiate real OIDC Authorization Code flow when platform `auth_mode == 'SSO'`."""
    svc = get_auth_service(request)
    policy, _, _ = await resolve_auth_policy_runtime(request)
    return await execute_oidc_authorize(
        request=request,
        response=response,
        svc=svc,
        policy=policy,
        trace_id=trace_id_for(request),
    )


@router.post(
    "/oidc/callback",
    response_model=AuthTokenResponse,
    summary="Exchange OIDC Authorization Code for ORCIA session tokens",
    responses=PROBLEM_RESPONSES,
)
async def oidc_callback(
    payload: OidcCallbackExchangeRequest, request: Request, response: Response
) -> AuthTokenResponse:
    """Complete real OIDC login, bind to PG user, and issue JWT + HttpOnly refresh cookie."""
    svc = get_auth_service(request)
    _, _, engine = await resolve_auth_policy_runtime(request)
    return await execute_oidc_callback(
        engine=engine,
        request=request,
        response=response,
        svc=svc,
        payload=payload,
        trace_id=trace_id_for(request),
    )


@router.post(
    "/login/oidc",
    response_model=AuthTokenResponse,
    summary="Authenticate via Enterprise SSO OIDC / OAuth 2.1 subject claim",
    responses=PROBLEM_RESPONSES,
)
async def login_oidc(
    payload: OidcLoginRequest, request: Request, response: Response
) -> AuthTokenResponse:
    """Authenticate OIDC user when SSO mode is enabled (blocked when exclusive LOCAL is active)."""
    trace_id = trace_id_for(request)
    svc = get_auth_service(request)
    policy, strict_exclusive, engine = await resolve_auth_policy_runtime(request)
    if strict_exclusive and policy.auth_mode != "SSO":
        raise SsoAuthDisabledByPolicyError(instance=str(request.url.path))

    if engine is not None:
        async with engine.begin() as conn:
            users_count = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM users"))).scalar() or 0
            )
            if users_count > 0 or not svc.list_personas():
                candidate = await load_auth_candidate_by_oidc_from_postgres18(
                    conn, oidc_subject=payload.oidc_subject, email=payload.email
                )
                if (
                    candidate is None
                    or not candidate.is_active
                    or candidate.iam_status == "DISABLED"
                ):
                    raise InvalidCredentialsError(instance=str(request.url.path))
                user = user_identity_from_candidate(candidate, auth_mode="OIDC")
                return issue_completed_auth_response(
                    response=response,
                    request=request,
                    svc=svc,
                    user=user,
                    trace_id=trace_id,
                    auth_mode="OIDC",
                )

    user, tokens = svc.login_oidc(payload.oidc_subject, email=payload.email)
    return serialize_auth_token_response(response, user, tokens, trace_id, request)
