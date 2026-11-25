"""Async Mode A Preview & Conversational Governance Loaders (`Story 26.4b`, `Story 30.2`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from orcia_core.orchestration.assistant_governance_models import (
    AssembledLayerPreviewItem,
    AssistantGovernanceView,
    ConversationalGovernanceContext,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_governance_studio import (
    build_five_layers_preview_items,
    can_manage_workspace_or_team,
)
from orcia_core.orchestration.assistant_prompt_preview import (
    resolve_default_hat,
    resolve_human_user_label,
    resolve_human_workspace_label,
)
from orcia_core.permissions.models import UserIdentity

if TYPE_CHECKING:
    from orcia_core.orchestration._internal.sql_assistant_governance import (
        SqlAssistantGovernanceRepository,
    )


class _AssistantGovernanceAsyncViewsMixin:
    """Async PG18 preview and conversational governance bundle loaders."""

    _sql_repo: SqlAssistantGovernanceRepository | None

    if TYPE_CHECKING:

        async def _pg_ready(self) -> bool: ...
        def _default_team_instructions(self, locale: str) -> str: ...
        def _with_resolved_hat(
            self,
            prefs: UserLayerPreferences,
            *,
            user: UserIdentity | None = None,
            fallback: str | None = None,
        ) -> UserLayerPreferences: ...
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
        ) -> ConversationalGovernanceContext: ...
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
        ) -> tuple[AssembledLayerPreviewItem, ...]: ...
        def get_governance_view(
            self,
            user: UserIdentity,
            *,
            workspace_id: str,
            pack_key: str | None = None,
            locale: str = "fr",
        ) -> AssistantGovernanceView: ...

    async def _resolve_pg_bundle(
        self,
        *,
        workspace_id: str,
        user_id: str,
        user_email: str | None = None,
        user: UserIdentity | None = None,
        fallback_hat: str | None = None,
        locale: str = "fr",
    ) -> tuple[UserLayerPreferences, WorkspaceLayerSettings, str, str | None, str | None]:
        assert self._sql_repo is not None
        (
            prefs,
            ws_set,
            team_instr,
            pg_ws,
            pg_u,
        ) = await self._sql_repo.get_mode_a_layers_bundle_with_labels(
            workspace_id=workspace_id, user_id=user_id, user_email=user_email
        )
        eff = self._with_resolved_hat(prefs, user=user, fallback=fallback_hat)
        return eff, ws_set, team_instr or self._default_team_instructions(locale), pg_ws, pg_u

    async def load_conversational_governance_async(
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
    ) -> ConversationalGovernanceContext:
        """Load Mode A governance state from PG18 for live conversational turns."""
        if await self._pg_ready() and self._sql_repo is not None:
            eff, ws_set, team, pg_ws, pg_u = await self._resolve_pg_bundle(
                workspace_id=workspace_id,
                user_id=user_id,
                user_email=user_email,
                fallback_hat=default_hat_fallback,
                locale=locale,
            )
            return ConversationalGovernanceContext(
                workspace_id=workspace_id,
                workspace_label=resolve_human_workspace_label(
                    workspace_id, workspace_display_name or pg_ws, locale=locale
                ),
                user_label=resolve_human_user_label(
                    user_id, user_display_name or pg_u, locale=locale
                ),
                team_instructions=team,
                workspace_instructions=ws_set.workspace_instructions,
                response_tone=eff.response_tone,
                favorite_format=eff.favorite_format,
                default_hat=eff.default_hat,
                personal_instructions=eff.personal_instructions,
                pack_key=pack_key,
            )
        return self.load_conversational_governance(
            workspace_id=workspace_id,
            user_id=user_id,
            pack_key=pack_key,
            locale=locale,
            workspace_display_name=workspace_display_name,
            user_display_name=user_display_name,
            default_hat_fallback=default_hat_fallback,
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
            eff, ws_set, team, pg_ws, pg_u = await self._resolve_pg_bundle(
                workspace_id=workspace_id,
                user_id=user_id,
                user_email=user_email,
                fallback_hat=default_hat_fallback,
                locale=locale,
            )
            return build_five_layers_preview_items(
                workspace_id=workspace_id,
                user_id=user_id,
                pack_key=pack_key,
                user_prefs=eff,
                ws_settings=ws_set,
                team_instr=team,
                locale=locale,
                workspace_display_name=workspace_display_name or pg_ws,
                user_display_name=user_display_name or pg_u,
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
            eff, ws_set, team, pg_ws, pg_u = await self._resolve_pg_bundle(
                workspace_id=workspace_id,
                user_id=user.id,
                user_email=user.email,
                user=user,
                fallback_hat=resolved_hat,
                locale=locale,
            )
            assembled = build_five_layers_preview_items(
                workspace_id=workspace_id,
                user_id=user.id,
                pack_key=pack_key,
                user_prefs=eff,
                ws_settings=ws_set,
                team_instr=team,
                locale=locale,
                workspace_display_name=pg_ws,
                user_display_name=user.display_name or pg_u,
            )
            return AssistantGovernanceView(
                workspace_id=workspace_id,
                can_edit_workspace_layer=can_manage_workspace_or_team(user),
                user_preferences=eff,
                workspace_settings=ws_set,
                assembled_layers=assembled,
                override_records=await self._sql_repo.list_overrides(workspace_id=workspace_id),
            )
        return self.get_governance_view(
            user, workspace_id=workspace_id, pack_key=pack_key, locale=locale
        )
