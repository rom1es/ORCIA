"""Differentiated Hybrid RAG (`halfvec(1024)` + BM25) & Tripartite Graph package (`AD-8`, `AD-20`).

By default in runtime (`build_empty_rag_service()`), the system is 100% empty of sample data.
Zero hardcoded demo datasets inside `orcia_core.rag.__init__.py` (`DEC-SEED-01`, `AC-E0`).
"""

from __future__ import annotations

import importlib
from typing import Any

from orcia_core.rag._internal.sql_repository import SqlHybridRagRepository
from orcia_core.rag.connector_hub_and_ingestion import (
    ConnectorConnectionTestResult,
    ConnectorHealthKind,
    ConnectorHubAndIngestionService,
    ConnectorInstanceRecord,
    DataSecurityClassification,
    DocumentIngestionReport,
    PiiArbitrationDecision,
    RagReciprocityVerificationResult,
    detect_pii_categories,
    scrub_pii_reversibly,
)
from orcia_core.rag.context_adapters import (
    CatalogAndBlackboardContextSourceAdapter,
    HybridRagVectorStoreAdapter,
)
from orcia_core.rag.indexer_and_rrf import (
    ALLOWED_JIRA_REFERENCE_TYPES,
    EMBEDDING_DIM,
    DifferentiatedIncrementalIndexer,
    build_contextual_header,
    cosine_similarity,
)
from orcia_core.rag.models import (
    ChunkRole,
    CodeGraphEdgeEntity,
    CodeGraphEdgeType,
    CoreChunkRole,
    CoreIndexingRegime,
    DocVsCodeAuditFinding,
    HybridRagHit,
    IndexingRegime,
    KbChunkEntity,
    KbDocumentEntity,
    KbStaleAlertEntity,
    StaleAlertReason,
    TripartiteNodeType,
    TripartiteRelationType,
    TripartiteTraceEdgeEntity,
)
from orcia_core.rag.source_freshness_reconciler import (
    FreshnessEvaluationResult,
    RemoteFingerprintProbePort,
    evaluate_24h_freshness_probe,
    reconcile_incoming_fingerprint,
)
from orcia_core.rag.tripartite_and_freshness import (
    HybridRagService,
    TripartiteGraphAndFreshnessService,
    extract_jira_issue_keys,
)
from orcia_core.rag.two_speed_search import (
    SEVEN_SEARCH_FAMILIES,
    FederatedSearchCandidate,
    FederatedSearchHit,
    SearchFamilyKey,
    SearchScopeMode,
    TwoSpeedFederatedSearchService,
    TwoSpeedSearchReport,
    build_speed2_redis_cache_key,
)

DOMAIN_NAME: str = "rag"


def build_empty_rag_service(
    embedding_port: Any = None,
) -> tuple[HybridRagService, TripartiteGraphAndFreshnessService]:
    """Return an empty Hybrid RAG & Tripartite Graph bundle (default runtime state: 0 rows)."""
    rag = HybridRagService(embedding_port=embedding_port)
    tripartite = TripartiteGraphAndFreshnessService(rag_service=rag)
    return rag, tripartite


def build_seeded_rag_service(
    *,
    workspace_id: str = "ws-claims-alpha",
    embedding_port: Any = None,
) -> tuple[HybridRagService, TripartiteGraphAndFreshnessService]:
    """Delegate test dataset seeding to `orcia_core.bootstrap.rag_seeds` (`DEC-SEED-01`)."""
    rag, tripartite = build_empty_rag_service(embedding_port=embedding_port)
    bootstrap_mod = importlib.import_module("orcia_core.bootstrap.rag_seeds")
    populate_fn = bootstrap_mod.populate_rag_test_dataset
    return populate_fn(  # type: ignore[no-any-return]
        rag, tripartite, workspace_id=workspace_id, embedding_port=embedding_port
    )


__all__ = [
    "ALLOWED_JIRA_REFERENCE_TYPES",
    "CatalogAndBlackboardContextSourceAdapter",
    "ChunkRole",
    "CodeGraphEdgeEntity",
    "CodeGraphEdgeType",
    "ConnectorConnectionTestResult",
    "ConnectorHealthKind",
    "ConnectorHubAndIngestionService",
    "ConnectorInstanceRecord",
    "CoreChunkRole",
    "CoreIndexingRegime",
    "DataSecurityClassification",
    "DifferentiatedIncrementalIndexer",
    "DocVsCodeAuditFinding",
    "DocumentIngestionReport",
    "EMBEDDING_DIM",
    "FederatedSearchCandidate",
    "FederatedSearchHit",
    "FreshnessEvaluationResult",
    "HybridRagHit",
    "HybridRagService",
    "HybridRagVectorStoreAdapter",
    "IndexingRegime",
    "KbChunkEntity",
    "KbDocumentEntity",
    "KbStaleAlertEntity",
    "PiiArbitrationDecision",
    "RagReciprocityVerificationResult",
    "RemoteFingerprintProbePort",
    "SEVEN_SEARCH_FAMILIES",
    "SearchFamilyKey",
    "SearchScopeMode",
    "SqlHybridRagRepository",
    "StaleAlertReason",
    "TripartiteGraphAndFreshnessService",
    "TripartiteNodeType",
    "TripartiteRelationType",
    "TripartiteTraceEdgeEntity",
    "TwoSpeedFederatedSearchService",
    "TwoSpeedSearchReport",
    "build_contextual_header",
    "build_empty_rag_service",
    "build_seeded_rag_service",
    "build_speed2_redis_cache_key",
    "cosine_similarity",
    "detect_pii_categories",
    "evaluate_24h_freshness_probe",
    "extract_jira_issue_keys",
    "reconcile_incoming_fingerprint",
    "scrub_pii_reversibly",
]
