"""HybridRagService (`halfvec(1024)` + BM25 via Reciprocal Rank Fusion, Story 2.3, AD-8).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import math
import re

from orcia_core.domain.exceptions import ResourceNotFoundError
from orcia_core.rag.indexer_and_rrf import (
    compute_deterministic_halfvec_1024,
    cosine_similarity,
)
from orcia_core.rag.models import (
    CodeGraphEdgeEntity,
    HybridRagHit,
    KbChunkEntity,
    KbDocumentEntity,
)

RRF_K: int = 60


class HybridRagService:
    """Reciprocal Rank Fusion (`halfvec(1024)` + BM25) with Passthrough source filtering."""

    def __init__(
        self,
        *,
        documents: tuple[KbDocumentEntity, ...] = (),
        chunks: tuple[KbChunkEntity, ...] = (),
        code_edges: tuple[CodeGraphEdgeEntity, ...] = (),
    ) -> None:
        self._documents: dict[str, KbDocumentEntity] = {d.id: d for d in documents}
        self._doc_by_key: dict[str, KbDocumentEntity] = {d.doc_key: d for d in documents}
        self._chunks: dict[str, KbChunkEntity] = {c.id: c for c in chunks}
        self._code_edges: list[CodeGraphEdgeEntity] = list(code_edges)

    def list_documents(self, *, workspace_id: str | None = None) -> tuple[KbDocumentEntity, ...]:
        docs = list(self._documents.values())
        if workspace_id is not None:
            docs = [d for d in docs if d.workspace_id == workspace_id]
        return tuple(docs)

    def list_code_edges(
        self, *, workspace_id: str | None = None
    ) -> tuple[CodeGraphEdgeEntity, ...]:
        if workspace_id is None:
            return tuple(self._code_edges)
        return tuple(e for e in self._code_edges if e.workspace_id == workspace_id)

    def should_reindex_document(self, *, doc_key: str, new_sha256: str) -> bool:
        """Incremental check: skip re-vectorization when SHA-256 hash is unchanged."""
        existing = self._doc_by_key.get(doc_key)
        if existing is None:
            return True
        return existing.content_sha256 != new_sha256

    def upsert_indexed_bundle(
        self,
        *,
        document: KbDocumentEntity,
        chunks: tuple[KbChunkEntity, ...],
        code_edges: tuple[CodeGraphEdgeEntity, ...] = (),
    ) -> bool:
        """Idempotent incremental upsert: returns False when SHA-256 is unchanged (no-op)."""
        if not self.should_reindex_document(
            doc_key=document.doc_key, new_sha256=document.content_sha256
        ):
            return False

        old = self._doc_by_key.get(document.doc_key)
        if old is not None:
            self._documents.pop(old.id, None)
            stale_chunk_ids = [c.id for c in self._chunks.values() if c.document_id == old.id]
            for cid in stale_chunk_ids:
                self._chunks.pop(cid, None)
            old_prefix = f"edge-{old.datasource_alias}-{old.title}-"
            self._code_edges = [
                e for e in self._code_edges if not e.edge_key.startswith(old_prefix)
            ]

        self._documents[document.id] = document
        self._doc_by_key[document.doc_key] = document
        for chunk in chunks:
            self._chunks[chunk.id] = chunk
        existing_edge_keys = {e.edge_key for e in self._code_edges}
        for edge in code_edges:
            if edge.edge_key not in existing_edge_keys:
                self._code_edges.append(edge)
                existing_edge_keys.add(edge.edge_key)
        return True

    def mark_document_stale(self, *, doc_key: str, age_days: int | None = None) -> KbDocumentEntity:
        doc = self._doc_by_key.get(doc_key)
        if doc is None:
            raise ResourceNotFoundError(detail_override=f"Document '{doc_key}' not found.")
        updated = KbDocumentEntity(
            id=doc.id,
            doc_key=doc.doc_key,
            workspace_id=doc.workspace_id,
            datasource_id=doc.datasource_id,
            datasource_alias=doc.datasource_alias,
            source_uri=doc.source_uri,
            source_scheme=doc.source_scheme,
            indexing_regime=doc.indexing_regime,
            title=doc.title,
            revision_tag=doc.revision_tag,
            content_sha256=doc.content_sha256,
            freshness_ttl_days=doc.freshness_ttl_days,
            age_days=age_days if age_days is not None else doc.age_days,
            is_stale=True,
        )
        self._documents[updated.id] = updated
        self._doc_by_key[updated.doc_key] = updated
        return updated

    def search_hybrid_rrf(
        self,
        *,
        workspace_id: str,
        query_text: str,
        allowed_datasource_aliases: frozenset[str] | None = None,
        top_k: int = 5,
    ) -> tuple[HybridRagHit, ...]:
        """Combine `halfvec(1024)` cosine similarity and BM25 lexical matching via RRF (`< 50 ms`).

        When a `CHILD` chunk matches, injects the `PARENT` chunk's `content_text` into context.
        Enforces Passthrough read access filtering via `allowed_datasource_aliases`.
        """
        searchable = [
            c
            for c in self._chunks.values()
            if c.workspace_id == workspace_id
            and c.embedding is not None
            and (
                allowed_datasource_aliases is None
                or c.datasource_alias in allowed_datasource_aliases
            )
        ]
        if not searchable:
            return ()

        query_vec = compute_deterministic_halfvec_1024(query_text)
        query_tokens = set(re.findall(r"[a-z0-9_/-]{2,}", query_text.lower()))

        vector_scored = sorted(
            searchable,
            key=lambda c: cosine_similarity(query_vec, c.embedding or ()),
            reverse=True,
        )
        vector_ranks = {c.id: rank for rank, c in enumerate(vector_scored, start=1)}

        def _bm25_score(chunk: KbChunkEntity) -> float:
            haystack = f"{chunk.contextual_header} {chunk.content_text}".lower()
            score = 0.0
            for tok in query_tokens:
                count = haystack.count(tok)
                if count > 0:
                    score += (count * 2.2) / (count + 1.2) + math.log1p(len(tok))
            return score

        bm25_scored = sorted(searchable, key=_bm25_score, reverse=True)
        bm25_ranks = {c.id: rank for rank, c in enumerate(bm25_scored, start=1)}

        hits: list[HybridRagHit] = []
        for chunk in searchable:
            v_rank = vector_ranks[chunk.id]
            b_rank = bm25_ranks[chunk.id]
            rrf = round((1.0 / (RRF_K + v_rank)) + (1.0 / (RRF_K + b_rank)), 6)
            parent = (
                self._chunks.get(chunk.parent_chunk_id)
                if chunk.parent_chunk_id is not None
                else None
            )
            injected_text = parent.content_text if parent is not None else chunk.content_text
            parent_key = parent.chunk_key if parent is not None else chunk.chunk_key
            doc = self._documents[chunk.document_id]
            hits.append(
                HybridRagHit(
                    chunk_key=chunk.chunk_key,
                    parent_chunk_key=parent_key,
                    document_key=doc.doc_key,
                    datasource_alias=chunk.datasource_alias,
                    source_uri=doc.source_uri,
                    revision_tag=doc.revision_tag,
                    contextual_header=chunk.contextual_header,
                    injected_content=injected_text,
                    rrf_score=rrf,
                    vector_rank=v_rank,
                    bm25_rank=b_rank,
                    is_stale=doc.is_stale,
                    stale_warning_marker="[STALE_WARNING]" if doc.is_stale else None,
                )
            )

        hits.sort(key=lambda h: (-h.rrf_score, h.vector_rank, h.chunk_key))
        return tuple(hits[:top_k])
