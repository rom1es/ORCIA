"""Shared authentication token serialization, user resolution, and RFC 9457 metadata."""

from __future__ import annotations

from typing import Any

from fastapi import Request, Response

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._auth_pg_helpers import set_auth_refresh_cookie
from orcia_api.schemas.auth_and_org import AuthTokenResponse
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.bootstrap import LocalAuthCandidate
from orcia_core.permissions import (
    AuthAndOrganizationService,
    SessionTokenPair,
    UserIdentity,
)
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.permissions.models import AuthMode

PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}


def resolve_request_user(request: Request, persona_key: str | None = None) -> UserIdentity:
    """Resolve authenticated `UserIdentity` from `Authorization: Bearer ...` or `persona_key`."""
    svc = get_auth_service(request)
    bearer_token = request.headers.get("Authorization")
    try:
        return svc.resolve_user(persona_key=persona_key, bearer_token=bearer_token)
    except ResourceNotFoundError:
        cached_user: UserIdentity | None = getattr(request.state, "resolved_bearer_user", None)
        if persona_key is None and bearer_token and cached_user is not None:
            svc.register_user(cached_user)
            return svc.resolve_user(persona_key=persona_key, bearer_token=bearer_token)
        raise


def user_identity_from_candidate(
    candidate: LocalAuthCandidate,
    *,
    auth_mode: AuthMode = "LOCAL",
) -> UserIdentity:
    """Convert a PostgreSQL `LocalAuthCandidate` into a domain `UserIdentity`."""
    return UserIdentity(
        id=candidate.user_id,
        email=candidate.email,
        display_name=candidate.display_name,
        auth_mode=auth_mode,
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


def serialize_auth_token_response(
    response: Response,
    user: UserIdentity,
    tokens: SessionTokenPair,
    trace_id: str,
    request: Request,
) -> AuthTokenResponse:
    """Attach HttpOnly refresh cookie and serialize `AuthTokenResponse`."""
    set_auth_refresh_cookie(response, tokens.refresh_token, request)
    return AuthTokenResponse(
        access_token=tokens.access_token,
        expires_in_seconds=tokens.expires_in_seconds,
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        platform_role=user.platform_role,
        human_profile_archetype=user.human_profile_archetype,
        primary_org_unit_id=user.primary_org_unit_id,
        roles=list(user.roles),
        must_change_password=user.must_change_password,
        requires_two_factor=False,
        trace_id=trace_id,
    )


def issue_completed_auth_response(
    *,
    response: Response,
    request: Request,
    svc: AuthAndOrganizationService,
    user: UserIdentity,
    trace_id: str,
    auth_mode: AuthMode = "LOCAL",
) -> AuthTokenResponse:
    """Register user session, mint JWT + refresh cookie, and build `AuthTokenResponse`."""
    svc.register_user(user)
    tokens: SessionTokenPair = svc.jwt_manager.issue_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.platform_role,
        org_unit_id=user.primary_org_unit_id,
        archetype=user.human_profile_archetype,
        auth_mode=auth_mode,
    )
    return serialize_auth_token_response(response, user, tokens, trace_id, request)
