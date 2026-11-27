"""Branch coverage tests for Story 31.4 SQL workspace pack views & pin guard (<= 300 L)."""

from __future__ import annotations

from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult

from orcia_core.kernel.errors import ResourcePinnedByActiveRunsError
from orcia_core.packs._internal._sql_workspace_pack_views import (
    list_workspace_packs_sql,
    load_active_workspace_packs_for_run_conn,
)
from orcia_core.packs.errors import PackActivationInvalidError, PackSlotUnboundError
from orcia_core.storage.run_lock_guard import (
    assert_pack_bundle_not_pinned_by_active_runs_conn,
    assert_resource_not_pinned_by_active_runs_conn,
)

WS_UUID = "0195f000-0000-7000-8000-000000000701"
OU_UUID = "0195f000-0000-7000-8000-000000000702"
B_UUID = "0195f000-0000-7000-8000-000000000703"


@pytest.mark.asyncio
async def test_list_workspace_packs_and_active_pack_loading_branches() -> None:
    def _list_h(sql: str, _p: dict[str, Any]) -> FakeSqlResult:
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(WS_UUID, OU_UUID)])
        if "FROM declarative_pack_bundles" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": "b-hide",
                        "pack_id": "p-h",
                        "slug": "hide",
                        "name": "H",
                        "version": "1",
                        "bundle_kind": "IMPORTED",
                        "scope_type": "WORKSPACE",
                        "scope_id": "ws-other",
                        "status": "PUBLISHED",
                        "archive_sha256": "a" * 64,
                        "cas_object_key": None,
                        "declared_slots_jsonb": [],
                        "author": None,
                        "description": "",
                    },
                    {
                        "id": B_UUID,
                        "pack_id": "p-a",
                        "slug": "alpha",
                        "name": "A",
                        "version": "1",
                        "bundle_kind": "IMPORTED",
                        "scope_type": "GLOBAL",
                        "scope_id": "global",
                        "status": "PUBLISHED",
                        "archive_sha256": "b" * 64,
                        "cas_object_key": "cas/a",
                        "declared_slots_jsonb": [
                            {"slot_key": "repo", "scheme": "git", "required": True}
                        ],
                        "author": "ORCIA",
                        "description": "desc",
                    },
                ]
            )
        if "FROM workspace_pack_activations" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "pack_bundle_id": B_UUID,
                        "pack_slug": "alpha",
                        "priority_order": 1,
                        "is_active": True,
                        "activated_by": "u-1",
                        "activated_at": "2026-11-26T00:00:00Z",
                    }
                ]
            )
        return FakeSqlResult()

    packs = await list_workspace_packs_sql(FakeSqlEngine(_list_h), WS_UUID)  # type: ignore[arg-type]
    assert len(packs) == 1
    assert packs[0].is_active is True and packs[0].missing_slots == ["repo"]

    def _mk_conn(
        bundle: dict[str, Any] | None, *, ws_found: bool, active: list[dict[str, Any]]
    ) -> Any:
        def _h(sql: str, _p: dict[str, Any]) -> FakeSqlResult:
            if "FROM declarative_pack_bundles" in sql:
                return FakeSqlResult(mappings=[bundle] if bundle else [])
            if "FROM workspaces" in sql:
                return FakeSqlResult(rows=[(WS_UUID,)] if ws_found else [])
            if "FROM workspace_pack_activations" in sql:
                return FakeSqlResult(mappings=active)
            return FakeSqlResult()

        return FakeSqlEngine(_h).connect()._conn

    req_b = {
        "id": B_UUID,
        "pack_id": "p-a",
        "slug": "alpha",
        "declared_slots_jsonb": [{"slot_key": "repo", "scheme": "git", "required": True}],
    }
    noreq_b = {"id": B_UUID, "pack_id": "p-b", "slug": "beta", "declared_slots_jsonb": []}

    assert (
        await load_active_workspace_packs_for_run_conn(
            _mk_conn(None, ws_found=True, active=[]), workspace_id=None
        )
        == []
    )
    assert (
        await load_active_workspace_packs_for_run_conn(
            _mk_conn(None, ws_found=False, active=[]), workspace_id="x"
        )
        == []
    )
    with pytest.raises(PackSlotUnboundError):
        await load_active_workspace_packs_for_run_conn(
            _mk_conn(req_b, ws_found=True, active=[]), workspace_id=None, workflow_pack_id="p-a"
        )
    with pytest.raises(PackActivationInvalidError):
        await load_active_workspace_packs_for_run_conn(
            _mk_conn(noreq_b, ws_found=True, active=[]), workspace_id=None, workflow_pack_id="p-b"
        )
    with pytest.raises(PackActivationInvalidError):
        await load_active_workspace_packs_for_run_conn(
            _mk_conn(noreq_b, ws_found=False, active=[]), workspace_id="ws", workflow_pack_id="p-b"
        )
    with pytest.raises(PackSlotUnboundError):
        await load_active_workspace_packs_for_run_conn(
            _mk_conn(req_b, ws_found=True, active=[]), workspace_id=WS_UUID, workflow_pack_id="p-a"
        )
    with pytest.raises(PackActivationInvalidError):
        await load_active_workspace_packs_for_run_conn(
            _mk_conn(noreq_b, ws_found=True, active=[]),
            workspace_id=WS_UUID,
            workflow_pack_id="p-b",
        )
    assert (
        await load_active_workspace_packs_for_run_conn(
            _mk_conn(None, ws_found=True, active=[]), workspace_id=WS_UUID
        )
        == []
    )
    pinned = await load_active_workspace_packs_for_run_conn(
        _mk_conn(
            noreq_b,
            ws_found=True,
            active=[
                {
                    "pack_bundle_id": B_UUID,
                    "pack_id": "p-b",
                    "slug": "beta",
                    "version": "1.0.0",
                    "archive_sha256": "a" * 64,
                    "declared_slots_jsonb": [],
                    "priority_order": 1,
                }
            ],
        ),
        workspace_id=WS_UUID,
        workflow_pack_id="p-b",
    )
    assert len(pinned) == 1


@pytest.mark.asyncio
async def test_run_lock_guard_edge_branches() -> None:
    no_tbl_conn = (
        FakeSqlEngine(lambda _s, _p: FakeSqlResult(scalar_val=False, has_scalar=True))
        .connect()
        ._conn
    )
    await assert_resource_not_pinned_by_active_runs_conn(
        no_tbl_conn, target_kind="WORKSPACE_DATASOURCE", target_id="d1"
    )  # type: ignore[arg-type]
    pin_conn = (
        FakeSqlEngine(
            lambda s, _p: (
                FakeSqlResult(scalar_val=True, has_scalar=True)
                if "to_regclass" in s
                else FakeSqlResult(scalar_val=1, has_scalar=True)
            )
        )
        .connect()
        ._conn
    )
    with pytest.raises(ResourcePinnedByActiveRunsError):
        await assert_resource_not_pinned_by_active_runs_conn(
            pin_conn, target_kind="WORKSPACE_DATASOURCE", target_id="d1"
        )  # type: ignore[arg-type]
    ok_conn = (
        FakeSqlEngine(
            lambda s, _p: (
                FakeSqlResult(scalar_val=True, has_scalar=True)
                if "to_regclass" in s
                else FakeSqlResult(scalar_val=None, has_scalar=True)
            )
        )
        .connect()
        ._conn
    )
    await assert_pack_bundle_not_pinned_by_active_runs_conn(
        ok_conn, bundle_id=B_UUID, slug="alpha", version=None
    )  # type: ignore[arg-type]
    await assert_pack_bundle_not_pinned_by_active_runs_conn(
        ok_conn, bundle_id=B_UUID, slug=None, version=None
    )  # type: ignore[arg-type]
