"""Qualified Pack & Workspace Entity Namespacing Helpers for Agents & Skills (`Story 31.3`).

Zero framework imports; delegates pure parsing & flat ranking to `orcia_core.domain.namespacing`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from orcia_core.domain.namespacing import (
    ResolutionTier,
    ResolvedEntityCandidate,
    WorkspaceEntityCandidate,
    format_agent_mention,
    format_skill_command,
    parse_qualified_entity_ref,
    rank_workspace_entity_candidates,
)
from orcia_core.orchestration.agents_and_skills_models import (
    ManagedAgentRecord,
    ManagedSkillRecord,
)


def infer_record_pack_slug_and_tier(
    *,
    entity_id: str,
    slug: str,
    uri: str,
    visibility_scope: str,
    source_pack_key: str | None,
    explicit_pack_slug: str | None = None,
    explicit_tier: ResolutionTier | None = None,
    bundle_kind: str | None = None,
) -> tuple[str | None, ResolutionTier]:
    """Infer `(pack_slug, resolution_tier)` cleanly without mutating upstream identifiers."""
    _ = slug
    default_pack_tier: ResolutionTier = (
        "SYSTEM_PACK" if (bundle_kind or "").upper() == "SYSTEM" else "WORKSPACE_PACK"
    )
    if explicit_pack_slug:
        return explicit_pack_slug.strip().lower(), explicit_tier or default_pack_tier
    if visibility_scope == "PACK":
        low_uri = (uri or "").strip().lower()
        if low_uri.startswith(("orcia://packs/", "pack://")):
            parsed = parse_qualified_entity_ref(low_uri)
            if parsed.pack_slug and parsed.pack_slug != "workspace":
                return parsed.pack_slug, explicit_tier or default_pack_tier
        if ":" in entity_id:
            prefix = entity_id.split(":", 1)[0].strip().lower()
            if prefix:
                return prefix, explicit_tier or default_pack_tier
        if source_pack_key and source_pack_key.strip():
            raw = source_pack_key.strip().lower().removeprefix("orcia-pack-")
            return raw, explicit_tier or default_pack_tier
    return None, explicit_tier or "WORKSPACE_OVERRIDE"


def _to_candidate(
    record: ManagedAgentRecord | ManagedSkillRecord,
    *,
    active_pack_priorities: Mapping[str, int] | None,
) -> WorkspaceEntityCandidate:
    entity_id = record.agent_id if isinstance(record, ManagedAgentRecord) else record.skill_id
    pack_slug, default_tier = infer_record_pack_slug_and_tier(
        entity_id=entity_id,
        slug=record.slug,
        uri=record.uri,
        visibility_scope=record.visibility_scope,
        source_pack_key=record.source_pack_key,
        explicit_pack_slug=record.pack_slug,
        explicit_tier=record.resolution_tier if record.pack_slug else None,
        bundle_kind="SYSTEM" if record.resolution_tier == "SYSTEM_PACK" else None,
    )
    prio = (
        active_pack_priorities.get(pack_slug, None)
        if active_pack_priorities and pack_slug
        else None
    )
    tier: ResolutionTier = (
        "WORKSPACE_PACK"
        if pack_slug and active_pack_priorities and pack_slug in active_pack_priorities
        else default_tier
    )
    return WorkspaceEntityCandidate(
        entity_id=entity_id,
        entity_slug=record.slug,
        pack_slug=pack_slug,
        resolution_tier=tier,
        priority_order=prio,
        is_active_in_workspace=record.enabled_in_workspace,
        payload=record,
    )


def annotate_skills_and_agents_namespacing(
    skills: tuple[ManagedSkillRecord, ...],
    agents: tuple[ManagedAgentRecord, ...],
    *,
    active_pack_priorities: Mapping[str, int] | None = None,
) -> tuple[tuple[ManagedSkillRecord, ...], tuple[ManagedAgentRecord, ...]]:
    """Populate `pack_slug`, `qualified_ref`, `is_colliding`, `collision_pack_slugs`, and tier."""
    skill_cands = [_to_candidate(s, active_pack_priorities=active_pack_priorities) for s in skills]
    agent_cands = [_to_candidate(a, active_pack_priorities=active_pack_priorities) for a in agents]

    annotated_skills = tuple(
        replace(
            sk,
            pack_slug=cand.pack_slug,
            qualified_ref=format_skill_command(
                sk.slug, pack_slug=cand.pack_slug, workspace_scoped=(cand.pack_slug is None)
            ),
            is_colliding=len(holders) > 1,
            collision_pack_slugs=holders,
            resolution_tier=cand.resolution_tier,
        )
        for sk, cand in zip(skills, skill_cands, strict=True)
        for _, _, holders in [
            rank_workspace_entity_candidates(
                sk.slug,
                skill_cands,
                default_kind="skills",
                active_pack_priorities=active_pack_priorities,
            )
        ]
    )
    annotated_agents = tuple(
        replace(
            ag,
            pack_slug=cand.pack_slug,
            qualified_ref=format_agent_mention(
                ag.slug, pack_slug=cand.pack_slug, workspace_scoped=(cand.pack_slug is None)
            ),
            is_colliding=len(holders) > 1,
            collision_pack_slugs=holders,
            resolution_tier=cand.resolution_tier,
        )
        for ag, cand in zip(agents, agent_cands, strict=True)
        for _, _, holders in [
            rank_workspace_entity_candidates(
                ag.slug,
                agent_cands,
                default_kind="agents",
                active_pack_priorities=active_pack_priorities,
            )
        ]
    )
    return annotated_skills, annotated_agents


def _resolve_entity_reference(
    records: Sequence[ManagedAgentRecord | ManagedSkillRecord],
    raw_ref: str,
    *,
    default_kind: str,
    active_pack_priorities: Mapping[str, int] | None = None,
) -> ResolvedEntityCandidate | None:
    cleaned = (raw_ref or "").strip()
    if not cleaned:
        return None
    formatter = format_skill_command if default_kind == "skills" else format_agent_mention
    cands = [_to_candidate(r, active_pack_priorities=active_pack_priorities) for r in records]
    for rec, cand in zip(records, cands, strict=True):
        if not cand.is_active_in_workspace:
            continue
        if cand.entity_id.lower() == cleaned.lower():
            _, _, holders = rank_workspace_entity_candidates(
                rec.slug,
                cands,
                default_kind=default_kind,
                active_pack_priorities=active_pack_priorities,
            )
            return ResolvedEntityCandidate(
                winner=cand,
                candidates=(cand,),
                pack_slug=cand.pack_slug,
                qualified_ref=formatter(
                    rec.slug, pack_slug=cand.pack_slug, workspace_scoped=(cand.pack_slug is None)
                ),
                is_colliding=len(holders) > 1,
                collision_pack_slugs=holders,
                resolution_tier=cand.resolution_tier,
            )
    _, ordered, holders = rank_workspace_entity_candidates(
        cleaned, cands, default_kind=default_kind, active_pack_priorities=active_pack_priorities
    )
    if not ordered:
        return None
    winner = ordered[0]
    return ResolvedEntityCandidate(
        winner=winner,
        candidates=ordered,
        pack_slug=winner.pack_slug,
        qualified_ref=formatter(
            winner.entity_slug,
            pack_slug=winner.pack_slug,
            workspace_scoped=(winner.pack_slug is None),
        ),
        is_colliding=len(holders) > 1,
        collision_pack_slugs=holders,
        resolution_tier=winner.resolution_tier,
    )


def resolve_agent_reference(
    agents: tuple[ManagedAgentRecord, ...],
    raw_ref: str,
    *,
    active_pack_priorities: Mapping[str, int] | None = None,
) -> ResolvedEntityCandidate | None:
    """Resolve an agent reference (`@pack/slug`, `pack:slug`, `@slug`, `agent_id`, or URI)."""
    return _resolve_entity_reference(
        agents, raw_ref, default_kind="agents", active_pack_priorities=active_pack_priorities
    )


def resolve_skill_reference(
    skills: tuple[ManagedSkillRecord, ...],
    raw_ref: str,
    *,
    active_pack_priorities: Mapping[str, int] | None = None,
) -> ResolvedEntityCandidate | None:
    """Resolve a skill reference (`/pack/slug`, `pack:slug`, `/slug`, `skill_id`, or URI)."""
    return _resolve_entity_reference(
        skills, raw_ref, default_kind="skills", active_pack_priorities=active_pack_priorities
    )


__all__ = [
    "annotate_skills_and_agents_namespacing",
    "infer_record_pack_slug_and_tier",
    "resolve_agent_reference",
    "resolve_skill_reference",
]
