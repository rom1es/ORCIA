"""Story 17.2 — Hierarchical Organizational Units CRUD Router (`/api/v1/org-units`)."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.routers._org_units_helpers import (
    classify_and_handle_pg_error,
    create_in_evaluator,
    delete_in_evaluator,
    enforce_org_unit_mutation_access,
    pg_sync_enabled,
    resolve_trace_id,
    serialize_org_unit_summary,
    sync_evaluator_from_summaries,
    update_in_evaluator,
)
from orcia_api.routers._org_units_users import (
    collect_known_org_users,
    serialize_known_users,
    validate_and_normalize_org_unit_users_in_request,
)
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
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import OrgUnitNode, OrgUnitSummary, list_evaluator_org_unit_summaries
from orcia_core.permissions.errors import OrciaDomainError
from orcia_core.permissions.org_user_validation import KnownOrgUser

logger = get_logger("orcia.api.org_units")
router = APIRouter()

ORG_UNITS_MUTATION_RESPONSES = {
    **PROBLEM_RESPONSES,
    409: PROBLEM_RESPONSES[422],
}


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
    known_users_raw: list[KnownOrgUser] = []
    if pg_sync_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            summaries = await list_org_units_from_postgres18(engine)
            sync_evaluator_from_summaries(svc.evaluator, summaries)
            async with engine.connect() as conn:
                known_users_raw = await collect_known_org_users(request, conn)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_units_list_pg_error", operation="list_org_units", error=str(exc))
            classify_and_handle_pg_error(exc, operation="list_org_units")
            summaries = None
    if summaries is None:
        summaries = list_evaluator_org_unit_summaries(
            svc.evaluator.org_units,
            [w.owner_org_unit_id for w in svc.evaluator.workspaces],
            svc.evaluator.workspaces,
        )
    if not known_users_raw:
        known_users_raw = await collect_known_org_users(request, None)
    return OrgUnitsListResponse(
        org_units=[serialize_org_unit_summary(s) for s in summaries],
        known_users=serialize_known_users(known_users_raw),
        trace_id=resolve_trace_id(request),
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
    enforce_org_unit_mutation_access(request, persona_key)
    svc = get_auth_service(request)
    created: OrgUnitSummary | None = None
    if pg_sync_enabled():
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
            logger.warning("org_units_create_pg_error", operation="create_org_unit", error=str(exc))
            classify_and_handle_pg_error(exc, operation="create_org_unit")
            created = None
    if created is None:
        resolved_lead, resolved_members = await validate_and_normalize_org_unit_users_in_request(
            request, payload.lead_user_id, payload.member_user_ids, conn=None
        )
        created = create_in_evaluator(
            svc.evaluator,
            payload,
            resolved_lead=resolved_lead,
            resolved_members=resolved_members,
        )
    return serialize_org_unit_summary(created)


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
    enforce_org_unit_mutation_access(request, persona_key)
    svc = get_auth_service(request)
    updated: OrgUnitSummary | None = None
    if pg_sync_enabled():
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
            logger.warning("org_units_patch_pg_error", operation="patch_org_unit", error=str(exc))
            classify_and_handle_pg_error(exc, operation="patch_org_unit")
            updated = None
    if updated is None:
        should_validate_users = (
            "lead_user_id" in payload.model_fields_set
            and bool((payload.lead_user_id or "").strip())
        ) or (payload.member_user_ids is not None)
        if should_validate_users:
            (
                resolved_lead,
                resolved_members,
            ) = await validate_and_normalize_org_unit_users_in_request(
                request,
                payload.lead_user_id if "lead_user_id" in payload.model_fields_set else None,
                payload.member_user_ids,
                conn=None,
            )
        else:
            resolved_lead, resolved_members = None, None
        updated = update_in_evaluator(
            svc.evaluator,
            org_unit_id,
            payload,
            resolved_lead=resolved_lead,
            resolved_members=resolved_members,
        )
    return serialize_org_unit_summary(updated)


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
    enforce_org_unit_mutation_access(request, persona_key)
    svc = get_auth_service(request)
    deleted_id: str | None = None
    if pg_sync_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            deleted_id = await delete_org_unit_on_postgres18(engine, org_unit_id=org_unit_id)
            svc.evaluator.remove_org_unit_node(deleted_id)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_units_delete_pg_error", operation="delete_org_unit", error=str(exc))
            classify_and_handle_pg_error(exc, operation="delete_org_unit")
            deleted_id = None
    if deleted_id is None:
        deleted_id = delete_in_evaluator(svc.evaluator, org_unit_id)
    return OrgUnitDeleteResponse(
        deleted_id=deleted_id,
        deleted=True,
        trace_id=resolve_trace_id(request),
    )


__all__ = ["router"]
