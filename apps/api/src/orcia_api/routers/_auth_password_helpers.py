"""Password update helpers for authenticated user sessions (`AD-6`, `Story 3.2a`, `CAP-063`).

Zero blocking I/O in ASGI event loop (`TID251`).
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.routers._auth_pg_helpers import (
    REFRESH_COOKIE_NAME,
    hydrate_user_identity_from_pg,
    rehydrate_user_from_pg_by_id,
)
from orcia_api.schemas.iam_password_models import ChangePasswordResponse
from orcia_core.bootstrap import update_user_password_on_postgres18
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    AuthAndOrganizationService,
    validate_password_policy,
)
from orcia_core.permissions.errors import (
    AuthenticationRequiredError,
    InvalidCurrentPasswordError,
    LocalPasswordChangeForbiddenForSsoError,
    PasswordUnchangedError,
    ResourceNotFoundError,
)
from orcia_core.permissions.models import UserIdentity

logger = get_logger("orcia.api.auth.password")


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
            try:
                user = svc.get_user_by_id(claims.sub)
            except (ResourceNotFoundError, KeyError):
                user = None
            if user is None and engine is not None:
                user = await rehydrate_user_from_pg_by_id(
                    engine,
                    svc,
                    claims.sub,
                    auth_mode=claims.auth_mode,
                )
        except Exception as exc:
            logger.warning("auth_refresh_token_decode_failed", error_type=type(exc).__name__)
            user = None

    if user is None:
        raise AuthenticationRequiredError(instance=str(request.url.path))

    # Rehydrate user to get current password hash and state from PG if available
    user = await hydrate_user_identity_from_pg(engine, user, svc=svc)

    # SSO/OIDC guard: external SSO accounts cannot change passwords locally
    if user.auth_mode == "OIDC":
        raise LocalPasswordChangeForbiddenForSsoError(instance=str(request.url.path))

    # Strict current password check (no silent bypass!)
    if not user.password_hash_argon2id:
        raise InvalidCurrentPasswordError(instance=str(request.url.path))

    current_valid = await asyncio.to_thread(
        svc.hasher.verify_password,
        user.password_hash_argon2id,
        current_password,
    )
    if not current_valid:
        raise InvalidCurrentPasswordError(instance=str(request.url.path))

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


__all__ = ["execute_change_password"]
