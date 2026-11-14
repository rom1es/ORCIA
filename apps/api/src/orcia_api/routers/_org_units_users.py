"""Extraction and aggregation of known platform users for org units router (`CAP-067`).

Supports both PostgreSQL 18 single-query load and memory fallback (tests / socket failures).
Enforces strict validation against active known accounts.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_api.dependencies import get_or_create_shared_db_engine
from orcia_api.routers._org_units_helpers import (
    classify_and_handle_pg_error,
    normalize_text_search,
    pg_sync_enabled,
)
from orcia_api.schemas.org_unit_models import KnownOrgUserResponse
from orcia_core.bootstrap._internal.sql_org_known_users import (
    load_known_org_users_from_postgres18,
    search_known_org_users_from_postgres18,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions.errors import OrciaDomainError
from orcia_core.permissions.org_user_validation import (
    KnownOrgUser,
    resolve_and_validate_org_unit_users,
)

logger = get_logger("orcia.api.org_units.users")


async def collect_known_org_users(
    request: Request,
    conn: AsyncConnection | None = None,
) -> list[KnownOrgUser]:
    """Return active known platform users from PostgreSQL 18 or memory fallback."""
    if conn is not None:
        return await load_known_org_users_from_postgres18(conn)

    users_by_key: dict[str, KnownOrgUser] = {}
    auth_service = getattr(request.app.state, "auth_service", None)
    if auth_service is not None:
        raw_users = getattr(auth_service, "_users_by_id", {})
        for u in raw_users.values():
            if getattr(u, "is_active", True):
                p_id = str(getattr(u, "email", None) or getattr(u, "id", "")).strip()
                if not p_id:
                    continue
                d_name = str(getattr(u, "display_name", "") or p_id).strip()
                mail = str(getattr(u, "email", "")).strip() or None
                user_obj = KnownOrgUser(principal_id=p_id, display_name=d_name, email=mail)
                users_by_key[p_id.lower()] = user_obj
                if mail:
                    users_by_key[mail.lower()] = user_obj

    iam_svc = getattr(request.app.state, "iam_accounts_service", None)
    if iam_svc is not None:
        raw_accounts = getattr(iam_svc, "_accounts", {})
        for a in raw_accounts.values():
            kind = str(getattr(a, "account_kind", "HUMAN")).upper()
            status = str(getattr(a, "status", "ACTIVE")).upper()
            if kind == "HUMAN" and status != "DISABLED":
                p_id = str(getattr(a, "principal_id", "")).strip()
                if not p_id:
                    continue
                d_name = str(getattr(a, "display_name", "") or p_id).strip()
                mail = str(getattr(a, "email", "") or "").strip() or None
                canon_key = p_id.lower()
                existing = users_by_key.get(canon_key) or (
                    users_by_key.get(mail.lower()) if mail else None
                )
                if existing is not None:
                    merged = KnownOrgUser(
                        principal_id=existing.principal_id,
                        display_name=existing.display_name or d_name,
                        email=existing.email or mail,
                    )
                    users_by_key[canon_key] = merged
                    if mail:
                        users_by_key[mail.lower()] = merged
                else:
                    new_acc = KnownOrgUser(principal_id=p_id, display_name=d_name, email=mail)
                    users_by_key[canon_key] = new_acc
                    if mail:
                        users_by_key[mail.lower()] = new_acc

    unique_users = {id(u): u for u in users_by_key.values()}.values()
    return sorted(unique_users, key=lambda u: (u.display_name.lower(), u.principal_id.lower()))


def filter_known_users_in_memory(
    users: list[KnownOrgUser],
    *,
    q: str | None = None,
    limit: int = 10,
) -> tuple[list[KnownOrgUser], bool]:
    """Filter and sort known users in memory with NFD accent stripping and pagination."""
    clean_q = (q or "").replace("\x00", "").strip()
    safe_limit = max(1, min(limit, 100))
    if clean_q:
        norm_q = normalize_text_search(clean_q)
        filtered = [
            u
            for u in users
            if norm_q in normalize_text_search(u.display_name)
            or norm_q in normalize_text_search(u.principal_id)
            or (u.email is not None and norm_q in normalize_text_search(u.email))
        ]
    else:
        filtered = list(users)
    filtered.sort(key=lambda u: (u.display_name.lower(), u.principal_id.lower()))
    has_more = len(filtered) > safe_limit
    return filtered[:safe_limit], has_more


async def search_known_org_users_for_request(
    request: Request,
    svc: object,
    *,
    q: str | None,
    limit: int = 10,
) -> tuple[list[KnownOrgUser], bool]:
    """Search known users on PostgreSQL 18 with schema guard and memory fallback."""
    safe_limit = max(1, min(limit, 100))
    if pg_sync_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            async with engine.connect() as conn:
                return await search_known_org_users_from_postgres18(conn, q=q, limit=safe_limit)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning(
                "org_units_search_known_users_pg_error",
                operation="search_known_org_users",
                error=str(exc),
            )
            classify_and_handle_pg_error(exc, operation="search_known_org_users")

    all_users = await collect_known_org_users(request, None)
    return filter_known_users_in_memory(all_users, q=q, limit=safe_limit)


def serialize_known_users(users: Sequence[KnownOrgUser]) -> list[KnownOrgUserResponse]:
    """Project domain `KnownOrgUser` items to OpenAPI `KnownOrgUserResponse` DTOs."""
    return [
        KnownOrgUserResponse(
            principal_id=u.principal_id,
            display_name=u.display_name,
            email=u.email,
        )
        for u in users
    ]


async def validate_and_normalize_org_unit_users_in_request(
    request: Request,
    lead_user_id: str | None,
    member_user_ids: Sequence[str] | None,
    conn: AsyncConnection | None = None,
) -> tuple[str | None, tuple[str, ...]]:
    """Validate and resolve lead and member identifiers to canonical `principal_id`."""
    known_users = await collect_known_org_users(request, conn)
    return resolve_and_validate_org_unit_users(
        lead_user_id=lead_user_id,
        member_user_ids=member_user_ids or (),
        known_users=known_users,
    )


__all__ = [
    "collect_known_org_users",
    "filter_known_users_in_memory",
    "search_known_org_users_for_request",
    "serialize_known_users",
    "validate_and_normalize_org_unit_users_in_request",
]
