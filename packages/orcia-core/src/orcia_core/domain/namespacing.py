"""Canonical Qualified Pack & Workspace Entity Namespacing (`D6.a`, `R3`, `Story 31.3`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dbos`, `redis`, `litellm`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.domain._namespacing_parser import (
    QualifiedEntityRef,
    format_agent_mention,
    format_pack_resource_uri,
    format_skill_command,
    parse_qualified_entity_ref,
)

ResolutionTier = Literal["WORKSPACE_OVERRIDE", "WORKSPACE_PACK", "SYSTEM_PACK"]


@dataclass(frozen=True, slots=True)
class WorkspaceEntityCandidate:
    """Candidate entity evaluated during flat priority-ordered workspace resolution."""

    entity_id: str
    entity_slug: str
    pack_slug: str | None
    resolution_tier: ResolutionTier
    priority_order: int | None = None
    is_active_in_workspace: bool = True
    payload: Any = None


@dataclass(frozen=True, slots=True)
class ResolvedEntityCandidate:
    """Deterministic resolution outcome including collision transparency metadata."""

    winner: WorkspaceEntityCandidate
    candidates: tuple[WorkspaceEntityCandidate, ...]
    pack_slug: str | None
    qualified_ref: str
    is_colliding: bool
    collision_pack_slugs: tuple[str, ...]
    resolution_tier: ResolutionTier


def _candidate_sort_key(
    candidate: WorkspaceEntityCandidate,
    active_pack_priorities: Mapping[str, int] | None,
) -> tuple[int, int, str, str]:
    tier_rank = {"WORKSPACE_OVERRIDE": 0, "WORKSPACE_PACK": 1, "SYSTEM_PACK": 2}[
        candidate.resolution_tier
    ]
    pack_key = (candidate.pack_slug or "").strip().lower()
    prio = 999999
    if candidate.resolution_tier == "WORKSPACE_OVERRIDE":
        prio = 0
    elif active_pack_priorities is not None and pack_key in active_pack_priorities:
        prio = active_pack_priorities[pack_key]
    elif candidate.priority_order is not None:
        prio = candidate.priority_order
    return (tier_rank, prio, pack_key, candidate.entity_id)


def rank_workspace_entity_candidates(
    ref_or_raw: str | QualifiedEntityRef,
    candidates: Iterable[WorkspaceEntityCandidate],
    *,
    default_kind: str | None = None,
    active_pack_priorities: Mapping[str, int] | None = None,
) -> tuple[QualifiedEntityRef, tuple[WorkspaceEntityCandidate, ...], tuple[str, ...]]:
    """Rank candidates by flat precedence (`WORKSPACE_OVERRIDE > priority ASC > SYSTEM`)."""
    parsed = (
        ref_or_raw
        if isinstance(ref_or_raw, QualifiedEntityRef)
        else parse_qualified_entity_ref(ref_or_raw, default_kind=default_kind)
    )
    all_slug_matches = [
        c
        for c in candidates
        if c.is_active_in_workspace and c.entity_slug.strip().lower() == parsed.entity_slug
    ]
    collision_holders: list[str] = []
    for c in sorted(
        all_slug_matches,
        key=lambda item: _candidate_sort_key(item, active_pack_priorities),
    ):
        holder = (
            "workspace"
            if c.resolution_tier == "WORKSPACE_OVERRIDE"
            else (c.pack_slug or "workspace").strip().lower()
        )
        if holder not in collision_holders:
            collision_holders.append(holder)

    if parsed.is_qualified:
        if parsed.is_workspace_scope:
            filtered = [
                c
                for c in all_slug_matches
                if c.resolution_tier == "WORKSPACE_OVERRIDE"
                or (c.pack_slug or "").strip().lower() == "workspace"
            ]
        else:
            filtered = [
                c
                for c in all_slug_matches
                if (c.pack_slug or "").strip().lower() == parsed.pack_slug
            ]
    else:
        filtered = all_slug_matches

    ordered = tuple(
        sorted(filtered, key=lambda item: _candidate_sort_key(item, active_pack_priorities))
    )
    return parsed, ordered, tuple(collision_holders)


__all__ = [
    "QualifiedEntityRef",
    "ResolutionTier",
    "ResolvedEntityCandidate",
    "WorkspaceEntityCandidate",
    "format_agent_mention",
    "format_pack_resource_uri",
    "format_skill_command",
    "parse_qualified_entity_ref",
    "rank_workspace_entity_candidates",
]
