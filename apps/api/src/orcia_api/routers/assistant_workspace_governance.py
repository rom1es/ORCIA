"""Epic 10 Sub-Router — `Mon Assistant` Mode A 3-Level Governance (`Story 10.1`, `Story 26.4b`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import (
    get_assistant_governance_service,
    get_assistant_three_speed_router_service,
)
from orcia_api.dependencies._assistant_guards import (
    can_user_manage_workspace_governance,
    enforce_assistant_workspace_guard,
)
from orcia_api.routers._assistant_prompt_sanitization import resolve_request_locale
from orcia_api.routers._assistant_usage_telemetry import resolve_assistant_outbox_emitter
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    AssembledLayerPreviewSchemaItem,
    AssistantGovernanceViewResponse,
    UpdateUserLayerPreferencesRequest,
    UpdateWorkspaceLayerSettingsRequest,
    UserLayerPreferencesSchemaItem,
    WorkspaceLayerSettingsSchemaItem,
)
from orcia_core.orchestration.assistant_governance import (
    AssistantFourLevelGovernanceService,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_three_speed_router import AssistantThreeSpeedRouterService
from orcia_core.permissions.models import UserIdentity

router = APIRouter()

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
GovernanceServiceDep = Annotated[
    AssistantFourLevelGovernanceService, Depends(get_assistant_governance_service)
]
ThreeSpeedRouterDep = Annotated[
    AssistantThreeSpeedRouterService, Depends(get_assistant_three_speed_router_service)
]


def _to_user_prefs_schema(prefs: UserLayerPreferences) -> UserLayerPreferencesSchemaItem:
    return UserLayerPreferencesSchemaItem(
        user_id=prefs.user_id,
        workspace_id=prefs.workspace_id,
        response_tone=prefs.response_tone,
        favorite_format=prefs.favorite_format,
        default_hat=prefs.default_hat,
        personal_instructions=prefs.personal_instructions,
        sha256=prefs.sha256,
    )


def _to_workspace_settings_schema(ws: WorkspaceLayerSettings) -> WorkspaceLayerSettingsSchemaItem:
    return WorkspaceLayerSettingsSchemaItem(
        workspace_id=ws.workspace_id,
        workspace_instructions=ws.workspace_instructions,
        default_checked_sources=list(ws.default_checked_sources),
        recommended_agents=list(ws.recommended_agents),
        arbitration_policy=ws.arbitration_policy,
        welcome_suggestions=list(ws.welcome_suggestions),
        mcp_expose_assistant=ws.mcp_expose_assistant,
        mcp_frozen_by_upper_layer=ws.mcp_frozen_by_upper_layer,
        mcp_frozen_origin=ws.mcp_frozen_origin,
        mcp_endpoint_url=ws.mcp_endpoint_url,
        mcp_tool_name=ws.mcp_tool_name,
        mcp_ide_config_json=ws.mcp_ide_config_json,
        sha256=ws.sha256,
    )


@router.get("/governance", response_model=AssistantGovernanceViewResponse)
async def get_assistant_governance_endpoint(
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    workspace_id: Annotated[str, Query()] = "scope-global",
    pack_key: Annotated[str | None, Query()] = None,
) -> AssistantGovernanceViewResponse:
    """Return Mode A (3 tabs) governance state hydrated from PG18 (`Story 26.4b`)."""
    await enforce_assistant_workspace_guard(
        request,
        user,
        workspace_id,
        require_write=False,
        scope_level="GLOBAL" if workspace_id == "scope-global" else "WORKSPACE",
    )
    can_manage = await can_user_manage_workspace_governance(request, user, workspace_id)
    view = await svc.get_governance_view_async(
        user,
        workspace_id=workspace_id,
        pack_key=pack_key,
        locale=resolve_request_locale(request),
    )
    return AssistantGovernanceViewResponse(
        workspace_id=view.workspace_id,
        can_edit_workspace_layer=can_manage,
        user_preferences=_to_user_prefs_schema(view.user_preferences),
        workspace_settings=_to_workspace_settings_schema(view.workspace_settings),
        assembled_layers=[
            AssembledLayerPreviewSchemaItem(
                layer_number=layer.layer_number,
                layer_code=layer.layer_code,
                label=layer.label,
                immutable=layer.immutable,
                origin_badge=layer.origin_badge,
                content=layer.content,
                sha256=layer.sha256,
            )
            for layer in view.assembled_layers
        ],
    )


@router.put("/governance/mode-a/user", response_model=UserLayerPreferencesSchemaItem)
async def update_user_layer_preferences_endpoint(
    payload: UpdateUserLayerPreferencesRequest,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> UserLayerPreferencesSchemaItem:
    """Update Tab 1 (`USER` layer 5) and persist to PG18 (`Story 26.4b`)."""
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    updated = await svc.update_user_preferences_async(
        user,
        workspace_id=payload.workspace_id,
        response_tone=payload.response_tone,
        favorite_format=payload.favorite_format,
        default_hat=payload.default_hat,
        personal_instructions=payload.personal_instructions,
    )
    router_svc.invalidate_prompt_cache(
        workspace_id=payload.workspace_id, reason="OVERRIDE_UPDATED", user_id=user.id
    )
    outbox = resolve_assistant_outbox_emitter(request)
    if outbox is not None:
        await outbox.emit_settings_changed(
            workspace_id=payload.workspace_id,
            setting_key="assistant.mode_a.user",
            actor_id=user.id,
            trace_id=str(getattr(getattr(request, "state", None), "trace_id", "") or ""),
            scope_level="USER",
            after_sha256=updated.sha256,
        )
    return _to_user_prefs_schema(updated)


@router.put("/governance/mode-a/workspace", response_model=WorkspaceLayerSettingsSchemaItem)
async def update_workspace_layer_settings_endpoint(
    payload: UpdateWorkspaceLayerSettingsRequest,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> WorkspaceLayerSettingsSchemaItem:
    """Update Tab 2 (`WORKSPACE` layer 4) and persist to PG18 (`Story 26.4b`)."""
    await enforce_assistant_workspace_guard(
        request, user, payload.workspace_id, require_write=True, require_manage=True
    )
    updated = await svc.update_workspace_settings_async(
        user,
        workspace_id=payload.workspace_id,
        workspace_instructions=payload.workspace_instructions,
        default_checked_sources=tuple(payload.default_checked_sources),
        recommended_agents=tuple(payload.recommended_agents),
        arbitration_policy=payload.arbitration_policy,
        welcome_suggestions=(
            tuple(payload.welcome_suggestions) if payload.welcome_suggestions is not None else None
        ),
        mcp_expose_assistant=payload.mcp_expose_assistant,
    )
    router_svc.invalidate_prompt_cache(workspace_id=payload.workspace_id, reason="SETTINGS_CHANGED")
    outbox = resolve_assistant_outbox_emitter(request)
    if outbox is not None:
        await outbox.emit_settings_changed(
            workspace_id=payload.workspace_id,
            setting_key="assistant.mode_a.workspace",
            actor_id=user.id,
            trace_id=str(getattr(getattr(request, "state", None), "trace_id", "") or ""),
            scope_level="WORKSPACE",
            after_sha256=updated.sha256,
        )
    return _to_workspace_settings_schema(updated)
