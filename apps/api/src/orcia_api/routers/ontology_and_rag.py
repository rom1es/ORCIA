"""Epic 2 Router: 4-Level Ontology, What-If Simulator, Hybrid RAG & Tripartite Graph."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_ontology_and_rag_services,
    require_rag_available,
)
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers._ontology_promotions_helpers import (
    load_ontology_topology,
    resolve_ontology_caller,
)
from orcia_api.routers._ontology_rag_guards import (
    enforce_ontology_rag_workspace_access,
    execute_hybrid_rag_search,
    filter_ontology_rag_state_for_caller,
    hydrate_tripartite_rag_state_from_pg,
    persist_tripartite_audit_traceability,
)
from orcia_api.routers._ontology_resolve_guards import (
    resolve_ontology_for_caller,
    simulate_what_if_for_caller,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.routers.ontology_rag_helpers import (
    build_sql_rag_repo_from_request,
    get_trace_id,
    serialize_concept,
    serialize_doc,
    serialize_promotion,
    serialize_relation,
    serialize_stale_alert,
    serialize_trace_edge,
)
from orcia_api.schemas import ontology_and_rag as s
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag import DifferentiatedIncrementalIndexer, SqlHybridRagRepository

router = APIRouter(prefix="/api/v1/ontology-rag", tags=["ontology-rag"])


def _get_optional_sql_rag_repo(request: Request) -> SqlHybridRagRepository | None:
    """Return `SqlHybridRagRepository` when PG18 `session_maker` or `engine` is active."""
    return build_sql_rag_repo_from_request(request)


@router.get(
    "/state",
    response_model=s.OntologyAndRagStateResponse,
    summary="Inspect 4-Level Ontology, Promotions, Hybrid RAG Documents & Tripartite Graph",
    responses=PROBLEM_RESPONSES,
)
async def get_ontology_and_rag_state(
    request: Request,
    fixture: bool = Query(default=False, description="Use deterministic test fixture data"),
    workspace_id: str | None = Query(default=None),
    seed_uri: str | None = Query(default=None),
    persona_key: str | None = Query(default=None),
) -> s.OntologyAndRagStateResponse:
    user = resolve_ontology_caller(request, persona_key)
    gov, rag, trip = get_ontology_and_rag_services(request, fixture=fixture)
    edges = list(trip.list_edges())
    documents = list(rag.list_documents())
    alerts = list(trip.list_alerts())
    if not fixture:
        await hydrate_tripartite_rag_state_from_pg(
            request,
            workspace_id=workspace_id,
            seed_uri=seed_uri,
            edges=edges,
            documents=documents,
            alerts=alerts,
        )

    concepts = list(gov.concepts)
    proposals = list(gov.proposals)
    if not fixture:
        concepts, proposals, edges, documents, alerts = await filter_ontology_rag_state_for_caller(
            request, user=user, gov=gov, edges=edges, documents=documents, alerts=alerts
        )
    return s.OntologyAndRagStateResponse(
        concepts=[serialize_concept(c) for c in concepts],
        relations=[serialize_relation(r) for r in gov.relations],
        promotions=[serialize_promotion(p) for p in proposals],
        documents=[serialize_doc(d) for d in documents],
        tripartite_edges=[serialize_trace_edge(e) for e in edges],
        stale_alerts=[serialize_stale_alert(a) for a in alerts],
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
    return await resolve_ontology_for_caller(request, body=body, gov=gov, fixture=fixture)


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
    return await simulate_what_if_for_caller(request, body=body, gov=gov, fixture=fixture)


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
    user = resolve_ontology_caller(request, persona_key)
    auth_svc = get_auth_service(request)
    if not fixture:
        await sync_evaluator_topology_from_pg(request, auth_svc)
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    _, org_units, workspaces = await load_ontology_topology(request, fixture=fixture)
    memberships = auth_svc.evaluator.list_memberships()
    proposal = gov.promote_concept(
        user,
        proposal_key=body.proposal_key,
        org_units=org_units,
        workspaces=workspaces,
        memberships=memberships,
        allow_fixture_fallback=fixture,
    )
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
    embedding_port: Annotated[EmbeddingPort, Depends(require_rag_available)],
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.HybridRagSearchResponse:
    await enforce_ontology_rag_workspace_access(
        request,
        body.workspace_id,
        fixture=fixture,
        persona_key=persona_key,
        require_write=False,
    )
    gov, rag, _ = get_ontology_and_rag_services(
        request, fixture=fixture, embedding_port=embedding_port
    )
    return await execute_hybrid_rag_search(
        request, gov=gov, rag=rag, body=body, embedding_port=embedding_port, fixture=fixture
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
    embedding_port: Annotated[EmbeddingPort, Depends(require_rag_available)],
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.KbDocumentSchemaItem:
    await enforce_ontology_rag_workspace_access(
        request,
        body.workspace_id,
        fixture=fixture,
        persona_key=persona_key,
        require_write=True,
    )
    _, rag, _ = get_ontology_and_rag_services(request, fixture=fixture)
    doc, chunks = await DifferentiatedIncrementalIndexer.index_db_ddl_schema_only(
        workspace_id=body.workspace_id,
        datasource_id=body.datasource_id,
        datasource_alias=body.datasource_alias,
        db_uri=body.db_uri,
        ddl_sql=body.ddl_sql,
        schema_version=body.schema_version,
        embedding_port=embedding_port,
        ontology_concepts=tuple(body.ontology_concepts),
    )
    rag.upsert_indexed_bundle(document=doc, chunks=chunks)
    if not fixture:
        sql_rag_repo = build_sql_rag_repo_from_request(request)
        if sql_rag_repo is not None:
            persisted = await sql_rag_repo.upsert_document_bundle_pg(document=doc, chunks=chunks)
            if persisted is not None:
                doc = persisted
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
    persona_key: str | None = Query(default=None),
) -> s.DocVsCodeAuditResponse:
    _, target_ws = await enforce_ontology_rag_workspace_access(
        request,
        body.workspace_id,
        fixture=fixture,
        persona_key=persona_key,
        require_write=not fixture,
    )
    _, _, trip = get_ontology_and_rag_services(request, fixture=fixture)
    finding = trip.audit_doc_vs_code_divergence(
        confluence_uri=body.confluence_uri,
        git_repo_uri=body.git_repo_uri,
        git_symbol=body.git_symbol,
        doc_rule_summary=body.doc_rule_summary,
        code_rule_summary=body.code_rule_summary,
        newer_done_jira_key=body.newer_done_jira_key,
    )
    await persist_tripartite_audit_traceability(
        request, trip=trip, target_ws=target_ws, body=body, fixture=fixture
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
