"""Helper functions for PostgreSQL 18-backed authentication & password lifecycle (`AD-6`).

Handles non-blocking Argon2id verification, session cookie policies, and PG hydration.
"""

from __future__ import annotations

import asyncio
import inspect
import os
from dataclasses import replace

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.schemas.auth_and_org import (
    WorkspaceDatasourceItem,
    WorkspaceSummaryItem,
)
from orcia_api.schemas.iam_password_models import (
    ChangePasswordResponse,
)
from orcia_core.bootstrap import (
    LocalAuthCandidate,
    load_auth_candidate_by_id_from_postgres18,
    load_local_auth_candidate_from_postgres18,
    update_user_password_on_postgres18,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    REFRESH_TOKEN_TTL_SECONDS,
    AuthAndOrganizationService,
    SessionTokenPair,
    UserIdentity,
    WorkspaceAccessSummary,
    validate_password_policy,
)
from orcia_core.permissions.errors import (
    AuthenticationRequiredError,
    InvalidCredentialsError,
    OrciaDomainError,
    PasswordUnchangedError,
    ResourceNotFoundError,
)

logger = get_logger("orcia.api.auth.helpers")
REFRESH_COOKIE_NAME: str = "orcia_refresh_token"


def set_auth_refresh_cookie(response: Response, refresh_token: str, request: Request) -> None:
    """Set HttpOnly refresh cookie with lax SameSite policy and environment-aware secure flag."""
    is_secure = request.url.scheme == "https" or os.getenv("ORCIA_ENV") == "production"
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=REFRESH_TOKEN_TTL_SECONDS,
        path="/api/v1/auth",
        secure=is_secure,
        httponly=True,
        samesite="lax",
    )


def user_identity_from_candidate(
    candidate: LocalAuthCandidate,
    *,
    auth_mode: str = "LOCAL",
) -> UserIdentity:
    """Convert a `LocalAuthCandidate` loaded from PostgreSQL into domain `UserIdentity`."""
    return UserIdentity(
        id=candidate.user_id,
        email=candidate.email,
        display_name=candidate.display_name,
        auth_mode=auth_mode,  # type: ignore[arg-type]
        human_profile_archetype=candidate.human_profile_archetype,
        platform_role=candidate.platform_role,  # type: ignore[arg-type]
        primary_org_unit_id=candidate.primary_org_unit_id,
        password_hash_argon2id=candidate.password_hash_argon2id,
        is_active=candidate.is_active,
        must_change_password=candidate.must_change_password,
        roles=candidate.roles,
        totp_enabled=candidate.totp_enabled,
        totp_secret=candidate.totp_secret_encrypted,
    )


async def rehydrate_user_from_pg_by_id(
    engine: AsyncEngine | None,
    svc: AuthAndOrganizationService,
    user_id: str,
    *,
    auth_mode: str = "LOCAL",
) -> UserIdentity | None:
    """Fetch candidate from PostgreSQL 18 by user ID and register into memory if active."""
    if engine is None:
        return None
    try:
        conn_ctx = engine.connect()
        if inspect.iscoroutine(conn_ctx):
            conn_ctx.close()
            return None
        async with conn_ctx as conn:
            candidate = await load_auth_candidate_by_id_from_postgres18(conn, user_id=user_id)
        if candidate is not None and candidate.is_active and candidate.iam_status != "DISABLED":
            user = user_identity_from_candidate(candidate, auth_mode=auth_mode)
            svc.register_user(user)
            return user
        if candidate is not None and (
            not candidate.is_active or candidate.iam_status == "DISABLED"
        ):
            svc.unregister_user(user_id)
    except Exception as exc:
        logger.warning(
            "rehydrate_user_from_pg_by_id_failed",
            user_id=user_id,
            error_type=type(exc).__name__,
        )
    return None


async def rehydrate_bearer_subject_from_pg_if_missing(request: Request) -> None:
    """ASGI/HTTP middleware hook rehydrating caller identity from PG 18 if RAM was cleared."""
    auth_hdr = request.headers.get("Authorization")
    if not auth_hdr:
        return
    clean_hdr = auth_hdr.strip()
    if not (clean_hdr.startswith("Bearer ") or clean_hdr.startswith("bearer ")):
        return

    auth_svc: AuthAndOrganizationService | None = getattr(request.app.state, "auth_service", None)
    if auth_svc is None:
        return

    try:
        claims = auth_svc.verify_access_token_claims(clean_hdr)
    except OrciaDomainError:
        return
    except Exception as exc:
        logger.debug("auth_claims_verification_skipped", error_type=type(exc).__name__)
        return

    if auth_svc.has_user_in_memory(claims.sub):
        return

    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") == "1":
        return

    try:
        from orcia_api.dependencies import get_or_create_shared_db_engine

        engine = get_or_create_shared_db_engine(request)
        await rehydrate_user_from_pg_by_id(engine, auth_svc, claims.sub, auth_mode=claims.auth_mode)
    except Exception as exc:
        get_logger("orcia.api.auth").warning(
            "rehydrate_bearer_subject_from_pg_failed",
            sub=claims.sub,
            error_type=type(exc).__name__,
        )


async def authenticate_via_postgres18(
    engine: AsyncEngine,
    email: str,
    password: str,
    svc: AuthAndOrganizationService,
) -> tuple[UserIdentity, SessionTokenPair]:
    """Authenticate credentials against PostgreSQL 18 `users` + `iam_accounts`."""
    async with engine.begin() as conn:
        candidate = await load_local_auth_candidate_from_postgres18(conn, email=email)

    if candidate is None:
        raise InvalidCredentialsError()

    if not candidate.is_active or candidate.iam_status == "DISABLED":
        raise InvalidCredentialsError()

    if not candidate.password_hash_argon2id:
        raise InvalidCredentialsError()

    is_valid = await asyncio.to_thread(
        svc.hasher.verify_password,
        candidate.password_hash_argon2id,
        password,
    )
    if not is_valid:
        raise InvalidCredentialsError()

    user = user_identity_from_candidate(candidate, auth_mode="LOCAL")
    svc.register_user(user)
    tokens = svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode="LOCAL",
    )
    return user, tokens


async def hydrate_user_identity_from_pg(
    engine: AsyncEngine | None,
    user: UserIdentity,
    svc: AuthAndOrganizationService | None = None,
) -> UserIdentity:
    """Enrich in-memory `UserIdentity` with active roles and `must_change_password` from PG."""
    if engine is None:
        return user
    try:
        async with engine.begin() as conn:
            candidate = await load_local_auth_candidate_from_postgres18(conn, email=user.email)
        if candidate is not None:
            if not candidate.is_active or candidate.iam_status == "DISABLED":
                if svc is not None:
                    svc.unregister_user(user.id)
                raise ResourceNotFoundError()
            return replace(
                user,
                roles=candidate.roles,
                must_change_password=candidate.must_change_password,
                is_active=candidate.is_active,
            )
        else:
            if svc is not None:
                svc.unregister_user(user.id)
            raise ResourceNotFoundError()
    except ResourceNotFoundError:
        raise
    except Exception as exc:
        logger.warning("hydrate_user_identity_from_pg_failed", error_type=type(exc).__name__)
    return user


async def execute_change_password(
    request: Request,
    current_password: str,
    new_password: str,
    trace_id: str,
    svc: AuthAndOrganizationService,
    engine: AsyncEngine | None,
) -> ChangePasswordResponse:
    """Validate and apply password change on PostgreSQL 18 and active memory session."""
    raw_auth = request.headers.get("Authorization")
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME) or request.headers.get("X-Refresh-Token")

    user: UserIdentity | None = None
    if raw_auth:
        raw_token = raw_auth.removeprefix("Bearer ").removeprefix("bearer ").strip()
        try:
            user = svc.authenticate_access_token(raw_token)
        except Exception as exc:
            logger.warning("auth_bearer_token_decode_failed", error_type=type(exc).__name__)
            user = None

    if user is None and raw_refresh:
        try:
            claims = svc.verify_refresh_token_claims(raw_refresh)
            user = svc.get_user_by_id(claims.sub)
        except Exception as exc:
            logger.warning("auth_refresh_token_decode_failed", error_type=type(exc).__name__)
            user = None

    if user is None:
        raise AuthenticationRequiredError(instance=str(request.url.path))

    # Rehydrate user to get current password hash from PG if available
    user = await hydrate_user_identity_from_pg(engine, user)

    # Verify current password
    if user.password_hash_argon2id:
        current_valid = await asyncio.to_thread(
            svc.hasher.verify_password,
            user.password_hash_argon2id,
            current_password,
        )
        if not current_valid:
            raise InvalidCredentialsError(instance=str(request.url.path))

    if new_password == current_password:
        raise PasswordUnchangedError(instance=str(request.url.path))

    validate_password_policy(new_password, instance=str(request.url.path))

    new_hash = await asyncio.to_thread(svc.hasher.hash_password, new_password)

    if engine is not None:
        async with engine.begin() as conn:
            await update_user_password_on_postgres18(
                conn,
                email=user.email,
                new_password_hash_argon2id=new_hash,
            )

    updated_user = replace(
        user,
        password_hash_argon2id=new_hash,
        must_change_password=False,
    )
    svc.register_user(updated_user)

    return ChangePasswordResponse(
        success=True,
        email=user.email,
        must_change_password=False,
        trace_id=trace_id,
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
