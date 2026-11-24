"""OrgUnit summary models, deletion invariants & DFS projections (`Story 17.2`)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.permissions._permissions_locales import format_org_unit_deletion_details
from orcia_core.permissions.errors import OrgUnitNotEmptyError
from orcia_core.permissions.models import OrgUnitNode, normalize_lead_user_ids
from orcia_kernel.ids import new_uuid7_str

OrgUnitKind = Literal["BU", "TEAM"]


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


def assert_org_unit_deletable(
    *,
    target_name: str,
    child_units_count: int,
    attached_workspaces_count: int,
) -> None:
    """Enforce `CA-17.2.3`: reject deletion with `HTTP 409 ERR_ORG_UNIT_NOT_EMPTY` if non-empty."""
    if child_units_count <= 0 and attached_workspaces_count <= 0:
        return
    details = format_org_unit_deletion_details(
        child_units_count=child_units_count,
        attached_workspaces_count=attached_workspaces_count,
    )
    raise OrgUnitNotEmptyError(
        detail_code="ERR_ORG_UNIT_NOT_EMPTY_DETAIL",
        detail_params={"target_name": target_name, "details": details},
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

    def _visit(parent_id: str | None) -> None:
        for child in children_by_parent.get(parent_id, ()):
            ordered.append(child)
            _visit(child.id)

    _visit(None)
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
    "assert_org_unit_deletable",
    "build_org_unit_summary",
    "generate_new_org_unit_id",
    "list_evaluator_org_unit_summaries",
    "map_node_to_kind",
    "normalize_exposed_parent_id",
    "sort_org_unit_summaries_dfs",
]
