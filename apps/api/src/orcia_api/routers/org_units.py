"""Story 17.2 — Hierarchical Organizational Units CRUD Router (`/api/v1/org-units`)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.auth_and_org import (
    OrgUnitCreateRequest,
    OrgUnitDeleteResponse,
    OrgUnitPatchRequest,
    OrgUnitResponse,
    OrgUnitsListResponse,
)
from orcia_core.bootstrap import (
    create_org_unit_on_postgres18,
    delete_org_unit_on_postgres18,
    list_org_units_from_postgres18,
    update_org_unit_on_postgres18,
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
    list_evaluator_org_unit_summaries,
    normalize_member_user_ids,
    normalize_org_unit_slug,
    validate_org_unit_hierarchy,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    OrciaDomainError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)

logger = get_logger("orcia.api.org_units")
router = APIRouter()

ORG_UNITS_MUTATION_RESPONSES = {
    **PROBLEM_RESPONSES,
    409: PROBLEM_RESPONSES[422],
}


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_summary(summary: OrgUnitSummary) -> OrgUnitResponse:
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
    )


def _enforce_org_unit_mutation_access(request: Request, persona_key: str | None) -> None:
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


def _sync_evaluator_from_summaries(
    evaluator: MatrixPermissionEvaluator,
    summaries: list[OrgUnitSummary],
) -> None:
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


def _pg_enabled() -> bool:
    return os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1"


def _create_in_evaluator(
    evaluator: MatrixPermissionEvaluator,
    payload: OrgUnitCreateRequest,
) -> OrgUnitSummary:
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
    node = OrgUnitNode(
        id=generate_new_org_unit_id(),
        slug=normalized_slug,
        name=cleaned_name,
        unit_type=payload.kind,
        parent_id=resolved_parent,
        billing_enabled=payload.billing_enabled,
        lead_user_id=(payload.lead_user_id or "").strip() or None,
        member_user_ids=normalize_member_user_ids(payload.member_user_ids),
    )
    evaluator.upsert_org_unit(node)
    units_by_id[node.id] = node
    return build_org_unit_summary(node, units_by_id, attached_workspaces_count=0)


def _update_in_evaluator(
    evaluator: MatrixPermissionEvaluator,
    org_unit_id: str,
    payload: OrgUnitPatchRequest,
) -> OrgUnitSummary:
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
    next_lead = (
        ((payload.lead_user_id or "").strip() or None)
        if "lead_user_id" in payload.model_fields_set
        else target.lead_user_id
    )
    next_members = (
        normalize_member_user_ids(payload.member_user_ids)
        if payload.member_user_ids is not None
        else target.member_user_ids
    )
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


def _delete_in_evaluator(evaluator: MatrixPermissionEvaluator, org_unit_id: str) -> str:
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


@router.get(
    "/org-units",
    response_model=OrgUnitsListResponse,
    summary="List hierarchical organizational units (`BU -> Sous-BU -> TEAM`) with FinOps & counts",
    responses=PROBLEM_RESPONSES,
)
async def list_org_units(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> OrgUnitsListResponse:
    svc = get_auth_service(request)
    effective_persona = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    resolve_request_user(request, persona_key=effective_persona)
    summaries: list[OrgUnitSummary] | None = None
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            summaries = await list_org_units_from_postgres18(engine)
            _sync_evaluator_from_summaries(svc.evaluator, summaries)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_units_list_pg_fallback", error_type=type(exc).__name__)
            summaries = None
    if summaries is None:
        summaries = list_evaluator_org_unit_summaries(
            svc.evaluator.org_units,
            [w.owner_org_unit_id for w in svc.evaluator.workspaces],
        )
    return OrgUnitsListResponse(
        org_units=[_serialize_summary(s) for s in summaries],
        trace_id=_trace(request),
    )


@router.post(
    "/org-units",
    response_model=OrgUnitResponse,
    summary="Create a Division (`BU`), Sub-Division (`BU` with parent), or Team (`TEAM`)",
    responses=ORG_UNITS_MUTATION_RESPONSES,
)
async def create_org_unit(
    payload: OrgUnitCreateRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> OrgUnitResponse:
    _enforce_org_unit_mutation_access(request, persona_key)
    svc = get_auth_service(request)
    created: OrgUnitSummary | None = None
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            created = await create_org_unit_on_postgres18(
                engine,
                name=payload.name,
                kind=payload.kind,
                slug=payload.slug,
                parent_id=payload.parent_id,
                billing_enabled=payload.billing_enabled,
                lead_user_id=payload.lead_user_id,
                member_user_ids=payload.member_user_ids,
            )
            svc.evaluator.upsert_org_unit(
                OrgUnitNode(
                    id=created.id,
                    slug=created.slug,
                    name=created.name,
                    unit_type=created.kind,
                    parent_id=created.parent_id,
                    billing_enabled=created.billing_enabled,
                    lead_user_id=created.lead_user_id,
                    member_user_ids=created.member_user_ids,
                )
            )
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_units_create_pg_fallback", error_type=type(exc).__name__)
            created = None
    if created is None:
        created = _create_in_evaluator(svc.evaluator, payload)
    return _serialize_summary(created)


@router.patch(
    "/org-units/{org_unit_id}",
    response_model=OrgUnitResponse,
    summary="Update an organizational unit's name, parent hierarchy, FinOps billing, or members",
    responses=ORG_UNITS_MUTATION_RESPONSES,
)
async def patch_org_unit(
    payload: OrgUnitPatchRequest,
    request: Request,
    org_unit_id: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> OrgUnitResponse:
    _enforce_org_unit_mutation_access(request, persona_key)
    svc = get_auth_service(request)
    updated: OrgUnitSummary | None = None
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            updated = await update_org_unit_on_postgres18(
                engine,
                org_unit_id=org_unit_id,
                name=payload.name,
                parent_id=payload.parent_id,
                parent_id_provided="parent_id" in payload.model_fields_set,
                billing_enabled=payload.billing_enabled,
                lead_user_id=payload.lead_user_id,
                lead_user_id_provided="lead_user_id" in payload.model_fields_set,
                member_user_ids=payload.member_user_ids,
            )
            svc.evaluator.upsert_org_unit(
                OrgUnitNode(
                    id=updated.id,
                    slug=updated.slug,
                    name=updated.name,
                    unit_type=updated.kind,
                    parent_id=updated.parent_id,
                    billing_enabled=updated.billing_enabled,
                    lead_user_id=updated.lead_user_id,
                    member_user_ids=updated.member_user_ids,
                )
            )
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_units_patch_pg_fallback", error_type=type(exc).__name__)
            updated = None
    if updated is None:
        updated = _update_in_evaluator(svc.evaluator, org_unit_id, payload)
    return _serialize_summary(updated)


@router.delete(
    "/org-units/{org_unit_id}",
    response_model=OrgUnitDeleteResponse,
    summary="Delete an empty organizational unit (`HTTP 409 ERR_ORG_UNIT_NOT_EMPTY` if non-empty)",
    responses=ORG_UNITS_MUTATION_RESPONSES,
)
async def delete_org_unit(
    request: Request,
    org_unit_id: str = Path(..., min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> OrgUnitDeleteResponse:
    _enforce_org_unit_mutation_access(request, persona_key)
    svc = get_auth_service(request)
    deleted_id: str | None = None
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            deleted_id = await delete_org_unit_on_postgres18(engine, org_unit_id=org_unit_id)
            svc.evaluator.remove_org_unit_node(deleted_id)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_units_delete_pg_fallback", error_type=type(exc).__name__)
            deleted_id = None
    if deleted_id is None:
        deleted_id = _delete_in_evaluator(svc.evaluator, org_unit_id)
    return OrgUnitDeleteResponse(
        deleted_id=deleted_id,
        deleted=True,
        trace_id=_trace(request),
    )
