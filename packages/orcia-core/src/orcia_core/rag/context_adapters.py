"""Concrete Adapters for `ContextSourcePort` and `VectorStorePort` (`DEC-CTX-01`, `Story 26.5`).

Provides:
- `HybridRagVectorStoreAdapter`: implements `VectorStorePort` on top of `SqlHybridRagRepository`
  (PG18 `halfvec(1024)` + BM25 RRF) and/or `HybridRagService`.
- `CatalogAndBlackboardContextSourceAdapter`: implements `ContextSourcePort` across JSON payloads,
  CAS blobs (`sha256:`), PG18 KB documents, Federated Catalog items, active PG18 Blackboard
  snapshots, and Permission Broker policies.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from typing import Any

from orcia_core.rag._context_adapters_helpers import (
    build_blackboard_slices,
    build_catalog_slices,
    build_kb_document_slices,
    build_permission_slices,
    sha256_text,
    to_vector_hits,
)
from orcia_core.rag._internal.sql_repository import SqlHybridRagRepository
from orcia_core.rag.hybrid_rag_service import HybridRagService
from orcia_kernel.context_ports import (
    ContextSliceKind,
    ContextSliceRecord,
    ContextSourcePort,
    VectorSearchHitRecord,
    VectorStorePort,
)


class HybridRagVectorStoreAdapter(VectorStorePort):
    """`VectorStorePort` adapter backed by PG18 `SqlHybridRagRepository` and `HybridRagService`."""

    def __init__(
        self,
        rag_service: HybridRagService,
        embedding_port: Any = None,
        *,
        sql_rag_repo: SqlHybridRagRepository | None = None,
        embedding_model_id: str | None = None,
    ) -> None:
        self._rag = rag_service
        self._embedding_port = embedding_port or getattr(rag_service, "_embedding_port", None)
        self._sql_rag_repo = sql_rag_repo
        self._embedding_model_id = embedding_model_id

    async def _resolve_query_embedding_async(
        self, query_text: str, query_embedding: tuple[float, ...] | None
    ) -> tuple[float, ...] | None:
        if query_embedding is not None:
            return query_embedding
        if self._embedding_port is None:
            return None
        if hasattr(self._embedding_port, "embed_query"):
            return tuple(await self._embedding_port.embed_query(query_text))
        if hasattr(self._embedding_port, "embed_query_sync"):
            return tuple(self._embedding_port.embed_query_sync(query_text))
        return None

    async def hybrid_search_async(
        self,
        *,
        workspace_id: str,
        query_text: str,
        allowed_datasource_aliases: frozenset[str],
        top_k: int = 5,
        query_embedding: tuple[float, ...] | None = None,
    ) -> tuple[VectorSearchHitRecord, ...]:
        """Async hybrid search via PG18 `SqlHybridRagRepository` (or in-memory fallback)."""
        effective_embedding = await self._resolve_query_embedding_async(query_text, query_embedding)
        if self._sql_rag_repo is not None:
            fetch_limit = max(top_k, 15) if allowed_datasource_aliases else top_k
            sql_hits = await self._sql_rag_repo.search_hybrid_rrf(
                workspace_id=workspace_id,
                query_text=query_text,
                query_embedding=effective_embedding,
                embedding_model_id=self._embedding_model_id,
                limit=fetch_limit,
            )
            if allowed_datasource_aliases:
                sql_hits = tuple(
                    h for h in sql_hits if h.datasource_alias in allowed_datasource_aliases
                )
            if sql_hits or effective_embedding is None:
                return to_vector_hits(sql_hits[:top_k])
        if effective_embedding is None:
            return ()
        hits = await self._rag.search_hybrid_rrf_async(
            workspace_id=workspace_id,
            query_text=query_text,
            query_embedding=effective_embedding,
            allowed_datasource_aliases=(
                allowed_datasource_aliases if allowed_datasource_aliases else None
            ),
            top_k=top_k,
        )
        return to_vector_hits(hits)

    def hybrid_search(
        self,
        *,
        workspace_id: str,
        query_text: str,
        allowed_datasource_aliases: frozenset[str],
        top_k: int = 5,
        query_embedding: tuple[float, ...] | None = None,
    ) -> tuple[VectorSearchHitRecord, ...]:
        effective_embedding = query_embedding
        if effective_embedding is None and self._embedding_port is not None:
            if hasattr(self._embedding_port, "embed_query_sync"):
                effective_embedding = tuple(self._embedding_port.embed_query_sync(query_text))
            elif hasattr(self._embedding_port, "embed_query"):
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    effective_embedding = tuple(
                        asyncio.run(self._embedding_port.embed_query(query_text))
                    )
                else:
                    raise RuntimeError(
                        "HybridRagVectorStoreAdapter.hybrid_search() cannot run inside an active "
                        "event loop; await hybrid_search_async() instead."
                    ) from None
        if effective_embedding is None:
            return ()
        hits = self._rag.search_hybrid_rrf(
            workspace_id=workspace_id,
            query_text=query_text,
            query_embedding=effective_embedding,
            allowed_datasource_aliases=(
                allowed_datasource_aliases if allowed_datasource_aliases else None
            ),
            top_k=top_k,
        )
        return to_vector_hits(hits)


class CatalogAndBlackboardContextSourceAdapter(ContextSourcePort):
    """`ContextSourcePort` retrieving structured slices from Catalog, CAS, Blackboard & KB."""

    def __init__(
        self,
        *,
        rag_service: HybridRagService | None = None,
        sql_rag_repo: SqlHybridRagRepository | None = None,
        catalog_items_provider: Any = None,
        blackboard_snapshots_provider: Any = None,
        blackboard_snapshots_async_provider: Any = None,
        permission_policies_provider: Any = None,
    ) -> None:
        self._rag = rag_service
        self._sql_rag_repo = sql_rag_repo
        self._catalog_provider = catalog_items_provider
        self._blackboard_provider = blackboard_snapshots_provider
        self._blackboard_async_provider = blackboard_snapshots_async_provider
        self._permission_provider = permission_policies_provider
        self._custom_slices: list[ContextSliceRecord] = []

    def register_context_slice(
        self,
        *,
        slice_id: str,
        source_uri: str,
        source_kind: ContextSliceKind,
        title: str,
        structured_payload: dict[str, Any],
        text_excerpt: str = "",
        is_stale: bool = False,
        stale_warning_marker: str | None = None,
    ) -> ContextSliceRecord:
        """Register an explicit JSON/CAS/Document context slice (`DEC-CTX-01`)."""
        serialized = json.dumps(structured_payload, sort_keys=True)
        record = ContextSliceRecord(
            slice_id=slice_id,
            source_uri=source_uri,
            source_kind=source_kind,
            content_sha256=sha256_text(f"{serialized}:{text_excerpt}"),
            title=title,
            structured_payload=dict(structured_payload),
            text_excerpt=text_excerpt or serialized,
            is_stale=is_stale,
            stale_warning_marker=stale_warning_marker,
        )
        self._custom_slices.append(record)
        return record

    def _collect_static_slices(
        self,
        *,
        workspace_id: str,
        query: str,
        uris: tuple[str, ...],
        include_sources: tuple[str, ...],
        extra_kb_docs: tuple[Any, ...] = (),
        bb_snapshots: Any = None,
    ) -> list[ContextSliceRecord]:
        results: list[ContextSliceRecord] = []
        uri_filter = set(uris)
        query_terms = [t.lower() for t in query.split() if len(t) >= 3]
        for custom in self._custom_slices:
            if not uri_filter or custom.source_uri in uri_filter:
                results.append(custom)
        if "kb" in include_sources:
            docs = extra_kb_docs or (
                self._rag.list_documents(workspace_id=workspace_id) if self._rag is not None else ()
            )
            results.extend(
                build_kb_document_slices(
                    docs, query_terms=query_terms, uri_filter=uri_filter, current_count=len(results)
                )
            )
        if "catalog" in include_sources and callable(self._catalog_provider):
            results.extend(
                build_catalog_slices(self._catalog_provider(workspace_id), uri_filter=uri_filter)
            )
        if "blackboard" in include_sources and bb_snapshots is not None:
            results.extend(
                build_blackboard_slices(
                    bb_snapshots, workspace_id=workspace_id, uri_filter=uri_filter
                )
            )
        if "permissions" in include_sources and callable(self._permission_provider):
            results.extend(
                build_permission_slices(
                    self._permission_provider(workspace_id), uri_filter=uri_filter
                )
            )
        return results

    def fetch_context_slices(
        self,
        *,
        workspace_id: str,
        query: str,
        uris: tuple[str, ...] = (),
        include_sources: tuple[str, ...] = ("catalog", "blackboard", "permissions", "cas", "kb"),
    ) -> tuple[ContextSliceRecord, ...]:
        """Retrieve matching context slices synchronously (in-memory/non-async providers)."""
        bb_snaps = (
            self._blackboard_provider(workspace_id)
            if ("blackboard" in include_sources and callable(self._blackboard_provider))
            else None
        )
        if inspect.isawaitable(bb_snaps):
            bb_snaps = ()
        return tuple(
            self._collect_static_slices(
                workspace_id=workspace_id,
                query=query,
                uris=uris,
                include_sources=include_sources,
                bb_snapshots=bb_snaps,
            )
        )

    async def fetch_context_slices_async(
        self,
        *,
        workspace_id: str,
        query: str,
        uris: tuple[str, ...] = (),
        include_sources: tuple[str, ...] = ("catalog", "blackboard", "permissions", "cas", "kb"),
    ) -> tuple[ContextSliceRecord, ...]:
        """Async context slice loader querying PG18 `blackboard_snapshots` and `kb_documents`."""
        kb_docs: tuple[Any, ...] = ()
        if "kb" in include_sources and self._sql_rag_repo is not None:
            kb_docs = await self._sql_rag_repo.list_documents_pg(workspace_id=workspace_id)
        bb_snaps: Any = None
        if "blackboard" in include_sources:
            if callable(self._blackboard_async_provider):
                bb_snaps = await self._blackboard_async_provider(workspace_id)
            elif callable(self._blackboard_provider):
                maybe = self._blackboard_provider(workspace_id)
                bb_snaps = await maybe if inspect.isawaitable(maybe) else maybe
        return tuple(
            self._collect_static_slices(
                workspace_id=workspace_id,
                query=query,
                uris=uris,
                include_sources=include_sources,
                extra_kb_docs=kb_docs,
                bb_snapshots=bb_snaps,
            )
        )
