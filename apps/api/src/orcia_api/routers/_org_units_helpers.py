"""Story 17.2 — Helpers for Hierarchical Organizational Units router (`/api/v1/org-units`).

DTO serialization, memory evaluator mutations, and strict PostgreSQL exception classification
(connectivity loss fallback vs `HTTP 503 ERR_ORG_STORAGE_SCHEMA_OUTDATED` on schema drift).
"""

from __future__ import annotations

import os

from fastapi import Request

from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.auth_and_org import (
    AttachedWorkspaceRefResponse,
    OrgUnitCreateRequest,
    OrgUnitPatchRequest,
    OrgUnitResponse,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import (
    ADMIN_MODULE_ALLOWED_ROLES,
    MatrixPermissionEvaluator,
    OrgUnitKind,
    OrgUnitNode,
    OrgUnitSummary,
    assert_org_unit_deletable,
    assert_unique_org_unit_slug,
    build_org_unit_summary,
    generate_new_org_unit_id,
    normalize_member_user_ids,
    normalize_org_unit_slug,
    validate_org_unit_hierarchy,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    OrgUnitStorageSchemaError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)

logger = get_logger("orcia.api.org_units.helpers")


def resolve_trace_id(request: Request) -> str:
    """Return request W3C trace ID or ambient logging trace ID."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def serialize_org_unit_summary(summary: OrgUnitSummary) -> OrgUnitResponse:
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
    )


def enforce_org_unit_mutation_access(request: Request, persona_key: str | None) -> None:
    """Reject `READ_ONLY_OBSERVER` (`403`) and non-admin/supervisor callers (`403`)."""
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or observer_hdr in ("1", "true", "yes")
        or active_hat == "OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
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
            id=item.id,
            slug=item.slug,
            name=item.name,
            unit_type=item.kind,
            parent_id=item.parent_id,
            billing_enabled=item.billing_enabled,
            lead_user_id=item.lead_user_id,
            member_user_ids=item.member_user_ids,
        )
        for item in summaries
    )
    evaluator.replace_org_units(nodes)


def pg_sync_enabled() -> bool:
    """Return True if PostgreSQL sync is active (disabled by default in isolated unit tests)."""
    return os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1"


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

        # Explicit SQL schema/syntax errors are NEVER connectivity errors
        if curr_type in (
            "ProgrammingError",
            "UndefinedColumnError",
            "UndefinedTableError",
            "InvalidColumnReferenceError",
            "DuplicateTableError",
            "DataError",
            "IntegrityError",
        ):
            return False

        pgcode = getattr(current, "pgcode", None) or getattr(
            getattr(current, "orig", None), "pgcode", None
        )
        if pgcode and str(pgcode).startswith(("42", "22", "23")):
            return False

        if isinstance(current, (OSError, TimeoutError, ConnectionError)):
            return True
        if any(
            token in curr_msg
            for token in (
                "connection refused",
                "could not connect",
                "connection reset",
                "broken pipe",
                "connect_tcp",
            )
        ):
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
            "org_units_pg_connectivity_fallback",
            operation=operation,
            error_type=type(exc).__name__,
        )
        return

    logger.error(
        "org_units_pg_schema_error",
        operation=operation,
        error_type=type(exc).__name__,
        error=str(exc),
    )
    raise OrgUnitStorageSchemaError(
        detail_override=(
            f"Schéma PostgreSQL de l'organisation obsolète ou incompatible lors de '{operation}' "
            f"({type(exc).__name__}). Une migration Alembic est requise."
        )
    ) from exc


def create_in_evaluator(
    evaluator: MatrixPermissionEvaluator,
    payload: OrgUnitCreateRequest,
    *,
    resolved_lead: str | None = None,
    resolved_members: tuple[str, ...] | None = None,
) -> OrgUnitSummary:
    """Create unit in memory evaluator when PostgreSQL sync is disabled or disconnected."""
    cleaned_name = payload.name.strip()
    if not cleaned_name:
        raise ValidationDomainError(detail_override="Le nom de l'unité ne peut pas être vide.")
    normalized_slug = normalize_org_unit_slug(payload.slug, cleaned_name)
    units_by_id = {u.id: u for u in evaluator.org_units}
    assert_unique_org_unit_slug(normalized_slug, units_by_id)
    resolved_parent = validate_org_unit_hierarchy(
        unit_id=None,
        kind=payload.kind,
        parent_id=payload.parent_id,
        units_by_id=units_by_id,
    )
    effective_lead = (
        resolved_lead
        if resolved_lead is not None
        else ((payload.lead_user_id or "").strip() or None)
    )
    effective_members = (
        resolved_members
        if resolved_members is not None
        else normalize_member_user_ids(payload.member_user_ids)
    )
    node = OrgUnitNode(
        id=generate_new_org_unit_id(),
        slug=normalized_slug,
        name=cleaned_name,
        unit_type=payload.kind,
        parent_id=resolved_parent,
        billing_enabled=payload.billing_enabled,
        lead_user_id=effective_lead,
        member_user_ids=effective_members,
    )
    evaluator.upsert_org_unit(node)
    units_by_id[node.id] = node
    return build_org_unit_summary(node, units_by_id, attached_workspaces_count=0)


def update_in_evaluator(
    evaluator: MatrixPermissionEvaluator,
    org_unit_id: str,
    payload: OrgUnitPatchRequest,
    *,
    resolved_lead: str | None = None,
    resolved_members: tuple[str, ...] | None = None,
) -> OrgUnitSummary:
    """Update unit in memory evaluator when PostgreSQL sync is disabled or disconnected."""
    units_by_id = {u.id: u for u in evaluator.org_units}
    target = evaluator.get_org_unit(org_unit_id)
    if target is None or target.unit_type == "ENTERPRISE":
        raise ResourceNotFoundError(
            detail_override=f"Unité organisationnelle introuvable : '{org_unit_id}'."
        )
    target_kind: OrgUnitKind = "BU" if target.unit_type in ("BU", "TRIBE") else "TEAM"
    next_name = target.name
    if payload.name is not None:
        stripped = payload.name.strip()
        if not stripped:
            raise ValidationDomainError(detail_override="Le nom de l'unité ne peut pas être vide.")
        next_name = stripped

    if "parent_id" in payload.model_fields_set:
        next_parent = validate_org_unit_hierarchy(
            unit_id=target.id,
            kind=target_kind,
            parent_id=payload.parent_id,
            units_by_id=units_by_id,
        )
    else:
        parent_node = units_by_id.get(target.parent_id or "")
        next_parent = (
            None
            if parent_node is not None and parent_node.unit_type == "ENTERPRISE"
            else target.parent_id
        )

    next_billing = (
        target.billing_enabled if payload.billing_enabled is None else payload.billing_enabled
    )
    next_lead: str | None
    if resolved_lead is not None:
        next_lead = resolved_lead
    elif "lead_user_id" in payload.model_fields_set:
        next_lead = (payload.lead_user_id or "").strip() or None
    else:
        next_lead = target.lead_user_id

    if resolved_members is not None:
        next_members = resolved_members
    elif payload.member_user_ids is not None:
        next_members = normalize_member_user_ids(payload.member_user_ids)
    else:
        next_members = target.member_user_ids
    updated = OrgUnitNode(
        id=target.id,
        slug=target.slug,
        name=next_name,
        unit_type=target_kind,
        parent_id=next_parent,
        billing_enabled=next_billing,
        lead_user_id=next_lead,
        member_user_ids=next_members,
    )
    evaluator.upsert_org_unit(updated)
    units_by_id[updated.id] = updated
    ws_cnt = sum(1 for w in evaluator.workspaces if w.owner_org_unit_id == updated.id)
    return build_org_unit_summary(updated, units_by_id, attached_workspaces_count=ws_cnt)


def delete_in_evaluator(evaluator: MatrixPermissionEvaluator, org_unit_id: str) -> str:
    """Delete unit in memory evaluator when PostgreSQL sync is disabled or disconnected."""
    target = evaluator.get_org_unit(org_unit_id)
    if target is None or target.unit_type == "ENTERPRISE":
        raise ResourceNotFoundError(
            detail_override=f"Unité organisationnelle introuvable : '{org_unit_id}'."
        )
    child_cnt = sum(
        1 for u in evaluator.org_units if u.parent_id == target.id and u.unit_type != "ENTERPRISE"
    )
    ws_cnt = sum(1 for w in evaluator.workspaces if w.owner_org_unit_id == target.id)
    assert_org_unit_deletable(
        target_name=target.name,
        child_units_count=child_cnt,
        attached_workspaces_count=ws_cnt,
    )
    evaluator.remove_org_unit_node(target.id)
    return target.id
