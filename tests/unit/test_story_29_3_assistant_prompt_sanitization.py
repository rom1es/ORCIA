"""Story 29.3 - Unit tests for prompt sanitization and clean role/speed labels."""

from __future__ import annotations

from tests.unit.fakes.in_memory_assistant_governance import InMemoryAssistantGovernanceStore

from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.assistant_governance_models import (
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder
from orcia_core.orchestration.assistant_prompt_preview import (
    build_five_layers_preview_items,
    format_system_instructions_text,
    resolve_default_hat,
)
from orcia_core.permissions.models import UserIdentity


def _make_team_lead() -> UserIdentity:
    return UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000999",
        email="helene.lead@orcia.fr",
        display_name="Helene Lead",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
    )


def test_story_29_3_five_layers_preview_sanitizes_uuids_and_omits_unattached_defaults() -> None:
    """Layer preview must hide raw UUIDv7s and omit empty sources/agents."""
    ws_uuid = "01a26729-1111-7000-8000-000000000042"
    user_uuid = "01a26729-2222-7000-8000-000000000099"
    ws_settings = WorkspaceLayerSettings(workspace_id=ws_uuid)
    user_prefs = UserLayerPreferences(user_id=user_uuid, workspace_id=ws_uuid)

    assert ws_settings.default_checked_sources == ()
    assert ws_settings.recommended_agents == ()
    assert user_prefs.default_hat == ""

    preview_fr = build_five_layers_preview_items(
        workspace_id=ws_uuid,
        user_id=user_uuid,
        workspace_display_name="Espace Pilotage",
        user_display_name="Helene Lead",
        pack_key="orcia-pack-sdlc",
        user_prefs=user_prefs,
        ws_settings=ws_settings,
        team_instr="Team standards.",
        locale="fr",
    )
    combined_fr = "\n".join(item.content for item in preview_fr)
    assert ws_uuid not in combined_fr
    assert user_uuid not in combined_fr
    assert "Espace Pilotage" in combined_fr
    assert "Helene Lead" in combined_fr
    assert "orcia://sources/repo-main" not in combined_fr
    assert "@spec-architect" not in combined_fr
    assert "@security-reviewer" not in combined_fr

    # Without explicit display names, UUIDs must still never leak into prompt text.
    fallback_en = build_five_layers_preview_items(
        workspace_id=ws_uuid,
        user_id=user_uuid,
        pack_key=None,
        user_prefs=user_prefs,
        ws_settings=ws_settings,
        team_instr="Team standards.",
        locale="en",
    )
    combined_en = "\n".join(item.content for item in fallback_en)
    assert ws_uuid not in combined_en
    assert user_uuid not in combined_en
    assert "Active space" in combined_en
    assert "Active user" in combined_en


def test_story_29_3_system_instructions_localize_speed_and_hat_without_enum_leaks() -> None:
    """System instructions must never expose internal SPEED_* enums."""
    for speed_code in ("SPEED_1_FAST", "SPEED_2_AGENT_TOOLS", "SPEED_3_DEEP_AUDIT"):
        sys_fr = format_system_instructions_text(
            hat="TEAM_LEAD",
            speed_mode=speed_code,
            requested_tier="medium",
            thinking_effort="balanced",
            assembled_5_layers_prompt=None,
            ontology_concepts_summary=None,
            federated_evidence_summary=None,
            custom_block="",
            locale="fr",
        )
        assert speed_code not in sys_fr
        assert "SPEED_" not in sys_fr

        sys_en = format_system_instructions_text(
            hat="TEAM_LEAD",
            speed_mode=speed_code,
            requested_tier="medium",
            thinking_effort="balanced",
            assembled_5_layers_prompt=None,
            ontology_concepts_summary=None,
            federated_evidence_summary=None,
            custom_block="",
            locale="en",
        )
        assert speed_code not in sys_en
        assert "SPEED_" not in sys_en
        assert "Team Lead" in sys_en


def test_story_29_3_assemble_prompt_and_governance_resolve_real_user_hat_and_clean_scope() -> None:
    """Prompt assembly and Mode A governance resolve user's real role and clean workspace label."""
    ws_uuid = "01a26729-3333-7000-8000-000000000077"
    lead = _make_team_lead()
    builder = AssistantPromptBuilder()

    assembled_global = builder.assemble_prompt(
        user_prompt="Summarize priorities",
        human_profile_archetype="TECH_LEAD",
        workspace_id="scope-global",
        intent="QA_COACHING",
        locale="en",
    )
    assert "scope-global" not in assembled_global.system_prompt
    assert "scope-global" not in assembled_global.user_prompt
    assert "All my spaces" in assembled_global.user_prompt

    assembled_uuid = builder.assemble_prompt(
        user_prompt="Check status",
        human_profile_archetype="TECH_LEAD",
        workspace_id=ws_uuid,
        workspace_display_name="Operations Core",
        intent="QA_COACHING",
        locale="en",
    )
    assert ws_uuid not in assembled_uuid.system_prompt
    assert ws_uuid not in assembled_uuid.user_prompt
    assert "Operations Core" in assembled_uuid.user_prompt

    gov = AssistantFourLevelGovernanceService(store=InMemoryAssistantGovernanceStore())
    view = gov.get_governance_view(lead, workspace_id=ws_uuid, locale="fr")
    assert view.user_preferences.default_hat == "TECH_LEAD"
    assert view.workspace_settings.default_checked_sources == ()
    assert view.workspace_settings.recommended_agents == ()

    contributor_no_arch = UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000888",
        email="member@orcia.fr",
        display_name="Member User",
        auth_mode="LOCAL",
        human_profile_archetype="",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
    )
    assert resolve_default_hat(explicit_hat=None, user=contributor_no_arch) == "CONTRIBUTOR"
