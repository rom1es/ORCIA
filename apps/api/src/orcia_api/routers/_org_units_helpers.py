"""Story 17.2 — Helpers for Hierarchical Organizational Units router (`/api/v1/org-units`).

DTO serialization, memory evaluator mutations (via `_org_units_evaluator_ops`),
and strict PostgreSQL exception classification
(connectivity loss fallback vs `HTTP 503 ERR_ORG_STORAGE_SCHEMA_OUTDATED` on schema drift).
"""

from __future__ import annotations

import unicodedata

from fastapi import Request

from orcia_api.routers._org_units_evaluator_ops import (
    create_in_evaluator,
    delete_in_evaluator,
    update_in_evaluator,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.auth_and_org import (
    AttachedWorkspaceRefResponse,
    OrgUnitResponse,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import (
    ADMIN_MODULE_ALLOWED_ROLES,
    MatrixPermissionEvaluator,
    OrgUnitCapabilities,
    OrgUnitKind,
    OrgUnitNode,
    OrgUnitSummary,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    OrgUnitStorageSchemaError,
    ScopeAccessDeniedError,
)

logger = get_logger("orcia.api.org_units.helpers")
_SCHEMA_DRIFT_EXC_NAMES = frozenset(
    {
        "ProgrammingError",
        "UndefinedColumnError",
        "UndefinedTableError",
        "InvalidColumnReferenceError",
        "DuplicateTableError",
        "DataError",
        "IntegrityError",
    }
)


def resolve_trace_id(request: Request) -> str:
    """Return request W3C trace ID or ambient logging trace ID."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def serialize_org_unit_summary(
    summary: OrgUnitSummary,
    capabilities: OrgUnitCapabilities | None = None,
) -> OrgUnitResponse:
    """Serialize pure domain `OrgUnitSummary` to OpenAPI `OrgUnitResponse` DTO."""
    return OrgUnitResponse(
        id=summary.id,
        slug=summary.slug,
        name=summary.name,
        kind=summary.kind,
        parent_id=summary.parent_id,
        billing_enabled=summary.billing_enabled,
        lead_user_id=summary.lead_user_id,
        member_user_ids=list(summary.member_user_ids),
        attached_workspaces_count=summary.attached_workspaces_count,
        attached_workspaces=[
            AttachedWorkspaceRefResponse(id=ws.id, slug=ws.slug, name=ws.name)
            for ws in summary.attached_workspaces
        ],
        lead_user_ids=list(summary.lead_user_ids),
        ontology_lead_user_ids=list(summary.ontology_lead_user_ids),
        can_edit=capabilities.can_edit if capabilities else True,
        can_create_child=capabilities.can_create_child if capabilities else (summary.kind == "BU"),
        can_delete=capabilities.can_delete if capabilities else True,
        can_manage_members=(
            capabilities.can_manage_members if capabilities else (summary.kind == "TEAM")
        ),
        can_manage_ontology_leads=(
            capabilities.can_manage_ontology_leads if capabilities else (summary.kind == "BU")
        ),
        can_invite_users=capabilities.can_invite_users if capabilities else True,
    )


def enforce_org_unit_mutation_access(request: Request, persona_key: str | None) -> None:
    """Reject `READ_ONLY_OBSERVER` (`403`) and non-admin/supervisor callers (`403`)."""
    is_obs = (
        request.headers.get("x-orcia-access-mode", "").strip().upper() == "READ_ONLY_OBSERVER"
        or request.headers.get("x-orcia-observer-mode", "").strip().lower() in {"1", "true", "yes"}
        or request.headers.get("x-orcia-active-hat", "").strip().upper() == "OBSERVER"
    )
    if is_obs:
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if active_hat and active_hat not in (*ADMIN_MODULE_ALLOWED_ROLES, "BU_LEAD"):
        raise ScopeAccessDeniedError(instance=str(request.url.path))

    effective_persona = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    user = resolve_request_user(request, persona_key=effective_persona)
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    if user.platform_role not in ADMIN_MODULE_ALLOWED_ROLES:
        raise ScopeAccessDeniedError(instance=str(request.url.path))


def sync_evaluator_from_summaries(
    evaluator: MatrixPermissionEvaluator,
    summaries: list[OrgUnitSummary],
) -> None:
    """Synchronize `evaluator` in-memory graph from PostgreSQL summaries."""
    nodes = tuple(
        OrgUnitNode(
            id=s.id,
            slug=s.slug,
            name=s.name,
            unit_type=s.kind,
            parent_id=s.parent_id,
            billing_enabled=s.billing_enabled,
            lead_user_id=s.lead_user_id,
            lead_user_ids=s.lead_user_ids,
            ontology_lead_user_ids=s.ontology_lead_user_ids,
            member_user_ids=s.member_user_ids,
        )
        for s in summaries
    )
    evaluator.replace_org_units(nodes)


def normalize_text_search(text: str) -> str:
    """NFD normalization removing diacritics and lowercasing."""
    return (
        "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
        .lower()
        .strip()
    )


def filter_org_unit_summaries_in_memory(
    summaries: list[OrgUnitSummary],
    *,
    q: str | None = None,
    kind: OrgUnitKind | None = None,
    limit: int | None = None,
) -> list[OrgUnitSummary]:
    """Filter and sort summaries in memory with exact parity to PostgreSQL 18 search."""
    filtered = list(summaries)
    if kind is not None:
        filtered = [s for s in filtered if s.kind == kind]
    if q is not None and q.strip():
        norm_q = normalize_text_search(q)
        filtered = [
            s
            for s in filtered
            if norm_q in normalize_text_search(s.name) or norm_q in normalize_text_search(s.slug)
        ]
    filtered.sort(key=lambda s: (s.kind, s.name.lower(), s.slug.lower()))
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def pg_sync_enabled() -> bool:
    """Return True if PostgreSQL sync is active."""
    from orcia_api.dependencies._core_providers import is_pg_runtime_active

    return is_pg_runtime_active()


def is_pg_connectivity_error(exc: Exception) -> bool:
    """Return True only if `exc` indicates unreachable DB or socket failure (not schema error)."""
    if isinstance(exc, (OSError, TimeoutError, ConnectionError)):
        return True

    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        curr_type = type(current).__name__
        curr_msg = str(current).lower()

        if curr_type in _SCHEMA_DRIFT_EXC_NAMES:
            return False

        pgcode = getattr(current, "pgcode", None) or getattr(
            getattr(current, "orig", None), "pgcode", None
        )
        if pgcode and str(pgcode).startswith(("42", "22", "23")):
            return False

        if isinstance(current, (OSError, TimeoutError, ConnectionError)):
            return True
        conn_kw = ("connection refused", "could not connect", "connection reset", "broken pipe")
        if any(token in curr_msg for token in (*conn_kw, "connect_tcp")):
            return True

        orig = getattr(current, "orig", None)
        current = orig if orig is not None else current.__cause__

    import sqlalchemy.exc as sa_exc

    if isinstance(exc, (sa_exc.InterfaceError, sa_exc.OperationalError)):
        err_msg = str(exc).lower()
        if any(token in err_msg for token in ("connection", "refused", "timeout", "closed")):
            return True

    return False


def classify_and_handle_pg_error(exc: Exception, operation: str) -> None:
    """Classify PostgreSQL exception: fallback on connectivity loss, raise 503 on schema drift."""
    if isinstance(exc, OrciaDomainError):
        raise exc

    if is_pg_connectivity_error(exc):
        logger.warning(
            "org_units_pg_connectivity_fallback", operation=operation, error_type=type(exc).__name__
        )
        return

    logger.error(
        "org_units_pg_schema_error",
        operation=operation,
        error_type=type(exc).__name__,
        error=str(exc),
    )
    raise OrgUnitStorageSchemaError(
        detail_code="ERR_ORG_PG_SCHEMA_OUTDATED",
        detail_params={"op": operation, "exc": type(exc).__name__},
    ) from exc


__all__ = [
    "classify_and_handle_pg_error",
    "create_in_evaluator",
    "delete_in_evaluator",
    "enforce_org_unit_mutation_access",
    "filter_org_unit_summaries_in_memory",
    "is_pg_connectivity_error",
    "normalize_text_search",
    "pg_sync_enabled",
    "resolve_trace_id",
    "serialize_org_unit_summary",
    "sync_evaluator_from_summaries",
    "update_in_evaluator",
]
