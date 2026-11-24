"""Patch and delete mutation handlers for `/api/v1/org-units` (`Story 17.2`, `Story 27.7`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.routers._auth_pg_helpers import sync_auth_service_user_by_email_from_pg
from orcia_api.routers._org_units_delegation_helpers import (
    enforce_org_delete_delegation,
    enforce_org_patch_delegation,
    ensure_evaluator_org_units_synced,
    record_governance_audit_event,
    resolve_org_caller,
    serialize_org_unit_with_capabilities,
)
from orcia_api.routers._org_units_helpers import (
    classify_and_handle_pg_error,
    delete_in_evaluator,
    pg_sync_enabled,
    resolve_trace_id,
    update_in_evaluator,
)
from orcia_api.routers._org_units_users import validate_and_normalize_org_unit_users_in_request
from orcia_api.schemas.auth_and_org import (
    OrgUnitDeleteResponse,
    OrgUnitPatchRequest,
    OrgUnitResponse,
)
from orcia_core.bootstrap import delete_org_unit_on_postgres18, update_org_unit_on_postgres18
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import OrgUnitNode, OrgUnitSummary
from orcia_core.permissions.errors import OrciaDomainError

logger = get_logger("orcia.api.org_units.mutations")


async def execute_patch_org_unit(
    request: Request,
    org_unit_id: str,
    payload: OrgUnitPatchRequest,
    persona_key: str | None,
) -> OrgUnitResponse:
    """Update an organizational unit's name, parent hierarchy, FinOps billing, or members."""
    svc = get_auth_service(request)
    caller = resolve_org_caller(request, persona_key)
    await ensure_evaluator_org_units_synced(request, svc.evaluator)
    target_node = enforce_org_patch_delegation(request, caller, org_unit_id, payload, svc.evaluator)
    old_leads_and_onto = {*target_node.lead_user_ids, *target_node.ontology_lead_user_ids}
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
                lead_user_ids=payload.lead_user_ids,
                lead_user_ids_provided="lead_user_ids" in payload.model_fields_set,
                ontology_lead_user_ids=payload.ontology_lead_user_ids,
                ontology_lead_user_ids_provided=(
                    "ontology_lead_user_ids" in payload.model_fields_set
                ),
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
                    lead_user_ids=updated.lead_user_ids,
                    ontology_lead_user_ids=updated.ontology_lead_user_ids,
                    member_user_ids=updated.member_user_ids,
                )
            )
            for uid in {
                *old_leads_and_onto,
                *updated.lead_user_ids,
                *updated.ontology_lead_user_ids,
            }:
                await sync_auth_service_user_by_email_from_pg(request, svc, uid)
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
    await record_governance_audit_event(
        request,
        actor=caller,
        event_type="ORG_UNIT_UPDATED",
        summary=get_router_copy().org_unit_updated.format(name=updated.name, kind=updated.kind),
        org_unit_id=updated.id,
        scope_path=updated.slug or "GLOBAL",
        metadata={"changed_fields": sorted(payload.model_fields_set)},
    )
    return serialize_org_unit_with_capabilities(request, caller, updated, svc.evaluator)


async def execute_delete_org_unit(
    request: Request,
    org_unit_id: str,
    persona_key: str | None,
) -> OrgUnitDeleteResponse:
    """Delete an empty organizational unit (`HTTP 409 ERR_ORG_UNIT_NOT_EMPTY` if non-empty)."""
    svc = get_auth_service(request)
    caller = resolve_org_caller(request, persona_key)
    await ensure_evaluator_org_units_synced(request, svc.evaluator)
    old_node = enforce_org_delete_delegation(request, caller, org_unit_id, svc.evaluator)
    old_leads = {*old_node.lead_user_ids, *old_node.ontology_lead_user_ids}
    deleted_id: str | None = None
    if pg_sync_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            deleted_id = await delete_org_unit_on_postgres18(engine, org_unit_id=org_unit_id)
            svc.evaluator.remove_org_unit_node(deleted_id)
            for uid in old_leads:
                await sync_auth_service_user_by_email_from_pg(request, svc, uid)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("org_units_delete_pg_error", operation="delete_org_unit", error=str(exc))
            classify_and_handle_pg_error(exc, operation="delete_org_unit")
            deleted_id = None
    if deleted_id is None:
        deleted_id = delete_in_evaluator(svc.evaluator, org_unit_id)
    await record_governance_audit_event(
        request,
        actor=caller,
        event_type="ORG_UNIT_DELETED",
        summary=get_router_copy().org_unit_deleted.format(
            name=old_node.name, kind=old_node.unit_type
        ),
        org_unit_id=deleted_id,
        scope_path=old_node.slug or "GLOBAL",
        metadata={"kind": old_node.unit_type},
    )
    return OrgUnitDeleteResponse(
        deleted_id=deleted_id,
        deleted=True,
        trace_id=resolve_trace_id(request),
    )
