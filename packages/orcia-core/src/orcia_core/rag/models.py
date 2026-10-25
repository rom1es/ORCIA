"""Pure domain models for Differentiated Hybrid RAG (`halfvec(1024)` + BM25) & Tripartite Graph.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IndexingRegime = Literal["DOC_PARENT_CHILD", "CODE_AST_GRAPH", "DB_DDL_ONLY"]

ChunkRole = Literal["PARENT", "CHILD", "UNIFIED_JIRA", "AST_SYMBOL", "DDL_SCHEMA"]

CodeGraphEdgeType = Literal[
    "DEFINES",
    "CALLS",
    "IMPORTS",
    "IMPLEMENTS_CONCEPT",
    "TESTED_BY",
]

TripartiteNodeType = Literal[
    "CONFLUENCE_PAGE",
    "JIRA_ISSUE",
    "GIT_SYMBOL",
    "GIT_COMMIT",
    "ONTOLOGY_CONCEPT",
]

TripartiteRelationType = Literal[
    "DOCUMENTS",
    "SPECIFIES",
    "FIXES",
    "BLOCKS",
    "IMPLEMENTS_ISSUE",
    "AFFECTS_CONCEPT",
]

StaleAlertReason = Literal[
    "TTL_EXPIRED",
    "NEWER_JIRA_CONTRADICTION",
    "CODE_DRIFT_DETECTED",
]


@dataclass(frozen=True, slots=True)
class KbDocumentEntity:
    """Indexed multi-source document header (`confluence://`, `jira://`, `git://`, `db://`)."""

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
    freshness_ttl_days: int = 90
    age_days: int = 0
    is_stale: bool = False


@dataclass(frozen=True, slots=True)
class KbChunkEntity:
    """Indexed chunk carrying contextual header, `halfvec(1024)` vector, and parent link."""

    id: str
    chunk_key: str
    document_id: str
    workspace_id: str
    datasource_alias: str
    parent_chunk_id: str | None
    chunk_role: ChunkRole
    contextual_header: str
    content_text: str
    token_count: int
    embedding: tuple[float, ...] | None = None


@dataclass(frozen=True, slots=True)
class CodeGraphEdgeEntity:
    """Directed edge in the intra/inter-repository AST Code Property Graph (Story 2.3)."""

    id: str
    edge_key: str
    workspace_id: str
    source_repo_uri: str
    source_symbol: str
    target_repo_uri: str
    target_symbol: str
    edge_type: CodeGraphEdgeType


@dataclass(frozen=True, slots=True)
class HybridRagHit:
    """Reciprocal Rank Fusion (`halfvec(1024)` + BM25) search result returning parent context."""

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


@dataclass(frozen=True, slots=True)
class TripartiteTraceEdgeEntity:
    """Cross-source traceability edge (`Confluence <-> Jira <-> Git <-> Ontology`, Story 2.4)."""

    id: str
    edge_key: str
    workspace_id: str
    source_uri: str
    source_node_type: TripartiteNodeType
    target_uri: str
    target_node_type: TripartiteNodeType
    relation_type: TripartiteRelationType
    jira_issue_key: str | None = None


@dataclass(frozen=True, slots=True)
class KbStaleAlertEntity:
    """`[STALE_WARNING]` alert raised by the `data-freshness` brick (Story 2.4)."""

    id: str
    alert_key: str
    workspace_id: str
    document_key: str
    source_uri: str
    alert_reason: StaleAlertReason
    diagnostic_marker: str
    justifying_jira_key: str | None
    impacted_run_ids: tuple[str, ...]
    resolved: bool = False


@dataclass(frozen=True, slots=True)
class DocVsCodeAuditFinding:
    """Tripartite Doc vs Code audit comparison finding (`[DOC_OBSOLETE_SUSPECTED]`, UJ-10)."""

    confluence_uri: str
    git_repo_uri: str
    git_symbol: str
    qualification_marker: Literal["[DOC_OBSOLETE_SUSPECTED]", "[BUG_CODE_SUSPECTED]", "[ALIGNED]"]
    justifying_jira_key: str | None
    explanation: str
