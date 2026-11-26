"""Story 20.2 Router: PG18 Ontology Concepts, Role Permissions & Step-by-Step Promotions."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._entity_delete_rbac import (
    build_ontology_target_authorizer,
    prepare_entity_delete_guards,
)
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
from orcia_api.schemas._pack_composer import GuardedEntityDeleteResponse
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.storage.entity_delete_tx import delete_entity_guarded_tx

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


async def _delete_ontology_entity(
    request: Request,
    *,
    entity_type: str,
    entity_id: str,
    unlink_from_draft_packs: bool,
    persona_key: str | None,
) -> GuardedEntityDeleteResponse:
    inst = str(request.url.path)
    user, auth_svc, trace_id, authorize_draft = await prepare_entity_delete_guards(
        request, persona_key=persona_key
    )
    engine = get_configured_db_engine(request)
    if engine is None:
        raise ResourceNotFoundError(
            detail_override=f"{entity_type} '{entity_id}' not found.",
            instance=inst,
        )
    outcome = await delete_entity_guarded_tx(
        engine,
        entity_type=entity_type,
        entity_id_or_key=entity_id,
        unlink_from_draft_packs=unlink_from_draft_packs,
        authorize_target_cb=build_ontology_target_authorizer(
            auth_svc, user, entity_type=entity_type, instance=inst
        ),
        authorize_draft_cb=authorize_draft,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=inst,
    )
    return GuardedEntityDeleteResponse(
        entity_type=outcome.entity_type,
        deleted_id=outcome.deleted_id,
        deleted_uuid=outcome.deleted_uuid,
        unlinked_draft_packs=list(outcome.unlinked_draft_packs),
        trace_id=trace_id,
    )


@router.delete(
    "/concepts/{concept_id}",
    response_model=GuardedEntityDeleteResponse,
    responses=PROBLEM_RESPONSES,
)
async def delete_ontology_concept_endpoint(
    request: Request,
    concept_id: str = Path(..., min_length=1, max_length=128),
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> GuardedEntityDeleteResponse:
    """Delete an ontology concept with `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` guard."""
    return await _delete_ontology_entity(
        request,
        entity_type="ONTOLOGY_CONCEPT",
        entity_id=concept_id,
        unlink_from_draft_packs=unlink_from_draft_packs,
        persona_key=persona_key,
    )


@router.delete(
    "/relations/{relation_id}",
    response_model=GuardedEntityDeleteResponse,
    responses=PROBLEM_RESPONSES,
)
async def delete_ontology_relation_endpoint(
    request: Request,
    relation_id: str = Path(..., min_length=1, max_length=128),
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> GuardedEntityDeleteResponse:
    """Delete an ontology relation with `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` guard."""
    return await _delete_ontology_entity(
        request,
        entity_type="ONTOLOGY_RELATION",
        entity_id=relation_id,
        unlink_from_draft_packs=unlink_from_draft_packs,
        persona_key=persona_key,
    )


@router.delete(
    "/axioms/{axiom_id}",
    response_model=GuardedEntityDeleteResponse,
    responses=PROBLEM_RESPONSES,
)
async def delete_ontology_axiom_endpoint(
    request: Request,
    axiom_id: str = Path(..., min_length=1, max_length=128),
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> GuardedEntityDeleteResponse:
    """Delete an ontology axiom with `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` guard."""
    return await _delete_ontology_entity(
        request,
        entity_type="ONTOLOGY_AXIOM",
        entity_id=axiom_id,
        unlink_from_draft_packs=unlink_from_draft_packs,
        persona_key=persona_key,
    )
