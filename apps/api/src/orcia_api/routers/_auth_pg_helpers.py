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

from orcia_api.schemas.auth_and_org import WorkspaceDatasourceItem, WorkspaceSummaryItem
from orcia_api.schemas.iam_password_models import ChangePasswordResponse
from orcia_core.bootstrap import (
    LocalAuthCandidate,
    load_auth_candidate_by_id_from_postgres18,
    load_local_auth_candidate_from_postgres18,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    REFRESH_TOKEN_TTL_SECONDS,
    AuthAndOrganizationService,
    SessionTokenPair,
    UserIdentity,
    WorkspaceAccessSummary,
)
from orcia_core.permissions.errors import (
    InvalidCredentialsError,
    OrciaDomainError,
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


def resolve_app_db_engine(request: Request) -> AsyncEngine | None:
    """Resolve shared PostgreSQL `AsyncEngine`, returning `None` in pure in-memory unit tests."""
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    try:
        return get_configured_db_engine(request)
    except Exception as exc:
        logger.warning("resolve_app_db_engine_failed", error_type=type(exc).__name__)
        return None


async def sync_auth_service_user_by_email_from_pg(
    request: Request,
    auth_svc: AuthAndOrganizationService,
    email: str | None,
) -> None:
    """Sync in-memory user cache in `AuthAndOrganizationService` from PG 18 by email/principal."""
    if not email or not email.strip():
        return
    clean_email = email.strip()
    engine = resolve_app_db_engine(request)
    if engine is None:
        return
    try:
        conn_ctx = engine.connect()
        if inspect.iscoroutine(conn_ctx):
            conn_ctx.close()
            return
        async with conn_ctx as conn:
            candidate = await load_local_auth_candidate_from_postgres18(conn, email=clean_email)
        if candidate is not None and candidate.is_active and candidate.iam_status != "DISABLED":
            auth_svc.register_user(user_identity_from_candidate(candidate))
        elif candidate is not None and (
            not candidate.is_active or candidate.iam_status == "DISABLED"
        ):
            auth_svc.unregister_user(candidate.user_id)
    except Exception as exc:
        logger.warning(
            "sync_auth_service_user_by_email_from_pg_failed",
            email=clean_email,
            error_type=type(exc).__name__,
        )


async def rehydrate_bearer_subject_from_pg_if_missing(
    request: Request,
) -> AuthAndOrganizationService | None:
    """ASGI/HTTP middleware hook rehydrating caller identity from PG 18 if RAM was cleared."""
    auth_hdr = request.headers.get("Authorization")
    if not auth_hdr:
        return None
    clean_hdr = auth_hdr.strip()
    if not (clean_hdr.startswith("Bearer ") or clean_hdr.startswith("bearer ")):
        return None

    auth_svc: AuthAndOrganizationService | None = getattr(request.app.state, "auth_service", None)
    if auth_svc is None:
        return None

    try:
        claims = auth_svc.verify_access_token_claims(clean_hdr)
    except OrciaDomainError:
        return auth_svc
    except Exception as exc:
        logger.debug("auth_claims_verification_skipped", error_type=type(exc).__name__)
        return auth_svc

    if auth_svc.has_user_in_memory(claims.sub):
        request.state.hydrated_auth_service = auth_svc
        return auth_svc

    engine = resolve_app_db_engine(request)
    hydrated_user: UserIdentity | None = None
    if engine is not None:
        try:
            hydrated_user = await rehydrate_user_from_pg_by_id(
                engine, auth_svc, claims.sub, auth_mode=claims.auth_mode
            )
        except Exception as exc:
            get_logger("orcia.api.auth").warning(
                "rehydrate_bearer_subject_from_pg_failed",
                sub=claims.sub,
                error_type=type(exc).__name__,
            )

    current_svc: AuthAndOrganizationService | None = getattr(
        request.app.state, "auth_service", None
    )
    active_svc = current_svc or auth_svc
    if hydrated_user is not None:
        if current_svc is not None and current_svc is not auth_svc:
            current_svc.register_user(hydrated_user)
        request.state.resolved_bearer_user = hydrated_user
    request.state.hydrated_auth_service = active_svc
    return active_svc


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
            hydrated = replace(
                user,
                platform_role=candidate.platform_role,  # type: ignore[arg-type]
                roles=candidate.roles,
                must_change_password=candidate.must_change_password,
                is_active=candidate.is_active,
                password_hash_argon2id=candidate.password_hash_argon2id
                or user.password_hash_argon2id,
            )
            if svc is not None:
                svc.register_user(hydrated)
            return hydrated
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
    """Validate and apply password change (delegated to _auth_password_helpers)."""
    from orcia_api.routers._auth_password_helpers import (
        execute_change_password as _execute_impl,
    )

    return await _execute_impl(
        request=request,
        current_password=current_password,
        new_password=new_password,
        trace_id=trace_id,
        svc=svc,
        engine=engine,
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


__all__ = [
    "REFRESH_COOKIE_NAME",
    "authenticate_via_postgres18",
    "execute_change_password",
    "hydrate_user_identity_from_pg",
    "rehydrate_bearer_subject_from_pg_if_missing",
    "rehydrate_user_from_pg_by_id",
    "resolve_app_db_engine",
    "serialize_workspace_summary",
    "set_auth_refresh_cookie",
    "sync_auth_service_user_by_email_from_pg",
    "user_identity_from_candidate",
]
