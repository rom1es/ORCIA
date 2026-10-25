"""Idempotent Dramatiq actor `docling_indexer_actor` for Differentiated Multi-Source Indexing.

Story 2.3 AC:
- Enforces incremental SHA-256 deduplication across retries (`already_indexed: True` on retry).
- Supports all 3 indexing regimes (`DOC_PARENT_CHILD`, `CODE_AST_GRAPH`, `DB_DDL_ONLY`).
"""

from __future__ import annotations

from dataclasses import dataclass

import dramatiq

from orcia_core.observability.logging import bind_trace_context, get_logger
from orcia_core.rag import (
    CodeGraphEdgeEntity,
    DifferentiatedIncrementalIndexer,
    HybridRagService,
    KbChunkEntity,
    KbDocumentEntity,
    build_empty_rag_service,
)

logger = get_logger("orcia.worker.docling_indexer")


@dataclass(frozen=True, slots=True)
class DoclingIndexExecutionResult:
    """Result of an idempotent `docling_indexer_actor` invocation."""

    doc_key: str
    trace_id: str
    already_indexed: bool
    chunks_count: int


_default_worker_rag, _ = build_empty_rag_service()


def execute_docling_index_job(
    *,
    workspace_id: str,
    datasource_id: str,
    datasource_alias: str,
    source_uri: str,
    title: str,
    hierarchy_path: str,
    markdown_sections: tuple[str, ...],
    revision_tag: str,
    trace_id: str,
    ontology_concepts: tuple[str, ...] = (),
    labels: tuple[str, ...] = ("orcia-kb",),
    page_status: str = "current",
    indexing_regime: str = "DOC_PARENT_CHILD",
    jira_issue_key: str | None = None,
    jira_issue_type: str = "Story",
    rag_service: HybridRagService | None = None,
) -> DoclingIndexExecutionResult:
    """Execute idempotent incremental indexing of a multi-source document across all 3 regimes."""
    ctx = bind_trace_context(trace_id)
    target_rag = rag_service if rag_service is not None else _default_worker_rag
    code_edges: tuple[CodeGraphEdgeEntity, ...] = ()
    doc: KbDocumentEntity | None
    chunks: tuple[KbChunkEntity, ...]

    full_body = "\n\n".join(markdown_sections)
    if indexing_regime == "CODE_AST_GRAPH":
        doc, chunks, code_edges = DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph(
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            repo_uri=source_uri,
            file_path=title,
            python_source=full_body,
            commit_sha=revision_tag,
        )
    elif indexing_regime == "DB_DDL_ONLY":
        doc, chunks = DifferentiatedIncrementalIndexer.index_db_ddl_schema_only(
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            db_uri=source_uri,
            ddl_sql=full_body,
            schema_version=revision_tag,
            ontology_concepts=ontology_concepts,
        )
    elif jira_issue_key is not None or source_uri.startswith("jira://"):
        doc, chunks = DifferentiatedIncrementalIndexer.index_jira_reference_issue(
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            issue_key=jira_issue_key or title,
            issue_type=jira_issue_type,
            title=title,
            body_text=full_body,
            updated_tag=revision_tag,
            ontology_concepts=ontology_concepts,
        )
    else:
        doc, chunks = DifferentiatedIncrementalIndexer.index_confluence_parent_child(
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            source_uri=source_uri,
            title=title,
            hierarchy_path=hierarchy_path,
            markdown_sections=markdown_sections,
            revision_tag=revision_tag,
            labels=labels,
            page_status=page_status,
            ontology_concepts=ontology_concepts,
        )

    if doc is None:
        return DoclingIndexExecutionResult(
            doc_key=f"skipped-{datasource_alias}",
            trace_id=ctx.trace_id,
            already_indexed=True,
            chunks_count=0,
        )

    inserted_or_updated = target_rag.upsert_indexed_bundle(
        document=doc, chunks=chunks, code_edges=code_edges
    )
    logger.info(
        "worker.docling_indexer",
        doc_key=doc.doc_key,
        already_indexed=not inserted_or_updated,
        chunks_count=len(chunks),
        trace_id=ctx.trace_id,
    )
    return DoclingIndexExecutionResult(
        doc_key=doc.doc_key,
        trace_id=ctx.trace_id,
        already_indexed=not inserted_or_updated,
        chunks_count=len(chunks),
    )


@dramatiq.actor(actor_name="docling_indexer", max_retries=3)
def docling_indexer_actor(
    workspace_id: str,
    datasource_id: str,
    datasource_alias: str,
    source_uri: str,
    title: str,
    hierarchy_path: str,
    markdown_sections: list[str],
    revision_tag: str,
    trace_id: str,
) -> None:
    """Idempotent Dramatiq actor `docling_indexer` for background KB indexing."""
    execute_docling_index_job(
        workspace_id=workspace_id,
        datasource_id=datasource_id,
        datasource_alias=datasource_alias,
        source_uri=source_uri,
        title=title,
        hierarchy_path=hierarchy_path,
        markdown_sections=tuple(markdown_sections),
        revision_tag=revision_tag,
        trace_id=trace_id,
    )
