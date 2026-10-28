"""SQLAlchemy 2.1 Asyncio (`asyncpg`) Repository for Differentiated Hybrid RAG (`Story 3.2b`).

Implements native PostgreSQL 18 hybrid search (`pgvector halfvec(1024)` HNSW `<=>` + `tsvector`
GIN `ts_rank_cd` weighted `A/B/C/D` fused by Reciprocal Rank Fusion `RRF k=60`, `ARCH-P7`) and
bounded recursive CTE (`WITH RECURSIVE ... WHERE depth <= 2`) on `tripartite_trace_edges`.
"""

from __future__ import annotations

from typing import cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.rag.models import (
    HybridRagHit,
    TripartiteNodeType,
    TripartiteRelationType,
    TripartiteTraceEdgeEntity,
)


class SqlHybridRagRepository:
    """Async SQLAlchemy 2.1 repository executing `halfvec(1024)` + `ts_rank_cd` RRF (`k=60`)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def format_halfvec_literal(embedding: tuple[float, ...], dim: int = 1024) -> str:
        """Format a float vector as a `pgvector` `halfvec(dim)` literal string."""
        padded = list(embedding[:dim]) + [0.0] * max(0, dim - len(embedding))
        return "[" + ",".join(f"{v:.6f}" for v in padded) + "]"

    async def search_hybrid_rrf(
        self,
        *,
        workspace_id: str,
        query_text: str,
        query_embedding: tuple[float, ...],
        rrf_k: int = 60,
        limit: int = 5,
    ) -> tuple[HybridRagHit, ...]:
        """Execute native SQL hybrid search (`halfvec(1024) <=>` + `ts_rank_cd` RRF `k=60`)."""
        vec_literal = self.format_halfvec_literal(query_embedding, dim=1024)
        async with self._session_factory() as session:
            rows = (
                (
                    await session.execute(
                        sa.text(
                            """
                            WITH candidate_chunks AS (
                                SELECT
                                    c.id,
                                    c.chunk_key,
                                    COALESCE(p.chunk_key, c.chunk_key) AS parent_chunk_key,
                                    d.doc_key AS document_key,
                                    c.datasource_alias,
                                    d.source_uri,
                                    d.revision_tag,
                                    c.contextual_header,
                                    COALESCE(p.content_text, c.content_text) AS injected_content,
                                    d.is_stale,
                                    ROW_NUMBER() OVER (
                                        ORDER BY (
                                            c.embedding <=> CAST(:vec_literal AS halfvec(1024))
                                        ) ASC,
                                        c.chunk_key ASC
                                    ) AS vector_rank,
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
                                LEFT JOIN kb_chunks p ON p.id = c.parent_chunk_id
                                WHERE c.workspace_id = CAST(:workspace_id AS uuid)
                                  AND c.chunk_role != 'PARENT'
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
                                vector_rank::int AS vector_rank,
                                bm25_rank::int AS bm25_rank,
                                ROUND(
                                    (
                                        (1.0 / (:rrf_k + vector_rank))
                                        + (1.0 / (:rrf_k + bm25_rank))
                                    )::numeric,
                                    6
                                )::float8 AS rrf_score
                            FROM candidate_chunks
                            ORDER BY rrf_score DESC, chunk_key ASC
                            LIMIT :limit;
                            """
                        ),
                        {
                            "workspace_id": workspace_id,
                            "query_text": query_text,
                            "vec_literal": vec_literal,
                            "rrf_k": rrf_k,
                            "limit": limit,
                        },
                    )
                )
                .mappings()
                .all()
            )
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
                    )
                )
            return tuple(hits)

    async def traverse_tripartite_neighborhood(
        self,
        *,
        workspace_id: str,
        seed_uri: str,
        max_depth: int = 2,
    ) -> tuple[TripartiteTraceEdgeEntity, ...]:
        """Traverse `tripartite_trace_edges` with a bounded recursive CTE (`depth <= 2`, `AD-8`)."""
        bounded_depth = min(max(1, max_depth), 2)
        async with self._session_factory() as session:
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


__all__ = ["SqlHybridRagRepository"]
