"""Promotion decision handler for Story 20.2 PG18 Ontology & Promotions Router."""

from __future__ import annotations

from dataclasses import replace
from typing import Literal

from fastapi import Request

from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.routers._ontology_promotions_helpers import (
    prepare_ontology_handler_context,
    serialize_proposal_detail,
)
from orcia_api.routers.ontology_rag_helpers import get_trace_id, serialize_concept
from orcia_api.schemas import ontology_promotions as s
from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyGovernanceService,
    OntologyLevel,
    OntologyPromotionProposal,
    WhatIfImpactReport,
    assert_can_review_promotion,
    decide_proposal_pg,
    find_workspace,
    get_proposal_pg,
    record_ontology_audit_event_pg,
)
from orcia_core.ontology.errors import (
    OntologyConflictError,
    ResourceNotFoundError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str


def build_promotion_impact(
    gov: OntologyGovernanceService,
    source: OntologyConceptEntity,
    target_level: OntologyLevel,
    proposed_change: str | None,
) -> WhatIfImpactReport:
    """Compute What-If impact report or lightweight report for PG-only concepts."""
    summary = proposed_change or f"Promote {source.canonical_term} to {target_level}"
    if any(c.concept_key == source.concept_key for c in gov.concepts):
        return gov.simulate_what_if(concept_key=source.concept_key, proposed_change=summary)
    return WhatIfImpactReport(
        concept_key=source.concept_key,
        canonical_term=source.canonical_term,
        proposed_change=summary,
        transitively_affected_concepts=(),
        impacted_artifact_templates=(),
        impacted_workflow_uris=(),
        impacted_active_run_ids=(),
        has_immutable_axiom_conflict=False,
    )


def create_proposal_in_memory(
    gov: OntologyGovernanceService,
    *,
    concepts: list[OntologyConceptEntity],
    source: OntologyConceptEntity,
    target_level: OntologyLevel,
    target_scope_id: str,
    user: UserIdentity,
    impact: WhatIfImpactReport,
) -> OntologyPromotionProposal:
    """Create and store a promotion proposal in the in-memory governance service."""
    coll = next(
        (
            c
            for c in concepts
            if c.level == target_level
            and c.scope_id == target_scope_id
            and c.canonical_term.lower() == source.canonical_term.lower()
        ),
        None,
    )
    prop_id = new_uuid7_str()
    created = OntologyPromotionProposal(
        id=prop_id,
        proposal_key=f"prop-{source.concept_key}-to-{target_level.lower()}-{prop_id[-6:]}",
        concept_key=source.concept_key,
        canonical_term=source.canonical_term,
        source_level=source.level,
        target_level=target_level,
        target_scope_id=target_scope_id,
        proposed_by_user_id=user.email or user.id,
        status="PENDING_REVIEW",
        impact_report=impact,
        source_concept_id=source.id,
        source_scope_id=source.scope_id,
        definition_text=source.definition_text,
        collision_detected=coll is not None,
        colliding_definition=coll.definition_text if coll else None,
    )
    gov.save_proposal(created)
    return created


def _decide_proposal_in_memory(
    gov: OntologyGovernanceService,
    *,
    existing: OntologyPromotionProposal,
    decision: Literal["APPROVE", "REJECT"],
    reviewer: UserIdentity,
    review_comment: str | None,
) -> tuple[OntologyPromotionProposal, OntologyConceptEntity | None]:
    """Approve or reject a proposal in the in-memory governance service."""
    promoted_concept: OntologyConceptEntity | None = None
    if decision == "APPROVE":
        promoted_concept = OntologyConceptEntity(
            id=new_uuid7_str(),
            concept_key=f"{existing.concept_key}-{existing.target_level.lower()}",
            canonical_term=existing.canonical_term,
            level=existing.target_level,
            scope_id=existing.target_scope_id,
            definition_text=existing.definition_text or existing.canonical_term,
            parent_concept_id=existing.source_concept_id,
        )
        gov.upsert_concept(reviewer, promoted_concept)
    updated = replace(
        existing,
        status="APPROVED" if decision == "APPROVE" else "REJECTED",
        reviewed_by_user_id=reviewer.email or reviewer.id,
        review_comment=review_comment,
    )
    gov.save_proposal(updated)
    return updated, promoted_concept


async def handle_decide_promotion(
    request: Request,
    body: s.OntologyPromotionDecideRequest,
    *,
    proposal_id: str,
    fixture: bool,
    persona_key: str | None,
) -> s.OntologyPromotionDecideResponse:
    """Approve or reject a pending proposal (`ONTOLOGY_LEAD` for L2, `PLATFORM_ADMIN` for L1)."""
    user, memberships, gov, engine, org_units, workspaces = await prepare_ontology_handler_context(
        request, fixture=fixture, persona_key=persona_key, reject_observer=True
    )
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
        memberships,
        source_scope_id=existing.source_scope_id,
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
        updated, promoted_concept = _decide_proposal_in_memory(
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
