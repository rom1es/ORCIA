"""Pure domain invariants and DFS tree helpers for multi-level `OrgUnit` hierarchy (Story 17.2).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
Supports arbitrary multi-level hierarchies (`BU` -> `Sous-BU / Pôle` -> `TEAM`) while enforcing:
- `BU` cannot have a `TEAM` parent (`OrgUnitInvalidParentKindError` -> `HTTP 422`).
- Zero cycle in `parent_id` chains (`OrgUnitHierarchyCycleError` -> `HTTP 422`).
- Duplicate slug rejection (`OrgUnitDuplicateSlugError` -> `HTTP 409`).
- Non-empty deletion rejection (`OrgUnitNotEmptyError` -> `HTTP 409`).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.permissions.errors import (
    OrgUnitBuMembersForbiddenError,
    OrgUnitDuplicateSlugError,
    OrgUnitHierarchyCycleError,
    OrgUnitInvalidParentKindError,
    OrgUnitNotEmptyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.permissions.models import OrgUnitNode, normalize_lead_user_ids
from orcia_core.permissions.org_topology import sort_org_unit_dicts_topologically
from orcia_kernel.ids import new_uuid7_str

OrgUnitKind = Literal["BU", "TEAM"]

_SLUG_CLEAN_RE = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True, slots=True)
class AttachedWorkspaceRef:
    """Read projection of a solution workspace attached to an organizational unit."""

    id: str
    slug: str
    name: str


@dataclass(frozen=True, slots=True)
class OrgUnitSummary:
    """Read/write projection of an organizational unit node (`BU` or `TEAM`)."""

    id: str
    slug: str
    name: str
    kind: OrgUnitKind
    parent_id: str | None = None
    billing_enabled: bool = True
    lead_user_id: str | None = None
    member_user_ids: tuple[str, ...] = ()
    attached_workspaces_count: int = 0
    attached_workspaces: tuple[AttachedWorkspaceRef, ...] = ()
    lead_user_ids: tuple[str, ...] = ()
    ontology_lead_user_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        leads, primary = normalize_lead_user_ids(self.lead_user_ids, self.lead_user_id)
        object.__setattr__(self, "lead_user_ids", leads)
        object.__setattr__(self, "lead_user_id", primary)
        if self.kind == "BU":
            onto_leads, _ = normalize_lead_user_ids(self.ontology_lead_user_ids, None)
        else:
            onto_leads = ()
        object.__setattr__(self, "ontology_lead_user_ids", onto_leads)


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
            raise ValidationDomainError(
                detail_override=(
                    "Les référents glossaire (ONTOLOGY_LEAD) ne peuvent être désignés "
                    "que sur une Direction (BU)."
                )
            )


def normalize_org_unit_slug(raw_slug: str | None, fallback_name: str) -> str:
    """Normalize an optional user slug or derive a clean kebab-case slug from `fallback_name`."""
    candidate = (raw_slug or "").strip().lower() or fallback_name.strip().lower()
    cleaned = _SLUG_CLEAN_RE.sub("-", candidate).strip("-")
    if not cleaned:
        raise ValidationDomainError(
            detail_override="Le nom ou l'identifiant court de l'unité ne peut pas être vide."
        )
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


def normalize_exposed_parent_id(
    raw_parent_id: str | None,
    units_by_id: Mapping[str, OrgUnitNode],
) -> str | None:
    """Map technical `ENTERPRISE` root sentinels (`orcia-root` / `orcia-enterprise`) to `None`."""
    if not raw_parent_id or raw_parent_id == "scope-global":
        return None
    parent = units_by_id.get(raw_parent_id)
    if parent is not None and parent.unit_type == "ENTERPRISE":
        return None
    return raw_parent_id


def map_node_to_kind(node: OrgUnitNode) -> OrgUnitKind:
    """Normalize internal `OrgUnitType` (`BU`/`TRIBE` vs `TEAM`/`SUB_TEAM`) to `BU | TEAM`."""
    return "BU" if node.unit_type in ("BU", "TRIBE") else "TEAM"


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
            detail_override=f"Unité parente introuvable : '{cleaned_parent}'."
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
                detail_override=(
                    f"L'identifiant court '{slug}' est déjà utilisé par « {node.name} »."
                )
            )


def assert_org_unit_deletable(
    *,
    target_name: str,
    child_units_count: int,
    attached_workspaces_count: int,
) -> None:
    """Enforce `CA-17.2.3`: reject deletion with `HTTP 409 ERR_ORG_UNIT_NOT_EMPTY` if non-empty."""
    if child_units_count <= 0 and attached_workspaces_count <= 0:
        return
    parts: list[str] = []
    if child_units_count > 0:
        unit_lbl = "sous-unités enfants" if child_units_count > 1 else "sous-unité enfant"
        parts.append(f"{child_units_count} {unit_lbl}")
    if attached_workspaces_count > 0:
        ws_lbl = (
            "espaces de travail rattachés"
            if attached_workspaces_count > 1
            else "espace de travail rattaché"
        )
        parts.append(f"{attached_workspaces_count} {ws_lbl}")
    joined = " et ".join(parts)
    raise OrgUnitNotEmptyError(
        detail_override=(
            f"Suppression refusée pour « {target_name} » : {joined}. "
            "Déplacez ou supprimez d'abord ces éléments avant de supprimer l'unité."
        )
    )


def sort_org_unit_summaries_dfs(items: Sequence[OrgUnitSummary]) -> list[OrgUnitSummary]:
    """Order `OrgUnitSummary` items in hierarchical DFS order (`BU` first, then `TEAM`)."""
    by_id = {item.id: item for item in items}
    children_by_parent: dict[str | None, list[OrgUnitSummary]] = {}
    for item in items:
        effective_parent = item.parent_id if item.parent_id in by_id else None
        children_by_parent.setdefault(effective_parent, []).append(item)

    for siblings in children_by_parent.values():
        siblings.sort(key=lambda u: (0 if u.kind == "BU" else 1, u.name.lower(), u.slug))

    ordered: list[OrgUnitSummary] = []
    visited: set[str] = set()

    def _visit(parent_key: str | None) -> None:
        for child in children_by_parent.get(parent_key, ()):
            if child.id in visited:
                continue
            visited.add(child.id)
            ordered.append(child)
            _visit(child.id)

    _visit(None)
    for item in items:
        if item.id not in visited:
            ordered.append(item)
    return ordered


def generate_new_org_unit_id() -> str:
    """Return a fresh canonical `UUIDv7` string for a newly created `OrgUnit`."""
    return new_uuid7_str()


def build_org_unit_summary(
    node: OrgUnitNode,
    units_by_id: Mapping[str, OrgUnitNode],
    *,
    attached_workspaces_count: int = 0,
    attached_workspaces: Sequence[AttachedWorkspaceRef] = (),
) -> OrgUnitSummary:
    """Convert an `OrgUnitNode` into a normalized `OrgUnitSummary`."""
    return OrgUnitSummary(
        id=node.id,
        slug=node.slug,
        name=node.name,
        kind=map_node_to_kind(node),
        parent_id=normalize_exposed_parent_id(node.parent_id, units_by_id),
        billing_enabled=node.billing_enabled,
        lead_user_id=node.lead_user_id,
        member_user_ids=node.member_user_ids,
        attached_workspaces_count=attached_workspaces_count,
        attached_workspaces=tuple(attached_workspaces),
        lead_user_ids=node.lead_user_ids,
        ontology_lead_user_ids=node.ontology_lead_user_ids,
    )


def list_evaluator_org_unit_summaries(
    org_units: Sequence[OrgUnitNode],
    workspace_owner_ids: Sequence[str],
    workspaces: Sequence[Any] | None = None,
) -> list[OrgUnitSummary]:
    """List non-enterprise `OrgUnitSummary` items in DFS order with workspace counts and refs."""
    units_by_id = {u.id: u for u in org_units}
    ws_counts: dict[str, int] = {}
    ws_refs_by_owner: dict[str, list[AttachedWorkspaceRef]] = {}

    if workspaces is not None:
        for ws in workspaces:
            owner_id = str(
                getattr(ws, "owner_org_unit_id", None)
                or (ws.get("owner_org_unit_id") if isinstance(ws, dict) else None)
                or (ws.get("ownerOrgUnitId") if isinstance(ws, dict) else None)
                or ""
            ).strip()
            if not owner_id:
                continue
            ws_id = str(
                getattr(ws, "id", None) or (ws.get("id") if isinstance(ws, dict) else "") or ""
            )
            ws_slug = str(
                getattr(ws, "slug", None) or (ws.get("slug") if isinstance(ws, dict) else "") or ""
            )
            ws_name = str(
                getattr(ws, "name", None) or (ws.get("name") if isinstance(ws, dict) else "") or ""
            )
            ws_counts[owner_id] = ws_counts.get(owner_id, 0) + 1
            ws_refs_by_owner.setdefault(owner_id, []).append(
                AttachedWorkspaceRef(id=ws_id, slug=ws_slug, name=ws_name)
            )
    else:
        for owner_id in workspace_owner_ids:
            clean_owner = str(owner_id).strip()
            if clean_owner:
                ws_counts[clean_owner] = ws_counts.get(clean_owner, 0) + 1

    for refs in ws_refs_by_owner.values():
        refs.sort(key=lambda r: (r.name.lower(), r.slug.lower()))

    summaries = [
        build_org_unit_summary(
            node,
            units_by_id,
            attached_workspaces_count=ws_counts.get(node.id, 0),
            attached_workspaces=ws_refs_by_owner.get(node.id, ()),
        )
        for node in org_units
        if node.unit_type != "ENTERPRISE"
    ]
    return sort_org_unit_summaries_dfs(summaries)


__all__ = [
    "AttachedWorkspaceRef",
    "OrgUnitKind",
    "OrgUnitSummary",
    "assert_bu_has_no_members",
    "assert_bu_only_ontology_leads",
    "assert_unique_org_unit_slug",
    "build_org_unit_summary",
    "list_evaluator_org_unit_summaries",
    "normalize_member_user_ids",
    "normalize_org_unit_slug",
    "sort_org_unit_dicts_topologically",
    "sort_org_unit_summaries_dfs",
    "validate_org_unit_hierarchy",
]
