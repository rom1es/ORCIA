"""SQLAlchemy 2.1 Asyncio (`asyncpg`) Repository for Differentiated Hybrid RAG (`Story 3.2b`).

Implements native PostgreSQL 18 hybrid search (`pgvector halfvec(1024)` HNSW `<=>` + `tsvector`
GIN `ts_rank_cd` weighted `A/B/C/D` fused by Reciprocal Rank Fusion `RRF k=60`, `ARCH-P7`) and
bounded recursive CTE (`WITH RECURSIVE ... WHERE depth <= 2`) on `tripartite_trace_edges`.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.rag._internal.sql_hybrid_search_helpers import (
    execute_lexical_only_bm25_search,
    execute_tripartite_traversal,
    format_halfvec_literal,
    rows_to_hybrid_hits,
)
from orcia_core.rag._internal.sql_rag_writes import upsert_kb_document_bundle_pg
from orcia_core.rag._internal.sql_state_queries import (
    query_kb_documents_pg,
    query_kb_stale_alerts_pg,
    query_tripartite_edges_pg,
)
from orcia_core.rag._internal.sql_tripartite_writes import (
    upsert_kb_stale_alert_pg,
    upsert_tripartite_edges_pg,
)
from orcia_core.rag.models import (
    CodeGraphEdgeEntity,
    HybridRagHit,
    KbChunkEntity,
    KbDocumentEntity,
    KbStaleAlertEntity,
    TripartiteTraceEdgeEntity,
)


class SqlHybridRagRepository:
    """Async SQLAlchemy 2.1 repository executing `halfvec(1024)` + `ts_rank_cd` RRF (`k=60`)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def format_halfvec_literal(embedding: tuple[float, ...], dim: int = 1024) -> str:
        """Format a float vector as a `pgvector` `halfvec(dim)` literal string."""
        return format_halfvec_literal(embedding, dim=dim)

    async def search_hybrid_rrf(
        self,
        *,
        workspace_id: str,
        query_text: str,
        query_embedding: tuple[float, ...] | None = None,
        embedding_model_id: str | None = None,
        rrf_k: int = 60,
        limit: int = 5,
    ) -> tuple[HybridRagHit, ...]:
        """Execute native SQL hybrid search (`halfvec(1024)` + `ts_rank_cd`) or lexical BM25."""
        if query_embedding is None:
            async with self._session_factory() as session:
                return await execute_lexical_only_bm25_search(
                    session,
                    workspace_id=workspace_id,
                    query_text=query_text,
                    rrf_k=rrf_k,
                    limit=limit,
                )
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
                                    COALESCE(ds.role, 'ACTIVE') AS datasource_role,
                                    ROW_NUMBER() OVER (
                                        ORDER BY (
                                            CASE
                                                WHEN CAST(:active_model_id AS text) IS NOT NULL
                                                     AND (
                                                         c.embedding_model_id IS NULL
                                                         OR c.embedding_model_id
                                                         != CAST(:active_model_id AS uuid)
                                                     )
                                                THEN NULL
                                                ELSE c.embedding
                                            END <=> CAST(:vec_literal AS halfvec(1024))
                                        ) ASC NULLS LAST,
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
                                LEFT JOIN workspace_datasources ds ON ds.id = d.datasource_id
                                LEFT JOIN kb_chunks p ON p.id = c.parent_chunk_id
                                WHERE c.workspace_id = CAST(:workspace_id AS uuid)
                                  AND c.chunk_role != 'PARENT'
                                  AND (
                                      CAST(:active_model_id AS text) IS NULL
                                      OR c.embedding_model_id IS NULL
                                      OR c.embedding_model_id = CAST(:active_model_id AS uuid)
                                  )
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
                            "active_model_id": embedding_model_id,
                            "rrf_k": rrf_k,
                            "limit": limit,
                        },
                    )
                )
                .mappings()
                .all()
            )
            return rows_to_hybrid_hits(rows)

    async def traverse_tripartite_neighborhood(
        self,
        *,
        workspace_id: str,
        seed_uri: str,
        max_depth: int = 2,
    ) -> tuple[TripartiteTraceEdgeEntity, ...]:
        """Traverse `tripartite_trace_edges` with a bounded recursive CTE (`depth <= 2`, `AD-8`)."""
        async with self._session_factory() as session:
            return await execute_tripartite_traversal(
                session, workspace_id=workspace_id, seed_uri=seed_uri, max_depth=max_depth
            )

    async def list_documents_pg(
        self, *, workspace_id: str | None = None, limit: int = 200
    ) -> tuple[KbDocumentEntity, ...]:
        """List persisted `kb_documents` from PostgreSQL 18."""
        return await query_kb_documents_pg(
            self._session_factory, workspace_id=workspace_id, limit=limit
        )

    async def list_tripartite_edges_pg(
        self, *, workspace_id: str | None = None, limit: int = 200
    ) -> tuple[TripartiteTraceEdgeEntity, ...]:
        """List persisted `tripartite_trace_edges` from PostgreSQL 18."""
        return await query_tripartite_edges_pg(
            self._session_factory, workspace_id=workspace_id, limit=limit
        )

    async def list_stale_alerts_pg(
        self, *, workspace_id: str | None = None, limit: int = 200
    ) -> tuple[KbStaleAlertEntity, ...]:
        """List persisted `kb_stale_alerts` from PostgreSQL 18."""
        return await query_kb_stale_alerts_pg(
            self._session_factory, workspace_id=workspace_id, limit=limit
        )

    async def upsert_document_bundle_pg(
        self,
        *,
        document: KbDocumentEntity,
        chunks: tuple[KbChunkEntity, ...] = (),
        code_edges: tuple[CodeGraphEdgeEntity, ...] = (),
        embedding_model_id: str | None = None,
    ) -> KbDocumentEntity | None:
        """Persist `kb_documents`, `kb_chunks` (AD-24.7), and `code_graph_edges` in PG18."""
        return await upsert_kb_document_bundle_pg(
            self._session_factory,
            document=document,
            chunks=chunks,
            code_edges=code_edges,
            embedding_model_id=embedding_model_id,
        )

    async def upsert_tripartite_edges_pg(
        self, *, edges: tuple[TripartiteTraceEdgeEntity, ...]
    ) -> tuple[TripartiteTraceEdgeEntity, ...]:
        """Persist `tripartite_trace_edges` in PostgreSQL 18."""
        return await upsert_tripartite_edges_pg(self._session_factory, edges=edges)

    async def upsert_stale_alert_pg(
        self, *, alert: KbStaleAlertEntity
    ) -> KbStaleAlertEntity | None:
        """Persist a `kb_stale_alerts` entry in PostgreSQL 18."""
        return await upsert_kb_stale_alert_pg(self._session_factory, alert=alert)


__all__ = ["SqlHybridRagRepository"]
