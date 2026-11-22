"""In-memory fake for `AssistantGovernanceStorePort` for unit tests (`tests/unit/fakes/`)."""

from __future__ import annotations

from typing import Literal

from orcia_core.orchestration.assistant_governance_models import (
    AssistantCustomizationOverrideRecord,
    AssistantGovernanceStorePort,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_governance_studio import (
    build_default_user_preferences,
    build_default_workspace_layer_settings,
    build_frozen_workspace_settings,
)


class InMemoryAssistantGovernanceStore(AssistantGovernanceStorePort):
    """Deterministic unit-test store implementing `AssistantGovernanceStorePort` (`AD-19`)."""

    def __init__(self) -> None:
        self._user_prefs: dict[tuple[str, str], UserLayerPreferences] = {}
        self._workspace_settings: dict[str, WorkspaceLayerSettings] = {}
        self._team_instructions: dict[str, str] = {}
        self._team_mcp_frozen: dict[str, tuple[bool, Literal["PLATFORM", "TEAM"]]] = {}
        self._overrides: dict[str, AssistantCustomizationOverrideRecord] = {}

    def get_user_preferences(self, *, workspace_id: str, user_id: str) -> UserLayerPreferences:
        key = (workspace_id, user_id)
        if key not in self._user_prefs:
            return build_default_user_preferences(workspace_id=workspace_id, user_id=user_id)
        return self._user_prefs[key]

    def save_user_preferences(
        self,
        *,
        workspace_id: str,
        user_id: str,
        prefs: UserLayerPreferences,
        record: AssistantCustomizationOverrideRecord,
    ) -> UserLayerPreferences:
        self._user_prefs[(workspace_id, user_id)] = prefs
        self._overrides[record.override_key] = record
        return prefs

    def get_workspace_settings(self, workspace_id: str) -> WorkspaceLayerSettings:
        if workspace_id not in self._workspace_settings:
            base = build_default_workspace_layer_settings(workspace_id)
        else:
            base = self._workspace_settings[workspace_id]
        frozen = self._team_mcp_frozen.get(workspace_id)
        if frozen is not None and frozen[0]:
            return build_frozen_workspace_settings(base, origin=frozen[1])
        return base

    def save_workspace_settings(
        self,
        *,
        workspace_id: str,
        settings: WorkspaceLayerSettings,
        record: AssistantCustomizationOverrideRecord,
    ) -> WorkspaceLayerSettings:
        self._workspace_settings[workspace_id] = settings
        self._overrides[record.override_key] = record
        return settings

    def get_team_mcp_frozen(
        self, workspace_id: str
    ) -> tuple[bool, Literal["PLATFORM", "TEAM"]] | None:
        return self._team_mcp_frozen.get(workspace_id)

    def set_team_mcp_frozen(
        self,
        *,
        workspace_id: str,
        frozen: bool,
        origin: Literal["PLATFORM", "TEAM"] = "TEAM",
    ) -> None:
        if frozen:
            self._team_mcp_frozen[workspace_id] = (True, origin)
            existing = self.get_workspace_settings(workspace_id)
            self._workspace_settings[workspace_id] = build_frozen_workspace_settings(
                existing, origin=origin
            )
        else:
            self._team_mcp_frozen.pop(workspace_id, None)

    def get_team_instructions(self, workspace_id: str) -> str | None:
        return self._team_instructions.get(workspace_id)

    def list_overrides(self) -> tuple[AssistantCustomizationOverrideRecord, ...]:
        return tuple(self._overrides.values())


__all__ = ["InMemoryAssistantGovernanceStore"]
