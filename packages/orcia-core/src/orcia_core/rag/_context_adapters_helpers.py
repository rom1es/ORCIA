"""Slice and Vector Hit Mapping Helpers for `context_adapters.py` (`DEC-CTX-01`)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from orcia_kernel.context_ports import ContextSliceRecord, VectorSearchHitRecord


def build_kb_document_slices(
    docs: Iterable[Any],
    *,
    query_terms: list[str],
    uri_filter: set[str],
    current_count: int = 0,
) -> list[ContextSliceRecord]:
    """Convert `KbDocumentEntity` records into `ContextSliceRecord` entries."""
    out: list[ContextSliceRecord] = []
    for doc in docs:
        if uri_filter and doc.source_uri not in uri_filter:
            continue
        if (
            query_terms
            and not any(
                term in doc.title.lower() or term in doc.source_uri.lower() for term in query_terms
            )
            and (current_count + len(out)) >= 4
        ):
            continue
        warn = (
            f"[STALE_WARNING: age={doc.age_days}d > ttl={doc.freshness_ttl_days}d]"
            if doc.is_stale
            else None
        )
        out.append(
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
    return out


def sha256_text(text: str) -> str:
    """Return canonical `sha256:<hex>` digest for `text`."""
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def to_vector_hits(hits: tuple[Any, ...]) -> tuple[VectorSearchHitRecord, ...]:
    """Map internal hybrid RAG hit objects to `VectorSearchHitRecord` contracts."""
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


def build_catalog_slices(items: Any, *, uri_filter: set[str]) -> list[ContextSliceRecord]:
    """Convert catalog items into `ContextSliceRecord` entries."""
    out: list[ContextSliceRecord] = []
    for item in items:
        uri = str(
            item.get("canonical_uri") or item.get("uri") or ""
            if isinstance(item, dict)
            else getattr(item, "canonical_uri", None) or getattr(item, "uri", None) or ""
        )
        if not uri or (uri_filter and uri not in uri_filter):
            continue
        title = str(
            item.get("display_name") or item.get("title") or uri
            if isinstance(item, dict)
            else getattr(item, "display_name", None) or getattr(item, "title", None) or uri
        )
        sha = str(
            item.get("content_sha256") or item.get("sha256") or sha256_text(uri)
            if isinstance(item, dict)
            else getattr(item, "content_sha256", None)
            or getattr(item, "sha256", None)
            or sha256_text(uri)
        )
        kind_val = str(
            item.get("item_kind") or "WORKFLOW"
            if isinstance(item, dict)
            else getattr(item, "item_kind", None) or "WORKFLOW"
        )
        out.append(
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
    return out


def build_blackboard_slices(
    snapshots: Any, *, workspace_id: str, uri_filter: set[str]
) -> list[ContextSliceRecord]:
    """Convert blackboard snapshot records into `ContextSliceRecord` entries."""
    out: list[ContextSliceRecord] = []
    for snap in snapshots:
        step_key = getattr(snap, "step_key", "step")
        snap_id = getattr(snap, "id", "snap")
        sha = getattr(snap, "artifact_sha256", sha256_text(snap_id))
        payload = getattr(snap, "artifact_payload", {})
        uri = f"orcia://blackboard/{workspace_id}/{step_key}@{sha[:12]}"
        if uri_filter and uri not in uri_filter:
            continue
        out.append(
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
    return out


def build_permission_slices(policies: Any, *, uri_filter: set[str]) -> list[ContextSliceRecord]:
    """Convert permission broker policies into `ContextSliceRecord` entries."""
    out: list[ContextSliceRecord] = []
    for pol in policies:
        pol_key = getattr(pol, "policy_key", "policy")
        uri_pat = getattr(pol, "uri_pattern", "orcia://*")
        req_role = getattr(pol, "required_role", "TEAM_MEMBER")
        uri = f"orcia://permissions/policies/{pol_key}"
        if uri_filter and uri not in uri_filter:
            continue
        out.append(
            ContextSliceRecord(
                slice_id=f"perm-{pol_key}",
                source_uri=uri,
                source_kind="PERMISSION_POLICY",
                content_sha256=sha256_text(f"{pol_key}:{uri_pat}:{req_role}"),
                title=f"Politique Permission Broker ({pol_key})",
                structured_payload={
                    "policy_key": pol_key,
                    "uri_pattern": uri_pat,
                    "required_role": req_role,
                },
                text_excerpt=f"Policy {pol_key}: {uri_pat} requires {req_role}",
            )
        )
    return out
