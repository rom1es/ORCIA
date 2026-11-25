"""Synchronous unit-test & store mixin for `AssistantFourLevelGovernanceService` (`Story 26.4b`)."""

from __future__ import annotations

from dataclasses import replace
from typing import Literal

from orcia_core.orchestration.assistant_governance_models import (
    AssembledLayerPreviewItem,
    AssistantArbitrationPolicy,
    AssistantGovernanceStorePort,
    AssistantGovernanceView,
    AssistantResponseFormat,
    AssistantResponseTone,
    ConversationalGovernanceContext,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_governance_studio import (
    build_default_user_preferences,
    build_default_workspace_layer_settings,
    build_five_layers_preview_items,
    build_updated_user_preferences_override,
    build_updated_workspace_settings_override,
    can_manage_workspace_or_team,
    ensure_workspace_or_team_manager,
)
from orcia_core.orchestration.assistant_prompt_preview import (
    resolve_default_hat,
    resolve_human_user_label,
    resolve_human_workspace_label,
)
from orcia_core.orchestration.errors import FunnelRuleViolationError, ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity


class _AssistantGovernanceSyncMixin:
    """Sync governance methods delegating to an injected `AssistantGovernanceStorePort` fake."""

    _store: AssistantGovernanceStorePort | None

    @staticmethod
    def _default_team_instructions(locale: str) -> str:
        from orcia_core.orchestration._assistant_locales import ASSISTANT_FOLDER_LOCALES

        loc: Literal["fr", "en"] = "en" if locale.startswith("en") else "fr"
        return ASSISTANT_FOLDER_LOCALES[loc]["team_instructions"]

    def freeze_mcp_at_upper_layer(
        self,
        *,
        workspace_id: str,
        frozen: bool,
        origin: Literal["PLATFORM", "TEAM"] = "TEAM",
    ) -> None:
        """Freeze or unfreeze MCP exposure from `TEAM` or `PLATFORM` via injected unit store."""
        if self._store is not None:
            self._store.set_team_mcp_frozen(workspace_id=workspace_id, frozen=frozen, origin=origin)

    def get_user_preferences(self, *, workspace_id: str, user_id: str) -> UserLayerPreferences:
        """Return `USER` layer preferences from unit store or deterministic defaults."""
        if self._store is not None:
            return self._store.get_user_preferences(workspace_id=workspace_id, user_id=user_id)
        return build_default_user_preferences(workspace_id=workspace_id, user_id=user_id)

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
        """Update Tab 1 (`USER` layer 5) via unit store or stateless validation."""
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
        if self._store is not None:
            return self._store.save_user_preferences(
                workspace_id=workspace_id, user_id=user.id, prefs=prefs, record=record
            )
        return prefs

    def get_workspace_settings(self, workspace_id: str) -> WorkspaceLayerSettings:
        """Return `WORKSPACE` layer settings from unit store or deterministic defaults."""
        if self._store is not None:
            return self._store.get_workspace_settings(workspace_id)
        return build_default_workspace_layer_settings(workspace_id)

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
        """Update Tab 2 (`WORKSPACE` layer 4), enforcing the Funnel Rule."""
        ensure_workspace_or_team_manager(
            user,
            detail="TEAM_LEAD or PLATFORM_ADMIN role required to update workspace settings.",
        )
        frozen_entry = self._store.get_team_mcp_frozen(workspace_id) if self._store else None
        if frozen_entry is not None and frozen_entry[0] and mcp_expose_assistant:
            raise FunnelRuleViolationError()
        current = self.get_workspace_settings(workspace_id)
        updated, record = build_updated_workspace_settings_override(
            workspace_id=workspace_id,
            current=current,
            workspace_instructions=workspace_instructions,
            default_checked_sources=default_checked_sources,
            recommended_agents=recommended_agents,
            arbitration_policy=arbitration_policy,
            welcome_suggestions=welcome_suggestions,
            mcp_expose_assistant=mcp_expose_assistant,
            frozen_entry=frozen_entry,
        )
        if self._store is not None:
            return self._store.save_workspace_settings(
                workspace_id=workspace_id, settings=updated, record=record
            )
        return updated

    @staticmethod
    def _with_resolved_hat(
        prefs: UserLayerPreferences,
        *,
        user: UserIdentity | None = None,
        fallback: str | None = None,
    ) -> UserLayerPreferences:
        if prefs.default_hat and prefs.default_hat.strip():
            return prefs
        resolved = resolve_default_hat(user=user, fallback=fallback or "ARCHITECT")
        return replace(prefs, default_hat=resolved)

    def load_conversational_governance(
        self,
        *,
        workspace_id: str,
        user_id: str,
        pack_key: str | None = None,
        locale: str = "fr",
        workspace_display_name: str | None = None,
        user_display_name: str | None = None,
        default_hat_fallback: str | None = None,
    ) -> ConversationalGovernanceContext:
        """Load Mode A governance fields for live conversational turns (no UI preview cards)."""
        team_instr = (
            self._store.get_team_instructions(workspace_id) if self._store else None
        ) or self._default_team_instructions(locale)
        prefs = self._with_resolved_hat(
            self.get_user_preferences(workspace_id=workspace_id, user_id=user_id),
            fallback=default_hat_fallback,
        )
        ws_settings = self.get_workspace_settings(workspace_id)
        return ConversationalGovernanceContext(
            workspace_id=workspace_id,
            workspace_label=resolve_human_workspace_label(
                workspace_id, workspace_display_name, locale=locale
            ),
            user_label=resolve_human_user_label(user_id, user_display_name, locale=locale),
            team_instructions=team_instr,
            workspace_instructions=ws_settings.workspace_instructions,
            response_tone=prefs.response_tone,
            favorite_format=prefs.favorite_format,
            default_hat=prefs.default_hat,
            personal_instructions=prefs.personal_instructions,
            pack_key=pack_key,
        )

    def assemble_five_layers_preview(
        self,
        *,
        workspace_id: str,
        user_id: str,
        pack_key: str | None = None,
        locale: str = "fr",
        workspace_display_name: str | None = None,
        user_display_name: str | None = None,
        default_hat_fallback: str | None = None,
    ) -> tuple[AssembledLayerPreviewItem, ...]:
        """Build Tab 3 (`Assemblage complet`) showing the 5 active prompt layers (`AD-15`)."""
        team_instr = (
            self._store.get_team_instructions(workspace_id) if self._store else None
        ) or self._default_team_instructions(locale)
        prefs = self._with_resolved_hat(
            self.get_user_preferences(workspace_id=workspace_id, user_id=user_id),
            fallback=default_hat_fallback,
        )
        return build_five_layers_preview_items(
            workspace_id=workspace_id,
            user_id=user_id,
            pack_key=pack_key,
            user_prefs=prefs,
            ws_settings=self.get_workspace_settings(workspace_id),
            team_instr=team_instr,
            locale=locale,
            workspace_display_name=workspace_display_name,
            user_display_name=user_display_name,
        )

    def get_governance_view(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        pack_key: str | None = None,
        locale: str = "fr",
    ) -> AssistantGovernanceView:
        """Assemble Mode A governance view from unit store or deterministic defaults."""
        resolved_hat = resolve_default_hat(user=user)
        prefs = self._with_resolved_hat(
            self.get_user_preferences(workspace_id=workspace_id, user_id=user.id),
            user=user,
            fallback=resolved_hat,
        )
        return AssistantGovernanceView(
            workspace_id=workspace_id,
            can_edit_workspace_layer=can_manage_workspace_or_team(user),
            user_preferences=prefs,
            workspace_settings=self.get_workspace_settings(workspace_id),
            assembled_layers=self.assemble_five_layers_preview(
                workspace_id=workspace_id,
                user_id=user.id,
                pack_key=pack_key,
                locale=locale,
                user_display_name=user.display_name,
                default_hat_fallback=resolved_hat,
            ),
            override_records=self._store.list_overrides() if self._store is not None else (),
        )
