"""Promotion decision handler for Story 20.2 PG18 Ontology & Promotions Router."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies import get_ontology_and_rag_services
from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.routers._ontology_promotions_helpers import (
    decide_proposal_in_memory,
    load_ontology_topology,
    resolve_ontology_caller,
    serialize_proposal_detail,
)
from orcia_api.routers.ontology_rag_helpers import get_trace_id, serialize_concept
from orcia_api.schemas import ontology_promotions as s
from orcia_core.ontology import (
    assert_can_review_promotion,
    decide_proposal_pg,
    find_workspace,
    get_proposal_pg,
    is_observer_user,
    record_ontology_audit_event_pg,
)
from orcia_core.ontology.errors import (
    ObserverModeReadOnlyError,
    OntologyConflictError,
    ResourceNotFoundError,
)


async def handle_decide_promotion(
    request: Request,
    body: s.OntologyPromotionDecideRequest,
    *,
    proposal_id: str,
    fixture: bool,
    persona_key: str | None,
) -> s.OntologyPromotionDecideResponse:
    """Approve or reject a pending proposal (`ONTOLOGY_LEAD` for L2, `PLATFORM_ADMIN` for L1)."""
    user = resolve_ontology_caller(request, persona_key)
    if is_observer_user(user):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    engine, org_units, workspaces = await load_ontology_topology(request, fixture=fixture)
    existing = (
        await get_proposal_pg(engine, proposal_id)
        if engine is not None
        else next(
            (p for p in gov.proposals if p.id == proposal_id or p.proposal_key == proposal_id), None
        )
    )
    if existing is None:
        raise ResourceNotFoundError(
            detail_code="ERR_ONTOLOGY_PROPOSAL_NOT_FOUND",
            detail_params={"proposal_id": proposal_id},
        )
    if existing.status != "PENDING_REVIEW":
        raise OntologyConflictError(
            detail_code="ERR_ONTOLOGY_PROMOTION_ALREADY_PROCESSED",
            detail_params={"proposal_id": existing.proposal_key},
        )
    assert_can_review_promotion(
        user,
        existing.target_level,
        existing.target_scope_id,
        org_units,
        workspaces,
        instance=str(request.url.path),
    )
    if engine is not None:
        updated, promoted_concept = await decide_proposal_pg(
            engine,
            proposal_id_or_key=proposal_id,
            decision=body.decision,
            reviewer=user,
            review_comment=body.review_comment,
        )
        ev_type = (
            "ONTOLOGY_PROMOTION_APPROVED"
            if body.decision == "APPROVE"
            else "ONTOLOGY_PROMOTION_REJECTED"
        )
        target_ws = find_workspace(workspaces, updated.target_scope_id)
        summary = get_router_copy().ontology_promo_decided.format(
            decision=body.decision,
            term=updated.canonical_term,
            level=updated.target_level,
        )
        await record_ontology_audit_event_pg(
            engine,
            actor=user,
            event_type=ev_type,
            summary=summary,
            scope_id=updated.target_scope_id,
            level=updated.target_level,
            owner_org_unit_id=target_ws.owner_org_unit_id if target_ws else None,
            metadata={"proposal_key": updated.proposal_key, "decision": body.decision},
            trace_id=get_trace_id(request),
        )
    else:
        updated, promoted_concept = decide_proposal_in_memory(
            gov,
            existing=existing,
            decision=body.decision,
            reviewer=user,
            review_comment=body.review_comment,
        )
    return s.OntologyPromotionDecideResponse(
        proposal=serialize_proposal_detail(updated, can_decide=True),
        promoted_concept=serialize_concept(promoted_concept) if promoted_concept else None,
        status=updated.status,
        trace_id=get_trace_id(request),
    )
