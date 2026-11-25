"""Story 29.3 — Unit tests for assistant turn plan, prompt builder, and preview helpers."""

from __future__ import annotations

from uuid import UUID

import pytest

from orcia_core.orchestration._assistant_turn_engine_plan import (
    assemble_prepared_turn_plan_async,
    run_n1_intent_guard,
)
from orcia_core.orchestration.ai_models_errors import ModelToolsUnsupportedError
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.assistant_prompt_builder import AssistantPromptBuilder
from orcia_core.orchestration.assistant_prompt_preview import (
    format_governance_and_folder_sections,
    resolve_default_hat,
    resolve_human_user_label,
    resolve_human_workspace_label,
)
from orcia_core.orchestration.assistant_three_speed_models import build_assistant_prompt_cache_key
from orcia_core.orchestration.errors import (
    DirectSiWriteRequiresProcessGateError,
    ImmutableHarnessBoundaryError,
    ObserverModeReadOnlyError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig

_USER_UUID = UUID("0195f293-0000-7000-8000-000000000301")


def _user(role: str = "TEAM_LEAD", archetype: str = "ARCHITECT") -> UserIdentity:
    return UserIdentity(
        id=str(_USER_UUID),
        email="lead@orcia.test",
        display_name="Lead User",
        auth_mode="LOCAL",
        human_profile_archetype=archetype,
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id="ou-1",
    )


@pytest.mark.asyncio
async def test_turn_engine_plan_and_prompt_preview_branches() -> None:
    builder = AssistantPromptBuilder()
    lead, obs = _user(role="TEAM_LEAD"), _user(role="OBSERVER")
    with pytest.raises(ObserverModeReadOnlyError):
        run_n1_intent_guard(builder, obs, user_prompt="hi", require_write=True)
    assert run_n1_intent_guard(builder, obs, user_prompt="hi", require_write=False)
    with pytest.raises(DirectSiWriteRequiresProcessGateError):
        run_n1_intent_guard(
            builder, lead, user_prompt="hi", requested_write_target_uri="orcia://si/1"
        )
    with pytest.raises(ImmutableHarnessBoundaryError):
        run_n1_intent_guard(builder, lead, user_prompt="hi", system_instructions_override="x")
    assert (
        builder.build_system_instructions(
            hat="ARCHITECT",
            speed_mode="SPEED_1_FAST",
            system_instructions_override="  custom  ",
            allow_system_override=True,
        )
        == "custom"
    )

    svc = AssistantFourLevelGovernanceService()
    ep = LlmEndpointConfig(
        provider="p",
        model_name="m1",
        endpoint_uri="https://x",
        auth_mode="API_KEY",
        supports_tools=False,
    )
    with pytest.raises(ModelToolsUnsupportedError):
        await assemble_prepared_turn_plan_async(
            governance=svc,
            prompt_builder=builder,
            intent="QA_COACHING",
            user=lead,
            workspace_id="w",
            user_prompt="audit",
            requested_speed="SPEED_2_AGENT_TOOLS",
            endpoint=ep,
        )
    p1 = await assemble_prepared_turn_plan_async(
        governance=svc,
        prompt_builder=builder,
        intent="QA_COACHING",
        user=lead,
        workspace_id="w",
        user_prompt="hi",
        assembled_5_layers_prompt="PREBUILT",
    )
    p2 = await assemble_prepared_turn_plan_async(
        governance=svc,
        prompt_builder=builder,
        intent="QA_COACHING",
        user=lead,
        workspace_id="w",
        user_prompt="hi",
    )
    assert p1.assembled_5_layers_prompt == "PREBUILT"
    assert "Principes de comportement fondamentaux" in p2.assembled_5_layers_prompt

    assert resolve_human_workspace_label("w", "Alpha", locale="en") == "Alpha"
    assert resolve_human_workspace_label("scope-global", None, locale="en") != "scope-global"
    assert resolve_human_user_label(str(_USER_UUID), None, locale="en") != str(_USER_UUID)
    assert resolve_default_hat(explicit_hat="reviewer") == "REVIEWER"
    assert resolve_default_hat(user=_user(role="TEAM_LEAD", archetype="")) == "TEAM_LEAD"
    assert format_governance_and_folder_sections() == ""
    blk = format_governance_and_folder_sections(
        response_tone="CONCISE",
        response_format="BULLETS",
        personal_instructions="P",
        workspace_instructions="W",
        folder_pinned_notes="N",
        locale="en",
    )
    assert "Workspace instructions:" in blk
    assert "Active folder pinned notes:" in blk
    assert build_assistant_prompt_cache_key("ws", "u", "  ") == "assistant:prompt:ws:u:ARCHITECT"
