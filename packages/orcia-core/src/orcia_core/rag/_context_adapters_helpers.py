"""Slice and Vector Hit Mapping Helpers for `context_adapters.py` (`DEC-CTX-01`)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from orcia_kernel.context_ports import ContextSliceRecord, VectorSearchHitRecord


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
