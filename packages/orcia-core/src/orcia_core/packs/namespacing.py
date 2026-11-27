"""Qualified Pack & Workspace Entity Namespacing (`D6.a`, `R3`, `Story 31.3`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dbos`, `redis`, `litellm`).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from orcia_core.domain.namespacing import (
    QualifiedEntityRef,
    ResolutionTier,
    ResolvedEntityCandidate,
    WorkspaceEntityCandidate,
    format_agent_mention,
    format_pack_resource_uri,
    format_skill_command,
    parse_qualified_entity_ref,
    rank_workspace_entity_candidates,
)
from orcia_core.packs.errors import PackEntityCollisionError
from orcia_kernel.errors import ResourceNotFoundError


def _format_candidate_ref(
    candidate: WorkspaceEntityCandidate,
    *,
    kind: str | None,
) -> str:
    pack_slug = (
        "workspace"
        if candidate.resolution_tier == "WORKSPACE_OVERRIDE"
        else (candidate.pack_slug or "workspace")
    )
    if kind == "skills":
        return format_skill_command(
            candidate.entity_slug,
            pack_slug=pack_slug,
            workspace_scoped=(pack_slug == "workspace"),
        )
    if kind in ("workflows", "vsm", "gates", "ontology", "instructions", "policies", "help"):
        return format_pack_resource_uri(pack_slug, kind, candidate.entity_slug)
    return format_agent_mention(
        candidate.entity_slug,
        pack_slug=pack_slug,
        workspace_scoped=(pack_slug == "workspace"),
    )


def resolve_workspace_entity_candidates(
    raw_ref: str,
    candidates: Iterable[WorkspaceEntityCandidate],
    *,
    default_kind: str | None = None,
    active_pack_priorities: Mapping[str, int] | None = None,
    strict_disambiguation: bool = False,
    instance: str | None = None,
) -> ResolvedEntityCandidate:
    """Resolve a qualified or bare entity ref in flat workspace priority order.

    Precedence:
    1. `WORKSPACE_OVERRIDE` (`pack_bundle_id IS NULL` for that workspace),
    2. `WORKSPACE_PACK` ordered by `workspace_pack_activations.priority_order ASC`,
    3. `SYSTEM_PACK` fallback (`bundle_kind = 'SYSTEM'`).
    """
    parsed, ordered, collision_holders = rank_workspace_entity_candidates(
        raw_ref,
        candidates,
        default_kind=default_kind,
        active_pack_priorities=active_pack_priorities,
    )
    if not ordered:
        raise ResourceNotFoundError(
            detail_override=f"Entity reference {raw_ref!r} not found in workspace scope.",
            instance=instance,
        )

    is_colliding = len(collision_holders) > 1
    if strict_disambiguation and not parsed.is_qualified and len(ordered) > 1:
        has_workspace_override = ordered[0].resolution_tier == "WORKSPACE_OVERRIDE"
        if not has_workspace_override:
            formatted_candidates = [
                _format_candidate_ref(c, kind=parsed.kind or default_kind) for c in ordered
            ]
            raise PackEntityCollisionError(
                entity_ref=raw_ref,
                candidates=formatted_candidates,
                instance=instance,
            )

    winner = ordered[0]
    winner_pack = (
        None
        if winner.resolution_tier == "WORKSPACE_OVERRIDE"
        else (winner.pack_slug or "").strip().lower() or None
    )
    qualified_ref = _format_candidate_ref(winner, kind=parsed.kind or default_kind)
    return ResolvedEntityCandidate(
        winner=winner,
        candidates=ordered,
        pack_slug=winner_pack,
        qualified_ref=qualified_ref,
        is_colliding=is_colliding,
        collision_pack_slugs=collision_holders,
        resolution_tier=winner.resolution_tier,
    )


__all__ = [
    "PackEntityCollisionError",
    "QualifiedEntityRef",
    "ResolutionTier",
    "ResolvedEntityCandidate",
    "WorkspaceEntityCandidate",
    "format_agent_mention",
    "format_pack_resource_uri",
    "format_skill_command",
    "parse_qualified_entity_ref",
    "resolve_workspace_entity_candidates",
]
