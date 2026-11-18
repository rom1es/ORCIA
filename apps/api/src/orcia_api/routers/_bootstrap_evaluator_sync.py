"""Synchronization helper between `platform_setup_snapshot` and `MatrixPermissionEvaluator`."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_core import bootstrap as bm
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    OrgUnitNode,
    OrgUnitType,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
    WorkspaceVisibilityMode,
)
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.api.bootstrap.evaluator_sync")

_SEEDED_WORKSPACE_IDS: frozenset[str] = frozenset(
    {
        "0192c4e0-0000-7000-8000-000000000201",
        "0192c4e0-0000-7000-8000-000000000202",
        "0192c4e0-0000-7000-8000-000000000203",
    }
)
_ROOT_ENTERPRISE_ID = "0192c4e0-0000-7000-8000-000000000101"
_VALID_OU_TYPES: frozenset[str] = frozenset({"ENTERPRISE", "BU", "TRIBE", "TEAM", "SUB_TEAM"})


def _resolve_workspace_owner_user(
    request: Request, first_admin: bm.FirstPlatformAdminRecord | None
) -> UserIdentity | None:
    auth_svc = get_auth_service(request)
    auth_header = request.headers.get("Authorization")
    if auth_header:
        try:
            return auth_svc.resolve_user(bearer_token=auth_header)
        except Exception as exc:
            logger.warning(
                "bootstrap_evaluator_sync_bearer_resolve_skipped",
                error_type=type(exc).__name__,
            )
    if first_admin is not None and auth_svc.has_user_in_memory(first_admin.user_id):
        return auth_svc.get_user_by_id(first_admin.user_id)
    return None


def sync_setup_snapshot_to_evaluator(
    request: Request,
    snap: bm.PlatformSetupSnapshotRecord,
    first_admin: bm.FirstPlatformAdminRecord | None,
) -> None:
    """Upsert user-created org units and workspaces into `auth_service.evaluator`.

    Ensures the authenticated creator (or Day-0 first admin) holds
    `CONTRIBUTOR_ACTION_REQUIRED` membership on user-created workspaces while leaving
    reference seed workspaces untouched.
    """
    auth_svc = get_auth_service(request)
    ev = auth_svc.evaluator

    for raw_ou in snap.org_units:
        if not isinstance(raw_ou, dict):
            continue
        ou_id = str(raw_ou.get("id") or "").strip()
        ou_name = str(raw_ou.get("name") or "").strip()
        if not ou_id or not ou_name:
            continue
        ou_slug = str(raw_ou.get("slug") or ou_id).strip()
        raw_level = str(raw_ou.get("level") or "TEAM").strip().upper()
        unit_type = cast(OrgUnitType, raw_level if raw_level in _VALID_OU_TYPES else "TEAM")
        raw_parent = str(raw_ou.get("parentId") or "").strip()
        parent_id: str | None = (
            _ROOT_ENTERPRISE_ID if not raw_parent or raw_parent == "scope-global" else raw_parent
        )
        ev.upsert_org_unit(
            OrgUnitNode(
                id=ou_id,
                slug=ou_slug,
                name=ou_name,
                unit_type=unit_type,
                parent_id=parent_id,
            )
        )

    owner_user = _resolve_workspace_owner_user(request, first_admin)
    for raw_ws in snap.workspaces:
        if not isinstance(raw_ws, dict):
            continue
        ws_id = str(raw_ws.get("workspaceId") or raw_ws.get("id") or "").strip()
        ws_name = str(raw_ws.get("name") or "").strip()
        if not ws_id or not ws_name or ws_id in _SEEDED_WORKSPACE_IDS:
            continue
        ws_slug = str(raw_ws.get("slug") or ws_id).strip()
        raw_owner_ou = str(raw_ws.get("ownerOrgUnitId") or "").strip()
        owner_ou_id = (
            raw_owner_ou if raw_owner_ou and ev.has_org_unit(raw_owner_ou) else _ROOT_ENTERPRISE_ID
        )
        raw_vis = str(raw_ws.get("visibilityMode") or "STANDARD").strip()
        vis_mode: WorkspaceVisibilityMode = (
            "CONFIDENTIAL_RESTRICTED" if raw_vis == "CONFIDENTIAL_RESTRICTED" else "STANDARD"
        )
        ev.upsert_workspace(
            WorkspaceEntity(
                id=ws_id,
                slug=ws_slug,
                name=ws_name,
                owner_org_unit_id=owner_ou_id,
                visibility_mode=vis_mode,
            )
        )
        if owner_user is not None and owner_user.platform_role not in ("OBSERVER", "BU_DIRECTOR"):
            ev.upsert_membership(
                WorkspaceMembershipEntity(
                    id=new_uuid7_str(),
                    workspace_id=ws_id,
                    role=owner_user.platform_role,
                    access_mode="CONTRIBUTOR_ACTION_REQUIRED",
                    user_id=owner_user.id,
                )
            )
