"""Branch coverage tests for Story 31.4 run-lock SQL, service, and API helpers (<= 300 L)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult

from orcia_core.packs import (
    EffectiveSlotBindingView,
    PackSlotSpec,
    PackSlotTargetKind,
    PinnedPackManifestEntry,
    WorkspacePacksService,
)
from orcia_core.packs._internal._sql_run_lock_pinning import (
    pin_workflow_v2_run_lock_sql,
    validate_and_snapshot_workspace_packs_sql,
)
from orcia_core.packs._internal._sql_run_lock_reads import (
    attach_pinned_packs_to_run_lock_sql,
    get_run_lock_manifest_sql,
    map_v2_status_to_workflow_run_status,
    sync_workflow_v2_run_status_sql,
)
from orcia_core.packs.slot_guard import is_binding_compatible_with_slot

WS_UUID = "0195f000-0000-7000-8000-000000000701"
RUN_UUID = "0195f000-0000-7000-8000-000000000777"
RUN_ID = f"run-{RUN_UUID}"


@pytest.mark.asyncio
async def test_run_lock_pinning_reads_and_service_forwarding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert map_v2_status_to_workflow_run_status("WAITING_FOR_HUMAN_ARBITRATION") == (
        "WAITING_FOR_HUMAN_ARBITRATION"
    )
    assert map_v2_status_to_workflow_run_status("PAUSED_BUDGET_EXCEEDED") == (
        "PAUSED_BUDGET_EXCEEDED"
    )
    assert not is_binding_compatible_with_slot(
        EffectiveSlotBindingView(
            workspace_id=WS_UUID,
            pack_slug="p",
            slot_key="k",
            target_kind=PackSlotTargetKind.INTERNAL,
            is_effective_bound=True,
        ),
        PackSlotSpec(slot_key="k", scheme="git"),
    )

    state: dict[str, Any] = {"ws": WS_UUID, "wf": None, "uid": RUN_UUID, "rlm": None}
    now = datetime(2026, 11, 26, tzinfo=UTC)

    def _h(sql: str, _p: dict[str, Any]) -> FakeSqlResult:
        if "FROM workspaces" in sql:
            return FakeSqlResult(scalar_val=state["ws"], has_scalar=True)
        if "FROM workflow_definitions" in sql:
            return FakeSqlResult(scalar_val=state["wf"] or "wf-def-1", has_scalar=True)
        if "FROM users" in sql:
            return FakeSqlResult(scalar_val=state["uid"], has_scalar=True)
        if "SELECT rlm.run_id::text" in sql:
            if state["rlm"] is None:
                return FakeSqlResult()
            return FakeSqlResult(rows=[state["rlm"]])
        if "SELECT manifest_jsonb FROM run_lock_manifests" in sql:
            return FakeSqlResult(
                rows=[(json.dumps({"run_id": RUN_ID, "pinned_packs": []}),)] if state["rlm"] else []
            )
        return FakeSqlResult()

    eng: Any = FakeSqlEngine(_h)
    assert await validate_and_snapshot_workspace_packs_sql(eng, workspace_id=None) == []
    assert await validate_and_snapshot_workspace_packs_sql(eng, workspace_id=WS_UUID) == []

    assert (
        await pin_workflow_v2_run_lock_sql(
            eng,
            run_id=RUN_ID,
            workspace_id=None,
            workflow_id="w",
            workflow_slug="w",
            workflow_version="1",
            workflow_sha256="a" * 64,
            status="RUNNING",
            actor_user_id=None,
            pinned_packs=[],
        )
        is None
    )
    assert (
        await pin_workflow_v2_run_lock_sql(
            eng,
            run_id="bad",
            workspace_id=WS_UUID,
            workflow_id="w",
            workflow_slug="w",
            workflow_version="1",
            workflow_sha256="a" * 64,
            status="RUNNING",
            actor_user_id=None,
            pinned_packs=[],
        )
        is None
    )
    state["ws"] = None
    assert (
        await pin_workflow_v2_run_lock_sql(
            eng,
            run_id=RUN_ID,
            workspace_id=WS_UUID,
            workflow_id="w",
            workflow_slug="w",
            workflow_version="1",
            workflow_sha256="a" * 64,
            status="RUNNING",
            actor_user_id=None,
            pinned_packs=[],
        )
        is None
    )
    state["ws"] = WS_UUID
    res = await pin_workflow_v2_run_lock_sql(
        eng,
        run_id=RUN_ID,
        workspace_id=WS_UUID,
        workflow_id="w",
        workflow_slug="w",
        workflow_version="1.0.0",
        workflow_sha256="a" * 64,
        status="RUNNING",
        actor_user_id="not-a-uuid",
        pinned_packs=[],
        v2_run_payload={"workflow_title": "W", "actor_slug": "bot", "state": {"ok": 1}},
    )
    assert res is not None and len(res[1]) == 64

    await sync_workflow_v2_run_status_sql(eng, run_id="bad", status="COMPLETED")
    await sync_workflow_v2_run_status_sql(eng, run_id=RUN_ID, status="COMPLETED")
    assert await get_run_lock_manifest_sql(eng, run_id="bad") is None
    assert await get_run_lock_manifest_sql(eng, run_id=RUN_ID) is None
    state["rlm"] = (
        RUN_UUID,
        WS_UUID,
        json.dumps(
            {"run_id": RUN_ID, "workflow_id": "w", "pinned_packs": [], "resolved_pack_slots": []}
        ),
        "c" * 64,
        now,
    )
    got = await get_run_lock_manifest_sql(eng, run_id=RUN_ID)
    assert got is not None and got["workspace_id"] == WS_UUID

    entry = PinnedPackManifestEntry(
        pack_bundle_id="b1",
        pack_slug="alpha",
        version="1.0.0",
        archive_sha256="a" * 64,
        priority_order=1,
    )
    await attach_pinned_packs_to_run_lock_sql(eng, run_id=RUN_ID, pinned_packs=[])
    await attach_pinned_packs_to_run_lock_sql(eng, run_id="bad", pinned_packs=[entry])
    await attach_pinned_packs_to_run_lock_sql(eng, run_id=RUN_ID, pinned_packs=[entry])
    state["rlm"] = None
    await attach_pinned_packs_to_run_lock_sql(eng, run_id=RUN_ID, pinned_packs=[entry])

    svc = WorkspacePacksService()
    svc.set_engine(eng)
    for fn_name, mod_fn in (
        ("list_workspace_packs_sql", "orcia_core.packs.workspace_packs_service"),
        ("bind_workspace_pack_slots_sql", "orcia_core.packs.workspace_packs_service"),
        ("activate_workspace_pack_sql", "orcia_core.packs.workspace_packs_service"),
        ("reorder_workspace_packs_sql", "orcia_core.packs.workspace_packs_service"),
    ):
        monkeypatch.setattr(f"{mod_fn}.{fn_name}", AsyncMock(return_value=[]))
    assert await svc.list_workspace_packs(WS_UUID) == []
    assert (
        await svc.bind_pack_slots(workspace_id=WS_UUID, pack_slug="a", bindings=[], actor_id="u")
        == []
    )
    await svc.activate_pack(workspace_id=WS_UUID, pack_slug="a", actor_id="u")
    await svc.reorder_packs(workspace_id=WS_UUID, ordered_pack_slugs=["a"], actor_id="u")
    await svc.enforce_run_start_readiness(workspace_id=WS_UUID)
    await svc.pin_run_lock(
        run_id=RUN_ID,
        workspace_id=WS_UUID,
        workflow_id="w",
        workflow_slug="w",
        workflow_version="1",
        workflow_sha256="a" * 64,
        status="RUNNING",
        actor_user_id=None,
        pinned_packs=[],
    )
    await svc.sync_run_status(run_id=RUN_ID, status="COMPLETED")
    await svc.attach_pinned_packs_to_run_lock(run_id=RUN_ID, pinned_packs=[entry])
    await svc.get_run_lock(run_id=RUN_ID)
