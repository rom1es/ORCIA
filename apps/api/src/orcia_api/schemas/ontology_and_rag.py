"""Pydantic v2 contracts for Epic 2: 4-Level Ontology, What-If, Hybrid RAG & Tripartite."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.ontology.models import (
    OntologyLevel,
    PromotionStatus,
    SnapshotBranchStatus,
)
from orcia_core.rag.models import (
    IndexingRegime,
    StaleAlertReason,
    TripartiteNodeType,
    TripartiteRelationType,
)


class OntologyConceptSchemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    concept_key: str
    canonical_term: str
    level: OntologyLevel
    scope_id: str
    definition_text: str
    parent_concept_id: str | None = None
    synonyms: list[str]
    banned_terms: list[str]
    profile_translations: dict[str, str]
    expected_schema: dict[str, str]
    introduced_in_snapshot_id: str | None = None
    snapshot_branch_status: SnapshotBranchStatus


class OntologyRelationSchemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    relation_key: str
    source_concept_key: str
    target_concept_key: str
    relation_type: str
    cardinality: str


class OntologyResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enterprise_scope_id: str = "scope-global"
    domain_scope_id: str = "scope-bu-digital"
    team_chain_scope_ids: list[str] = Field(
        default_factory=lambda: ["scope-subteam-checkout", "scope-team-core"]
    )
    workspace_scope_id: str = "ws-solution-paiement"
    run_scope_id: str | None = None
    human_profile: str = "TECH_LEAD"


class OntologyResolveResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concepts: list[OntologyConceptSchemaItem]
    relations: list[OntologyRelationSchemaItem]
    profile_labels: dict[str, str]
    trace_id: str | None = None


class OntologyUpsertConceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_key: str
    canonical_term: str
    level: OntologyLevel
    scope_id: str
    definition_text: str
    parent_concept_id: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    banned_terms: list[str] = Field(default_factory=list)
    profile_translations: dict[str, str] = Field(default_factory=dict)
    expected_schema: dict[str, str] = Field(default_factory=dict)
    introduced_in_snapshot_id: str | None = None


class WhatIfSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_key: str
    proposed_change: str


class WhatIfSimulationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_key: str
    canonical_term: str
    proposed_change: str
    transitively_affected_concepts: list[str]
    impacted_artifact_templates: list[str]
    impacted_workflow_uris: list[str]
    impacted_active_run_ids: list[str]
    has_immutable_axiom_conflict: bool
    trace_id: str | None = None


class OntologyPromoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_key: str


class OntologyPromotionProposalSchemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    proposal_key: str
    concept_key: str
    canonical_term: str
    source_level: OntologyLevel
    target_level: OntologyLevel
    target_scope_id: str
    proposed_by_user_id: str
    status: PromotionStatus
    impact_report: WhatIfSimulationResponse
    badge_color_token: str = "ontology-cyan"


class HybridRagSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    query_text: str
    allowed_datasource_aliases: list[str] | None = None
    top_k: int = Field(default=5, ge=1, le=25)


class HybridRagHitSchemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_key: str
    parent_chunk_key: str
    document_key: str
    datasource_alias: str
    source_uri: str
    revision_tag: str
    contextual_header: str
    injected_content: str
    rrf_score: float
    vector_rank: int
    bm25_rank: int
    is_stale: bool
    stale_warning_marker: str | None = None


class HybridRagSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expanded_terms: list[str]
    detected_banned_terms: list[str]
    hits: list[HybridRagHitSchemaItem]
    trace_id: str | None = None


class DbDdlIndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    datasource_id: str
    datasource_alias: str
    db_uri: str
    ddl_sql: str
    schema_version: str
    ontology_concepts: list[str] = Field(default_factory=list)


class KbDocumentSchemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    doc_key: str
    workspace_id: str
    datasource_id: str
    datasource_alias: str
    source_uri: str
    source_scheme: Literal["confluence", "jira", "git", "db"]
    indexing_regime: IndexingRegime
    title: str
    revision_tag: str
    content_sha256: str
    freshness_ttl_days: int
    age_days: int
    is_stale: bool


class TripartiteTraceEdgeSchemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    edge_key: str
    workspace_id: str
    source_uri: str
    source_node_type: TripartiteNodeType
    target_uri: str
    target_node_type: TripartiteNodeType
    relation_type: TripartiteRelationType
    jira_issue_key: str | None = None


class KbStaleAlertSchemaItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    alert_key: str
    workspace_id: str
    document_key: str
    source_uri: str
    alert_reason: StaleAlertReason
    diagnostic_marker: str
    justifying_jira_key: str | None = None
    impacted_run_ids: list[str]
    resolved: bool


class DocVsCodeAuditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confluence_uri: str
    git_repo_uri: str
    git_symbol: str
    doc_rule_summary: str
    code_rule_summary: str
    newer_done_jira_key: str | None = None


class DocVsCodeAuditResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confluence_uri: str
    git_repo_uri: str
    git_symbol: str
    qualification_marker: Literal["[DOC_OBSOLETE_SUSPECTED]", "[BUG_CODE_SUSPECTED]", "[ALIGNED]"]
    justifying_jira_key: str | None = None
    explanation: str
    trace_id: str | None = None


class OntologyAndRagStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concepts: list[OntologyConceptSchemaItem]
    relations: list[OntologyRelationSchemaItem]
    promotions: list[OntologyPromotionProposalSchemaItem]
    documents: list[KbDocumentSchemaItem]
    tripartite_edges: list[TripartiteTraceEdgeSchemaItem]
    stale_alerts: list[KbStaleAlertSchemaItem]
    trace_id: str | None = None
