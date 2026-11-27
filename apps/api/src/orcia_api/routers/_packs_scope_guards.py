"""Scope visibility, import & delete guards for `/api/v1/packs*` (`Story 31.7`, `<= 140 L`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._pack_composer_helpers import (
    compute_caller_composer_scopes,
    enforce_composer_scope_access,
)
from orcia_api.routers._packs_router_helpers import enforce_pack_mutation_guard
from orcia_api.routers._workspace_packs_guards import enforce_workspace_packs_access
from orcia_core.packs import (
    ApmPackCodec,
    PackBundleNotFoundError,
    PackImportService,
    PackScopeEscalationForbiddenError,
    PackScopeType,
    PackSourceOrigin,
    PackSystemDeleteForbiddenError,
)
from orcia_core.permissions.models import UserIdentity


async def filter_visible_pack_rows(
    request: Request,
    rows: list[dict[str, object]],
    *,
    persona_key: str | None = None,
) -> list[dict[str, object]]:
    """Filter `declarative_pack_bundles` rows by caller `GLOBAL | BU | TEAM | WORKSPACE` access."""
    user, is_admin, allowed_ws, allowed_orgs = await compute_caller_composer_scopes(
        request, persona_key=persona_key
    )
    if is_admin:
        return list(rows)
    ev = get_auth_service(request).evaluator
    visible: list[dict[str, object]] = []
    for row in rows:
        bkind = str(row.get("bundle_kind") or "").strip().upper()
        st = str(row.get("scope_type") or "GLOBAL").strip().upper()
        sid = str(row.get("scope_id") or "").strip()
        if st == "GLOBAL" or bkind == "SYSTEM":
            visible.append(row)
        elif st == "PRIVATE_USER":
            if sid and sid == str(user.id):
                visible.append(row)
        elif st == "WORKSPACE":
            ws_obj = ev.get_workspace(sid)
            if sid in allowed_ws or (ws_obj is not None and ws_obj.id in allowed_ws):
                visible.append(row)
        elif st in ("BU", "TEAM"):
            desc = {sid, *ev.get_descendant_org_unit_ids(sid)}
            has_ws = any(
                (ws := ev.get_workspace(wid)) is not None and ws.owner_org_unit_id in desc
                for wid in allowed_ws
            )
            if sid in allowed_orgs or has_ws:
                visible.append(row)
    return visible


async def resolve_and_authorize_import_scope(
    request: Request,
    *,
    zip_bytes: bytes,
    req_scope_type: PackScopeType | None,
    req_scope_id: str | None,
    persona_key: str | None = None,
) -> tuple[UserIdentity, PackScopeType, str]:
    """Resolve effective import `(scope_type, scope_id)` and enforce write `ScopeAccessGuard`."""
    enforce_pack_mutation_guard(request, persona_key=persona_key)
    path = str(request.url.path)
    if req_scope_type is not None and req_scope_id and req_scope_id.strip():
        eff_scope_type = req_scope_type
        eff_scope_id = req_scope_id.strip()
    else:
        bundle = ApmPackCodec().decode_zip_bytes(
            zip_bytes,
            source_origin=PackSourceOrigin.APM_ZIP,
            allow_system_kind=True,
        )
        eff_scope_type = req_scope_type or bundle.manifest.scope_type
        eff_scope_id = (req_scope_id or bundle.manifest.scope_id).strip() or "global"
        if bundle.manifest.bundle_kind.value == "SYSTEM":
            raise PackScopeEscalationForbiddenError(
                detail_override="User API imports cannot target SYSTEM bundle_kind.",
                instance=path,
            )
    if eff_scope_type == PackScopeType.GLOBAL:
        raise PackScopeEscalationForbiddenError(
            detail_override="User API imports cannot target GLOBAL scope_type.",
            instance=path,
        )
    user, resolved_scope_id = await enforce_composer_scope_access(
        request,
        scope_type=eff_scope_type.value,
        scope_id=eff_scope_id,
        require_write=True,
        persona_key=persona_key,
    )
    return user, eff_scope_type, resolved_scope_id


async def enforce_pack_bundle_delete_guard(
    request: Request,
    *,
    bundle_id: str,
    import_svc: PackImportService,
    persona_key: str | None = None,
) -> UserIdentity:
    """Enforce observer, SYSTEM, and target-scope write guards before deleting a bundle."""
    user = enforce_pack_mutation_guard(request, persona_key=persona_key)
    path = str(request.url.path)
    get_bundle_fn = getattr(import_svc, "get_bundle", None)
    bundle = await get_bundle_fn(bundle_id) if callable(get_bundle_fn) else None
    if bundle is None:
        if getattr(import_svc, "_engine", None) is not None:
            raise PackBundleNotFoundError(
                detail_override=f"Pack bundle {bundle_id!r} was not found.",
                instance=path,
            )
        return user
    if str(bundle.get("bundle_kind") or "").strip().upper() == "SYSTEM":
        raise PackSystemDeleteForbiddenError(
            detail_override=f"Built-in SYSTEM pack {bundle.get('slug')!r} cannot be deleted.",
            instance=path,
        )
    await enforce_composer_scope_access(
        request,
        scope_type=str(bundle.get("scope_type") or "GLOBAL"),
        scope_id=str(bundle.get("scope_id") or "global"),
        require_write=True,
        persona_key=persona_key,
    )
    return user


async def authorize_agents_skills_scope(
    request: Request,
    *,
    workspace_id: str | None,
    persona_key: str | None = None,
) -> tuple[str | None, bool, frozenset[str], frozenset[str]]:
    """Enforce `ScopeAccessGuard` when `workspace_id` is queried on `/agents-and-skills`."""
    if workspace_id is not None and workspace_id.strip():
        _, resolved_ws = await enforce_workspace_packs_access(
            request, workspace_id, require_write=False, persona_key=persona_key
        )
        return resolved_ws, True, frozenset({resolved_ws}), frozenset()
    _, is_admin, allowed_ws, allowed_orgs = await compute_caller_composer_scopes(
        request, persona_key=persona_key
    )
    return None, is_admin, allowed_ws, allowed_orgs


def filter_scoped_catalog_records(
    records: tuple[object, ...],
    *,
    resolved_ws: str | None,
    unrestricted: bool,
    allowed_ws: frozenset[str],
) -> list[object]:
    """Filter in-memory agents/skills by workspace ownership when `workspace_id` or non-admin."""
    if resolved_ws:
        return [
            r
            for r in records
            if not getattr(r, "owner_workspace_id", None)
            or getattr(r, "owner_workspace_id", None) == resolved_ws
        ]
    if unrestricted:
        return list(records)
    return [
        r
        for r in records
        if not getattr(r, "owner_workspace_id", None)
        or getattr(r, "owner_workspace_id", None) in allowed_ws
    ]


__all__ = [
    "authorize_agents_skills_scope",
    "enforce_pack_bundle_delete_guard",
    "filter_scoped_catalog_records",
    "filter_visible_pack_rows",
    "resolve_and_authorize_import_scope",
]
