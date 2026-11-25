"""PG18 topology synchronization helper for `auth_svc.evaluator` (`Story 26.6b`)."""

from __future__ import annotations

import json
from typing import cast

import sqlalchemy as sa
from fastapi import Request

from orcia_api.dependencies._core_providers import get_configured_db_engine, is_pg_runtime_active
from orcia_core.kernel.errors import TransientInfraError
from orcia_core.observability.logging import get_logger
from orcia_core.permissions.models import (
    AccessMode,
    OrgUnitNode,
    OrgUnitType,
    PlatformRole,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
    WorkspaceVisibilityMode,
)
from orcia_core.permissions.service import AuthAndOrganizationService

logger = get_logger("orcia.api.dependencies.topology_sync")


async def sync_evaluator_topology_from_pg(
    request: Request,
    auth_svc: AuthAndOrganizationService,
    *,
    force: bool = False,
) -> None:
    """Ensure `auth_svc.evaluator` reflects `org_units`, `workspaces`, and memberships in PG18."""
    req_state = getattr(request, "state", None)
    if not force and getattr(req_state, "_orcia_topology_synced", False):
        return
    engine = get_configured_db_engine(request)
    if engine is None:
        return
    from orcia_api.dependencies.core_and_lifespan import should_seed_test_personas_in_memory

    authoritative_pg_only = not should_seed_test_personas_in_memory()
    try:
        async with engine.connect() as conn:
            ou_rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id, slug, name, unit_type, parent_id, "
                            "lead_user_id, lead_user_ids_jsonb, member_user_ids_jsonb "
                            "FROM org_units;"
                        )
                    )
                )
                .mappings()
                .all()
            )
            pg_org_units: list[OrgUnitNode] = []
            for r in ou_rows:
                ou_id = str(r["id"])
                raw_leads = r.get("lead_user_ids_jsonb") or []
                if isinstance(raw_leads, str):
                    raw_leads = json.loads(raw_leads)
                raw_members = r.get("member_user_ids_jsonb") or []
                if isinstance(raw_members, str):
                    raw_members = json.loads(raw_members)
                node = OrgUnitNode(
                    id=ou_id,
                    slug=str(r["slug"]),
                    name=str(r["name"]),
                    unit_type=cast(OrgUnitType, str(r["unit_type"])),
                    parent_id=str(r["parent_id"]) if r["parent_id"] else None,
                    lead_user_id=str(r["lead_user_id"]) if r["lead_user_id"] else None,
                    lead_user_ids=tuple(str(x) for x in raw_leads),
                    member_user_ids=tuple(str(x) for x in raw_members),
                )
                pg_org_units.append(node)
                if not authoritative_pg_only:
                    auth_svc.evaluator.upsert_org_unit(node)
            if authoritative_pg_only:
                auth_svc.evaluator.replace_org_units(tuple(pg_org_units))

            ws_rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id, slug, name, owner_org_unit_id, visibility_mode, "
                            "settings_jsonb FROM workspaces "
                            "ORDER BY CASE WHEN COALESCE(settings_jsonb->>'ui_visibility_mode', "
                            "'STANDARD') = 'PRIVATE_USER' THEN 1 ELSE 0 END, "
                            "created_at ASC, slug ASC;"
                        )
                    )
                )
                .mappings()
                .all()
            )
            pg_workspaces: list[WorkspaceEntity] = []
            for w in ws_rows:
                ws_id = str(w["id"])
                raw_st = w.get("settings_jsonb")
                st_dict: dict[str, object] = {}
                if isinstance(raw_st, dict):
                    st_dict = raw_st
                elif isinstance(raw_st, str):
                    try:
                        decoded = json.loads(raw_st)
                        if isinstance(decoded, dict):
                            st_dict = decoded
                    except ValueError:
                        st_dict = {}
                ui_vis = (
                    str(st_dict["ui_visibility_mode"]).strip()
                    if st_dict.get("ui_visibility_mode")
                    else None
                )
                personal_owner = (
                    str(st_dict["personal_owner_user_id"]).strip()
                    if st_dict.get("personal_owner_user_id")
                    else None
                )
                raw_phase = str(st_dict.get("lifecycle_phase") or "BUILD").strip().upper()
                lifecycle_phase = (
                    raw_phase if raw_phase in ("BUILD", "RUN", "MIGRATION") else "BUILD"
                )
                db_vis = cast(WorkspaceVisibilityMode, str(w["visibility_mode"]))
                existing = auth_svc.evaluator.get_workspace(ws_id)
                ws_entity = WorkspaceEntity(
                    id=ws_id,
                    slug=str(w["slug"]),
                    name=str(w["name"]),
                    owner_org_unit_id=str(w["owner_org_unit_id"]),
                    visibility_mode=db_vis,
                    datasources=existing.datasources if existing else (),
                    personal_owner_user_id=personal_owner,
                    ui_visibility_mode=ui_vis,
                    lifecycle_phase=lifecycle_phase,
                )
                pg_workspaces.append(ws_entity)
                if not authoritative_pg_only and (
                    existing is None
                    or existing.owner_org_unit_id != str(w["owner_org_unit_id"])
                    or existing.name != str(w["name"])
                    or existing.visibility_mode != db_vis
                    or existing.personal_owner_user_id != personal_owner
                    or existing.ui_visibility_mode != ui_vis
                    or existing.lifecycle_phase != lifecycle_phase
                ):
                    auth_svc.evaluator.upsert_workspace(ws_entity)
            if authoritative_pg_only:
                auth_svc.evaluator.replace_workspaces(tuple(pg_workspaces))

            mem_rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id, workspace_id, user_id, invited_org_unit_id, "
                            "role, access_mode FROM workspace_memberships;"
                        )
                    )
                )
                .mappings()
                .all()
            )
            pg_memberships: list[WorkspaceMembershipEntity] = []
            for m in mem_rows:
                mem_entity = WorkspaceMembershipEntity(
                    id=str(m["id"]),
                    workspace_id=str(m["workspace_id"]),
                    role=cast(PlatformRole, str(m["role"])),
                    access_mode=cast(AccessMode, str(m["access_mode"])),
                    user_id=str(m["user_id"]) if m["user_id"] else None,
                    invited_org_unit_id=(
                        str(m["invited_org_unit_id"]) if m["invited_org_unit_id"] else None
                    ),
                )
                pg_memberships.append(mem_entity)
                if not authoritative_pg_only:
                    auth_svc.evaluator.upsert_membership(mem_entity)
            if authoritative_pg_only:
                auth_svc.evaluator.replace_memberships(tuple(pg_memberships))
        if req_state is not None:
            req_state._orcia_topology_synced = True
    except Exception as exc:
        logger.error(
            "finops_sync_evaluator_topology_failed",
            error_type=type(exc).__name__,
            detail=str(exc),
            authoritative_pg_only=authoritative_pg_only,
        )
        if authoritative_pg_only or is_pg_runtime_active():
            path = str(getattr(getattr(request, "url", None), "path", "/"))
            raise TransientInfraError(
                detail_code="ERR_ORG_PG_UNAVAILABLE_TOPOLOGY",
                instance=path,
            ) from exc
        return


__all__ = ["sync_evaluator_topology_from_pg"]
