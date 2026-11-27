"""Transitive dependency closure analyzer & auto-expander (`Story 31.5`, `<= 270 L`)."""

from __future__ import annotations

from collections import deque
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.packs._internal._pack_closure_helpers import (
    ExtractedRef,
    aliases_for_member,
    extract_refs_from_payload,
    fk_uuid_for_member,
    lint_prose_bare_handles,
    normalized_lookup_candidates,
)
from orcia_core.packs._internal._sql_pack_composer_hydration import decode_json_dict
from orcia_core.packs._internal._sql_pack_composer_members import insert_draft_membership_conn
from orcia_core.packs._internal._sql_pack_composer_targets import (
    ResolvedDraftTarget,
    resolve_draft_target_conn,
)
from orcia_core.packs._internal._sql_workspace_pack_queries import (
    load_ancestor_org_unit_ids_conn,
    resolve_workspace_identity_conn,
)
from orcia_core.packs.composer_models import (
    ClosureMissingDependency,
    PackClosureReport,
    PackDraftMemberInput,
    PackDraftMemberView,
    ProseLintWarning,
)
from orcia_core.packs.errors import PackClosureIncompleteError
from orcia_core.packs.models import PackDraftEntityType
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError

_PUBLISHABLE_STATUSES: frozenset[str] = frozenset({"ACTIVE", "PUBLISHED", "VALIDATED_TEST_BENCH"})


async def _load_entity_payload_conn(
    conn: AsyncConnection, *, etype: PackDraftEntityType, fk_uuid: str
) -> dict[str, Any]:
    if etype in (
        PackDraftEntityType.AGENT,
        PackDraftEntityType.SKILL,
        PackDraftEntityType.INSTRUCTION,
        PackDraftEntityType.HELP_ARTICLE,
    ):
        row = (
            await conn.execute(
                sa.text(
                    "SELECT title, metadata_jsonb FROM catalog_items WHERE id = CAST(:uid AS uuid)"
                ),
                {"uid": fk_uuid},
            )
        ).first()
        if row is None:
            return {}
        return {"title": str(row[0]), "meta": decode_json_dict(row[1])}
    if etype == PackDraftEntityType.WORKFLOW_V2:
        row = (
            await conn.execute(
                sa.text(
                    "SELECT status, spec_jsonb FROM workflow_definitions_v2 "
                    "WHERE id = CAST(:uid AS uuid)"
                ),
                {"uid": fk_uuid},
            )
        ).first()
        return {"status": str(row[0]), "spec": decode_json_dict(row[1])} if row else {}
    if etype == PackDraftEntityType.VSM_V2:
        row = (
            await conn.execute(
                sa.text("SELECT spec_jsonb FROM vsm_definitions_v2 WHERE id = CAST(:uid AS uuid)"),
                {"uid": fk_uuid},
            )
        ).first()
        return {"spec": decode_json_dict(row[0])} if row else {}
    if etype == PackDraftEntityType.ONTOLOGY_RELATION:
        row = (
            await conn.execute(
                sa.text(
                    "SELECT source_concept_id::text, target_concept_id::text "
                    "FROM ontology_relations WHERE id = CAST(:uid AS uuid)"
                ),
                {"uid": fk_uuid},
            )
        ).first()
        return {"source_concept_id": str(row[0]), "target_concept_id": str(row[1])} if row else {}
    if etype == PackDraftEntityType.ONTOLOGY_AXIOM:
        row = (
            await conn.execute(
                sa.text(
                    "SELECT concept_id::text FROM ontology_axioms WHERE id = CAST(:uid AS uuid)"
                ),
                {"uid": fk_uuid},
            )
        ).first()
        return {"concept_id": str(row[0])} if row else {}
    return {}


async def _try_resolve_dependency(
    conn: AsyncConnection,
    ref: ExtractedRef,
    *,
    scope_type: str,
    scope_id: str,
    ancestor_orgs: frozenset[str],
) -> ResolvedDraftTarget | None:
    for cand in normalized_lookup_candidates(ref.lookup_key):
        try:
            return await resolve_draft_target_conn(
                conn,
                PackDraftMemberInput(entity_type=ref.entity_type, entity_id=cand),
                draft_scope_type=scope_type,
                draft_scope_id=scope_id,
                ancestor_orgs=ancestor_orgs,
            )
        except (ResourceNotFoundError, ScopeAccessDeniedError):
            continue
    return None


async def analyze_and_optionally_expand_closure_conn(
    conn: AsyncConnection,
    *,
    bundle_id: str,
    scope_type: str,
    scope_id: str,
    members: list[PackDraftMemberView],
    auto_include_dependencies: bool = False,
    can_mutate_draft: bool = False,
    require_active: bool = False,
    fail_on_incomplete: bool = False,
    instance: str | None = None,
) -> PackClosureReport:
    """Analyze transitive closure over pack members, optionally auto-including in-scope deps."""
    orgs: frozenset[str] = frozenset()
    if scope_type == "WORKSPACE":
        _, ws_org = await resolve_workspace_identity_conn(conn, scope_id, instance=instance)
        orgs = await load_ancestor_org_unit_ids_conn(conn, ws_org)
    elif scope_type in ("BU", "TEAM"):
        orgs = await load_ancestor_org_unit_ids_conn(conn, scope_id)

    included_aliases: dict[PackDraftEntityType, set[str]] = {t: set() for t in PackDraftEntityType}
    non_active: list[ClosureMissingDependency] = []
    queue: deque[tuple[PackDraftEntityType, str, str, str]] = deque()
    agent_slugs: set[str] = set()
    skill_slugs: set[str] = set()
    prose_bodies: list[tuple[str, str, str]] = []

    for m in members:
        uid = fk_uuid_for_member(m)
        included_aliases[m.entity_type].update(
            aliases_for_member(m.entity_type, m.entity_id, m.entity_slug)
        )
        if uid:
            included_aliases[m.entity_type].add(uid.lower())
        if m.entity_type == PackDraftEntityType.AGENT:
            agent_slugs.add(m.entity_slug)
        elif m.entity_type == PackDraftEntityType.SKILL:
            skill_slugs.add(m.entity_slug)
        if str(m.lifecycle_status or "").upper() not in _PUBLISHABLE_STATUSES:
            non_active.append(
                ClosureMissingDependency(
                    entity_type=m.entity_type.value,
                    entity_id=m.entity_id,
                    reason="NON_ACTIVE_STATUS",
                    referenced_by="PACK_MEMBER",
                )
            )
        if uid:
            queue.append((m.entity_type, m.entity_id, m.entity_slug, uid))

    missing: list[ClosureMissingDependency] = []
    seen_missing: set[tuple[str, str]] = set()
    auto_included = 0

    while queue:
        etype, _eid, eslug, uid = queue.popleft()
        payload = await _load_entity_payload_conn(conn, etype=etype, fk_uuid=uid)
        if etype in (PackDraftEntityType.AGENT, PackDraftEntityType.SKILL):
            instr = str((payload.get("meta") or {}).get("instructions") or "")
            if instr:
                prose_bodies.append((etype.value, eslug, instr))
        for ref in extract_refs_from_payload(etype, eslug, payload):
            cands = [c.lower() for c in normalized_lookup_candidates(ref.lookup_key)]
            if any(c in included_aliases[ref.entity_type] for c in cands):
                continue
            resolved = await _try_resolve_dependency(
                conn, ref, scope_type=scope_type, scope_id=scope_id, ancestor_orgs=orgs
            )
            if resolved is not None and auto_include_dependencies and can_mutate_draft:
                await insert_draft_membership_conn(conn, draft_bundle_id=bundle_id, target=resolved)
                included_aliases[resolved.entity_type].update(
                    aliases_for_member(
                        resolved.entity_type, resolved.entity_id, resolved.entity_slug
                    )
                )
                included_aliases[resolved.entity_type].add(resolved.fk_uuid.lower())
                auto_included += 1
                queue.append(
                    (
                        resolved.entity_type,
                        resolved.entity_id,
                        resolved.entity_slug,
                        resolved.fk_uuid,
                    )
                )
                if resolved.entity_type == PackDraftEntityType.AGENT:
                    agent_slugs.add(resolved.entity_slug)
                elif resolved.entity_type == PackDraftEntityType.SKILL:
                    skill_slugs.add(resolved.entity_slug)
                if str(resolved.lifecycle_status or "").upper() not in _PUBLISHABLE_STATUSES:
                    non_active.append(
                        ClosureMissingDependency(
                            entity_type=resolved.entity_type.value,
                            entity_id=resolved.entity_id,
                            reason="NON_ACTIVE_STATUS",
                            referenced_by=ref.referenced_by,
                        )
                    )
                continue
            miss_key = (ref.entity_type.value, ref.lookup_key)
            if miss_key not in seen_missing:
                seen_missing.add(miss_key)
                reason = "MISSING_FROM_DRAFT" if resolved is not None else "TARGET_NOT_FOUND"
                missing.append(
                    ClosureMissingDependency(
                        entity_type=ref.entity_type.value,
                        entity_id=ref.lookup_key,
                        reason=reason,
                        referenced_by=ref.referenced_by,
                    )
                )

    warnings: list[ProseLintWarning] = []
    for et_str, e_slug, body in prose_bodies:
        warnings.extend(
            lint_prose_bare_handles(
                et_str,
                e_slug,
                body,
                known_agent_slugs=frozenset(agent_slugs),
                known_skill_slugs=frozenset(skill_slugs),
            )
        )
    is_complete = not missing and (not require_active or not non_active)
    if fail_on_incomplete and not is_complete:
        combined = [m.model_dump() for m in (missing + (non_active if require_active else []))]
        raise PackClosureIncompleteError(missing_dependencies=combined, instance=instance)
    return PackClosureReport(
        complete=is_complete,
        missing_dependencies=missing,
        non_active_dependencies=non_active,
        prose_lint_warnings=warnings,
        auto_included_count=auto_included,
    )


__all__ = ["analyze_and_optionally_expand_closure_conn"]
