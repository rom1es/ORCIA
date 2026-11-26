"""Shared service resolver and Pydantic serializers for Epic 2 (`ontology_and_rag` router)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any
from urllib.parse import urlparse

from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker

from orcia_api.dependencies import get_auth_service
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.schemas import ontology_and_rag as s
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyPromotionProposal,
    OntologyRelationEntity,
    WhatIfImpactReport,
    can_read_ontology_item,
)
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_core.rag import (
    KbChunkEntity,
    KbDocumentEntity,
    KbStaleAlertEntity,
    SqlHybridRagRepository,
    TripartiteTraceEdgeEntity,
)


def get_trace_id(request: Request) -> str:
    """Return active W3C OpenTelemetry trace_id from request state or contextvar."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def build_sql_rag_repo_from_request(request: Request) -> SqlHybridRagRepository | None:
    """Return `SqlHybridRagRepository` when PG18 `session_maker` or `engine` is active."""
    session_maker: Any = getattr(request.app.state, "session_maker", None)
    if session_maker is not None:
        return SqlHybridRagRepository(session_maker)
    engine = get_configured_db_engine(request)
    if engine is not None:
        return SqlHybridRagRepository(async_sessionmaker(engine, expire_on_commit=False))
    return None


def _infer_doc_scheme(uri: str) -> str:
    parsed = (urlparse(uri).scheme or "").lower()
    if parsed in {"confluence", "jira", "git", "db"}:
        return parsed
    lowered = uri.lower()
    if "git" in lowered:
        return "git"
    if "jira" in lowered:
        return "jira"
    if "db" in lowered or "postgres" in lowered:
        return "db"
    return "confluence"


async def persist_ingested_document_pg(
    request: Request,
    *,
    document_id: str,
    workspace_id: str,
    datasource_id: str | None,
    datasource_alias: str,
    uri: str,
    title: str,
    content_text: str,
    indexing_regime: str = "DOC_PARENT_CHILD",
    chunk_role: str = "PARENT",
    is_stale: bool = False,
) -> None:
    """Persist an ingested or synced document in PG18 `kb_documents` + `kb_chunks` (`AD-24.7`)."""
    sql_rag_repo = build_sql_rag_repo_from_request(request)
    if sql_rag_repo is None:
        return
    clean_text = content_text.strip() or title.strip() or uri.strip()
    sha256_hex = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
    scheme = _infer_doc_scheme(uri)
    doc_key = f"doc-{workspace_id[:8]}-{sha256_hex[:16]}"
    doc = KbDocumentEntity(
        id=document_id,
        doc_key=doc_key,
        workspace_id=workspace_id,
        datasource_id=datasource_id or new_uuid7_str(),
        datasource_alias=datasource_alias[:120] or scheme,
        source_uri=uri,
        source_scheme=scheme,
        indexing_regime=indexing_regime,
        title=title[:255] or datasource_alias,
        revision_tag="v1",
        content_sha256=sha256_hex,
        freshness_ttl_days=90,
        is_stale=is_stale,
    )
    chunk = KbChunkEntity(
        id=new_uuid7_str(),
        chunk_key=f"{doc_key}-chunk-01",
        document_id=document_id,
        workspace_id=workspace_id,
        datasource_alias=doc.datasource_alias,
        parent_chunk_id=None,
        chunk_role=chunk_role,
        contextual_header=f"[{doc.datasource_alias} | {doc.title}]",
        content_text=clean_text,
        token_count=max(1, len(clean_text.split())),
        embedding=None,
    )
    await sql_rag_repo.upsert_document_bundle_pg(document=doc, chunks=(chunk,))


def serialize_concept(c: OntologyConceptEntity) -> s.OntologyConceptSchemaItem:
    return s.OntologyConceptSchemaItem(
        id=c.id,
        concept_key=c.concept_key,
        canonical_term=c.canonical_term,
        level=c.level,
        scope_id=c.scope_id,
        definition_text=c.definition_text,
        parent_concept_id=c.parent_concept_id,
        synonyms=list(c.synonyms),
        banned_terms=list(c.banned_terms),
        profile_translations=dict(c.profile_translations),
        expected_schema=dict(c.expected_schema),
        introduced_in_snapshot_id=c.introduced_in_snapshot_id,
        snapshot_branch_status=c.snapshot_branch_status,
        pack_bundle_id=c.pack_bundle_id,
        pack_slug=c.pack_slug,
    )


def serialize_relation(r: OntologyRelationEntity) -> s.OntologyRelationSchemaItem:
    return s.OntologyRelationSchemaItem(
        id=r.id,
        relation_key=r.relation_key,
        source_concept_key=r.source_concept_key,
        target_concept_key=r.target_concept_key,
        relation_type=r.relation_type,
        cardinality=r.cardinality,
    )


def serialize_what_if(
    rep: WhatIfImpactReport, *, trace_id: str | None = None
) -> s.WhatIfSimulationResponse:
    return s.WhatIfSimulationResponse(
        concept_key=rep.concept_key,
        canonical_term=rep.canonical_term,
        proposed_change=rep.proposed_change,
        transitively_affected_concepts=list(rep.transitively_affected_concepts),
        impacted_artifact_templates=list(rep.impacted_artifact_templates),
        impacted_workflow_uris=list(rep.impacted_workflow_uris),
        impacted_active_run_ids=list(rep.impacted_active_run_ids),
        has_immutable_axiom_conflict=rep.has_immutable_axiom_conflict,
        trace_id=trace_id,
    )


def serialize_promotion(p: OntologyPromotionProposal) -> s.OntologyPromotionProposalSchemaItem:
    return s.OntologyPromotionProposalSchemaItem(
        id=p.id,
        proposal_key=p.proposal_key,
        concept_key=p.concept_key,
        canonical_term=p.canonical_term,
        source_level=p.source_level,
        target_level=p.target_level,
        target_scope_id=p.target_scope_id,
        proposed_by_user_id=p.proposed_by_user_id,
        status=p.status,
        impact_report=serialize_what_if(p.impact_report),
        badge_color_token=p.badge_color_token,
    )


def serialize_doc(d: KbDocumentEntity) -> s.KbDocumentSchemaItem:
    return s.KbDocumentSchemaItem(
        id=d.id,
        doc_key=d.doc_key,
        workspace_id=d.workspace_id,
        datasource_id=d.datasource_id,
        datasource_alias=d.datasource_alias,
        source_uri=d.source_uri,
        source_scheme=d.source_scheme,
        indexing_regime=d.indexing_regime,
        title=d.title,
        revision_tag=d.revision_tag,
        content_sha256=d.content_sha256,
        freshness_ttl_days=d.freshness_ttl_days,
        age_days=d.age_days,
        is_stale=d.is_stale,
    )


def serialize_trace_edge(e: TripartiteTraceEdgeEntity) -> s.TripartiteTraceEdgeSchemaItem:
    return s.TripartiteTraceEdgeSchemaItem(
        id=e.id,
        edge_key=e.edge_key,
        workspace_id=e.workspace_id,
        source_uri=e.source_uri,
        source_node_type=e.source_node_type,
        target_uri=e.target_uri,
        target_node_type=e.target_node_type,
        relation_type=e.relation_type,
        jira_issue_key=e.jira_issue_key,
    )


def serialize_stale_alert(a: KbStaleAlertEntity) -> s.KbStaleAlertSchemaItem:
    return s.KbStaleAlertSchemaItem(
        id=a.id,
        alert_key=a.alert_key,
        workspace_id=a.workspace_id,
        document_key=a.document_key,
        source_uri=a.source_uri,
        alert_reason=a.alert_reason,
        diagnostic_marker=a.diagnostic_marker,
        justifying_jira_key=a.justifying_jira_key,
        impacted_run_ids=list(a.impacted_run_ids),
        resolved=a.resolved,
    )


def is_concept_readable(
    request: Request,
    *,
    user: UserIdentity,
    concept: OntologyConceptEntity,
    concepts_by_id: dict[str, OntologyConceptEntity],
    org_units: Sequence[OrgUnitNode],
    workspaces: Sequence[WorkspaceEntity],
    memberships: Sequence[WorkspaceMembershipEntity],
    allowed_pack_slugs: frozenset[str] | None = None,
) -> bool:
    """Return True if `user` can read `concept` and its parent lineage without leaks."""
    if concept.pack_bundle_id is not None:
        pslug = (concept.pack_slug or concept.scope_id or "").strip().lower()
        if (concept.bundle_kind or "").upper() == "SYSTEM":
            return True
        return allowed_pack_slugs is not None and pslug in allowed_pack_slugs
    if not can_read_ontology_item(
        user, concept.level, concept.scope_id, org_units, workspaces, memberships
    ):
        return False
    auth_svc = get_auth_service(request)
    if concept.level == "4_RUN_EPHEMERAL":
        cc_svc = getattr(request.app.state, "control_center_service", None)
        if cc_svc is not None:
            run = getattr(cc_svc, "_runs", {}).get(concept.scope_id)
            if (
                run is not None
                and auth_svc.evaluator.resolve_workspace_access(user, run.workspace_id) is None
            ):
                return False
    cursor = concept.parent_concept_id
    visited: set[str] = set()
    while cursor and cursor in concepts_by_id and cursor not in visited and len(visited) < 32:
        visited.add(cursor)
        parent = concepts_by_id[cursor]
        if not can_read_ontology_item(
            user, parent.level, parent.scope_id, org_units, workspaces, memberships
        ):
            return False
        cursor = parent.parent_concept_id
    return True
