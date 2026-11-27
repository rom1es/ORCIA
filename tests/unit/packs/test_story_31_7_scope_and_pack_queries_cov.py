"""Targeted branch coverage tests for Story 31.7 scope guards, pack queries & packs router."""

from __future__ import annotations

import io
import zipfile
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
import yaml

from orcia_api.routers import _packs_scope_guards as scope_guards
from orcia_api.routers import packs as packs_router
from orcia_core.orchestration._internal._sql_agents_pack_queries import (
    is_pack_bundle_visible_in_scope,
    resolve_pack_tier_for_row,
    should_include_catalog_row,
)
from orcia_core.packs import PackBundleNotFoundError, PackScopeEscalationForbiddenError
from orcia_core.permissions.models import UserIdentity

pytestmark = pytest.mark.story("31.7")


def _make_system_zip(slug: str = "sys-escalate") -> bytes:
    buf = io.BytesIO()
    apm = yaml.safe_dump(
        {
            "name": slug,
            "version": "1.0.0",
            "x-orcia": {
                "slug": slug,
                "bundle_kind": "SYSTEM",
                "scope_type": "WORKSPACE",
                "scope_id": "ws-1",
            },
        },
        sort_keys=False,
    )
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("apm.yml", apm)
    return buf.getvalue()


def _user(uid: str = "u-1") -> UserIdentity:
    return UserIdentity(
        id=uid,
        email=f"{uid}@orcia.local",
        display_name=uid,
        auth_mode="local",
        platform_role="MEMBER",
        human_profile_archetype="LEAD",
        primary_org_unit_id="team-1",
    )


def _req(path: str = "/api/v1/packs") -> Any:
    return SimpleNamespace(
        url=SimpleNamespace(path=path),
        headers={},
        query_params={},
        state=SimpleNamespace(),
        app=SimpleNamespace(state=SimpleNamespace()),
    )


@pytest.mark.asyncio
async def test_filter_visible_pack_rows_private_and_org_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller = _user("u-alice")
    fake_ev = SimpleNamespace(
        get_workspace=lambda wid: (
            SimpleNamespace(id=wid, owner_org_unit_id="team-sub") if wid == "ws-child" else None
        ),
        get_descendant_org_unit_ids=lambda oid: {"team-sub"} if oid == "bu-parent" else set(),
    )
    monkeypatch.setattr(
        scope_guards,
        "compute_caller_composer_scopes",
        AsyncMock(return_value=(caller, False, frozenset({"ws-child"}), frozenset({"team-1"}))),
    )
    monkeypatch.setattr(
        scope_guards, "get_auth_service", lambda _req: SimpleNamespace(evaluator=fake_ev)
    )

    def _r(slug: str, st: str, sid: str) -> dict[str, object]:
        return {"slug": slug, "bundle_kind": "CUSTOM", "scope_type": st, "scope_id": sid}

    rows = [
        _r("priv-ok", "PRIVATE_USER", "u-alice"),
        _r("priv-no", "PRIVATE_USER", "u-bob"),
        _r("team-ok", "TEAM", "team-1"),
        _r("bu-desc", "BU", "bu-parent"),
        _r("bu-no", "BU", "bu-other"),
        _r("ws-ok", "WORKSPACE", "ws-child"),
    ]
    visible = await scope_guards.filter_visible_pack_rows(_req(), rows)
    assert [r["slug"] for r in visible] == ["priv-ok", "team-ok", "bu-desc", "ws-ok"]


@pytest.mark.asyncio
async def test_scope_guards_import_system_delete_and_authorize_ws(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caller = _user("u-alice")
    monkeypatch.setattr(scope_guards, "enforce_pack_mutation_guard", lambda *_a, **_kw: caller)
    req = _req("/api/v1/packs/import")

    with pytest.raises(PackScopeEscalationForbiddenError):
        await scope_guards.resolve_and_authorize_import_scope(
            req, zip_bytes=_make_system_zip(), req_scope_type=None, req_scope_id=None
        )

    with pytest.raises(PackBundleNotFoundError):
        await scope_guards.enforce_pack_bundle_delete_guard(
            req,
            bundle_id="missing",
            import_svc=SimpleNamespace(_engine=object(), get_bundle=AsyncMock(return_value=None)),
        )

    no_eng = SimpleNamespace(_engine=None, get_bundle=AsyncMock(return_value=None))
    assert (
        await scope_guards.enforce_pack_bundle_delete_guard(req, bundle_id="m", import_svc=no_eng)
        == caller
    )

    custom = SimpleNamespace(
        _engine=object(),
        get_bundle=AsyncMock(
            return_value={"bundle_kind": "CUSTOM", "scope_type": "WORKSPACE", "scope_id": "ws-1"}
        ),
    )
    monkeypatch.setattr(
        scope_guards, "enforce_composer_scope_access", AsyncMock(return_value=(caller, "ws-1"))
    )
    assert (
        await scope_guards.enforce_pack_bundle_delete_guard(req, bundle_id="c", import_svc=custom)
        == caller
    )

    monkeypatch.setattr(
        scope_guards,
        "enforce_workspace_packs_access",
        AsyncMock(return_value=(caller, "ws-uuid-1")),
    )
    assert await scope_guards.authorize_agents_skills_scope(req, workspace_id="ws-slug") == (
        "ws-uuid-1",
        True,
        frozenset({"ws-uuid-1"}),
        frozenset(),
    )


def test_pack_tier_and_bundle_visibility_edges() -> None:
    assert (
        resolve_pack_tier_for_row(
            pack_slug="custom", bundle_kind="CUSTOM", active_priorities={}, workspace_scoped=True
        )
        is None
    )
    assert is_pack_bundle_visible_in_scope(
        scope_type=None, scope_id=None, ws_uuid="w1", ancestor_org_unit_ids=frozenset()
    )
    assert is_pack_bundle_visible_in_scope(
        scope_type="BU", scope_id="bu-1", ws_uuid="w1", ancestor_org_unit_ids=frozenset({"bu-1"})
    )
    assert not is_pack_bundle_visible_in_scope(
        scope_type="PRIVATE_USER", scope_id="u-1", ws_uuid="w1", ancestor_org_unit_ids=frozenset()
    )


@pytest.mark.parametrize(
    ("owner_ws", "bid", "slug", "bkind", "st", "sid", "expected"),
    [
        ("ws-1", None, None, None, None, None, True),
        ("ws-2", None, None, None, None, None, False),
        (None, "b1", "sys", "SYSTEM", "GLOBAL", "global", True),
        (None, "b2", "ws-p", "CUSTOM", "WORKSPACE", "ws-1", True),
        (None, "b3", "ws-x", "CUSTOM", "WORKSPACE", "ws-other", False),
        (None, "b4", "tm-p", "CUSTOM", "TEAM", "team-1", True),
        (None, "b5", "priv", "CUSTOM", "PRIVATE_USER", "u-1", False),
    ],
)
def test_should_include_non_admin_without_ws(
    owner_ws: str | None,
    bid: str | None,
    slug: str | None,
    bkind: str | None,
    st: str | None,
    sid: str | None,
    expected: bool,
) -> None:
    assert (
        should_include_catalog_row(
            workspace_id=None,
            ws_uuid=None,
            ancestor_orgs=frozenset(),
            effective_owner_ws=owner_ws,
            pack_bundle_id=bid,
            pack_slug=slug,
            bundle_kind=bkind,
            bundle_scope_type=st,
            bundle_scope_id=sid,
            active_priorities={},
            unrestricted=False,
            allowed_workspace_ids=frozenset({"ws-1"}),
            allowed_org_ids=frozenset({"team-1"}),
        )
        is expected
    )


@pytest.mark.asyncio
async def test_packs_router_pg_connectors_none_engine_and_health_dedup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    req = _req()
    monkeypatch.setattr(packs_router, "is_pg_runtime_active", lambda _r: True)
    monkeypatch.setattr(packs_router, "get_configured_db_engine", lambda _r: None)
    assert await packs_router._load_pg_connectors_by_kind(req) == {}

    monkeypatch.setattr(packs_router, "get_configured_db_engine", lambda _r: object())
    rec = SimpleNamespace(connector_kind="Git")
    monkeypatch.setattr(
        packs_router, "list_enterprise_connectors_from_postgres18", AsyncMock(return_value=[rec])
    )
    assert await packs_router._load_pg_connectors_by_kind(req) == {"git": rec}

    monkeypatch.setattr(
        packs_router,
        "list_enterprise_connectors_from_postgres18",
        AsyncMock(side_effect=RuntimeError("boom")),
    )
    assert await packs_router._load_pg_connectors_by_kind(req) == {}
    assert await packs_router._list_pg_bundles(SimpleNamespace(_engine=None)) == []

    shared = [{"slot_key": "repo", "scheme": "git", "connector_kind": "git", "required": True}]
    rows = [{"declared_slots": shared, "manifest": {}}, {"declared_slots": shared, "manifest": {}}]
    monkeypatch.setattr(packs_router, "filter_visible_pack_rows", AsyncMock(return_value=rows))
    monkeypatch.setattr(packs_router, "_load_pg_connectors_by_kind", AsyncMock(return_value={}))
    res = await packs_router.check_packs_connectors_health(req, SimpleNamespace(_engine=None))
    assert res.total_count == 1
