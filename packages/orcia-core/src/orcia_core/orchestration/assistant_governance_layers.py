"""5-Layer Prompt Preview Builder delegating to `AssistantPromptBuilder` (`Story 26.2`)."""

from __future__ import annotations

from orcia_core.orchestration.assistant_governance_models import (
    AssembledLayerPreviewItem,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder

_SHARED_PROMPT_BUILDER = AssistantPromptBuilder()


def build_five_layers_preview_items(
    *,
    workspace_id: str,
    user_id: str,
    pack_key: str | None,
    user_prefs: UserLayerPreferences,
    ws_settings: WorkspaceLayerSettings,
    team_instr: str,
    locale: str = "fr",
    workspace_display_name: str | None = None,
    user_display_name: str | None = None,
) -> tuple[AssembledLayerPreviewItem, ...]:
    """Assemble the 5-layer preview tuple via unified `AssistantPromptBuilder`."""
    return _SHARED_PROMPT_BUILDER.build_five_layers_preview(
        workspace_id=workspace_id,
        user_id=user_id,
        pack_key=pack_key,
        user_prefs=user_prefs,
        ws_settings=ws_settings,
        team_instr=team_instr,
        locale=locale,
        workspace_display_name=workspace_display_name,
        user_display_name=user_display_name,
    )
