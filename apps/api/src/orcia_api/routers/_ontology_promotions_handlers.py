"""Handler orchestrations for Story 20.2 PG18 Ontology & Promotions Router."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies import get_auth_service, get_ontology_and_rag_services
from orcia_api.routers._ontology_promotions_helpers import (
    build_promotion_impact,
    compute_writable_options,
    create_proposal_in_memory,
    decide_proposal_in_memory,
    load_ontology_topology,
    resolve_dynamic_ontology_scopes,
    resolve_ontology_caller,
    serialize_proposal_detail,
)
from orcia_api.routers.ontology_rag_helpers import get_trace_id, serialize_concept
from orcia_api.schemas import ontology_and_rag as base_s
from orcia_api.schemas import ontology_promotions as s
from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyHierarchyResolver,
    OntologyLevel,
    assert_can_review_promotion,
    assert_can_write_ontology_level,
    can_read_ontology_item,
    can_review_promotion_target,
    can_write_ontology_level,
    create_proposal_pg,
    decide_proposal_pg,
    find_workspace,
    get_proposal_pg,
    is_observer_user,
    list_concepts_pg,
    list_proposals_pg,
    record_ontology_audit_event_pg,
    resolve_next_promotion_target,
    upsert_concept_pg,
)
from orcia_core.ontology.errors import (
    ObserverModeReadOnlyError,
    OntologyConflictError,
    PromotionLevelJumpError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_kernel.ids import new_uuid7_str


async def handle_list_concepts(
    request: Request, *, fixture: bool, persona_key: str | None
) -> s.OntologyConceptsListResponse:
    """List concepts readable by caller along with edit/promotion capabilities."""
    user = resolve_ontology_caller(request, persona_key)
    memberships = get_auth_service(request).evaluator.list_memberships()
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    engine, org_units, workspaces = await load_ontology_topology(request, fixture=fixture)
    raw_concepts = await list_concepts_pg(engine) if engine is not None else list(gov.concepts)
    items: list[s.OntologyConceptWithPermissionsItem] = []
    for c in raw_concepts:
        if not can_read_ontology_item(
            user, c.level, c.scope_id, org_units, workspaces, memberships
        ):
            continue
        next_lvl: OntologyLevel | None = None
        next_scope: str | None = None
        if c.level != "1_ENTERPRISE" and not is_observer_user(user):
            try:
                next_lvl, next_scope = resolve_next_promotion_target(
                    c.level, c.scope_id, org_units, workspaces
                )
            except PromotionLevelJumpError:
                next_lvl, next_scope = None, None
        items.append(
            s.OntologyConceptWithPermissionsItem(
                **serialize_concept(c).model_dump(),
                can_edit=can_write_ontology_level(
                    user, c.level, c.scope_id, org_units, workspaces, memberships
                ),
                can_propose_promotion=next_lvl is not None,
                next_promotion_level=next_lvl,
                next_promotion_scope_id=next_scope,
            )
        )
    writable_levels, writable_scopes = compute_writable_options(user, org_units, workspaces)
    return s.OntologyConceptsListResponse(
        concepts=items,
        writable_levels=writable_levels,
        writable_scopes=writable_scopes,
        trace_id=get_trace_id(request),
    )


async def handle_upsert_concept(
    request: Request,
    body: base_s.OntologyUpsertConceptRequest,
    *,
    fixture: bool,
    persona_key: str | None,
) -> base_s.OntologyConceptSchemaItem:
    """Create or update an ontology concept with L1–L4 RBAC & immutable axiom guard."""
    user = resolve_ontology_caller(request, persona_key)
    memberships = get_auth_service(request).evaluator.list_memberships()
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    engine, org_units, workspaces = await load_ontology_topology(request, fixture=fixture)
    assert_can_write_ontology_level(
        user,
        body.level,
        body.scope_id,
        org_units,
        workspaces,
        memberships,
        instance=str(request.url.path),
        allow_ephemeral_fallback=fixture,
    )
    candidate = OntologyConceptEntity(
        id=new_uuid7_str(),
        concept_key=body.concept_key,
        canonical_term=body.canonical_term,
        level=body.level,
        scope_id=body.scope_id,
        definition_text=body.definition_text,
        parent_concept_id=body.parent_concept_id,
        synonyms=tuple(body.synonyms),
        banned_terms=tuple(body.banned_terms),
        profile_translations=body.profile_translations,
        expected_schema=body.expected_schema,
        introduced_in_snapshot_id=body.introduced_in_snapshot_id,
    )
    existing = tuple(await list_concepts_pg(engine)) if engine is not None else gov.concepts
    ent_scope, dom_scope, team_scopes, ws_scope, run_scope = resolve_dynamic_ontology_scopes(
        body.level, body.scope_id, org_units, workspaces
    )
    OntologyHierarchyResolver.resolve_effective_ontology(
        concepts=(*existing, candidate),
        relations=gov.relations,
        axioms=gov.axioms,
        enterprise_scope_id=ent_scope,
        domain_scope_id=dom_scope,
        team_chain_scope_ids=team_scopes,
        workspace_scope_id=ws_scope,
        run_scope_id=run_scope,
    )
    if engine is not None:
        saved = await upsert_concept_pg(engine, candidate)
        ws_owner = find_workspace(workspaces, saved.scope_id)
        await record_ontology_audit_event_pg(
            engine,
            actor=user,
            event_type="ONTOLOGY_CONCEPT_CREATED",
            summary=f"Terme « {saved.canonical_term} » enregistré au niveau {saved.level}",
            scope_id=saved.scope_id,
            level=saved.level,
            owner_org_unit_id=ws_owner.owner_org_unit_id if ws_owner else None,
            metadata={"concept_key": saved.concept_key, "level": saved.level},
            trace_id=get_trace_id(request),
        )
        gov.upsert_concept(user, saved)
        return serialize_concept(saved)
    return serialize_concept(gov.upsert_concept(user, candidate))


async def handle_list_promotions(
    request: Request,
    *,
    status: str | None,
    fixture: bool,
    persona_key: str | None,
) -> s.OntologyPromotionsListResponse:
    """List visible promotion proposals annotated with caller `can_decide`."""
    user = resolve_ontology_caller(request, persona_key)
    memberships = get_auth_service(request).evaluator.list_memberships()
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    engine, org_units, workspaces = await load_ontology_topology(request, fixture=fixture)
    raw = (
        await list_proposals_pg(engine, status=status)
        if engine is not None
        else [p for p in gov.proposals if status is None or p.status == status]
    )
    items: list[s.OntologyPromotionProposalDetailItem] = []
    for p in raw:
        can_decide = can_review_promotion_target(
            user, p.target_level, p.target_scope_id, org_units, workspaces
        )
        src_scope = p.source_scope_id or p.target_scope_id
        if (
            can_decide
            or p.proposed_by_user_id in (user.id, user.email)
            or can_read_ontology_item(
                user, p.source_level, src_scope, org_units, workspaces, memberships
            )
        ):
            items.append(serialize_proposal_detail(p, can_decide=can_decide))
    return s.OntologyPromotionsListResponse(
        proposals=items,
        pending_count=sum(1 for i in items if i.status == "PENDING_REVIEW"),
        trace_id=get_trace_id(request),
    )


async def handle_create_promotion(
    request: Request,
    body: s.OntologyPromotionCreateRequest,
    *,
    fixture: bool,
    persona_key: str | None,
) -> s.OntologyPromotionProposalDetailItem:
    """Propose promotion strictly to the immediate next level (`L4 -> L3 -> L2 -> L1`)."""
    user = resolve_ontology_caller(request, persona_key)
    if is_observer_user(user):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    memberships = get_auth_service(request).evaluator.list_memberships()
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    engine, org_units, workspaces = await load_ontology_topology(request, fixture=fixture)
    concepts = await list_concepts_pg(engine) if engine is not None else list(gov.concepts)
    source = next((c for c in concepts if c.concept_key == body.concept_key), None)
    if source is None:
        raise ResourceNotFoundError(detail_override=f"Concept '{body.concept_key}' introuvable.")
    if not can_read_ontology_item(
        user, source.level, source.scope_id, org_units, workspaces, memberships
    ):
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    target_level, target_scope_id = resolve_next_promotion_target(
        source.level,
        source.scope_id,
        org_units,
        workspaces,
        explicit_target_level=body.target_level,
        explicit_target_scope_id=body.target_scope_id,
    )
    impact = build_promotion_impact(gov, source, target_level, body.proposed_change)
    if engine is not None:
        created = await create_proposal_pg(
            engine,
            source_concept=source,
            target_level=target_level,
            target_scope_id=target_scope_id,
            proposed_by=user,
            impact_report=impact,
        )
        target_ws = find_workspace(workspaces, target_scope_id)
        await record_ontology_audit_event_pg(
            engine,
            actor=user,
            event_type="ONTOLOGY_PROMOTION_PROPOSED",
            summary=(
                f"Promotion proposée pour « {source.canonical_term} » "
                f"({source.level} -> {target_level})"
            ),
            scope_id=target_scope_id,
            level=target_level,
            owner_org_unit_id=target_ws.owner_org_unit_id if target_ws else None,
            metadata={"proposal_key": created.proposal_key, "target_level": target_level},
            trace_id=get_trace_id(request),
        )
    else:
        created = create_proposal_in_memory(
            gov,
            concepts=concepts,
            source=source,
            target_level=target_level,
            target_scope_id=target_scope_id,
            user=user,
            impact=impact,
        )
    can_decide = can_review_promotion_target(
        user, created.target_level, created.target_scope_id, org_units, workspaces
    )
    return serialize_proposal_detail(created, can_decide=can_decide)


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
        raise ResourceNotFoundError(detail_override=f"Proposition '{proposal_id}' introuvable.")
    if existing.status != "PENDING_REVIEW":
        raise OntologyConflictError(
            detail_override=f"La proposition '{existing.proposal_key}' a déjà été traitée."
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
        await record_ontology_audit_event_pg(
            engine,
            actor=user,
            event_type=ev_type,
            summary=(
                f"Promotion {body.decision} pour « {updated.canonical_term} » "
                f"-> {updated.target_level}"
            ),
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
