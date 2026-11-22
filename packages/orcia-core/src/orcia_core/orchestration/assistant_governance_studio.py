"""Mode A 5-Layer Assembly & Governance Helper Builders (`Story 10.1`, `Story 26.4b`)."""

from __future__ import annotations

import json
from typing import Literal

from orcia_core.orchestration.assistant_agent import ASSISTANT_WORKFLOW_URI
from orcia_core.orchestration.assistant_governance_layers import (
    build_five_layers_preview_items as build_five_layers_preview_items,
)
from orcia_core.orchestration.assistant_governance_models import (
    AssistantArbitrationPolicy,
    AssistantCustomizationOverrideRecord,
    UserLayerPreferences,
    WorkspaceLayerSettings,
    _compute_sha256_hex,
)
from orcia_core.orchestration.assistant_harness import sanitize_layer_marker_tags
from orcia_core.orchestration.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str


def build_default_workspace_layer_settings(workspace_id: str) -> WorkspaceLayerSettings:
    """Create deterministic default Tab 2 settings for `workspace_id`."""
    endpoint_url = f"/api/v1/mcp/spaces/{workspace_id}"
    ide_cfg = json.dumps(
        {
            "mcpServers": {
                f"orcia-assistant-{workspace_id}": {
                    "url": endpoint_url,
                    "tool": "assistant.ask",
                    "headers": {"Authorization": "Bearer pat_mcp_<votre_jeton>"},
                }
            }
        },
        indent=2,
    )
    default = WorkspaceLayerSettings(
        workspace_id=workspace_id, mcp_endpoint_url=endpoint_url, mcp_ide_config_json=ide_cfg
    )
    digest = _compute_sha256_hex(
        {
            "workspace_instructions": default.workspace_instructions,
            "default_checked_sources": default.default_checked_sources,
            "recommended_agents": default.recommended_agents,
            "arbitration_policy": default.arbitration_policy,
            "mcp_expose_assistant": default.mcp_expose_assistant,
        }
    )
    return WorkspaceLayerSettings(
        workspace_id=workspace_id,
        workspace_instructions=default.workspace_instructions,
        default_checked_sources=default.default_checked_sources,
        recommended_agents=default.recommended_agents,
        arbitration_policy=default.arbitration_policy,
        welcome_suggestions=default.welcome_suggestions,
        mcp_expose_assistant=default.mcp_expose_assistant,
        mcp_frozen_by_upper_layer=False,
        mcp_frozen_origin=None,
        mcp_endpoint_url=endpoint_url,
        mcp_tool_name="assistant.ask",
        mcp_ide_config_json=ide_cfg,
        sha256=digest,
    )


def build_default_user_preferences(*, workspace_id: str, user_id: str) -> UserLayerPreferences:
    """Create default Tab 1 user layer preferences with SHA-256."""
    default = UserLayerPreferences(user_id=user_id, workspace_id=workspace_id)
    digest = _compute_sha256_hex(
        {
            "tone": default.response_tone,
            "format": default.favorite_format,
            "hat": default.default_hat,
            "instructions": default.personal_instructions,
        }
    )
    return UserLayerPreferences(
        user_id=user_id,
        workspace_id=workspace_id,
        response_tone=default.response_tone,
        favorite_format=default.favorite_format,
        default_hat=default.default_hat,
        personal_instructions=default.personal_instructions,
        sha256=digest,
    )


def build_updated_user_preferences_override(
    *,
    workspace_id: str,
    user_id: str,
    response_tone: str,
    favorite_format: str,
    default_hat: str,
    personal_instructions: str,
) -> tuple[UserLayerPreferences, AssistantCustomizationOverrideRecord]:
    """Build updated Layer 5 user preferences and override record."""
    default_hat_str = default_hat.strip().upper() or "ARCHITECT"
    personal_instr_str = sanitize_layer_marker_tags(personal_instructions)
    manifest: dict[str, object] = {
        "response_tone": response_tone,
        "favorite_format": favorite_format,
        "default_hat": default_hat_str,
        "personal_instructions": personal_instr_str,
    }
    digest = _compute_sha256_hex(manifest)
    prefs = UserLayerPreferences(
        user_id=user_id,
        workspace_id=workspace_id,
        response_tone=response_tone,  # type: ignore[arg-type]
        favorite_format=favorite_format,  # type: ignore[arg-type]
        default_hat=default_hat_str,
        personal_instructions=personal_instr_str,
        sha256=digest,
    )
    ov_key = f"assistant-user-{workspace_id}-{user_id}"
    record = AssistantCustomizationOverrideRecord(
        id=new_uuid7_str(),
        override_key=ov_key,
        org_unit_id=None,
        workspace_id=workspace_id,
        user_id=user_id,
        target_uri=ASSISTANT_WORKFLOW_URI,
        override_layer="USER",
        override_manifest_jsonb=manifest,
        sha256=digest,
    )
    return prefs, record


def build_updated_workspace_settings_override(
    *,
    workspace_id: str,
    current: WorkspaceLayerSettings,
    workspace_instructions: str,
    default_checked_sources: tuple[str, ...],
    recommended_agents: tuple[str, ...],
    arbitration_policy: AssistantArbitrationPolicy,
    welcome_suggestions: tuple[str, ...] | None,
    mcp_expose_assistant: bool,
    frozen_entry: tuple[bool, Literal["PLATFORM", "TEAM"]] | None,
) -> tuple[WorkspaceLayerSettings, AssistantCustomizationOverrideRecord]:
    """Build updated Layer 4 workspace settings and override record."""
    suggestions = (
        welcome_suggestions if welcome_suggestions is not None else current.welcome_suggestions
    )
    ws_instr_str = sanitize_layer_marker_tags(workspace_instructions)
    manifest: dict[str, object] = {
        "workspace_instructions": ws_instr_str,
        "default_checked_sources": list(default_checked_sources),
        "recommended_agents": list(recommended_agents),
        "arbitration_policy": arbitration_policy,
        "welcome_suggestions": list(suggestions),
        "mcp_expose_assistant": mcp_expose_assistant,
    }
    digest = _compute_sha256_hex(manifest)
    updated = WorkspaceLayerSettings(
        workspace_id=workspace_id,
        workspace_instructions=ws_instr_str,
        default_checked_sources=tuple(default_checked_sources),
        recommended_agents=tuple(recommended_agents),
        arbitration_policy=arbitration_policy,
        welcome_suggestions=tuple(suggestions),
        mcp_expose_assistant=mcp_expose_assistant,
        mcp_frozen_by_upper_layer=bool(frozen_entry and frozen_entry[0]),
        mcp_frozen_origin=frozen_entry[1] if frozen_entry else None,
        mcp_endpoint_url=current.mcp_endpoint_url,
        mcp_tool_name=current.mcp_tool_name,
        mcp_ide_config_json=current.mcp_ide_config_json,
        sha256=digest,
    )
    ov_key = f"assistant-workspace-{workspace_id}"
    record = AssistantCustomizationOverrideRecord(
        id=new_uuid7_str(),
        override_key=ov_key,
        org_unit_id=None,
        workspace_id=workspace_id,
        user_id=None,
        target_uri=ASSISTANT_WORKFLOW_URI,
        override_layer="WORKSPACE",
        override_manifest_jsonb=manifest,
        sha256=digest,
    )
    return updated, record


def build_frozen_workspace_settings(
    existing: WorkspaceLayerSettings,
    *,
    origin: Literal["PLATFORM", "TEAM"],
) -> WorkspaceLayerSettings:
    """Return workspace settings with MCP frozen by upper governance layer."""
    return WorkspaceLayerSettings(
        workspace_id=existing.workspace_id,
        workspace_instructions=existing.workspace_instructions,
        default_checked_sources=existing.default_checked_sources,
        recommended_agents=existing.recommended_agents,
        arbitration_policy=existing.arbitration_policy,
        welcome_suggestions=existing.welcome_suggestions,
        mcp_expose_assistant=False,
        mcp_frozen_by_upper_layer=True,
        mcp_frozen_origin=origin,
        mcp_endpoint_url=existing.mcp_endpoint_url,
        mcp_tool_name=existing.mcp_tool_name,
        mcp_ide_config_json=existing.mcp_ide_config_json,
        sha256=existing.sha256,
    )


def can_manage_workspace_or_team(user: UserIdentity) -> bool:
    """Return True if `user` holds an administrative or team/BU lead platform role."""
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        return False
    return user.platform_role in {"PLATFORM_ADMIN", "TEAM_LEAD", "BU_LEAD"}


def ensure_workspace_or_team_manager(user: UserIdentity, detail: str | None = None) -> None:
    """Enforce non-observer + manager privilege before Mode A governance writes."""
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError()
    if not can_manage_workspace_or_team(user):
        raise ScopeAccessDeniedError(detail_override=detail)
