"""Concrete Adapters for `ContextSourcePort` and `VectorStorePort` (`DEC-CTX-01`, `Story 3.3`).

Provides:
- `HybridRagVectorStoreAdapter`: implements `VectorStorePort` on top of `HybridRagIndexingService`
  (`halfvec(1024)` + BM25 Reciprocal Rank Fusion).
- `CatalogAndBlackboardContextSourceAdapter`: implements `ContextSourcePort` across JSON payloads,
  CAS blobs (`sha256:`), KB documents, Federated Catalog items, Blackboard snapshots, and
  Permission Broker policies without ever reading local Markdown files from disk.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from orcia_core.rag.hybrid_rag_service import HybridRagService
from orcia_kernel.context_ports import (
    ContextSliceKind,
    ContextSliceRecord,
    ContextSourcePort,
    VectorSearchHitRecord,
    VectorStorePort,
)


def _sha256_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


class HybridRagVectorStoreAdapter(VectorStorePort):
    """`VectorStorePort` adapter backed by `HybridRagService` (`DEC-CTX-01`)."""

    def __init__(self, rag_service: HybridRagService) -> None:
        self._rag = rag_service

    def hybrid_search(
        self,
        *,
        workspace_id: str,
        query_text: str,
        allowed_datasource_aliases: frozenset[str],
        top_k: int = 5,
    ) -> tuple[VectorSearchHitRecord, ...]:
        hits = self._rag.search_hybrid_rrf(
            workspace_id=workspace_id,
            query_text=query_text,
            allowed_datasource_aliases=(
                allowed_datasource_aliases if allowed_datasource_aliases else None
            ),
            top_k=top_k,
        )
        return tuple(
            VectorSearchHitRecord(
                chunk_key=h.chunk_key,
                document_key=h.document_key,
                source_uri=h.source_uri,
                contextual_header=h.contextual_header,
                injected_content=h.injected_content,
                rrf_score=h.rrf_score,
                is_stale=h.is_stale,
                stale_warning_marker=h.stale_warning_marker,
            )
            for h in hits
        )


class CatalogAndBlackboardContextSourceAdapter(ContextSourcePort):
    """`ContextSourcePort` retrieving structured slices from Catalog, CAS, Blackboard & KB."""

    def __init__(
        self,
        *,
        rag_service: HybridRagService | None = None,
        catalog_items_provider: Any = None,
        blackboard_snapshots_provider: Any = None,
        permission_policies_provider: Any = None,
    ) -> None:
        self._rag = rag_service
        self._catalog_provider = catalog_items_provider
        self._blackboard_provider = blackboard_snapshots_provider
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
            content_sha256=_sha256_text(f"{serialized}:{text_excerpt}"),
            title=title,
            structured_payload=dict(structured_payload),
            text_excerpt=text_excerpt or serialized,
            is_stale=is_stale,
            stale_warning_marker=stale_warning_marker,
        )
        self._custom_slices.append(record)
        return record

    def fetch_context_slices(
        self,
        *,
        workspace_id: str,
        query: str,
        uris: tuple[str, ...] = (),
        include_sources: tuple[str, ...] = ("catalog", "blackboard", "permissions", "cas", "kb"),
    ) -> tuple[ContextSliceRecord, ...]:
        """Retrieve matching context slices without reading local Markdown files."""
        results: list[ContextSliceRecord] = []
        uri_filter = set(uris)
        query_terms = [t.lower() for t in query.split() if len(t) >= 3]

        for custom in self._custom_slices:
            if uri_filter and custom.source_uri not in uri_filter:
                continue
            results.append(custom)

        if "kb" in include_sources and self._rag is not None:
            for doc in self._rag.list_documents(workspace_id=workspace_id):
                if uri_filter and doc.source_uri not in uri_filter:
                    continue
                if (
                    query_terms
                    and not any(
                        term in doc.title.lower() or term in doc.source_uri.lower()
                        for term in query_terms
                    )
                    and len(results) >= 4
                ):
                    continue
                warn = (
                    f"[STALE_WARNING: age={doc.age_days}d > ttl={doc.freshness_ttl_days}d]"
                    if doc.is_stale
                    else None
                )
                results.append(
                    ContextSliceRecord(
                        slice_id=f"kb-{doc.doc_key}",
                        source_uri=doc.source_uri,
                        source_kind="KB_DOCUMENT",
                        content_sha256=doc.content_sha256,
                        title=doc.title,
                        structured_payload={
                            "doc_key": doc.doc_key,
                            "indexing_regime": doc.indexing_regime,
                            "revision_tag": doc.revision_tag,
                            "datasource_alias": doc.datasource_alias,
                        },
                        text_excerpt=f"{doc.title} ({doc.source_uri}@{doc.revision_tag})",
                        is_stale=doc.is_stale,
                        stale_warning_marker=warn,
                    )
                )

        if "catalog" in include_sources and callable(self._catalog_provider):
            for item in self._catalog_provider(workspace_id):
                if isinstance(item, dict):
                    uri = str(item.get("canonical_uri") or item.get("uri") or "")
                    title = str(item.get("display_name") or item.get("title") or uri)
                    sha = str(item.get("content_sha256") or item.get("sha256") or _sha256_text(uri))
                    kind_val = str(item.get("item_kind") or "WORKFLOW")
                else:
                    uri = str(
                        getattr(item, "canonical_uri", None) or getattr(item, "uri", None) or ""
                    )
                    title = str(
                        getattr(item, "display_name", None) or getattr(item, "title", None) or uri
                    )
                    sha = str(
                        getattr(item, "content_sha256", None)
                        or getattr(item, "sha256", None)
                        or _sha256_text(uri)
                    )
                    kind_val = str(getattr(item, "item_kind", None) or "WORKFLOW")
                if not uri or (uri_filter and uri not in uri_filter):
                    continue
                results.append(
                    ContextSliceRecord(
                        slice_id=f"cat-{sha[:16]}",
                        source_uri=uri,
                        source_kind="CATALOG_ITEM",
                        content_sha256=sha,
                        title=title,
                        structured_payload={"canonical_uri": uri, "item_kind": kind_val},
                        text_excerpt=f"{title} [{kind_val}] ({uri})",
                    )
                )

        if "blackboard" in include_sources and callable(self._blackboard_provider):
            for snap in self._blackboard_provider(workspace_id):
                step_key = getattr(snap, "step_key", "step")
                snap_id = getattr(snap, "id", "snap")
                sha = getattr(snap, "artifact_sha256", _sha256_text(snap_id))
                payload = getattr(snap, "artifact_payload", {})
                uri = f"orcia://blackboard/{workspace_id}/{step_key}@{sha[:12]}"
                if uri_filter and uri not in uri_filter:
                    continue
                results.append(
                    ContextSliceRecord(
                        slice_id=f"bb-{snap_id}",
                        source_uri=uri,
                        source_kind="BLACKBOARD_SNAPSHOT",
                        content_sha256=sha,
                        title=f"Snapshot Blackboard ({step_key})",
                        structured_payload=dict(payload) if isinstance(payload, dict) else {},
                        text_excerpt=json.dumps(payload, sort_keys=True)[:240],
                    )
                )

        if "permissions" in include_sources and callable(self._permission_provider):
            for pol in self._permission_provider(workspace_id):
                pol_key = getattr(pol, "policy_key", "policy")
                uri_pat = getattr(pol, "uri_pattern", "orcia://*")
                req_role = getattr(pol, "required_role", "TEAM_MEMBER")
                uri = f"orcia://permissions/policies/{pol_key}"
                if uri_filter and uri not in uri_filter:
                    continue
                results.append(
                    ContextSliceRecord(
                        slice_id=f"perm-{pol_key}",
                        source_uri=uri,
                        source_kind="PERMISSION_POLICY",
                        content_sha256=_sha256_text(f"{pol_key}:{uri_pat}:{req_role}"),
                        title=f"Politique Permission Broker ({pol_key})",
                        structured_payload={
                            "policy_key": pol_key,
                            "uri_pattern": uri_pat,
                            "required_role": req_role,
                        },
                        text_excerpt=f"Policy {pol_key}: {uri_pat} requires {req_role}",
                    )
                )

        return tuple(results)
