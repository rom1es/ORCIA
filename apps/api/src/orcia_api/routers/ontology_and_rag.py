"""Epic 2 Router: 4-Level Ontology, What-If Simulator, Hybrid RAG & Tripartite Graph."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_ontology_and_rag_services
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.routers.ontology_rag_helpers import (
    get_trace_id,
    serialize_concept,
    serialize_doc,
    serialize_promotion,
    serialize_relation,
    serialize_stale_alert,
    serialize_trace_edge,
    serialize_what_if,
)
from orcia_api.schemas import ontology_and_rag as s
from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyHierarchyResolver,
    ProfileSemanticTranslator,
)
from orcia_core.ontology.errors import ObserverModeReadOnlyError
from orcia_core.rag import DifferentiatedIncrementalIndexer
from orcia_kernel.ids import new_uuid7_str

router = APIRouter(prefix="/api/v1/ontology-rag", tags=["ontology-rag"])


@router.get(
    "/state",
    response_model=s.OntologyAndRagStateResponse,
    summary="Inspect 4-Level Ontology, Promotions, Hybrid RAG Documents & Tripartite Graph",
    responses=PROBLEM_RESPONSES,
)
async def get_ontology_and_rag_state(
    request: Request,
    fixture: bool = Query(default=False, description="Use deterministic test fixture data"),
) -> s.OntologyAndRagStateResponse:
    gov, rag, trip = get_ontology_and_rag_services(request, fixture=fixture)
    return s.OntologyAndRagStateResponse(
        concepts=[serialize_concept(c) for c in gov.concepts],
        relations=[serialize_relation(r) for r in gov.relations],
        promotions=[serialize_promotion(p) for p in gov.proposals],
        documents=[serialize_doc(d) for d in rag.list_documents()],
        tripartite_edges=[serialize_trace_edge(e) for e in trip.list_edges()],
        stale_alerts=[serialize_stale_alert(a) for a in trip.list_alerts()],
        trace_id=get_trace_id(request),
    )


@router.post(
    "/ontology/resolve",
    response_model=s.OntologyResolveResponse,
    summary="Resolve effective 4-Level Ontology and Human Profile semantic translations",
    responses=PROBLEM_RESPONSES,
)
async def resolve_ontology_hierarchy(
    request: Request,
    body: s.OntologyResolveRequest,
    fixture: bool = Query(default=False),
) -> s.OntologyResolveResponse:
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    snap = gov.resolve_snapshot(
        enterprise_scope_id=body.enterprise_scope_id,
        domain_scope_id=body.domain_scope_id,
        team_chain_scope_ids=tuple(body.team_chain_scope_ids),
        workspace_scope_id=body.workspace_scope_id,
        run_scope_id=body.run_scope_id,
    )
    labels = {
        term: ProfileSemanticTranslator.translate_concept(c, body.human_profile)
        for term, c in snap.concepts_by_term.items()
    }
    return s.OntologyResolveResponse(
        concepts=[serialize_concept(c) for c in snap.concepts_by_term.values()],
        relations=[serialize_relation(r) for r in snap.relations],
        profile_labels=labels,
        trace_id=get_trace_id(request),
    )


@router.post(
    "/ontology/concepts",
    response_model=s.OntologyConceptSchemaItem,
    summary="Upsert an Ontology Concept (enforces L1 immutable axiom protection -> HTTP 422)",
    responses=PROBLEM_RESPONSES,
)
async def upsert_ontology_concept(
    request: Request,
    body: s.OntologyUpsertConceptRequest,
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.OntologyConceptSchemaItem:
    user = resolve_request_user(request, persona_key=persona_key)
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
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
    default_teams = ("scope-subteam-checkout", "scope-team-core")
    team_scopes = (
        (body.scope_id, *default_teams)
        if body.level == "3_TEAM" and body.scope_id not in default_teams
        else default_teams
    )
    OntologyHierarchyResolver.resolve_effective_ontology(
        concepts=(*gov.concepts, candidate),
        relations=gov.relations,
        axioms=gov.axioms,
        enterprise_scope_id=body.scope_id if body.level == "1_ENTERPRISE" else "scope-global",
        domain_scope_id=body.scope_id if body.level == "2_DOMAIN" else "scope-bu-digital",
        team_chain_scope_ids=team_scopes,
        workspace_scope_id=body.scope_id if body.level == "3_WORKSPACE" else "ws-solution-paiement",
        run_scope_id=body.scope_id if body.level == "4_RUN_EPHEMERAL" else None,
    )
    concept = gov.upsert_concept(user, candidate)
    return serialize_concept(concept)


@router.post(
    "/ontology/what-if",
    response_model=s.WhatIfSimulationResponse,
    summary="Execute What-If impact simulation across concepts, templates, workflows & runs",
    responses=PROBLEM_RESPONSES,
)
async def simulate_ontology_what_if(
    request: Request,
    body: s.WhatIfSimulationRequest,
    fixture: bool = Query(default=False),
) -> s.WhatIfSimulationResponse:
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    report = gov.simulate_what_if(
        concept_key=body.concept_key,
        proposed_change=body.proposed_change,
    )
    return serialize_what_if(report, trace_id=get_trace_id(request))


@router.post(
    "/ontology/promote",
    response_model=s.OntologyPromotionProposalSchemaItem,
    summary="Promote an Ontology concept proposal (L4 -> L3 or L3 -> L2 -> L1)",
    responses=PROBLEM_RESPONSES,
)
async def promote_ontology_proposal(
    request: Request,
    body: s.OntologyPromoteRequest,
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.OntologyPromotionProposalSchemaItem:
    user = resolve_request_user(request, persona_key=persona_key)
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    proposal = gov.promote_concept(user, proposal_key=body.proposal_key)
    return serialize_promotion(proposal)


@router.post(
    "/rag/search",
    response_model=s.HybridRagSearchResponse,
    summary="Execute Hybrid RAG search (`halfvec(1024)` + BM25 RRF) with Ontology query expansion",
    responses=PROBLEM_RESPONSES,
)
async def search_hybrid_rag(
    request: Request,
    body: s.HybridRagSearchRequest,
    fixture: bool = Query(default=False),
) -> s.HybridRagSearchResponse:
    gov, rag, _ = get_ontology_and_rag_services(request, fixture=fixture)
    snap = gov.resolve_snapshot(workspace_scope_id=body.workspace_id)
    expanded = OntologyHierarchyResolver.expand_rag_query(body.query_text, snap)
    combined_query = " ".join((body.query_text, *expanded.expanded_terms))
    allowed = (
        frozenset(body.allowed_datasource_aliases)
        if body.allowed_datasource_aliases is not None
        else None
    )
    hits = rag.search_hybrid_rrf(
        workspace_id=body.workspace_id,
        query_text=combined_query,
        allowed_datasource_aliases=allowed,
        top_k=body.top_k,
    )
    return s.HybridRagSearchResponse(
        expanded_terms=list(expanded.expanded_terms),
        detected_banned_terms=list(expanded.detected_banned_terms),
        hits=[
            s.HybridRagHitSchemaItem(
                chunk_key=h.chunk_key,
                parent_chunk_key=h.parent_chunk_key,
                document_key=h.document_key,
                datasource_alias=h.datasource_alias,
                source_uri=h.source_uri,
                revision_tag=h.revision_tag,
                contextual_header=h.contextual_header,
                injected_content=h.injected_content,
                rrf_score=h.rrf_score,
                vector_rank=h.vector_rank,
                bm25_rank=h.bm25_rank,
                is_stale=h.is_stale,
                stale_warning_marker=h.stale_warning_marker,
            )
            for h in hits
        ],
        trace_id=get_trace_id(request),
    )


@router.post(
    "/rag/index-db-ddl",
    response_model=s.KbDocumentSchemaItem,
    summary="Index DB DDL schema (`CREATE TABLE` only; rejects transactional SQL -> HTTP 422)",
    responses=PROBLEM_RESPONSES,
)
async def index_db_ddl_schema(
    request: Request,
    body: s.DbDdlIndexRequest,
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.KbDocumentSchemaItem:
    user = resolve_request_user(request, persona_key=persona_key)
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError(instance="/api/v1/ontology-rag/rag/index-db-ddl")
    _, rag, _ = get_ontology_and_rag_services(request, fixture=fixture)
    doc, chunks = DifferentiatedIncrementalIndexer.index_db_ddl_schema_only(
        workspace_id=body.workspace_id,
        datasource_id=body.datasource_id,
        datasource_alias=body.datasource_alias,
        db_uri=body.db_uri,
        ddl_sql=body.ddl_sql,
        schema_version=body.schema_version,
        ontology_concepts=tuple(body.ontology_concepts),
    )
    rag.upsert_indexed_bundle(document=doc, chunks=chunks)
    return serialize_doc(doc)


@router.post(
    "/tripartite/audit-doc-vs-code",
    response_model=s.DocVsCodeAuditResponse,
    summary="Qualify Doc vs Code divergence (`[DOC_OBSOLETE_SUSPECTED]` citing Done Jira ticket)",
    responses=PROBLEM_RESPONSES,
)
async def audit_doc_vs_code(
    request: Request,
    body: s.DocVsCodeAuditRequest,
    fixture: bool = Query(default=False),
) -> s.DocVsCodeAuditResponse:
    _, _, trip = get_ontology_and_rag_services(request, fixture=fixture)
    finding = trip.audit_doc_vs_code_divergence(
        confluence_uri=body.confluence_uri,
        git_repo_uri=body.git_repo_uri,
        git_symbol=body.git_symbol,
        doc_rule_summary=body.doc_rule_summary,
        code_rule_summary=body.code_rule_summary,
        newer_done_jira_key=body.newer_done_jira_key,
    )
    return s.DocVsCodeAuditResponse(
        confluence_uri=finding.confluence_uri,
        git_repo_uri=finding.git_repo_uri,
        git_symbol=finding.git_symbol,
        qualification_marker=finding.qualification_marker,
        justifying_jira_key=finding.justifying_jira_key,
        explanation=finding.explanation,
        trace_id=get_trace_id(request),
    )
