"""Scope & observer RBAC guards + serializers for `/api/v1/workspaces/{id}/packs` (`Story 31.4`)."""

from __future__ import annotations

from typing import Literal

from fastapi import Request

from orcia_api.dependencies import (
    get_agents_and_skills_service,
    get_auth_service,
)
from orcia_api.dependencies._core_providers import is_pg_runtime_active
from orcia_api.routers._agents_and_skills_helpers import sync_from_postgres18_if_enabled
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas._workspace_packs import (
    WorkspacePackItemResponse,
    WorkspacePackSlotBindingItemResponse,
)
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.packs.slot_guard import EffectiveSlotBindingView, WorkspacePackView
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import UserIdentity

TargetKindLiteral = Literal["UNBOUND", "WORKSPACE_DATASOURCE", "ENTERPRISE_CONNECTOR", "INTERNAL"]


def trace_id_for(request: Request) -> str:
    """Resolve active OpenTelemetry `trace_id`."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


async def enforce_workspace_packs_access(
    request: Request,
    workspace_id: str,
    *,
    require_write: bool,
    persona_key: str | None = None,
) -> tuple[UserIdentity, str]:
    """Enforce `ScopeAccessGuard` and `READ_ONLY_OBSERVER` checks on a workspace."""
    path = str(request.url.path)
    user = resolve_request_user(request, persona_key=persona_key)
    if require_write:
        enforce_observer_headers_guard(request, user)
        if (
            user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER", "BU_DIRECTOR")
            or "OBSERVER" in user.roles
            or "READ_ONLY_OBSERVER" in user.roles
        ):
            raise ObserverModeReadOnlyError(instance=path)

    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    cleaned_ws = workspace_id.strip().removeprefix("scope-ws-").strip()
    ws = auth_svc.evaluator.get_workspace(cleaned_ws)
    if ws is None:
        await sync_evaluator_topology_from_pg(request, auth_svc, force=True)
        ws = auth_svc.evaluator.get_workspace(cleaned_ws)
    if ws is None:
        raise ResourceNotFoundError(
            detail_override=f"Workspace {workspace_id!r} not found.",
            instance=path,
        )
    if ws.ui_visibility_mode == "PRIVATE_USER" and (
        ws.personal_owner_user_id is None or str(ws.personal_owner_user_id) != str(user.id)
    ):
        raise ScopeAccessDeniedError(instance=path)
    access = auth_svc.evaluator.resolve_workspace_access(user, ws.id)
    if access is None:
        raise ScopeAccessDeniedError(instance=path)
    if require_write and access.access_mode == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(instance=path)
    return user, ws.id


async def refresh_workspace_catalog_consistency(request: Request, workspace_id: str) -> None:
    """Refresh read-through PG18 agents/skills state for `workspace_id` after pack mutation."""
    if not is_pg_runtime_active(request):
        return
    svc = get_agents_and_skills_service(request)
    await sync_from_postgres18_if_enabled(request, svc, workspace_id=workspace_id)


def serialize_slot_binding(
    view: EffectiveSlotBindingView,
) -> WorkspacePackSlotBindingItemResponse:
    """Serialize `EffectiveSlotBindingView` into OpenAPI response model."""
    return WorkspacePackSlotBindingItemResponse(
        id=view.id,
        workspace_id=view.workspace_id,
        pack_bundle_id=view.pack_bundle_id,
        pack_slug=view.pack_slug,
        slot_key=view.slot_key,
        target_kind=view.target_kind.value,
        target_id=view.target_id,
        bound_datasource_id=view.bound_datasource_id,
        bound_connector_id=view.bound_connector_id,
        connector_scheme=view.connector_scheme,
        bound_by=view.bound_by,
        bound_at_iso=view.bound_at_iso,
        is_effective_bound=view.is_effective_bound,
        target_uri=view.target_uri,
        target_display_name=view.target_display_name,
        target_enabled=view.target_enabled,
    )


def serialize_workspace_pack(view: WorkspacePackView) -> WorkspacePackItemResponse:
    """Serialize `WorkspacePackView` into OpenAPI response model."""
    return WorkspacePackItemResponse(
        bundle_id=view.bundle_id,
        pack_id=view.pack_id,
        slug=view.slug,
        name=view.name,
        version=view.version,
        bundle_kind=view.bundle_kind,
        scope_type=view.scope_type,
        scope_id=view.scope_id,
        status=view.status,
        archive_sha256=view.archive_sha256,
        cas_object_key=view.cas_object_key,
        description=view.description,
        author=view.author,
        is_active=view.is_active,
        priority_order=view.priority_order,
        activated_at_iso=view.activated_at_iso,
        activated_by=view.activated_by,
        declared_slots=list(view.declared_slots),
        slot_bindings=[serialize_slot_binding(b) for b in view.slot_bindings],
        missing_slots=list(view.missing_slots),
        readiness_ok=view.readiness_ok,
    )


__all__ = [
    "enforce_workspace_packs_access",
    "refresh_workspace_catalog_consistency",
    "serialize_slot_binding",
    "serialize_workspace_pack",
    "trace_id_for",
]
