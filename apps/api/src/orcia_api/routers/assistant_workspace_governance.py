"""Epic 10 Sub-Router — `Mon Assistant` 4-Level Governance (`Mode A` & `Mode B`, `Story 10.1`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from orcia_api.dependencies import (
    get_assistant_governance_service,
    get_assistant_three_speed_router_service,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    AssembledLayerPreviewSchemaItem,
    AssistantGovernanceViewResponse,
    AssistantStudioGraphStateSchemaItem,
    AssistantStudioNodeSchemaItem,
    ResetAssistantStudioGraphRequest,
    SaveAssistantStudioGraphRequest,
    UpdateUserLayerPreferencesRequest,
    UpdateWorkspaceLayerSettingsRequest,
    UserLayerPreferencesSchemaItem,
    WorkspaceLayerSettingsSchemaItem,
)
from orcia_core.orchestration.assistant_governance import (
    AssistantFourLevelGovernanceService,
    AssistantStudioGraphState,
    AssistantStudioNodeSpec,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_three_speed_router import (
    AssistantThreeSpeedRouterService,
)
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


def _to_studio_graph_schema(st: AssistantStudioGraphState) -> AssistantStudioGraphStateSchemaItem:
    return AssistantStudioGraphStateSchemaItem(
        workflow_uri=st.workflow_uri,
        scope_level=st.scope_level,
        scope_id=st.scope_id,
        ai_pre_prompt=st.ai_pre_prompt,
        nodes=[
            AssistantStudioNodeSchemaItem(
                node_id=n.node_id,
                title=n.title,
                node_order=n.node_order,
                is_harness_boundary=n.is_harness_boundary,
                locked_by=n.locked_by,
                enabled=n.enabled,
                sub_layers_count=n.sub_layers_count,
                enabled_sub_layers=list(n.enabled_sub_layers),
                sub_agent_uri=n.sub_agent_uri,
            )
            for n in st.nodes
        ],
        override_key=st.override_key,
        sha256=st.sha256,
    )


@router.get("/governance", response_model=AssistantGovernanceViewResponse)
def get_assistant_governance_endpoint(
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    workspace_id: Annotated[str, Query()] = "ws-claims-alpha",
    pack_key: Annotated[str, Query()] = "orcia-pack-sdlc",
) -> AssistantGovernanceViewResponse:
    """Return Mode A (3 tabs) & Mode B (Studio graph) governance state (`Story 10.1`)."""
    view = svc.get_governance_view(user, workspace_id=workspace_id, pack_key=pack_key)
    return AssistantGovernanceViewResponse(
        workspace_id=view.workspace_id,
        can_edit_workspace_layer=view.can_edit_workspace_layer,
        can_open_studio_mode_b=view.can_open_studio_mode_b,
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
        studio_graph=_to_studio_graph_schema(view.studio_graph),
    )


@router.put("/governance/mode-a/user", response_model=UserLayerPreferencesSchemaItem)
def update_user_layer_preferences_endpoint(
    payload: UpdateUserLayerPreferencesRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> UserLayerPreferencesSchemaItem:
    """Update Tab 1 (`👤 Mes préférences — Couche 5 USER`) (`Story 10.1`)."""
    updated = svc.update_user_preferences(
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
    return _to_user_prefs_schema(updated)


@router.put("/governance/mode-a/workspace", response_model=WorkspaceLayerSettingsSchemaItem)
def update_workspace_layer_settings_endpoint(
    payload: UpdateWorkspaceLayerSettingsRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> WorkspaceLayerSettingsSchemaItem:
    """Update Tab 2 (`📦 Réglages de l'Espace — Couche 4 WORKSPACE`) (`Story 10.1`)."""
    updated = svc.update_workspace_settings(
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
    return _to_workspace_settings_schema(updated)


@router.post("/governance/mode-b/save", response_model=AssistantStudioGraphStateSchemaItem)
def save_assistant_studio_graph_endpoint(
    payload: SaveAssistantStudioGraphRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> AssistantStudioGraphStateSchemaItem:
    """Save Mode B Studio graph override (`TEAM` or `WORKSPACE`) (`🔒 AssistantHarness`)."""
    saved = svc.save_studio_graph_override(
        user,
        scope_level=payload.scope_level,
        scope_id=payload.scope_id,
        ai_pre_prompt=payload.ai_pre_prompt,
        nodes=tuple(
            AssistantStudioNodeSpec(
                node_id=n.node_id,
                title=n.title,
                node_order=n.node_order,
                is_harness_boundary=n.is_harness_boundary,
                locked_by=n.locked_by,
                enabled=n.enabled,
                sub_layers_count=n.sub_layers_count,
                enabled_sub_layers=tuple(n.enabled_sub_layers),
                sub_agent_uri=n.sub_agent_uri,
            )
            for n in payload.nodes
        ),
    )
    router_svc.invalidate_prompt_cache(workspace_id=payload.scope_id, reason="OVERRIDE_UPDATED")
    return _to_studio_graph_schema(saved)


@router.post("/governance/mode-b/reset", response_model=AssistantStudioGraphStateSchemaItem)
def reset_assistant_studio_graph_endpoint(
    payload: ResetAssistantStudioGraphRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> AssistantStudioGraphStateSchemaItem:
    """Reset Mode B Studio override in 1 click (`↺ Réinitialiser`) (`Story 10.1`)."""
    restored = svc.reset_studio_graph_override(
        user, scope_level=payload.scope_level, scope_id=payload.scope_id
    )
    router_svc.invalidate_prompt_cache(workspace_id=payload.scope_id, reason="OVERRIDE_UPDATED")
    return _to_studio_graph_schema(restored)
