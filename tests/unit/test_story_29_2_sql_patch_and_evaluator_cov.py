"""Story 29.2 (Layer 1a) — Unit tests for sql_workspace_patch & MatrixPermissionEvaluator."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from orcia_core.bootstrap._internal.sql_workspace_patch import (
    _decode_jsonb,
    _sync_patched_workspace_platform_settings,
    patch_workspace_on_postgres18,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    PrivateWorkspaceVisibilityLockedError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    CatalogAclEntry,
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
)


class _FakeConn:
    def __init__(
        self,
        *,
        ws_row: tuple[Any, ...] | None = None,
        user_row: tuple[Any, ...] | None = None,
        ps_rows: list[tuple[Any, ...]] | None = None,
    ) -> None:
        self.ws_row, self.user_row, self.ps_rows = ws_row, user_row, ps_rows or []
        self.executed: list[tuple[str, dict[str, Any]]] = []

    async def __aenter__(self) -> _FakeConn:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> SimpleNamespace:
        sql, bound = str(stmt), dict(params or {})
        self.executed.append((sql, bound))
        if "FROM workspaces w" in sql:
            return SimpleNamespace(first=lambda: self.ws_row)
        if "FROM users" in sql:
            return SimpleNamespace(first=lambda: self.user_row)
        if "FROM platform_settings" in sql:
            return SimpleNamespace(first=lambda: self.ps_rows[0] if self.ps_rows else None)
        return SimpleNamespace(first=lambda: None)


def _user(
    uid: str,
    role: str = "CONTRIBUTOR",
    ou: str = "ou-team",
    *,
    roles: tuple[str, ...] = (),
    groups: tuple[str, ...] = (),
) -> UserIdentity:
    return UserIdentity(
        id=uid,
        email=f"{uid}@orcia.test",
        display_name=uid,
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id=ou,
        transverse_groups=groups,
        roles=roles or (role,),
    )


def _ou(oid: str, unit_type: Any = "TEAM", parent_id: str | None = None) -> OrgUnitNode:
    return OrgUnitNode(id=oid, slug=f"s-{oid}", name=oid, unit_type=unit_type, parent_id=parent_id)


def test_decode_jsonb_variants() -> None:
    assert _decode_jsonb({"a": 1}) == {"a": 1}
    assert _decode_jsonb('{"k": "v"}') == {"k": "v"}
    assert _decode_jsonb("[1, 2]") == {}
    assert _decode_jsonb("{invalid") == {}
    assert _decode_jsonb(None) == {}


@pytest.mark.asyncio
async def test_sync_platform_settings_branches() -> None:
    ws_id = "0195f292-0000-7000-8000-000000000201"

    async def _sync(
        conn: _FakeConn, name: str = "A", vis: str = "STANDARD", ph: str = "BUILD"
    ) -> None:
        await _sync_patched_workspace_platform_settings(
            conn,
            ws_id_str=ws_id,
            ws_slug="a",
            next_name=name,
            next_ui_vis=vis,
            next_phase=ph,  # type: ignore[arg-type]
        )

    conn_none = _FakeConn(ps_rows=[(None,)])
    await _sync(conn_none)
    assert len(conn_none.executed) == 1

    ps = json.dumps(
        {"workspaces": ["bad", {"workspaceId": "o", "slug": "a", "name": "Old"}, {"id": "b"}]}
    )
    conn_slug = _FakeConn(ps_rows=[(ps,)])
    await _sync(conn_slug, "A2", "CONFIDENTIAL_RESTRICTED", "RUN")
    upd = [p for sql, p in conn_slug.executed if "UPDATE platform_settings" in sql]
    assert len(upd) == 1 and json.loads(upd[0]["value_jsonb"])["workspaces"][1]["name"] == "A2"

    conn_miss = _FakeConn(ps_rows=[({"workspaces": [{"id": "x", "slug": "z"}]},)])
    await _sync(conn_miss)
    assert not any("UPDATE platform_settings" in sql for sql, _ in conn_miss.executed)


@pytest.mark.asyncio
async def test_patch_workspace_pg18_errors_and_updates() -> None:
    ws_id = UUID("0195f292-0000-7000-8000-000000000210")
    ou_id = UUID("0195f292-0000-7000-8000-000000000010")
    actor_id = UUID("0195f292-0000-7000-8000-000000000301")

    async def _call(conn: _FakeConn, wid: str = str(ws_id), **kw: Any) -> Any:
        return await patch_workspace_on_postgres18(
            SimpleNamespace(begin=lambda: conn),
            workspace_id=wid,
            actor_user_id=kw.pop("actor_user_id", None),  # type: ignore[arg-type]
            actor_role=kw.pop("actor_role", "TEAM_LEAD"),
            **kw,
        )

    with pytest.raises(ResourceNotFoundError):
        await _call(_FakeConn(), wid="not-a-uuid")
    with pytest.raises(ResourceNotFoundError):
        await _call(_FakeConn(ws_row=None))

    std_row = (ws_id, "team-ws", "Team WS", ou_id, "STANDARD", 1.5, {}, "Team OU")
    with pytest.raises(PrivateWorkspaceVisibilityLockedError):
        await _call(_FakeConn(ws_row=std_row), visibility_mode="PRIVATE_USER")

    priv_row = (
        ws_id,
        "personal-u1",
        "My Space",
        ou_id,
        "CONFIDENTIAL_RESTRICTED",
        0.0,
        {"personal_owner_user_id": str(actor_id), "lifecycle_phase": "LEGACY"},
        None,
    )
    with pytest.raises(PrivateWorkspaceVisibilityLockedError):
        await _call(_FakeConn(ws_row=priv_row), visibility_mode="STANDARD")
    with pytest.raises(ValidationDomainError) as exc_name:
        await _call(_FakeConn(ws_row=std_row), name="   ")
    assert exc_name.value.detail_code == "ERR_WORKSPACE_EMPTY_NAME"
    with pytest.raises(ValidationDomainError):
        await _call(_FakeConn(ws_row=std_row), lifecycle_phase="INVALID")

    conn_upd = _FakeConn(
        ws_row=(ws_id, "ws-alpha", "Alpha", ou_id, "STANDARD", 2.25, "{}", "Alpha OU"),
        user_row=(actor_id, "TEAM_LEAD"),
        ps_rows=[({"workspaces": [{"workspaceId": str(ws_id), "name": "Alpha"}]},)],
    )
    res = await _call(
        conn_upd,
        actor_user_id=str(actor_id),
        name="  Alpha Updated  ",
        visibility_mode="CONFIDENTIAL_RESTRICTED",
        lifecycle_phase="run",
    )
    assert (res.name, res.visibility_mode, res.lifecycle_phase) == (
        "Alpha Updated",
        "CONFIDENTIAL_RESTRICTED",
        "RUN",
    )
    assert any("INSERT INTO workspace_memberships" in sql for sql, _ in conn_upd.executed)
    assert any("UPDATE platform_settings" in sql for sql, _ in conn_upd.executed)

    res_priv = await _call(_FakeConn(ws_row=priv_row), actor_user_id=str(actor_id))
    assert (res_priv.ui_visibility_mode, res_priv.visibility_mode, res_priv.lifecycle_phase) == (
        "PRIVATE_USER",
        "CONFIDENTIAL_RESTRICTED",
        "BUILD",
    )
    assert res_priv.personal_owner_user_id == str(actor_id)


def test_evaluator_org_unit_catalog_and_cycle_helpers() -> None:
    node_a, node_b = _ou("ou-a", "BU", "ou-b"), _ou("ou-b", "TEAM", "ou-a")
    acl = CatalogAclEntry(
        id="acl-1",
        resource_id="res-1",
        resource_uri="orcia://res/1",
        title="Res 1",
        visibility_scope="DRAFT",
        owner_org_unit_id="ou-a",
    )
    ev = MatrixPermissionEvaluator(org_units=(node_a, node_b), workspaces=(), catalog_acls=(acl,))
    assert ev.get_org_unit("s-ou-a") == node_a and ev.get_org_unit("missing") is None
    node_c = _ou("ou-c")
    assert ev.upsert_org_unit(node_c) == node_c and ev.has_org_unit("ou-c")
    ev.remove_org_unit_node("ou-c")
    ev.remove_org_unit_node("non-existent")
    assert not ev.has_org_unit("ou-c")
    assert ev.get_ancestor_org_unit_ids("ou-a") == {"ou-a", "ou-b"}
    assert ev.get_primary_catalog_acl("res-1") == acl and ev.get_primary_catalog_acl("x") is None
    assert (
        ev.get_catalog_acl_by_uri("orcia://res/1") == acl and ev.get_catalog_acl_by_uri("x") is None
    )


def test_evaluator_personal_workspace_rollup_and_guards() -> None:
    root, team, other = (
        _ou("ou-root", "ENTERPRISE"),
        _ou("ou-team", "TEAM", "ou-root"),
        _ou("ou-other", "TEAM", "ou-root"),
    )  # noqa: E501
    ws_priv = WorkspaceEntity(
        id="ws-priv",
        slug="personal-u1",
        name="Personal",
        owner_org_unit_id="ou-team",
        visibility_mode="CONFIDENTIAL_RESTRICTED",
        personal_owner_user_id="u-owner",
    )
    ws_std = WorkspaceEntity(id="ws-std", slug="ws-std", name="Std", owner_org_unit_id="ou-team")
    ev = MatrixPermissionEvaluator(org_units=(root, team, other), workspaces=(ws_priv, ws_std))

    owner_c, owner_o = _user("u-owner", "CONTRIBUTOR"), _user("u-owner", "OBSERVER")
    stranger = _user("u-stranger", "PLATFORM_ADMIN")
    assert ev.resolve_workspace_access(owner_c, "ws-missing") is None
    assert ev.resolve_workspace_access(stranger, "ws-priv") is None
    acc_c = ev.resolve_workspace_access(owner_c, "ws-priv")
    acc_o = ev.resolve_workspace_access(owner_o, "ws-priv")
    assert acc_c is not None and acc_c.access_mode == "CONTRIBUTOR_ACTION_REQUIRED"
    assert acc_o is not None and acc_o.access_mode == "READ_ONLY_OBSERVER"
    assert (
        ev.resolve_workspace_access(_user("u-s1", "CONTRIBUTOR", "", roles=("BU_LEAD",)), "ws-std")
        is None
    )  # noqa: E501
    assert ev.resolve_workspace_access(_user("u-s2", "BU_LEAD", "ou-other"), "ws-std") is None

    with pytest.raises(ResourceNotFoundError):
        ev.enforce_scope_mutation_guard(owner_c, "ws-missing")
    with pytest.raises(ScopeAccessDeniedError):
        ev.enforce_scope_mutation_guard(stranger, "ws-priv")
    with pytest.raises(ObserverModeReadOnlyError):
        ev.enforce_scope_mutation_guard(owner_o, "ws-priv")
    assert ev.enforce_scope_mutation_guard(owner_c, "ws-priv").workspace.id == "ws-priv"


def test_evaluator_catalog_acl_branches_and_module_access() -> None:
    acl_p = CatalogAclEntry(
        id="acl-p",
        resource_id="res-p",
        resource_uri="orcia://res/p",
        title="Pending",
        visibility_scope="PENDING_APPROVAL",
        owner_org_unit_id="ou-other",
        grantee_transverse_group="sec-guild",
        can_discover=True,
        can_execute=True,
        can_edit=True,
        can_admin=True,
    )
    ev = MatrixPermissionEvaluator(org_units=(_ou("ou-a"),), workspaces=(), catalog_acls=(acl_p,))
    eff_adm, _ = ev.evaluate_catalog_resource(_user("u-a", "PLATFORM_ADMIN", "ou-a"), "res-p")
    eff_g, _ = ev.evaluate_catalog_resource(
        _user("u-g", "CONTRIBUTOR", "ou-a", groups=("sec-guild",)), "res-p"
    )
    bu_dir = _user("u-d", "BU_DIRECTOR", "ou-a")
    eff_d, _ = ev.evaluate_catalog_resource(bu_dir, "res-p")
    eff_o, _ = ev.evaluate_catalog_resource(
        _user("u-o", "OBSERVER", "ou-a", groups=("sec-guild",)), "res-p"
    )
    assert eff_adm.can_admin and eff_g.can_execute and eff_d.can_discover
    assert eff_o.can_discover and not eff_o.can_edit and not eff_o.can_admin
    ev.enforce_module_access(bu_dir, "finops", has_workspaces=True)
    with pytest.raises(ScopeAccessDeniedError):
        ev.enforce_module_access(_user("u-c", "CONTRIBUTOR", "ou-a"), "admin", has_workspaces=True)
