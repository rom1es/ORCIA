"""Story 20.2 Router: PG18 Ontology Concepts, Role Permissions & Step-by-Step Promotions."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.routers._ontology_promotions_handlers import (
    handle_create_promotion,
    handle_decide_promotion,
    handle_list_concepts,
    handle_list_promotions,
    handle_upsert_concept,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas import ontology_and_rag as base_s
from orcia_api.schemas import ontology_promotions as s

router = APIRouter(prefix="/api/v1/ontology-rag/ontology", tags=["ontology-rag"])


@router.get("/concepts", response_model=s.OntologyConceptsListResponse, responses=PROBLEM_RESPONSES)
async def list_ontology_concepts(
    request: Request,
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.OntologyConceptsListResponse:
    """List concepts readable by caller along with edit/promotion capabilities."""
    return await handle_list_concepts(request, fixture=fixture, persona_key=persona_key)


@router.post(
    "/concepts", response_model=base_s.OntologyConceptSchemaItem, responses=PROBLEM_RESPONSES
)
async def upsert_ontology_concept(
    request: Request,
    body: base_s.OntologyUpsertConceptRequest,
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> base_s.OntologyConceptSchemaItem:
    """Create or update an ontology concept with L1–L4 RBAC & immutable axiom guard."""
    return await handle_upsert_concept(request, body, fixture=fixture, persona_key=persona_key)


@router.get(
    "/promotions", response_model=s.OntologyPromotionsListResponse, responses=PROBLEM_RESPONSES
)
async def list_ontology_promotions(
    request: Request,
    status: str | None = Query(default=None),
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.OntologyPromotionsListResponse:
    """List visible promotion proposals annotated with caller `can_decide`."""
    return await handle_list_promotions(
        request, status=status, fixture=fixture, persona_key=persona_key
    )


@router.post(
    "/promotions", response_model=s.OntologyPromotionProposalDetailItem, responses=PROBLEM_RESPONSES
)
async def create_ontology_promotion(
    request: Request,
    body: s.OntologyPromotionCreateRequest,
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.OntologyPromotionProposalDetailItem:
    """Propose promotion strictly to the immediate next level (`L4 -> L3 -> L2 -> L1`)."""
    return await handle_create_promotion(request, body, fixture=fixture, persona_key=persona_key)


@router.post(
    "/promotions/{proposal_id}/decide",
    response_model=s.OntologyPromotionDecideResponse,
    responses=PROBLEM_RESPONSES,
)
async def decide_ontology_promotion(
    request: Request,
    body: s.OntologyPromotionDecideRequest,
    proposal_id: str = Path(..., min_length=1, max_length=128),
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.OntologyPromotionDecideResponse:
    """Approve or reject a pending proposal (`ONTOLOGY_LEAD` for L2, `PLATFORM_ADMIN` for L1)."""
    return await handle_decide_promotion(
        request,
        body,
        proposal_id=proposal_id,
        fixture=fixture,
        persona_key=persona_key,
    )
