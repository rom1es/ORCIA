"""Story 10.1 / 26.4b — Mode A 3-Level Governance of `Mon Assistant` (PG18-backed, Zero RAM)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from orcia_core.orchestration._assistant_governance_sync import _AssistantGovernanceSyncMixin
from orcia_core.orchestration._internal.sql_assistant_governance import (
    SqlAssistantGovernanceRepository,
)
from orcia_core.orchestration.assistant_governance_models import (
    AssembledLayerPreviewItem,
    AssistantArbitrationPolicy,
    AssistantCustomizationOverrideRecord,
    AssistantGovernanceStorePort,
    AssistantGovernanceView,
    AssistantOverrideScope,
    AssistantResponseFormat,
    AssistantResponseTone,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_governance_studio import (
    build_five_layers_preview_items,
    build_frozen_workspace_settings,
    build_updated_user_preferences_override,
    build_updated_workspace_settings_override,
    can_manage_workspace_or_team,
    ensure_workspace_or_team_manager,
)
from orcia_core.orchestration.assistant_prompt_preview import resolve_default_hat
from orcia_core.orchestration.errors import FunnelRuleViolationError, ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

__all__ = [
    "AssembledLayerPreviewItem",
    "AssistantArbitrationPolicy",
    "AssistantCustomizationOverrideRecord",
    "AssistantFourLevelGovernanceService",
    "AssistantGovernanceStorePort",
    "AssistantGovernanceView",
    "AssistantOverrideScope",
    "AssistantResponseFormat",
    "AssistantResponseTone",
    "UserLayerPreferences",
    "WorkspaceLayerSettings",
]


class AssistantFourLevelGovernanceService(_AssistantGovernanceSyncMixin):
    """Manages Mode A (3-tab) governance persisted in `workspace_customization_overrides`."""

    def __init__(
        self,
        *,
        engine: AsyncEngine | None = None,
        store: AssistantGovernanceStorePort | None = None,
    ) -> None:
        self._engine: AsyncEngine | None = engine
        self._sql_repo: SqlAssistantGovernanceRepository | None = (
            SqlAssistantGovernanceRepository(engine) if engine is not None else None
        )
        self._store: AssistantGovernanceStorePort | None = store

    def set_engine(self, engine: AsyncEngine | None) -> None:
        """Bind or refresh the SQLAlchemy `AsyncEngine` from the Composition Root."""
        self._engine = engine
        self._sql_repo = SqlAssistantGovernanceRepository(engine) if engine is not None else None

    async def _pg_ready(self) -> bool:
        return self._sql_repo is not None and await self._sql_repo.pg_tables_ready()

    async def freeze_mcp_at_upper_layer_async(
        self,
        *,
        workspace_id: str,
        frozen: bool,
        origin: Literal["PLATFORM", "TEAM"] = "TEAM",
    ) -> None:
        """Freeze or unfreeze MCP exposure in PG18 `TEAM` override layer (or unit store)."""
        if await self._pg_ready() and self._sql_repo is not None:
            await self._sql_repo.set_team_mcp_frozen(
                workspace_id=workspace_id, frozen=frozen, origin=origin
            )
            return
        self.freeze_mcp_at_upper_layer(workspace_id=workspace_id, frozen=frozen, origin=origin)

    async def get_user_preferences_async(
        self, *, workspace_id: str, user_id: str, user_email: str | None = None
    ) -> UserLayerPreferences:
        """Load `USER` layer preferences from PG18 `workspace_customization_overrides`."""
        if await self._pg_ready() and self._sql_repo is not None:
            return await self._sql_repo.get_user_preferences(
                workspace_id=workspace_id, user_id=user_id, user_email=user_email
            )
        return self.get_user_preferences(workspace_id=workspace_id, user_id=user_id)

    async def update_user_preferences_async(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        response_tone: AssistantResponseTone,
        favorite_format: AssistantResponseFormat,
        default_hat: str,
        personal_instructions: str,
    ) -> UserLayerPreferences:
        """Persist Tab 1 (`USER` layer 5) to PG18 `workspace_customization_overrides`."""
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
        if await self._pg_ready() and self._sql_repo is not None:
            return await self._sql_repo.upsert_user_preferences(
                workspace_id=workspace_id,
                user_id=user.id,
                user_email=user.email,
                prefs=prefs,
                record=record,
            )
        if self._store is not None:
            return self._store.save_user_preferences(
                workspace_id=workspace_id, user_id=user.id, prefs=prefs, record=record
            )
        return prefs

    async def get_workspace_settings_async(self, workspace_id: str) -> WorkspaceLayerSettings:
        """Load `WORKSPACE` layer settings from PG18 `workspace_customization_overrides`."""
        if await self._pg_ready() and self._sql_repo is not None:
            return await self._sql_repo.get_workspace_settings(workspace_id)
        return self.get_workspace_settings(workspace_id)

    async def update_workspace_settings_async(
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
        """Persist Tab 2 (`WORKSPACE` layer 4) to PG18 while enforcing the Funnel Rule."""
        ensure_workspace_or_team_manager(
            user,
            detail="TEAM_LEAD or PLATFORM_ADMIN role required to update workspace settings.",
        )
        if await self._pg_ready() and self._sql_repo is not None:
            _, frozen_entry = await self._sql_repo.get_team_layer_state(workspace_id)
            if frozen_entry is not None and frozen_entry[0] and mcp_expose_assistant:
                raise FunnelRuleViolationError()
            current = await self._sql_repo.get_workspace_settings(workspace_id)
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
            if frozen_entry is not None and frozen_entry[0]:
                updated = build_frozen_workspace_settings(updated, origin=frozen_entry[1])
            return await self._sql_repo.upsert_workspace_settings(
                workspace_id=workspace_id, settings=updated, record=record
            )
        return self.update_workspace_settings(
            user,
            workspace_id=workspace_id,
            workspace_instructions=workspace_instructions,
            default_checked_sources=default_checked_sources,
            recommended_agents=recommended_agents,
            arbitration_policy=arbitration_policy,
            welcome_suggestions=welcome_suggestions,
            mcp_expose_assistant=mcp_expose_assistant,
        )

    async def assemble_five_layers_preview_async(
        self,
        *,
        workspace_id: str,
        user_id: str,
        pack_key: str | None = None,
        locale: str = "fr",
        user_email: str | None = None,
        workspace_display_name: str | None = None,
        user_display_name: str | None = None,
        default_hat_fallback: str | None = None,
    ) -> tuple[AssembledLayerPreviewItem, ...]:
        """Assemble Tab 3 5-layer preview hydrated from PG18 overrides in 1 SQL roundtrip."""
        if await self._pg_ready() and self._sql_repo is not None:
            (
                user_prefs,
                ws_settings,
                team_instr,
                pg_ws_name,
                pg_user_name,
            ) = await self._sql_repo.get_mode_a_layers_bundle_with_labels(
                workspace_id=workspace_id, user_id=user_id, user_email=user_email
            )
            effective_prefs = self._with_resolved_hat(user_prefs, fallback=default_hat_fallback)
            return build_five_layers_preview_items(
                workspace_id=workspace_id,
                user_id=user_id,
                pack_key=pack_key,
                user_prefs=effective_prefs,
                ws_settings=ws_settings,
                team_instr=team_instr or self._default_team_instructions(locale),
                locale=locale,
                workspace_display_name=workspace_display_name or pg_ws_name,
                user_display_name=user_display_name or pg_user_name,
            )
        return self.assemble_five_layers_preview(
            workspace_id=workspace_id,
            user_id=user_id,
            pack_key=pack_key,
            locale=locale,
            workspace_display_name=workspace_display_name,
            user_display_name=user_display_name,
            default_hat_fallback=default_hat_fallback,
        )

    async def get_governance_view_async(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        pack_key: str | None = None,
        locale: str = "fr",
    ) -> AssistantGovernanceView:
        """Assemble Mode A governance view from PG18 `workspace_customization_overrides`."""
        resolved_hat = resolve_default_hat(user=user)
        if await self._pg_ready() and self._sql_repo is not None:
            (
                raw_prefs,
                ws_settings,
                team_instr,
                pg_ws_name,
                pg_user_name,
            ) = await self._sql_repo.get_mode_a_layers_bundle_with_labels(
                workspace_id=workspace_id, user_id=user.id, user_email=user.email
            )
            effective_prefs = self._with_resolved_hat(raw_prefs, user=user, fallback=resolved_hat)
            assembled = build_five_layers_preview_items(
                workspace_id=workspace_id,
                user_id=user.id,
                pack_key=pack_key,
                user_prefs=effective_prefs,
                ws_settings=ws_settings,
                team_instr=team_instr or self._default_team_instructions(locale),
                locale=locale,
                workspace_display_name=pg_ws_name,
                user_display_name=user.display_name or pg_user_name,
            )
            return AssistantGovernanceView(
                workspace_id=workspace_id,
                can_edit_workspace_layer=can_manage_workspace_or_team(user),
                user_preferences=effective_prefs,
                workspace_settings=ws_settings,
                assembled_layers=assembled,
                override_records=await self._sql_repo.list_overrides(workspace_id=workspace_id),
            )
        return self.get_governance_view(
            user, workspace_id=workspace_id, pack_key=pack_key, locale=locale
        )

    @staticmethod
    def _can_manage_workspace_or_team(user: UserIdentity) -> bool:
        return can_manage_workspace_or_team(user)
