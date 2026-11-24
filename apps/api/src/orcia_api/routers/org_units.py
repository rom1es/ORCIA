"""Story 17.2 — Hierarchical Organizational Units CRUD Router (`/api/v1/org-units`)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.routers._auth_pg_helpers import sync_auth_service_user_by_email_from_pg
from orcia_api.routers._org_units_delegation_helpers import (
    enforce_org_create_delegation,
    ensure_evaluator_org_units_synced,
    filter_and_annotate_org_units,
    record_governance_audit_event,
    resolve_org_caller,
    serialize_org_unit_with_capabilities,
)
from orcia_api.routers._org_units_helpers import (
    classify_and_handle_pg_error,
    create_in_evaluator,
    filter_org_unit_summaries_in_memory,
    pg_sync_enabled,
    resolve_trace_id,
    sync_evaluator_from_summaries,
)
from orcia_api.routers._org_units_mutation_handlers import (
    execute_delete_org_unit,
    execute_patch_org_unit,
)
from orcia_api.routers._org_units_users import (
    collect_known_org_users,
    search_known_org_users_for_request,
    serialize_known_users,
    validate_and_normalize_org_unit_users_in_request,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.auth_and_org import (
    KnownOrgUsersSearchResponse,
    OrgUnitCreateRequest,
    OrgUnitDeleteResponse,
    OrgUnitPatchRequest,
    OrgUnitResponse,
    OrgUnitsListResponse,
)
from orcia_core.bootstrap import (
    create_org_unit_on_postgres18,
    list_org_units_from_postgres18,
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
    summary="List hierarchical organizational units (`BU -> Sub-BU -> TEAM`) with FinOps & counts",
    responses=PROBLEM_RESPONSES,
)
async def list_org_units(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
    q: str | None = Query(default=None, max_length=128),
    kind: Literal["BU", "TEAM"] | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
) -> OrgUnitsListResponse:
    svc = get_auth_service(request)
    caller = resolve_org_caller(request, persona_key)
    summaries: list[OrgUnitSummary] | None = None
    known_users_raw: list[KnownOrgUser] = []
    if pg_sync_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            summaries = await list_org_units_from_postgres18(engine, q=q, kind=kind, limit=limit)
            if q is None and kind is None and limit is None:
                sync_evaluator_from_summaries(svc.evaluator, summaries)
            else:
                await ensure_evaluator_org_units_synced(request, svc.evaluator)
            async with engine.connect() as conn:
                known_users_raw = await collect_known_org_users(request, conn)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_units_list_pg_error", operation="list_org_units", error=str(exc))
            classify_and_handle_pg_error(exc, operation="list_org_units")
            summaries = None
    if summaries is None:
        full_summaries = list_evaluator_org_unit_summaries(
            svc.evaluator.org_units,
            [w.owner_org_unit_id for w in svc.evaluator.workspaces],
            svc.evaluator.workspaces,
        )
        if q is not None or kind is not None or limit is not None:
            summaries = filter_org_unit_summaries_in_memory(
                full_summaries, q=q, kind=kind, limit=limit
            )
        else:
            summaries = full_summaries
    if not known_users_raw:
        known_users_raw = await collect_known_org_users(request, None)
    return OrgUnitsListResponse(
        org_units=filter_and_annotate_org_units(request, caller, summaries, svc.evaluator),
        known_users=serialize_known_users(known_users_raw),
        trace_id=resolve_trace_id(request),
    )


@router.get(
    "/org-units/known-users",
    response_model=KnownOrgUsersSearchResponse,
    summary="Search active known platform users with incremental query and pagination limit",
    responses=PROBLEM_RESPONSES,
)
async def search_known_org_users(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
    q: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=10, ge=1, le=100),
) -> KnownOrgUsersSearchResponse:
    effective_persona = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    resolve_request_user(request, persona_key=effective_persona)
    svc = get_auth_service(request)
    users, has_more = await search_known_org_users_for_request(request, svc, q=q, limit=limit)
    return KnownOrgUsersSearchResponse(
        items=serialize_known_users(users),
        has_more=has_more,
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
    svc = get_auth_service(request)
    caller = resolve_org_caller(request, persona_key)
    await ensure_evaluator_org_units_synced(request, svc.evaluator)
    enforce_org_create_delegation(request, caller, payload, svc.evaluator)
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
                lead_user_ids=payload.lead_user_ids,
                ontology_lead_user_ids=payload.ontology_lead_user_ids,
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
                    lead_user_ids=created.lead_user_ids,
                    ontology_lead_user_ids=created.ontology_lead_user_ids,
                    member_user_ids=created.member_user_ids,
                )
            )
            for uid in {*created.lead_user_ids, *created.ontology_lead_user_ids}:
                await sync_auth_service_user_by_email_from_pg(request, svc, uid)
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
    await record_governance_audit_event(
        request,
        actor=caller,
        event_type="ORG_UNIT_CREATED",
        summary=get_router_copy().org_unit_created.format(name=created.name, kind=created.kind),
        org_unit_id=created.id,
        scope_path=created.slug or "GLOBAL",
        metadata={"kind": created.kind, "slug": created.slug},
    )
    return serialize_org_unit_with_capabilities(request, caller, created, svc.evaluator)


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
    return await execute_patch_org_unit(request, org_unit_id, payload, persona_key)


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
    return await execute_delete_org_unit(request, org_unit_id, persona_key)


__all__ = ["router"]
