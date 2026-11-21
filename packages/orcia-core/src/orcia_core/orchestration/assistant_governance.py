"""Story 10.1 — 4-Level Governance & Customization of `Mon Assistant` (Mode A & Mode B)."""

from __future__ import annotations

from typing import Literal

from orcia_core.orchestration.assistant_agent import ASSISTANT_WORKFLOW_URI
from orcia_core.orchestration.assistant_governance_models import (
    ENTRY_HARNESS_NODE_ID,
    EXIT_HARNESS_NODE_ID,
    REQUIRED_CORE_NODE_IDS,
    AssembledLayerPreviewItem,
    AssistantArbitrationPolicy,
    AssistantCustomizationOverrideRecord,
    AssistantGovernanceView,
    AssistantOverrideScope,
    AssistantResponseFormat,
    AssistantResponseTone,
    AssistantStudioGraphState,
    AssistantStudioNodeSpec,
    UserLayerPreferences,
    WorkspaceLayerSettings,
    _compute_sha256_hex,
    build_default_studio_nodes,
)
from orcia_core.orchestration.assistant_governance_studio import (
    build_default_studio_graph_state,
    build_default_user_preferences,
    build_default_workspace_layer_settings,
    build_five_layers_preview_items,
    build_frozen_workspace_settings,
    build_saved_studio_graph_override,
    build_updated_user_preferences_override,
    can_manage_workspace_or_team,
    ensure_workspace_or_team_manager,
)
from orcia_core.orchestration.assistant_harness import sanitize_layer_marker_tags
from orcia_core.orchestration.errors import FunnelRuleViolationError, ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.ids import new_uuid7_str

__all__ = [
    "AssembledLayerPreviewItem",
    "AssistantArbitrationPolicy",
    "AssistantCustomizationOverrideRecord",
    "AssistantFourLevelGovernanceService",
    "AssistantGovernanceView",
    "AssistantOverrideScope",
    "AssistantResponseFormat",
    "AssistantResponseTone",
    "AssistantStudioGraphState",
    "AssistantStudioNodeSpec",
    "ENTRY_HARNESS_NODE_ID",
    "EXIT_HARNESS_NODE_ID",
    "REQUIRED_CORE_NODE_IDS",
    "UserLayerPreferences",
    "WorkspaceLayerSettings",
    "build_default_studio_nodes",
]


class AssistantFourLevelGovernanceService:
    """Manages Mode A (3-tab modal) & Mode B (Studio graph) for `Mon Assistant` (`Story 10.1`)."""

    def __init__(self) -> None:
        self._user_prefs: dict[tuple[str, str], UserLayerPreferences] = {}
        self._workspace_settings: dict[str, WorkspaceLayerSettings] = {}
        self._team_instructions: dict[str, str] = {}
        self._team_mcp_frozen: dict[str, tuple[bool, Literal["PLATFORM", "TEAM"]]] = {}
        self._studio_graphs: dict[tuple[str, str], AssistantStudioGraphState] = {}
        self._overrides: dict[str, AssistantCustomizationOverrideRecord] = {}
        self._version_counter: int = 1

    @property
    def version_counter(self) -> int:
        """Monotonic counter incremented whenever any assistant governance setting changes."""
        return self._version_counter

    def freeze_mcp_at_upper_layer(
        self,
        *,
        workspace_id: str,
        frozen: bool,
        origin: Literal["PLATFORM", "TEAM"] = "TEAM",
    ) -> None:
        """Freeze or unfreeze MCP exposure from `TEAM` or `PLATFORM` (`Principe G`)."""
        if frozen:
            self._team_mcp_frozen[workspace_id] = (True, origin)
            existing = self.get_workspace_settings(workspace_id)
            self._workspace_settings[workspace_id] = build_frozen_workspace_settings(
                existing, origin=origin
            )
        else:
            self._team_mcp_frozen.pop(workspace_id, None)
        self._version_counter += 1

    def get_user_preferences(self, *, workspace_id: str, user_id: str) -> UserLayerPreferences:
        key = (workspace_id, user_id)
        if key not in self._user_prefs:
            self._user_prefs[key] = build_default_user_preferences(
                workspace_id=workspace_id, user_id=user_id
            )
        return self._user_prefs[key]

    def update_user_preferences(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        response_tone: AssistantResponseTone,
        favorite_format: AssistantResponseFormat,
        default_hat: str,
        personal_instructions: str,
    ) -> UserLayerPreferences:
        """Update Tab 1 (`Mes préférences — Couche 5 USER`)."""
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise ObserverModeReadOnlyError()
        prefs, record = build_updated_user_preferences_override(
            workspace_id=workspace_id,
            user_id=user.id,
            response_tone=response_tone,
            favorite_format=favorite_format,
            default_hat=default_hat,
            personal_instructions=personal_instructions,
        )
        self._user_prefs[(workspace_id, user.id)] = prefs
        self._overrides[record.override_key] = record
        self._version_counter += 1
        return prefs

    def get_workspace_settings(self, workspace_id: str) -> WorkspaceLayerSettings:
        if workspace_id not in self._workspace_settings:
            self._workspace_settings[workspace_id] = build_default_workspace_layer_settings(
                workspace_id
            )
        return self._workspace_settings[workspace_id]

    def update_workspace_settings(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        workspace_instructions: str,
        default_checked_sources: tuple[str, ...],
        recommended_agents: tuple[str, ...],
        arbitration_policy: AssistantArbitrationPolicy,
        welcome_suggestions: tuple[str, ...] | None = None,
        mcp_expose_assistant: bool = True,
    ) -> WorkspaceLayerSettings:
        """Update Tab 2 (`Réglages de l'Espace — Couche 4 WORKSPACE`), enforcing Funnel Rule."""
        ensure_workspace_or_team_manager(
            user,
            detail="TEAM_LEAD or PLATFORM_ADMIN role required to update workspace settings.",
        )
        frozen_entry = self._team_mcp_frozen.get(workspace_id)
        if frozen_entry is not None and frozen_entry[0] and mcp_expose_assistant:
            raise FunnelRuleViolationError()

        current = self.get_workspace_settings(workspace_id)
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
        self._workspace_settings[workspace_id] = updated
        ov_key = f"assistant-workspace-{workspace_id}"
        self._overrides[ov_key] = AssistantCustomizationOverrideRecord(
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
        self._version_counter += 1
        return updated

    def assemble_five_layers_preview(
        self,
        *,
        workspace_id: str,
        user_id: str,
        pack_key: str | None = None,
        locale: str = "fr",
    ) -> tuple[AssembledLayerPreviewItem, ...]:
        """Build Tab 3 (`Assemblage complet`) showing the 5 active prompt layers (`AD-15`)."""
        return build_five_layers_preview_items(
            workspace_id=workspace_id,
            user_id=user_id,
            pack_key=pack_key,
            user_prefs=self.get_user_preferences(workspace_id=workspace_id, user_id=user_id),
            ws_settings=self.get_workspace_settings(workspace_id),
            team_instr=self._team_instructions.get(
                workspace_id,
                "Team standards: decision traceability and peer review."
                if locale.startswith("en")
                else (
                    "Standards d'équipe : traçabilité systématique des décisions "
                    "et revues croisées."
                ),
            ),
            locale=locale,
        )

    def get_studio_graph(
        self, *, workspace_id: str, team_id: str = "team-default"
    ) -> AssistantStudioGraphState:
        """Return active Mode B Studio graph (`WORKSPACE` -> `TEAM` -> `DEFAULT`)."""
        if ("WORKSPACE", workspace_id) in self._studio_graphs:
            return self._studio_graphs[("WORKSPACE", workspace_id)]
        if ("TEAM", team_id) in self._studio_graphs:
            return self._studio_graphs[("TEAM", team_id)]
        return build_default_studio_graph_state(workspace_id)

    def save_studio_graph_override(
        self,
        user: UserIdentity,
        *,
        scope_level: Literal["TEAM", "WORKSPACE"],
        scope_id: str,
        ai_pre_prompt: str,
        nodes: tuple[AssistantStudioNodeSpec, ...],
    ) -> AssistantStudioGraphState:
        """Validate `AssistantHarness` boundaries and persist Mode B graph override."""
        ensure_workspace_or_team_manager(
            user,
            detail="TEAM_LEAD or PLATFORM_ADMIN role required for Mode B Studio override.",
        )
        state, record = build_saved_studio_graph_override(
            scope_level=scope_level, scope_id=scope_id, ai_pre_prompt=ai_pre_prompt, nodes=nodes
        )
        self._studio_graphs[(scope_level, scope_id)] = state
        self._overrides[record.override_key] = record
        self._version_counter += 1
        return state

    def reset_studio_graph_override(
        self, user: UserIdentity, *, scope_level: Literal["TEAM", "WORKSPACE"], scope_id: str
    ) -> AssistantStudioGraphState:
        """1-click reset to default configuration."""
        ensure_workspace_or_team_manager(user)
        self._studio_graphs.pop((scope_level, scope_id), None)
        self._overrides.pop(f"assistant-studio-{scope_level.lower()}-{scope_id}", None)
        self._version_counter += 1
        return self.get_studio_graph(workspace_id=scope_id)

    def get_governance_view(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        pack_key: str | None = None,
        locale: str = "fr",
    ) -> AssistantGovernanceView:
        """Assemble full Mode A & Mode B governance view for `user` and `workspace_id`."""
        can_edit = can_manage_workspace_or_team(user)
        return AssistantGovernanceView(
            workspace_id=workspace_id,
            can_edit_workspace_layer=can_edit,
            can_open_studio_mode_b=can_edit,
            user_preferences=self.get_user_preferences(workspace_id=workspace_id, user_id=user.id),
            workspace_settings=self.get_workspace_settings(workspace_id),
            assembled_layers=self.assemble_five_layers_preview(
                workspace_id=workspace_id, user_id=user.id, pack_key=pack_key, locale=locale
            ),
            studio_graph=self.get_studio_graph(workspace_id=workspace_id),
            override_records=tuple(self._overrides.values()),
        )

    @staticmethod
    def _can_manage_workspace_or_team(user: UserIdentity) -> bool:
        return can_manage_workspace_or_team(user)
