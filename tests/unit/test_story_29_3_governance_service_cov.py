"""Story 29.3 — Unit tests for `AssistantFourLevelGovernanceService` PG18 & fallback paths."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from orcia_core.orchestration.assistant_governance import AssistantFourLevelGovernanceService
from orcia_core.orchestration.assistant_governance_studio import (
    build_default_user_preferences,
    build_default_workspace_layer_settings,
)
from orcia_core.orchestration.errors import FunnelRuleViolationError, ObserverModeReadOnlyError
from orcia_core.permissions.models import UserIdentity

_WS_UUID = UUID("0195f293-0000-7000-8000-000000000101")
_ORG_UUID = UUID("0195f293-0000-7000-8000-000000000010")
_USER_UUID = UUID("0195f293-0000-7000-8000-000000000301")


class _FakeConn:
    def __init__(self, **cfg: Any) -> None:
        self.cfg = cfg

    async def __aenter__(self) -> _FakeConn:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(self, stmt: Any, _params: dict[str, Any] | None = None) -> SimpleNamespace:
        sql = str(stmt)
        if "WITH target_ws" in sql:
            rows = list(self.cfg.get("bundle_rows", []))
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))
        if "SELECT override_key, override_manifest_jsonb" in sql:
            rows = list(self.cfg.get("team_rows", []))
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))
        if "SELECT id, override_key, org_unit_id" in sql:
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: []))
        if "to_regclass" in sql:
            return SimpleNamespace(scalar=lambda: self.cfg.get("regclass"))
        if "FROM workspaces WHERE id::text" in sql:
            return SimpleNamespace(first=lambda: (_WS_UUID,))
        if "SELECT owner_org_unit_id FROM workspaces" in sql:
            return SimpleNamespace(first=lambda: (_ORG_UUID,))
        if "FROM users" in sql:
            return SimpleNamespace(first=lambda: (_USER_UUID,))
        return SimpleNamespace(first=lambda: None, scalar=lambda: None)


class _FakeEngine:
    def __init__(self, **cfg: Any) -> None:
        self.conn = _FakeConn(**cfg)

    def connect(self) -> _FakeConn:
        return self.conn

    def begin(self) -> _FakeConn:
        return self.conn


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


def _mem_store() -> Any:
    saved: list[Any] = []

    def _save_prefs(*, workspace_id: str, user_id: str, prefs: Any, record: Any) -> Any:
        saved.append(prefs)
        return prefs

    return SimpleNamespace(
        saved=saved,
        get_user_preferences=lambda *, workspace_id, user_id: build_default_user_preferences(
            workspace_id=workspace_id, user_id=user_id
        ),
        save_user_preferences=_save_prefs,
        get_workspace_settings=lambda wid: build_default_workspace_layer_settings(wid),
        save_workspace_settings=lambda *, workspace_id, settings, record: settings,
        get_team_mcp_frozen=lambda wid: None,
        set_team_mcp_frozen=lambda **kw: None,
        get_team_instructions=lambda wid: None,
        list_overrides=lambda: (),
    )


@pytest.mark.asyncio
async def test_governance_service_async_pg_and_fallback_paths() -> None:
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

    store = _mem_store()
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

    eng = _FakeEngine(
        regclass="workspace_customization_overrides",
        bundle_rows=[
            {"workspace_name": "Alpha", "user_display_name": "Lead", "override_layer": None}
        ],
        team_rows=[
            {
                "override_key": "k",
                "override_manifest_jsonb": {"mcp_frozen": True, "origin": "PLATFORM"},
            }
        ],
    )
    svc.set_engine(eng)  # type: ignore[arg-type]
    assert await svc._pg_ready() is True
    await svc.freeze_mcp_at_upper_layer_async(
        workspace_id=str(_WS_UUID), frozen=True, origin="PLATFORM"
    )
    await svc.get_user_preferences_async(workspace_id=str(_WS_UUID), user_id=lead.id)
    await svc.get_workspace_settings_async(str(_WS_UUID))
    await svc.update_user_preferences_async(lead, **{**u_kw, "workspace_id": str(_WS_UUID)})
    ws_kw["workspace_id"] = str(_WS_UUID)
    with pytest.raises(FunnelRuleViolationError):
        await svc.update_workspace_settings_async(lead, mcp_expose_assistant=True, **ws_kw)
    upd = await svc.update_workspace_settings_async(lead, mcp_expose_assistant=False, **ws_kw)
    assert upd.mcp_frozen_by_upper_layer is True and upd.mcp_frozen_origin == "PLATFORM"
    assert (
        len(
            await svc.assemble_five_layers_preview_async(
                workspace_id=str(_WS_UUID), user_id=lead.id, locale="en"
            )
        )
        == 5
    )
    assert (
        await svc.get_governance_view_async(lead, workspace_id=str(_WS_UUID), locale="en")
    ).workspace_id == str(_WS_UUID)
    svc.set_engine(None)
    assert await svc._pg_ready() is False
