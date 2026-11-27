"""Scope visibility helpers for Pack Composer target resolution (`Story 31.5`, `<= 140 L`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_core.packs._internal._sql_workspace_pack_queries import is_bundle_visible_with_ancestors
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError


def is_ontology_level_visible(
    *,
    level: str | None,
    scope_id: str | None,
    draft_scope_type: str,
    draft_scope_id: str,
    ancestor_orgs: frozenset[str],
) -> bool:
    """Verify an ontology level/scope is visible inside `draft_scope_type`/`draft_scope_id`."""
    lvl = str(level or "").strip().upper()
    sid = str(scope_id or "").strip()
    if not lvl or lvl in ("1_ENTERPRISE", "GLOBAL"):
        return True
    if draft_scope_type == "GLOBAL":
        return False
    if lvl in ("2_DOMAIN", "2_BU", "2_ORG_UNIT", "TEAM", "3_TEAM"):
        if not sid:
            return False
        if draft_scope_type == "WORKSPACE":
            return sid in ancestor_orgs
        return sid == draft_scope_id or sid in ancestor_orgs
    return draft_scope_type == "WORKSPACE" and sid == draft_scope_id


async def assert_bundle_visible_conn(
    conn: AsyncConnection,
    *,
    pack_bundle_id: str | None,
    draft_scope_type: str,
    draft_scope_id: str,
    ancestor_orgs: frozenset[str],
    instance: str | None,
) -> None:
    """Verify source pack bundle is visible to `draft_scope_type`/`draft_scope_id`."""
    if not pack_bundle_id:
        return
    brow = (
        (
            await conn.execute(
                sa.text(
                    "SELECT scope_type, scope_id FROM declarative_pack_bundles "
                    "WHERE id = CAST(:bid AS uuid) LIMIT 1"
                ),
                {"bid": pack_bundle_id},
            )
        )
        .mappings()
        .first()
    )
    if brow is None:
        return
    b_type = str(brow["scope_type"]).upper()
    b_id = str(brow["scope_id"])
    if b_type == "GLOBAL":
        return
    if draft_scope_type == "WORKSPACE":
        visible = is_bundle_visible_with_ancestors(
            scope_type=b_type,
            scope_id=b_id,
            ws_uuid=draft_scope_id,
            ancestor_org_unit_ids=ancestor_orgs,
        )
    elif draft_scope_type in ("BU", "TEAM"):
        visible = b_type in ("BU", "TEAM") and (b_id == draft_scope_id or b_id in ancestor_orgs)
    else:
        visible = False
    if not visible:
        raise ScopeAccessDeniedError(
            detail_override="Target entity belongs to a pack outside this draft scope.",
            instance=instance,
        )


def assert_standalone_wf_vsm_visible(
    *,
    pack_id: str,
    spec: dict[str, Any],
    draft_scope_type: str,
    draft_scope_id: str,
    ancestor_orgs: frozenset[str],
    instance: str | None,
) -> None:
    """Enforce standalone `WORKFLOW_V2` / `VSM_V2` workspace or org-unit scope isolation."""
    ws_owner = str(spec.get("owner_workspace_id") or spec.get("workspace_id") or "").strip()
    if ws_owner and (draft_scope_type != "WORKSPACE" or ws_owner != draft_scope_id):
        raise ScopeAccessDeniedError(
            detail_override="Cannot add cross-workspace workflow/VSM to draft pack.",
            instance=instance,
        )
    pid_low = pack_id.strip().lower()
    for pfx in ("workspace:", "ws:"):
        if pid_low.startswith(pfx):
            owner_ws = pack_id.strip()[len(pfx) :].split(":", 1)[0]
            if owner_ws and (draft_scope_type != "WORKSPACE" or owner_ws != draft_scope_id):
                raise ScopeAccessDeniedError(
                    detail_override="Cannot add cross-workspace workflow/VSM to draft pack.",
                    instance=instance,
                )
    stype = str(spec.get("scope_type") or "").strip().upper()
    sid = str(spec.get("scope_id") or "").strip()
    if stype and sid:
        if stype == "WORKSPACE" and (draft_scope_type != "WORKSPACE" or sid != draft_scope_id):
            raise ScopeAccessDeniedError(
                detail_override="Cannot add cross-workspace workflow/VSM to draft pack.",
                instance=instance,
            )
        if stype in ("BU", "TEAM") and (
            draft_scope_type == "GLOBAL" or (sid != draft_scope_id and sid not in ancestor_orgs)
        ):
            raise ScopeAccessDeniedError(
                detail_override="Cannot add cross-org workflow/VSM to draft pack.",
                instance=instance,
            )


async def pick_first_visible(rows: Sequence[Any], validator: Any) -> Any:
    """Return the first row passing `validator`, or raise the last `ScopeAccessDeniedError`."""
    last_denied: ScopeAccessDeniedError | None = None
    for raw in rows:
        try:
            await validator(raw)
            return raw
        except ScopeAccessDeniedError as exc:
            last_denied = exc
    if last_denied is not None:
        raise last_denied
    raise ResourceNotFoundError()


__all__ = [
    "assert_bundle_visible_conn",
    "assert_standalone_wf_vsm_visible",
    "is_ontology_level_visible",
    "pick_first_visible",
]
