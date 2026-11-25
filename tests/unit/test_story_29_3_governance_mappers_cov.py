"""Story 29.3 — Unit tests for governance SQL mappers and repository."""

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
    resolve_optional_user_uuid,
    resolve_ws_context,
    row_to_override_record,
    rows_to_mode_a_bundle,
)
from orcia_core.orchestration._internal.sql_assistant_governance import (
    SqlAssistantGovernanceRepository,
)
from orcia_core.orchestration.assistant_governance_models import (
    AssistantCustomizationOverrideRecord,
)
from orcia_core.orchestration.assistant_governance_studio import (
    build_default_user_preferences,
    build_default_workspace_layer_settings,
)

_WS_UUID = UUID("0195f293-0000-7000-8000-000000000101")
_ORG_UUID = UUID("0195f293-0000-7000-8000-000000000010")
_USER_UUID = UUID("0195f293-0000-7000-8000-000000000301")
_URI = "orcia://system/bootstrap/assistant-agent"


class _FakeConn:
    def __init__(self, **cfg: Any) -> None:
        self.cfg = cfg
        self.executed: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> _FakeConn:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> SimpleNamespace:
        sql = str(stmt)
        self.executed.append((sql, dict(params or {})))
        if "WITH target_ws" in sql:
            rows = list(self.cfg.get("bundle_rows", []))
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))
        if "SELECT override_key, override_manifest_jsonb" in sql:
            rows = list(self.cfg.get("team_rows", []))
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))
        if "SELECT id, override_key, org_unit_id" in sql:
            rows = list(self.cfg.get("override_rows", []))
            return SimpleNamespace(mappings=lambda: SimpleNamespace(all=lambda: rows))
        if "to_regclass" in sql:
            return SimpleNamespace(scalar=lambda: self.cfg.get("regclass"))
        if "FROM workspaces WHERE id::text" in sql:
            return SimpleNamespace(first=lambda: self.cfg.get("ws_row"))
        if "SELECT owner_org_unit_id FROM workspaces" in sql:
            return SimpleNamespace(first=lambda: self.cfg.get("org_row"))
        if "FROM users" in sql:
            return SimpleNamespace(first=lambda: self.cfg.get("user_row"))
        return SimpleNamespace(first=lambda: None, scalar=lambda: None)


class _FakeEngine:
    def __init__(self, **cfg: Any) -> None:
        self.conn = _FakeConn(**cfg)

    def connect(self) -> _FakeConn:
        return self.conn

    def begin(self) -> _FakeConn:
        return self.conn


@pytest.mark.asyncio
async def test_sql_governance_queries_and_mappers() -> None:
    assert decode_manifest({"k": 1}) == {"k": 1}
    assert decode_manifest('{"k": "v"}') == {"k": "v"}
    assert decode_manifest("[1]") == {} and decode_manifest("  ") == {}
    assert decode_manifest(None) == {}

    c_hit: Any = _FakeConn(user_row=(_USER_UUID,), ws_row=(_WS_UUID,), org_row=(_ORG_UUID,))
    c_miss: Any = _FakeConn(user_row=(None,), ws_row=None)
    c_noorg: Any = _FakeConn(ws_row=(_WS_UUID,), org_row=None)
    assert await resolve_optional_user_uuid(c_hit, user_id="u1", email="a@b.c") == _USER_UUID
    assert await resolve_optional_user_uuid(c_miss, user_id="u1") is None
    assert await resolve_ws_context(c_hit, "ws") == (str(_WS_UUID), _WS_UUID, _ORG_UUID)
    assert await resolve_ws_context(c_miss, " ws ") == ("ws", None, None)
    assert await resolve_ws_context(c_noorg, "ws") == (str(_WS_UUID), _WS_UUID, None)

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
async def test_sql_assistant_governance_repository_paths() -> None:
    repo_nr = SqlAssistantGovernanceRepository(_FakeEngine(regclass=None))  # type: ignore[arg-type]
    assert await repo_nr.pg_tables_ready() is False

    eng = _FakeEngine(
        regclass="workspace_customization_overrides",
        ws_row=(_WS_UUID,),
        org_row=(_ORG_UUID,),
        user_row=(_USER_UUID,),
        bundle_rows=[
            {
                "workspace_name": "Alpha",
                "user_display_name": "Lead",
                "override_layer": "USER",
                "override_manifest_jsonb": {"default_hat": "TECH_LEAD"},
                "sha256": "su",
            },
            {
                "workspace_name": "Alpha",
                "user_display_name": "Lead",
                "override_layer": "TEAM",
                "override_manifest_jsonb": {"team_instructions": "Rule", "mcp_frozen": True},
                "sha256": "st",
            },
        ],
        team_rows=[{"override_key": "k", "override_manifest_jsonb": {"team_instructions": "Rule"}}],
        override_rows=[
            {
                "id": "o1",
                "override_key": "k1",
                "org_unit_id": _ORG_UUID,
                "workspace_id": _WS_UUID,
                "user_id": None,
                "target_uri": _URI,
                "override_layer": "WORKSPACE",
                "override_manifest_jsonb": {},
                "sha256": "sw",
            }
        ],
    )
    repo = SqlAssistantGovernanceRepository(eng)  # type: ignore[arg-type]
    assert await repo.pg_tables_ready() is True and await repo.pg_tables_ready() is True
    up, ws, ti, wl, ul = await repo.get_mode_a_layers_bundle_with_labels(
        workspace_id=str(_WS_UUID), user_id=str(_USER_UUID), user_email="u@orcia.test"
    )
    assert (up.default_hat, ws.mcp_frozen_by_upper_layer, ti, wl, ul) == (
        "TECH_LEAD",
        True,
        "Rule",
        "Alpha",
        "Lead",
    )
    assert (
        await repo.get_user_preferences(workspace_id=str(_WS_UUID), user_id=str(_USER_UUID))
    ).default_hat == "TECH_LEAD"
    assert (await repo.get_workspace_settings(str(_WS_UUID))).mcp_frozen_origin == "TEAM"
    assert (await repo.get_team_layer_state(str(_WS_UUID)))[0] == "Rule"

    rec = AssistantCustomizationOverrideRecord(
        id="",
        override_key="k",
        org_unit_id=None,
        workspace_id=str(_WS_UUID),
        user_id=str(_USER_UUID),
        target_uri=_URI,
        override_layer="USER",
        override_manifest_jsonb={},
        sha256="su",
    )
    await repo.upsert_user_preferences(
        workspace_id=str(_WS_UUID), user_id=str(_USER_UUID), user_email=None, prefs=up, record=rec
    )
    await repo.upsert_workspace_settings(workspace_id=str(_WS_UUID), settings=ws, record=rec)
    await repo.set_team_mcp_frozen(workspace_id=str(_WS_UUID), frozen=True, origin="PLATFORM")
    await repo.set_team_mcp_frozen(workspace_id=str(_WS_UUID), frozen=False)
    assert len(await repo.list_overrides(workspace_id=str(_WS_UUID))) == 1
    assert any("DELETE FROM workspace_customization_overrides" in s for s, _ in eng.conn.executed)

    repo_u = SqlAssistantGovernanceRepository(_FakeEngine(ws_row=None, user_row=None))  # type: ignore[arg-type]
    assert (await repo_u.get_mode_a_layers_bundle_with_labels(workspace_id="ws", user_id="u"))[
        3:
    ] == (None, None)
    await repo_u.upsert_user_preferences(
        workspace_id="ws", user_id="u", user_email=None, prefs=up, record=rec
    )
    await repo_u.set_team_mcp_frozen(workspace_id="ws", frozen=True)
    await repo_u.upsert_workspace_settings(workspace_id="ws", settings=ws, record=rec)
    assert await repo_u.list_overrides(workspace_id="ws") == ()
