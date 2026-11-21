"""5-Layer Assembly Preview & Mode B Studio Graph Helpers (`Story 10.1`, `Story 26.1`)."""

from __future__ import annotations

import json
from typing import Literal

from orcia_core.orchestration.assistant_agent import ASSISTANT_WORKFLOW_URI
from orcia_core.orchestration.assistant_governance_layers import (
    build_five_layers_preview_items as build_five_layers_preview_items,
)
from orcia_core.orchestration.assistant_governance_models import (
    AssistantCustomizationOverrideRecord,
    AssistantStudioGraphState,
    AssistantStudioNodeSpec,
    UserLayerPreferences,
    WorkspaceLayerSettings,
    _compute_sha256_hex,
    build_default_studio_nodes,
    validate_harness_boundaries,
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


def build_default_studio_graph_state(workspace_id: str) -> AssistantStudioGraphState:
    """Build default Mode B Studio graph state when no override is active."""
    nodes = build_default_studio_nodes()
    pre_prompt = (
        "Exécuter le graphe assistant-agent à 5 nœuds entre les bornes 🔒 AssistantHarness."
    )
    return AssistantStudioGraphState(
        workflow_uri=ASSISTANT_WORKFLOW_URI,
        scope_level="DEFAULT",
        scope_id=workspace_id,
        ai_pre_prompt=pre_prompt,
        nodes=nodes,
        override_key=None,
        sha256=_compute_sha256_hex({"pre_prompt": pre_prompt, "nodes": [n.node_id for n in nodes]}),
    )


def build_saved_studio_graph_override(
    *,
    scope_level: Literal["TEAM", "WORKSPACE"],
    scope_id: str,
    ai_pre_prompt: str,
    nodes: tuple[AssistantStudioNodeSpec, ...],
) -> tuple[AssistantStudioGraphState, AssistantCustomizationOverrideRecord]:
    """Validate boundaries and return `(graph_state, override_record)`."""
    validate_harness_boundaries(nodes)
    clean_pre_prompt = sanitize_layer_marker_tags(ai_pre_prompt)
    manifest: dict[str, object] = {
        "workflow_uri": ASSISTANT_WORKFLOW_URI,
        "scope_level": scope_level,
        "scope_id": scope_id,
        "ai_pre_prompt": clean_pre_prompt,
        "nodes": [
            {
                "node_id": n.node_id,
                "title": n.title,
                "node_order": n.node_order,
                "is_harness_boundary": n.is_harness_boundary,
                "locked_by": n.locked_by,
                "enabled": n.enabled,
                "sub_layers_count": n.sub_layers_count,
                "enabled_sub_layers": list(n.enabled_sub_layers),
                "sub_agent_uri": n.sub_agent_uri,
            }
            for n in nodes
        ],
    }
    digest = _compute_sha256_hex(manifest)
    ov_key = f"assistant-studio-{scope_level.lower()}-{scope_id}"
    state = AssistantStudioGraphState(
        workflow_uri=ASSISTANT_WORKFLOW_URI,
        scope_level=scope_level,
        scope_id=scope_id,
        ai_pre_prompt=clean_pre_prompt,
        nodes=nodes,
        override_key=ov_key,
        sha256=digest,
    )
    record = AssistantCustomizationOverrideRecord(
        id=new_uuid7_str(),
        override_key=ov_key,
        org_unit_id=scope_id if scope_level == "TEAM" else None,
        workspace_id=scope_id if scope_level == "WORKSPACE" else None,
        user_id=None,
        target_uri=ASSISTANT_WORKFLOW_URI,
        override_layer=scope_level,
        override_manifest_jsonb=manifest,
        sha256=digest,
    )
    return state, record


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
    default_hat_str = default_hat.strip().upper() or "PM"
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
    """Enforce non-observer + manager privilege before Mode A/B governance writes."""
    if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
        raise ObserverModeReadOnlyError()
    if not can_manage_workspace_or_team(user):
        raise ScopeAccessDeniedError(detail_override=detail)
