"""Epic 2 Router: 4-Level Ontology, What-If Simulator, Hybrid RAG & Tripartite Graph."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_ontology_and_rag_services,
    require_rag_available,
)
from orcia_api.routers._ontology_promotions_helpers import (
    load_ontology_topology,
    resolve_ontology_caller,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.routers.ontology_rag_helpers import (
    build_sql_rag_repo_from_request,
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
    OntologyHierarchyResolver,
    ProfileSemanticTranslator,
    can_read_ontology_item,
    list_concepts_pg,
    list_proposals_pg,
)
from orcia_core.ontology.errors import ObserverModeReadOnlyError
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag import (
    DifferentiatedIncrementalIndexer,
    SqlHybridRagRepository,
)

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
) -> s.OntologyAndRagStateResponse:
    user = resolve_ontology_caller(request, None)
    gov, rag, trip = get_ontology_and_rag_services(request, fixture=fixture)
    edges = list(trip.list_edges())
    documents = list(rag.list_documents())
    alerts = list(trip.list_alerts())
    sql_rag_repo = _get_optional_sql_rag_repo(request)
    if not fixture and sql_rag_repo is not None:
        if workspace_id and seed_uri:
            sql_edges = await sql_rag_repo.traverse_tripartite_neighborhood(
                workspace_id=workspace_id,
                seed_uri=seed_uri,
                max_depth=2,
            )
        else:
            sql_edges = await sql_rag_repo.list_tripartite_edges_pg(workspace_id=workspace_id)
        existing_edge_keys = {e.edge_key for e in edges}
        for sql_edge in sql_edges:
            if sql_edge.edge_key not in existing_edge_keys:
                edges.append(sql_edge)
                existing_edge_keys.add(sql_edge.edge_key)

        sql_docs = await sql_rag_repo.list_documents_pg(workspace_id=workspace_id)
        existing_doc_keys = {d.doc_key for d in documents}
        for sql_doc in sql_docs:
            if sql_doc.doc_key not in existing_doc_keys:
                documents.append(sql_doc)
                existing_doc_keys.add(sql_doc.doc_key)

        sql_alerts = await sql_rag_repo.list_stale_alerts_pg(workspace_id=workspace_id)
        existing_alert_keys = {a.alert_key for a in alerts}
        for sql_alert in sql_alerts:
            if sql_alert.alert_key not in existing_alert_keys:
                alerts.append(sql_alert)
                existing_alert_keys.add(sql_alert.alert_key)

    concepts = list(gov.concepts)
    proposals = list(gov.proposals)
    if not fixture:
        engine, org_units, workspaces = await load_ontology_topology(request, fixture=False)
        auth_svc = get_auth_service(request)
        memberships = auth_svc.evaluator.list_memberships()
        if not concepts and engine is not None:
            concepts = await list_concepts_pg(engine)
            proposals = await list_proposals_pg(engine)
        concepts = [
            c
            for c in concepts
            if can_read_ontology_item(user, c.level, c.scope_id, org_units, workspaces, memberships)
        ]
        if user.platform_role != "PLATFORM_ADMIN":
            known_ws_ids = {ws.id for ws in workspaces}
            allowed_ws = {
                ws_id
                for ws_id in known_ws_ids
                if auth_svc.evaluator.resolve_workspace_access(user, ws_id) is not None
            }
            edges = [
                e
                for e in edges
                if e.workspace_id not in known_ws_ids or e.workspace_id in allowed_ws
            ]
            documents = [
                d
                for d in documents
                if d.workspace_id not in known_ws_ids or d.workspace_id in allowed_ws
            ]
            alerts = [
                a
                for a in alerts
                if a.workspace_id not in known_ws_ids or a.workspace_id in allowed_ws
            ]
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
    user = resolve_ontology_caller(request, persona_key)
    gov, _, _ = get_ontology_and_rag_services(request, fixture=fixture)
    _, org_units, workspaces = await load_ontology_topology(request, fixture=fixture)
    memberships = get_auth_service(request).evaluator.list_memberships()
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
) -> s.HybridRagSearchResponse:
    gov, rag, _ = get_ontology_and_rag_services(
        request, fixture=fixture, embedding_port=embedding_port
    )
    snap = gov.resolve_snapshot(workspace_scope_id=body.workspace_id)
    expanded = OntologyHierarchyResolver.expand_rag_query(body.query_text, snap)
    combined_query = " ".join((body.query_text, *expanded.expanded_terms))
    allowed = (
        frozenset(body.allowed_datasource_aliases)
        if body.allowed_datasource_aliases is not None
        else None
    )
    sql_rag_repo = _get_optional_sql_rag_repo(request)
    hits: tuple[Any, ...] = ()
    query_embedding = tuple(await embedding_port.embed_query(combined_query))
    if not fixture and sql_rag_repo is not None:
        sql_hits = await sql_rag_repo.search_hybrid_rrf(
            workspace_id=body.workspace_id,
            query_text=combined_query,
            query_embedding=query_embedding,
            limit=body.top_k,
        )
        if allowed is not None:
            hits = tuple(h for h in sql_hits if h.datasource_alias in allowed)
        else:
            hits = sql_hits
    if not hits:
        hits = rag.search_hybrid_rrf(
            workspace_id=body.workspace_id,
            query_text=combined_query,
            query_embedding=query_embedding,
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
    embedding_port: Annotated[EmbeddingPort, Depends(require_rag_available)],
    fixture: bool = Query(default=False),
    persona_key: str | None = Query(default=None),
) -> s.KbDocumentSchemaItem:
    user = resolve_request_user(request, persona_key=persona_key)
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError(instance="/api/v1/ontology-rag/rag/index-db-ddl")
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
    target_ws = (body.workspace_id or "").strip() or None
    if not fixture:
        if target_ws is None:
            _, _, workspaces = await load_ontology_topology(request, fixture=False)
            if workspaces:
                target_ws = workspaces[0].id
        if target_ws is not None:
            jira_hint = body.newer_done_jira_key or ""
            edges = trip.register_cross_source_traceability(
                workspace_id=target_ws,
                confluence_uri=body.confluence_uri,
                confluence_text=f"{body.doc_rule_summary} {jira_hint}".strip(),
                git_repo_uri=body.git_repo_uri,
                git_symbol=body.git_symbol,
                commit_message=f"{body.code_rule_summary} {jira_hint}".strip(),
            )
            sql_rag_repo = build_sql_rag_repo_from_request(request)
            if sql_rag_repo is not None and edges:
                await sql_rag_repo.upsert_tripartite_edges_pg(edges=edges)
    return s.DocVsCodeAuditResponse(
        confluence_uri=finding.confluence_uri,
        git_repo_uri=finding.git_repo_uri,
        git_symbol=finding.git_symbol,
        qualification_marker=finding.qualification_marker,
        justifying_jira_key=finding.justifying_jira_key,
        explanation=finding.explanation,
        trace_id=get_trace_id(request),
    )
