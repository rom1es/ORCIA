"""Lexical-only BM25 fallback and row mapping helpers for `SqlHybridRagRepository`."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from orcia_core.rag.models import (
    HybridRagHit,
    TripartiteNodeType,
    TripartiteRelationType,
    TripartiteTraceEdgeEntity,
)


def format_halfvec_literal(embedding: tuple[float, ...], dim: int = 1024) -> str:
    """Format a float vector as a `pgvector` `halfvec(dim)` literal string."""
    padded = list(embedding[:dim]) + [0.0] * max(0, dim - len(embedding))
    return "[" + ",".join(f"{v:.6f}" for v in padded) + "]"


def rows_to_hybrid_hits(rows: Iterable[Any]) -> tuple[HybridRagHit, ...]:
    """Map SQL rows from `kb_chunks`/`kb_documents` into `HybridRagHit` domain objects."""
    hits: list[HybridRagHit] = []
    for r in rows:
        is_stale = bool(r["is_stale"])
        hits.append(
            HybridRagHit(
                chunk_key=str(r["chunk_key"]),
                parent_chunk_key=str(r["parent_chunk_key"]),
                document_key=str(r["document_key"]),
                datasource_alias=str(r["datasource_alias"]),
                source_uri=str(r["source_uri"]),
                revision_tag=str(r["revision_tag"]),
                contextual_header=str(r["contextual_header"]),
                injected_content=str(r["injected_content"]),
                rrf_score=float(r["rrf_score"]),
                vector_rank=int(r["vector_rank"]),
                bm25_rank=int(r["bm25_rank"]),
                is_stale=is_stale,
                stale_warning_marker=(
                    f"[STALE_WARNING: {r['document_key']} @ {r['revision_tag']}]"
                    if is_stale
                    else None
                ),
                datasource_role=str(r.get("datasource_role") or "ACTIVE"),
            )
        )
    return tuple(hits)


async def execute_lexical_only_bm25_search(
    session: AsyncSession,
    *,
    workspace_id: str,
    query_text: str,
    rrf_k: int = 60,
    limit: int = 5,
) -> tuple[HybridRagHit, ...]:
    """Execute lexical `ts_rank_cd` search without vectors when no embedding model is active."""
    clean_query = query_text.strip()
    if not clean_query:
        return ()
    rows = (
        (
            await session.execute(
                sa.text(
                    """
                    WITH candidate_chunks AS (
                        SELECT
                            c.chunk_key,
                            COALESCE(p.chunk_key, c.chunk_key) AS parent_chunk_key,
                            d.doc_key AS document_key,
                            c.datasource_alias,
                            d.source_uri,
                            d.revision_tag,
                            c.contextual_header,
                            COALESCE(p.content_text, c.content_text) AS injected_content,
                            d.is_stale,
                            COALESCE(ds.role, 'ACTIVE') AS datasource_role,
                            ts_rank_cd(
                                '{0.1, 0.2, 0.4, 1.0}',
                                c.search_tsv,
                                websearch_to_tsquery('simple', :query_text)
                            ) AS lex_score,
                            ROW_NUMBER() OVER (
                                ORDER BY ts_rank_cd(
                                    '{0.1, 0.2, 0.4, 1.0}',
                                    c.search_tsv,
                                    websearch_to_tsquery('simple', :query_text)
                                ) DESC,
                                c.chunk_key ASC
                            ) AS bm25_rank
                        FROM kb_chunks c
                        JOIN kb_documents d ON d.id = c.document_id
                        LEFT JOIN workspace_datasources ds ON ds.id = d.datasource_id
                        LEFT JOIN kb_chunks p ON p.id = c.parent_chunk_id
                        WHERE c.workspace_id = CAST(:workspace_id AS uuid)
                          AND c.chunk_role != 'PARENT'
                          AND c.search_tsv @@ websearch_to_tsquery('simple', :query_text)
                    )
                    SELECT
                        chunk_key,
                        parent_chunk_key,
                        document_key,
                        datasource_alias,
                        source_uri,
                        revision_tag,
                        contextual_header,
                        injected_content,
                        is_stale,
                        datasource_role,
                        0 AS vector_rank,
                        bm25_rank::int AS bm25_rank,
                        ROUND((1.0 / (:rrf_k + bm25_rank))::numeric, 6)::float8 AS rrf_score
                    FROM candidate_chunks
                    WHERE lex_score > 0
                    ORDER BY rrf_score DESC, chunk_key ASC
                    LIMIT :limit;
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "query_text": clean_query,
                    "rrf_k": rrf_k,
                    "limit": limit,
                },
            )
        )
        .mappings()
        .all()
    )
    return rows_to_hybrid_hits(rows)


async def execute_tripartite_traversal(
    session: AsyncSession,
    *,
    workspace_id: str,
    seed_uri: str,
    max_depth: int = 2,
) -> tuple[TripartiteTraceEdgeEntity, ...]:
    """Execute bounded recursive CTE (`depth <= 2`, `AD-8`) on `tripartite_trace_edges`."""
    bounded_depth = min(max(1, max_depth), 2)
    rows = (
        (
            await session.execute(
                sa.text(
                    """
                    WITH RECURSIVE tripartite_walk AS (
                        SELECT
                            e.id::text AS id,
                            e.edge_key,
                            e.workspace_id::text AS workspace_id,
                            e.source_uri,
                            e.source_node_type,
                            e.target_uri,
                            e.target_node_type,
                            e.relation_type,
                            e.jira_issue_key,
                            1 AS depth
                        FROM tripartite_trace_edges e
                        WHERE e.workspace_id = CAST(:workspace_id AS uuid)
                          AND (e.source_uri = :seed_uri OR e.target_uri = :seed_uri)
                        UNION
                        SELECT
                            n.id::text AS id,
                            n.edge_key,
                            n.workspace_id::text AS workspace_id,
                            n.source_uri,
                            n.source_node_type,
                            n.target_uri,
                            n.target_node_type,
                            n.relation_type,
                            n.jira_issue_key,
                            w.depth + 1 AS depth
                        FROM tripartite_trace_edges n
                        JOIN tripartite_walk w
                          ON n.workspace_id = CAST(:workspace_id AS uuid)
                         AND (
                             n.source_uri = w.target_uri
                             OR n.target_uri = w.source_uri
                             OR n.source_uri = w.source_uri
                             OR n.target_uri = w.target_uri
                         )
                        WHERE w.depth < :bounded_depth
                    )
                    SELECT DISTINCT
                        id, edge_key, workspace_id, source_uri, source_node_type,
                        target_uri, target_node_type, relation_type, jira_issue_key
                    FROM tripartite_walk
                    ORDER BY edge_key ASC;
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "seed_uri": seed_uri,
                    "bounded_depth": bounded_depth,
                },
            )
        )
        .mappings()
        .all()
    )
    return tuple(
        TripartiteTraceEdgeEntity(
            id=str(r["id"]),
            edge_key=str(r["edge_key"]),
            workspace_id=str(r["workspace_id"]),
            source_uri=str(r["source_uri"]),
            source_node_type=cast(TripartiteNodeType, str(r["source_node_type"])),
            target_uri=str(r["target_uri"]),
            target_node_type=cast(TripartiteNodeType, str(r["target_node_type"])),
            relation_type=cast(TripartiteRelationType, str(r["relation_type"])),
            jira_issue_key=str(r["jira_issue_key"]) if r["jira_issue_key"] else None,
        )
        for r in rows
    )


__all__ = [
    "execute_lexical_only_bm25_search",
    "execute_tripartite_traversal",
    "format_halfvec_literal",
    "rows_to_hybrid_hits",
]
