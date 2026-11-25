"""RBAC, confidential workspace & fail-closed guards for `ontology_and_rag` router."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers._ontology_promotions_helpers import (
    is_restricted_proposal_denied,
    load_ontology_topology,
    resolve_ontology_caller,
)
from orcia_api.routers.ontology_rag_helpers import build_sql_rag_repo_from_request, get_trace_id
from orcia_api.schemas import ontology_and_rag as s
from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyGovernanceService,
    OntologyHierarchyResolver,
    OntologyPromotionProposal,
    can_read_ontology_item,
    can_review_promotion_target,
    list_concepts_pg,
    list_proposals_pg,
)
from orcia_core.ontology.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.embedding import EmbeddingPort


async def filter_ontology_rag_state_for_caller(
    request: Request,
    *,
    user: UserIdentity,
    gov: OntologyGovernanceService,
    edges: list[Any],
    documents: list[Any],
    alerts: list[Any],
) -> tuple[
    list[OntologyConceptEntity],
    list[OntologyPromotionProposal],
    list[Any],
    list[Any],
    list[Any],
]:
    """Enforce L1-L4 ontology, promotion, and strict workspace isolation for `GET /state`."""
    concepts = list(gov.concepts)
    proposals = list(gov.proposals)
    engine, org_units, workspaces = await load_ontology_topology(request, fixture=False)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    memberships = auth_svc.evaluator.list_memberships()
    if not concepts and engine is not None:
        concepts = await list_concepts_pg(engine)
        proposals = await list_proposals_pg(engine)

    filtered_concepts = [
        c
        for c in concepts
        if can_read_ontology_item(user, c.level, c.scope_id, org_units, workspaces, memberships)
    ]
    filtered_proposals = [
        p
        for p in proposals
        if not is_restricted_proposal_denied(user, p, workspaces, memberships)
        and (
            can_review_promotion_target(
                user,
                p.target_level,
                p.target_scope_id,
                org_units,
                workspaces,
                memberships,
                source_scope_id=p.source_scope_id,
            )
            or p.proposed_by_user_id in (user.id, user.email)
            or can_read_ontology_item(
                user,
                p.source_level,
                p.source_scope_id or p.target_scope_id,
                org_units,
                workspaces,
                memberships,
            )
        )
    ]
    allowed_ws = {
        ws.id
        for ws in workspaces
        if auth_svc.evaluator.resolve_workspace_access(user, ws.id) is not None
    }
    filtered_edges = [e for e in edges if e.workspace_id in allowed_ws]
    filtered_docs = [d for d in documents if d.workspace_id in allowed_ws]
    filtered_alerts = [a for a in alerts if a.workspace_id in allowed_ws]
    return filtered_concepts, filtered_proposals, filtered_edges, filtered_docs, filtered_alerts


async def enforce_ontology_rag_workspace_access(
    request: Request,
    workspace_id: str | None,
    *,
    fixture: bool,
    persona_key: str | None,
    require_write: bool,
) -> tuple[UserIdentity, str | None]:
    """Validate caller identity, observer guard, and workspace membership fail-closed."""
    user = resolve_ontology_caller(request, persona_key)
    path = str(request.url.path)
    if require_write:
        enforce_observer_headers_guard(request, user)
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise ObserverModeReadOnlyError(instance=path)

    auth_svc = get_auth_service(request)
    if not fixture:
        await sync_evaluator_topology_from_pg(request, auth_svc)

    clean_ws = (workspace_id or "").strip()
    if not clean_ws or clean_ws in ("scope-global", "GLOBAL"):
        if require_write and not fixture:
            all_access = [
                auth_svc.evaluator.resolve_workspace_access(user, ws.id)
                for ws in auth_svc.evaluator.workspaces
            ]
            non_null_access = [acc for acc in all_access if acc is not None]
            writable = [acc for acc in non_null_access if acc.access_mode != "READ_ONLY_OBSERVER"]
            if not writable:
                if non_null_access or user.platform_role in (
                    "OBSERVER",
                    "READ_ONLY_OBSERVER",
                    "BU_DIRECTOR",
                ):
                    raise ObserverModeReadOnlyError(instance=path)
                raise ScopeAccessDeniedError(instance=path)
            return user, writable[0].workspace.id
        return user, None

    ws_ent = auth_svc.evaluator.get_workspace(clean_ws)
    if ws_ent is None:
        if not fixture:
            raise ScopeAccessDeniedError(instance=path)
        return user, clean_ws

    access = auth_svc.evaluator.resolve_workspace_access(user, ws_ent.id)
    if access is None:
        raise ScopeAccessDeniedError(instance=path)
    if require_write and access.access_mode == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(instance=path)
    return user, ws_ent.id


async def hydrate_tripartite_rag_state_from_pg(
    request: Request,
    *,
    workspace_id: str | None,
    seed_uri: str | None,
    edges: list[Any],
    documents: list[Any],
    alerts: list[Any],
) -> None:
    """Append PG18 tripartite edges, documents, and stale alerts without duplicates."""
    sql_rag_repo = build_sql_rag_repo_from_request(request)
    if sql_rag_repo is None:
        return
    if workspace_id and seed_uri:
        sql_edges = await sql_rag_repo.traverse_tripartite_neighborhood(
            workspace_id=workspace_id,
            seed_uri=seed_uri,
            max_depth=2,
        )
    else:
        sql_edges = await sql_rag_repo.list_tripartite_edges_pg(workspace_id=workspace_id)
    seen_edges = {e.edge_key for e in edges}
    for e in sql_edges:
        if e.edge_key not in seen_edges:
            edges.append(e)
            seen_edges.add(e.edge_key)

    seen_docs = {d.doc_key for d in documents}
    for d in await sql_rag_repo.list_documents_pg(workspace_id=workspace_id):
        if d.doc_key not in seen_docs:
            documents.append(d)
            seen_docs.add(d.doc_key)

    seen_alerts = {a.alert_key for a in alerts}
    for a in await sql_rag_repo.list_stale_alerts_pg(workspace_id=workspace_id):
        if a.alert_key not in seen_alerts:
            alerts.append(a)
            seen_alerts.add(a.alert_key)


def serialize_rag_search_response(
    request: Request,
    *,
    expanded_terms: tuple[str, ...],
    detected_banned_terms: tuple[str, ...],
    hits: tuple[Any, ...],
) -> s.HybridRagSearchResponse:
    """Serialize Hybrid RAG search results with trace ID."""
    return s.HybridRagSearchResponse(
        expanded_terms=list(expanded_terms),
        detected_banned_terms=list(detected_banned_terms),
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


async def persist_tripartite_audit_traceability(
    request: Request,
    *,
    trip: Any,
    target_ws: str | None,
    body: s.DocVsCodeAuditRequest,
    fixture: bool,
) -> None:
    """Persist cross-source tripartite edges for non-fixture Doc-vs-Code audit."""
    if fixture or target_ws is None:
        return
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


async def execute_hybrid_rag_search(
    request: Request,
    *,
    gov: OntologyGovernanceService,
    rag: Any,
    body: s.HybridRagSearchRequest,
    embedding_port: EmbeddingPort,
    fixture: bool,
) -> s.HybridRagSearchResponse:
    """Expand query with Ontology and execute Hybrid RAG across PG18 & in-memory fallback."""
    snap = gov.resolve_snapshot(workspace_scope_id=body.workspace_id)
    expanded = OntologyHierarchyResolver.expand_rag_query(body.query_text, snap)
    combined_query = " ".join((body.query_text, *expanded.expanded_terms))
    allowed = (
        frozenset(body.allowed_datasource_aliases)
        if body.allowed_datasource_aliases is not None
        else None
    )
    sql_rag_repo = build_sql_rag_repo_from_request(request)
    hits: tuple[Any, ...] = ()
    query_embedding = tuple(await embedding_port.embed_query(combined_query))
    if not fixture and sql_rag_repo is not None:
        sql_hits = await sql_rag_repo.search_hybrid_rrf(
            workspace_id=body.workspace_id,
            query_text=combined_query,
            query_embedding=query_embedding,
            limit=body.top_k,
        )
        hits = tuple(h for h in sql_hits if h.datasource_alias in allowed) if allowed else sql_hits
    if not hits:
        hits = rag.search_hybrid_rrf(
            workspace_id=body.workspace_id,
            query_text=combined_query,
            query_embedding=query_embedding,
            allowed_datasource_aliases=allowed,
            top_k=body.top_k,
        )
    return serialize_rag_search_response(
        request,
        expanded_terms=expanded.expanded_terms,
        detected_banned_terms=expanded.detected_banned_terms,
        hits=hits,
    )
