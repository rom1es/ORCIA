"""Pure domain invariants and DFS tree helpers for multi-level `OrgUnit` hierarchy (Story 17.2).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from orcia_core.permissions._org_hierarchy_summary import (
    AttachedWorkspaceRef,
    OrgUnitKind,
    OrgUnitSummary,
    assert_org_unit_deletable,
    build_org_unit_summary,
    generate_new_org_unit_id,
    list_evaluator_org_unit_summaries,
    map_node_to_kind,
    normalize_exposed_parent_id,
    sort_org_unit_summaries_dfs,
)
from orcia_core.permissions.errors import (
    OrgUnitBuMembersForbiddenError,
    OrgUnitDuplicateSlugError,
    OrgUnitHierarchyCycleError,
    OrgUnitInvalidParentKindError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.models import OrgUnitNode
from orcia_core.permissions.org_topology import sort_org_unit_dicts_topologically

_SLUG_CLEAN_RE = re.compile(r"[^a-z0-9-]+")


def assert_bu_has_no_members(kind_or_type: str, member_user_ids: Sequence[str] | None) -> None:
    """Reject non-empty members on BU units (`ERR_ORG_UNIT_BU_MEMBERS_FORBIDDEN`)."""
    if str(kind_or_type).upper() in ("BU", "TRIBE") and member_user_ids:
        cleaned = [m for m in member_user_ids if str(m).strip()]
        if cleaned:
            raise OrgUnitBuMembersForbiddenError()


def assert_bu_only_ontology_leads(
    kind_or_type: str, ontology_lead_user_ids: Sequence[str] | None
) -> None:
    """Reject non-empty ontology leads on TEAM units (`HTTP 422`)."""
    if str(kind_or_type).upper() not in ("BU", "TRIBE") and ontology_lead_user_ids:
        cleaned = [m for m in ontology_lead_user_ids if str(m).strip()]
        if cleaned:
            raise ValidationDomainError(detail_code="ERR_ORG_ONTOLOGY_LEAD_BU_ONLY")


def normalize_org_unit_slug(raw_slug: str | None, fallback_name: str) -> str:
    """Normalize an optional user slug or derive a clean kebab-case slug from `fallback_name`."""
    candidate = (raw_slug or "").strip().lower() or fallback_name.strip().lower()
    cleaned = _SLUG_CLEAN_RE.sub("-", candidate).strip("-")
    if not cleaned:
        raise ValidationDomainError(detail_code="ERR_ORG_UNIT_EMPTY_NAME_OR_SLUG")
    return cleaned[:120]


def normalize_member_user_ids(raw_members: Sequence[str] | None) -> tuple[str, ...]:
    """Deduplicate and trim member user identifiers while preserving insertion order."""
    if not raw_members:
        return ()
    seen: set[str] = set()
    ordered: list[str] = []
    for item in raw_members:
        cleaned = str(item).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return tuple(ordered)


def validate_org_unit_hierarchy(
    *,
    unit_id: str | None,
    kind: OrgUnitKind,
    parent_id: str | None,
    units_by_id: Mapping[str, OrgUnitNode],
) -> str | None:
    """Validate parent existence, `BU`-under-`TEAM` prohibition, and cycle absence."""
    cleaned_parent = (parent_id or "").strip() or None
    if cleaned_parent is None or cleaned_parent == "scope-global":
        return None

    if unit_id is not None and cleaned_parent == unit_id:
        raise OrgUnitHierarchyCycleError()

    parent = units_by_id.get(cleaned_parent)
    if parent is None:
        parent = next(
            (
                u
                for u in units_by_id.values()
                if u.slug == cleaned_parent and u.unit_type != "ENTERPRISE"
            ),
            None,
        )
    if parent is None or parent.unit_type == "ENTERPRISE":
        raise ResourceNotFoundError(
            detail_code="ERR_ORG_UNIT_PARENT_NOT_FOUND",
            detail_params={"parent_ref": cleaned_parent},
        )

    if kind == "BU" and parent.unit_type in ("TEAM", "SUB_TEAM"):
        raise OrgUnitInvalidParentKindError()

    if unit_id is not None:
        visited: set[str] = {unit_id}
        cursor: OrgUnitNode | None = parent
        while cursor is not None:
            if cursor.id in visited:
                raise OrgUnitHierarchyCycleError()
            visited.add(cursor.id)
            next_pid = cursor.parent_id
            cursor = units_by_id.get(next_pid) if next_pid else None

    return parent.id


def assert_unique_org_unit_slug(
    slug: str,
    units_by_id: Mapping[str, OrgUnitNode],
    *,
    exclude_unit_id: str | None = None,
) -> None:
    """Reject duplicate slugs across active organizational units (`HTTP 409`)."""
    for node in units_by_id.values():
        if node.unit_type == "ENTERPRISE":
            continue
        if exclude_unit_id is not None and node.id == exclude_unit_id:
            continue
        if node.slug == slug:
            raise OrgUnitDuplicateSlugError(
                detail_code="ERR_ORG_UNIT_DUPLICATE_SLUG_OWNED",
                detail_params={"slug": slug, "owner_name": node.name},
            )


__all__ = [
    "AttachedWorkspaceRef",
    "OrgUnitKind",
    "OrgUnitSummary",
    "assert_bu_has_no_members",
    "assert_bu_only_ontology_leads",
    "assert_org_unit_deletable",
    "assert_unique_org_unit_slug",
    "build_org_unit_summary",
    "generate_new_org_unit_id",
    "list_evaluator_org_unit_summaries",
    "map_node_to_kind",
    "normalize_exposed_parent_id",
    "normalize_member_user_ids",
    "normalize_org_unit_slug",
    "sort_org_unit_dicts_topologically",
    "sort_org_unit_summaries_dfs",
    "validate_org_unit_hierarchy",
]
