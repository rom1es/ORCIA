"""Branch coverage tests for Story 31.4 SQL queries, views & run-lock pin guard (<= 300 L)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult

from orcia_core.packs._internal._sql_workspace_pack_queries import (
    decode_declared_slots,
    is_bundle_visible_to_workspace_conn,
    is_bundle_visible_with_ancestors,
    load_ancestor_org_unit_ids_conn,
    load_effective_slot_bindings_conn,
    resolve_bundle_for_workspace_conn,
    resolve_workspace_identity_conn,
)
from orcia_core.packs.errors import PackActivationInvalidError, PackBundleNotFoundError
from orcia_core.permissions.errors import ResourceNotFoundError, ScopeAccessDeniedError

WS_UUID = "0195f000-0000-7000-8000-000000000701"
OU_UUID = "0195f000-0000-7000-8000-000000000702"
B_UUID = "0195f000-0000-7000-8000-000000000703"


@pytest.mark.asyncio
async def test_queries_decode_identity_ancestors_visibility_and_bindings() -> None:
    assert decode_declared_slots([{"slot_key": "repo", "scheme": "git"}])[0].slot_key == "repo"
    assert decode_declared_slots('{"not": "list"}') == []
    assert decode_declared_slots(123) == []

    now = datetime(2026, 11, 26, tzinfo=UTC)

    def _h(sql: str, p: dict[str, Any]) -> FakeSqlResult:
        if "FROM workspaces" in sql:
            if p.get("ws") == "missing":
                return FakeSqlResult()
            return FakeSqlResult(rows=[(WS_UUID, OU_UUID)])
        if "WITH RECURSIVE anc" in sql:
            return FakeSqlResult(rows=[(OU_UUID,), ("ou-parent",)])
        if "FROM workspace_pack_slot_bindings" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": "sb-1",
                        "workspace_id": WS_UUID,
                        "pack_bundle_id": B_UUID,
                        "pack_slug": "alpha",
                        "slot_key": "repo",
                        "target_kind": "WORKSPACE_DATASOURCE",
                        "target_id": "ds-1",
                        "bound_datasource_id": "ds-1",
                        "bound_connector_id": None,
                        "connector_scheme": "git",
                        "bound_by": "u-1",
                        "bound_at": now,
                        "live_ds_id": "ds-1",
                        "live_ds_uri": "git://r",
                        "live_ds_alias": "R",
                        "live_ec_id": None,
                        "live_ec_url": None,
                        "live_ec_name": None,
                        "live_ec_enabled": None,
                    },
                    {
                        "id": "sb-2",
                        "workspace_id": WS_UUID,
                        "pack_bundle_id": B_UUID,
                        "pack_slug": "alpha",
                        "slot_key": "ec",
                        "target_kind": "ENTERPRISE_CONNECTOR",
                        "target_id": "ec-1",
                        "bound_datasource_id": None,
                        "bound_connector_id": "ec-1",
                        "connector_scheme": "git",
                        "bound_by": "u-1",
                        "bound_at": "2026-11-26T00:00:00Z",
                        "live_ds_id": None,
                        "live_ds_uri": None,
                        "live_ds_alias": None,
                        "live_ec_id": "ec-1",
                        "live_ec_url": "https://gitlab",
                        "live_ec_name": "GL",
                        "live_ec_enabled": True,
                    },
                    {
                        "id": "sb-3",
                        "workspace_id": WS_UUID,
                        "pack_bundle_id": B_UUID,
                        "pack_slug": "alpha",
                        "slot_key": "int",
                        "target_kind": "INTERNAL",
                        "target_id": "internal:int",
                        "bound_datasource_id": None,
                        "bound_connector_id": None,
                        "connector_scheme": None,
                        "bound_by": "u-1",
                        "bound_at": now,
                        "live_ds_id": None,
                        "live_ds_uri": None,
                        "live_ds_alias": None,
                        "live_ec_id": None,
                        "live_ec_url": None,
                        "live_ec_name": None,
                        "live_ec_enabled": None,
                    },
                ]
            )
        return FakeSqlResult()

    conn = FakeSqlEngine(_h).connect()._conn
    with pytest.raises(ResourceNotFoundError):
        await resolve_workspace_identity_conn(conn, "   ")  # type: ignore[arg-type]
    with pytest.raises(ResourceNotFoundError):
        await resolve_workspace_identity_conn(conn, "missing")  # type: ignore[arg-type]
    assert await resolve_workspace_identity_conn(conn, WS_UUID) == (WS_UUID, OU_UUID)  # type: ignore[arg-type]

    assert await load_ancestor_org_unit_ids_conn(conn, None) == frozenset()  # type: ignore[arg-type]
    ancs = await load_ancestor_org_unit_ids_conn(conn, OU_UUID)  # type: ignore[arg-type]
    assert "ou-parent" in ancs
    assert is_bundle_visible_with_ancestors(
        scope_type="GLOBAL", scope_id="global", ws_uuid=WS_UUID, ancestor_org_unit_ids=ancs
    )
    assert is_bundle_visible_with_ancestors(
        scope_type="WORKSPACE", scope_id=WS_UUID, ws_uuid=WS_UUID, ancestor_org_unit_ids=ancs
    )
    assert is_bundle_visible_with_ancestors(
        scope_type="BU", scope_id="ou-parent", ws_uuid=WS_UUID, ancestor_org_unit_ids=ancs
    )
    assert not is_bundle_visible_with_ancestors(
        scope_type="OTHER", scope_id="x", ws_uuid=WS_UUID, ancestor_org_unit_ids=ancs
    )
    assert await is_bundle_visible_to_workspace_conn(
        conn,
        scope_type="TEAM",
        scope_id=OU_UUID,
        ws_uuid=WS_UUID,
        ws_org_unit_id=OU_UUID,  # type: ignore[arg-type]
    )
    loaded = await load_effective_slot_bindings_conn(conn, WS_UUID)  # type: ignore[arg-type]
    assert loaded["alpha"]["repo"].is_effective_bound is True
    assert loaded["alpha"]["ec"].target_display_name == "GL"
    assert loaded["alpha"]["int"].target_uri == "orcia://internal/int"


@pytest.mark.asyncio
async def test_resolve_bundle_branches_and_list_workspace_packs() -> None:
    def _empty(_sql: str, _p: dict[str, Any]) -> FakeSqlResult:
        return FakeSqlResult()

    conn_empty = FakeSqlEngine(_empty).connect()._conn
    with pytest.raises(PackBundleNotFoundError):
        await resolve_bundle_for_workspace_conn(
            conn_empty,
            ws_uuid=WS_UUID,
            ws_org_unit_id=OU_UUID,
            pack_slug="x",
            bundle_id="b-1",  # type: ignore[arg-type]
        )

    def _hidden(_sql: str, _p: dict[str, Any]) -> FakeSqlResult:
        if "declarative_pack_bundles" in _sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": B_UUID,
                        "scope_type": "WORKSPACE",
                        "scope_id": "other-ws",
                        "status": "PUBLISHED",
                        "slug": "x",
                    }
                ]
            )
        return FakeSqlResult()

    with pytest.raises(ScopeAccessDeniedError):
        await resolve_bundle_for_workspace_conn(
            FakeSqlEngine(_hidden).connect()._conn,  # type: ignore[arg-type]
            ws_uuid=WS_UUID,
            ws_org_unit_id=OU_UUID,
            pack_slug="x",
            version="1.0.0",
        )

    def _draft(_sql: str, _p: dict[str, Any]) -> FakeSqlResult:
        if "declarative_pack_bundles" in _sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": B_UUID,
                        "scope_type": "GLOBAL",
                        "scope_id": "global",
                        "status": "DRAFT",
                        "slug": "x",
                    }
                ]
            )
        return FakeSqlResult()

    with pytest.raises(PackActivationInvalidError):
        await resolve_bundle_for_workspace_conn(
            FakeSqlEngine(_draft).connect()._conn,  # type: ignore[arg-type]
            ws_uuid=WS_UUID,
            ws_org_unit_id=OU_UUID,
            pack_slug="x",
        )
