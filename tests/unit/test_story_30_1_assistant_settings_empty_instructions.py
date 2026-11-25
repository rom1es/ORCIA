"""Story 30.1 — Unit tests for empty default personal instructions and min_length=0."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tests.unit.fakes.in_memory_assistant_governance import InMemoryAssistantGovernanceStore

from orcia_api.main import app
from orcia_api.schemas.assistant_governance_and_three_speed import (
    UpdateUserLayerPreferencesRequest,
)
from orcia_core.orchestration._assistant_locales import ASSISTANT_FOLDER_LOCALES
from orcia_core.orchestration._internal._sql_assistant_governance_queries import (
    manifest_to_user_prefs,
)
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.assistant_governance_models import UserLayerPreferences
from orcia_core.orchestration.assistant_governance_studio import build_default_user_preferences
from orcia_core.permissions.models import UserIdentity


def _make_user(user_id: str = "u-30-1") -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=f"{user_id}@orcia.local",
        display_name="Helene",
        auth_mode="LOCAL",
        human_profile_archetype="PM",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="org-unit-alpha",
    )


def test_story_30_1_default_personal_instructions_are_empty_in_fr_and_en() -> None:
    """Default personal_instructions must be empty string in both locales and models."""
    assert ASSISTANT_FOLDER_LOCALES["fr"]["user_default_instructions"] == ""
    assert ASSISTANT_FOLDER_LOCALES["en"]["user_default_instructions"] == ""

    model_default = UserLayerPreferences(user_id="u-1", workspace_id="ws-1")
    assert model_default.personal_instructions == ""

    studio_default = build_default_user_preferences(workspace_id="ws-1", user_id="u-1")
    assert studio_default.personal_instructions == ""

    hydrated = manifest_to_user_prefs(
        workspace_id="ws-1",
        user_id="u-1",
        manifest={"response_tone": "BALANCED", "favorite_format": "STRUCTURED_SECTIONS"},
        sha256="a" * 64,
    )
    assert hydrated.personal_instructions == ""


def test_story_30_1_request_schema_allows_empty_personal_instructions() -> None:
    """UpdateUserLayerPreferencesRequest accepts empty and omitted personal_instructions."""
    req_empty = UpdateUserLayerPreferencesRequest(
        workspace_id="ws-1",
        personal_instructions="",
    )
    assert req_empty.personal_instructions == ""

    req_omitted = UpdateUserLayerPreferencesRequest(workspace_id="ws-1")
    assert req_omitted.personal_instructions == ""

    with pytest.raises(ValidationError):
        UpdateUserLayerPreferencesRequest(
            workspace_id="ws-1",
            personal_instructions="x" * 4001,
        )


def test_story_30_1_service_and_api_persist_empty_personal_instructions() -> None:
    """Service and PUT /mode-a/user accept clearing personal_instructions back to empty."""
    svc = AssistantFourLevelGovernanceService(store=InMemoryAssistantGovernanceStore())
    user = _make_user()

    svc.update_user_preferences(
        user,
        workspace_id="ws-1",
        response_tone="BALANCED",
        favorite_format="STRUCTURED_SECTIONS",
        default_hat="PM",
        personal_instructions="Initial rule",
    )
    cleared = svc.update_user_preferences(
        user,
        workspace_id="ws-1",
        response_tone="BALANCED",
        favorite_format="STRUCTURED_SECTIONS",
        default_hat="PM",
        personal_instructions="",
    )
    assert cleared.personal_instructions == ""
    reloaded = svc.get_user_preferences(workspace_id="ws-1", user_id=user.id)
    assert reloaded.personal_instructions == ""

    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    with TestClient(app) as client:
        put_resp = client.put(
            "/api/v1/assistant/governance/mode-a/user",
            params={"persona_key": "marc"},
            json={
                "workspace_id": ws_id,
                "response_tone": "BALANCED",
                "favorite_format": "STRUCTURED_SECTIONS",
                "default_hat": "PM",
                "personal_instructions": "",
            },
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["personal_instructions"] == ""
