"""Bearer token PG18 rehydration helper extracted from `_auth_pg_helpers`."""

from __future__ import annotations

from fastapi import Request

from orcia_core.observability.logging import get_logger
from orcia_core.permissions import AuthAndOrganizationService, UserIdentity
from orcia_core.permissions.errors import OrciaDomainError

logger = get_logger("orcia.api.auth")


async def rehydrate_bearer_subject_from_pg_if_missing(
    request: Request,
) -> AuthAndOrganizationService | None:
    """ASGI/HTTP middleware hook rehydrating caller identity from PG 18 if RAM was cleared."""
    from orcia_api.routers._auth_pg_helpers import (
        rehydrate_user_from_pg_by_id,
        resolve_app_db_engine,
    )

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
            logger.warning(
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


__all__ = ["rehydrate_bearer_subject_from_pg_if_missing"]
