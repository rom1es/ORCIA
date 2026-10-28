"""Differentiated Hybrid RAG (`halfvec(1024)` + BM25) & Tripartite Graph package (`AD-8`, `AD-20`).

By default in runtime (`build_empty_rag_service()`), the system is 100% empty of sample data.
Zero hardcoded demo datasets inside `orcia_core.rag.__init__.py` (`DEC-SEED-01`, `AC-E0`).
"""

from __future__ import annotations

import importlib

from orcia_core.rag.indexer_and_rrf import (
    ALLOWED_JIRA_REFERENCE_TYPES,
    EMBEDDING_DIM,
    DifferentiatedIncrementalIndexer,
    build_contextual_header,
    compute_deterministic_halfvec_1024,
    cosine_similarity,
)
from orcia_core.rag.models import (
    ChunkRole,
    CodeGraphEdgeEntity,
    CodeGraphEdgeType,
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
from orcia_core.rag.tripartite_and_freshness import (
    HybridRagService,
    TripartiteGraphAndFreshnessService,
    extract_jira_issue_keys,
)

DOMAIN_NAME: str = "rag"


def build_empty_rag_service() -> tuple[HybridRagService, TripartiteGraphAndFreshnessService]:
    """Return an empty Hybrid RAG & Tripartite Graph bundle (default runtime state: 0 rows)."""
    rag = HybridRagService()
    tripartite = TripartiteGraphAndFreshnessService(rag_service=rag)
    return rag, tripartite


def build_seeded_rag_service(
    *, workspace_id: str = "ws-claims-alpha"
) -> tuple[HybridRagService, TripartiteGraphAndFreshnessService]:
    """Delegate test dataset seeding to `orcia_core.bootstrap.rag_seeds` (`DEC-SEED-01`)."""
    rag, tripartite = build_empty_rag_service()
    bootstrap_mod = importlib.import_module("orcia_core.bootstrap.rag_seeds")
    populate_fn = bootstrap_mod.populate_rag_test_dataset
    return populate_fn(rag, tripartite, workspace_id=workspace_id)  # type: ignore[no-any-return]


__all__ = [
    "ALLOWED_JIRA_REFERENCE_TYPES",
    "ChunkRole",
    "CodeGraphEdgeEntity",
    "CodeGraphEdgeType",
    "DifferentiatedIncrementalIndexer",
    "DocVsCodeAuditFinding",
    "EMBEDDING_DIM",
    "HybridRagHit",
    "HybridRagService",
    "IndexingRegime",
    "KbChunkEntity",
    "KbDocumentEntity",
    "KbStaleAlertEntity",
    "StaleAlertReason",
    "TripartiteGraphAndFreshnessService",
    "TripartiteNodeType",
    "TripartiteRelationType",
    "TripartiteTraceEdgeEntity",
    "build_contextual_header",
    "build_empty_rag_service",
    "build_seeded_rag_service",
    "compute_deterministic_halfvec_1024",
    "cosine_similarity",
    "extract_jira_issue_keys",
]
