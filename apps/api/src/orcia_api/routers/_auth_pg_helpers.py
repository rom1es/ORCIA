"""Helper functions for PostgreSQL 18-backed authentication & password lifecycle (`AD-6`).

Handles non-blocking Argon2id verification, session cookie policies, and PG hydration.
"""

from __future__ import annotations

import asyncio
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
    PasswordUnchangedError,
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

    user = UserIdentity(
        id=candidate.user_id,
        email=candidate.email,
        display_name=candidate.display_name,
        auth_mode="LOCAL",
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
) -> UserIdentity:
    """Enrich in-memory `UserIdentity` with active roles and `must_change_password` from PG."""
    if engine is None:
        return user
    try:
        async with engine.begin() as conn:
            candidate = await load_local_auth_candidate_from_postgres18(conn, email=user.email)
        if candidate is not None:
            return replace(
                user,
                roles=candidate.roles,
                must_change_password=candidate.must_change_password,
                is_active=candidate.is_active,
            )
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
            claims = svc.jwt_manager.verify_token(raw_refresh, expected_type="refresh")
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
