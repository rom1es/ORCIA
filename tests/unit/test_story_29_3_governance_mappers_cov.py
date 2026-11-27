"""Story 29.3 — Unit tests for governance SQL mappers & in-memory fallback guards."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from orcia_core.orchestration._internal._sql_assistant_governance_queries import (
    decode_manifest,
    manifest_to_user_prefs,
    manifest_to_workspace_settings,
    parse_team_rows,
    row_to_override_record,
    rows_to_mode_a_bundle,
)
from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.assistant_governance_studio import (
    build_default_user_preferences,
    build_default_workspace_layer_settings,
)
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity

_WS_UUID = UUID("0195f293-0000-7000-8000-000000000101")
_ORG_UUID = UUID("0195f293-0000-7000-8000-000000000010")
_USER_UUID = UUID("0195f293-0000-7000-8000-000000000301")
_URI = "orcia://system/bootstrap/assistant-agent"


def test_sql_governance_mappers_and_bundle_assembly() -> None:
    assert decode_manifest({"k": 1}) == {"k": 1}
    assert decode_manifest('{"k": "v"}') == {"k": "v"}
    assert decode_manifest("[1]") == {} and decode_manifest("  ") == {}
    assert decode_manifest(None) == {}

    base = {"id": "o1", "override_key": "k1", "target_uri": _URI, "sha256": "s"}
    r_full = row_to_override_record(
        {
            **base,
            "org_unit_id": _ORG_UUID,
            "workspace_id": _WS_UUID,
            "user_id": _USER_UUID,
            "override_layer": "USER",
            "override_manifest_jsonb": '{"response_tone": "CONCISE"}',
        }  # type: ignore[arg-type]
    )
    r_min = row_to_override_record(
        {
            **base,
            "org_unit_id": None,
            "workspace_id": None,
            "user_id": None,
            "override_layer": "TEAM",
            "override_manifest_jsonb": None,
        }  # type: ignore[arg-type]
    )
    assert r_full.user_id == str(_USER_UUID) and r_min.org_unit_id is None

    assert parse_team_rows([]) == (None, None)
    ti, fr = parse_team_rows(
        [
            {"override_manifest_jsonb": {"team_instructions": "First", "mcp_frozen": False}},
            {
                "override_manifest_jsonb": {
                    "team_instructions": "Second",
                    "mcp_frozen": True,
                    "origin": "PLATFORM",
                }
            },
            {"override_manifest_jsonb": {"mcp_frozen": True, "origin": "TEAM"}},
        ]
    )
    assert ti == "First" and fr == (True, "PLATFORM")

    du = build_default_user_preferences(workspace_id="ws-1", user_id="u-1")
    dw = build_default_workspace_layer_settings("ws-1")
    rows = [
        {"override_layer": None},
        {"override_layer": "PLATFORM", "override_manifest_jsonb": {}, "sha256": "x"},
        {
            "override_layer": "USER",
            "override_manifest_jsonb": {"default_hat": "CFO"},
            "sha256": "u1",
        },
        {
            "override_layer": "USER",
            "override_manifest_jsonb": {"default_hat": "QA"},
            "sha256": "u2",
        },
        {
            "override_layer": "WORKSPACE",
            "override_manifest_jsonb": {"workspace_instructions": "W1"},
            "sha256": "w1",
        },
        {
            "override_layer": "WORKSPACE",
            "override_manifest_jsonb": {"workspace_instructions": "W2"},
            "sha256": "w2",
        },
        {"override_layer": "TEAM", "override_manifest_jsonb": {"team_instructions": "T1"}},
    ]
    up, ws, t_i, f_e = rows_to_mode_a_bundle(
        rows, workspace_id="ws-1", user_id="u-1", default_user_prefs=du, default_ws_settings=dw
    )
    assert up.default_hat == "CFO" and ws.workspace_instructions == "W1"
    assert t_i == "T1" and f_e is None
    assert rows_to_mode_a_bundle(
        [], workspace_id="ws-1", user_id="u-1", default_user_prefs=du, default_ws_settings=dw
    )[:2] == (du, dw)
    assert (
        manifest_to_user_prefs(workspace_id="w", user_id="u", manifest={}, sha256="s").sha256 == "s"
    )
    assert manifest_to_workspace_settings(base=dw, manifest={}, sha256="s").sha256 == "s"


@pytest.mark.asyncio
async def test_governance_service_fallback_and_rbac_paths() -> None:
    def _user(role: str = "TEAM_LEAD") -> UserIdentity:
        return UserIdentity(
            id=str(_USER_UUID),
            email="lead@orcia.test",
            display_name="Lead User",
            auth_mode="LOCAL",
            human_profile_archetype="ARCHITECT",
            platform_role=role,  # type: ignore[arg-type]
            primary_org_unit_id="ou-1",
        )

    saved: list[Any] = []
    store = SimpleNamespace(
        saved=saved,
        get_user_preferences=lambda *, workspace_id, user_id: build_default_user_preferences(
            workspace_id=workspace_id, user_id=user_id
        ),
        save_user_preferences=lambda *, workspace_id, user_id, prefs, record: (
            saved.append(prefs),
            prefs,
        )[1],
        get_workspace_settings=lambda wid: build_default_workspace_layer_settings(wid),
        save_workspace_settings=lambda *, workspace_id, settings, record: settings,
        get_team_mcp_frozen=lambda wid: None,
        set_team_mcp_frozen=lambda **kw: None,
        get_team_instructions=lambda wid: None,
        list_overrides=lambda: (),
    )
    svc = AssistantFourLevelGovernanceService()
    lead, obs = _user(role="TEAM_LEAD"), _user(role="OBSERVER")
    assert await svc._pg_ready() is False and svc._can_manage_workspace_or_team(lead) is True

    u_kw: dict[str, Any] = {
        "workspace_id": "w",
        "response_tone": "BALANCED",
        "favorite_format": "BULLETS",
        "default_hat": "QA",
        "personal_instructions": "",
    }
    with pytest.raises(ObserverModeReadOnlyError):
        await svc.update_user_preferences_async(obs, **u_kw)
    assert (await svc.update_user_preferences_async(lead, **u_kw)).default_hat == "QA"

    svc_s = AssistantFourLevelGovernanceService(store=store)
    await svc_s.update_user_preferences_async(lead, **u_kw)
    assert len(store.saved) == 1
    await svc_s.freeze_mcp_at_upper_layer_async(workspace_id="w", frozen=False)
    assert (
        await svc_s.get_user_preferences_async(workspace_id="w", user_id=lead.id)
    ).workspace_id == "w"
    assert (await svc_s.get_workspace_settings_async("w")).workspace_id == "w"
    ws_kw: dict[str, Any] = {
        "workspace_id": "w",
        "workspace_instructions": "W",
        "default_checked_sources": (),
        "recommended_agents": (),
        "arbitration_policy": "HUMAN_CONFIRMATION_REQUIRED",
    }
    await svc_s.update_workspace_settings_async(lead, **ws_kw)
    assert (
        len(await svc_s.assemble_five_layers_preview_async(workspace_id="w", user_id=lead.id)) == 5
    )
    assert (
        await svc_s.get_governance_view_async(lead, workspace_id="w")
    ).can_edit_workspace_layer is True
