"""Shared service resolver and Pydantic serializers for Epic 2 (`ontology_and_rag` router)."""

from __future__ import annotations

from fastapi import Request

from orcia_core.observability.logging import get_current_trace_id
from orcia_core.ontology import (
    OntologyConceptEntity,
    OntologyGovernanceService,
    OntologyPromotionProposal,
    OntologyRelationEntity,
    WhatIfImpactReport,
    build_empty_ontology_service,
    build_seeded_ontology_service,
)
from orcia_core.rag import (
    HybridRagService,
    KbDocumentEntity,
    KbStaleAlertEntity,
    TripartiteGraphAndFreshnessService,
    TripartiteTraceEdgeEntity,
    build_empty_rag_service,
    build_seeded_rag_service,
)
from orcia_core.schemas import ontology_and_rag as s


def get_trace_id(request: Request) -> str:
    """Return active W3C OpenTelemetry trace_id from request state or contextvar."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def get_epic2_services(
    request: Request, *, fixture: bool = False
) -> tuple[
    OntologyGovernanceService,
    HybridRagService,
    TripartiteGraphAndFreshnessService,
]:
    """Return Either the empty runtime Epic 2 bundle or the deterministic test fixture bundle."""
    if fixture:
        seeded: (
            tuple[
                OntologyGovernanceService,
                HybridRagService,
                TripartiteGraphAndFreshnessService,
            ]
            | None
        ) = getattr(request.app.state, "epic2_seeded_bundle", None)
        if seeded is None:
            gov = build_seeded_ontology_service()
            rag, trip = build_seeded_rag_service()
            seeded = (gov, rag, trip)
            request.app.state.epic2_seeded_bundle = seeded
        return seeded

    runtime: (
        tuple[
            OntologyGovernanceService,
            HybridRagService,
            TripartiteGraphAndFreshnessService,
        ]
        | None
    ) = getattr(request.app.state, "epic2_runtime_bundle", None)
    if runtime is None:
        gov = build_empty_ontology_service()
        rag, trip = build_empty_rag_service()
        runtime = (gov, rag, trip)
        request.app.state.epic2_runtime_bundle = runtime
    return runtime


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
