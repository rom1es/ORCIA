"""Branch coverage tests for Story 31.4 slot bindings, mutations & reorder (<= 300 L)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import DBAPIError
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult

from orcia_core.packs._internal._sql_workspace_slot_bindings import (
    _is_connector_kind_compatible,
    bind_workspace_pack_slots_conn,
    bind_workspace_pack_slots_sql,
)
from orcia_core.packs.errors import PackSlotBindingInvalidError
from orcia_core.packs.models import PackSlotTargetKind
from orcia_core.packs.slot_guard import SlotBindingInput

WS_UUID = "0195f000-0000-7000-8000-000000000701"
OU_UUID = "0195f000-0000-7000-8000-000000000702"
B_UUID = "0195f000-0000-7000-8000-000000000703"
DS_UUID = "0195f000-0000-7000-8000-000000000704"
EC_UUID = "0195f000-0000-7000-8000-000000000705"


def _dbapi_err(msg: str) -> DBAPIError:
    return DBAPIError("stmt", {}, Exception(msg))


@pytest.mark.asyncio
async def test_slot_bindings_all_validation_and_happy_branches() -> None:
    assert _is_connector_kind_compatible("GITLAB", "*")
    assert _is_connector_kind_compatible("GITLAB", "git")
    assert _is_connector_kind_compatible("S3_OBJECT_STORE", "s3")
    assert not _is_connector_kind_compatible("GITLAB", "db")

    bundle_row: dict[str, Any] = {
        "id": B_UUID,
        "slug": "alpha",
        "version": "1.0.0",
        "scope_type": "WORKSPACE",
        "scope_id": WS_UUID,
        "status": "PUBLISHED",
        "declared_slots_jsonb": [
            {"slot_key": "repo", "scheme": "git", "required": True},
            {"slot_key": "ec", "scheme": "git", "required": False},
            {"slot_key": "int", "scheme": "internal", "required": False},
            {"slot_key": "opt", "scheme": "db", "required": False},
        ],
    }

    state: dict[str, Any] = {
        "ds": (DS_UUID, "git"),
        "ec": (EC_UUID, True, "GITLAB"),
        "scheme_ok": True,
    }

    def _h(sql: str, p: dict[str, Any]) -> FakeSqlResult:
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(WS_UUID, OU_UUID)])
        if "FROM declarative_pack_bundles" in sql:
            return FakeSqlResult(mappings=[bundle_row])
        if "FROM workspace_datasources" in sql:
            return FakeSqlResult(rows=[state["ds"]] if state["ds"] else [])
        if "FROM enterprise_connectors" in sql:
            return FakeSqlResult(rows=[state["ec"]] if state["ec"] else [])
        if "FROM connector_schemes" in sql:
            return FakeSqlResult(scalar_val=p["s"] if state["scheme_ok"] else None, has_scalar=True)
        return FakeSqlResult()

    conn: Any = FakeSqlEngine(_h).connect()._conn
    for bad in (
        SlotBindingInput(slot_key="nope", target_kind=PackSlotTargetKind.UNBOUND),
        SlotBindingInput(
            slot_key="repo", target_kind=PackSlotTargetKind.WORKSPACE_DATASOURCE, target_id="bad"
        ),
        SlotBindingInput(slot_key="repo", target_kind=PackSlotTargetKind.INTERNAL),
    ):
        with pytest.raises(PackSlotBindingInvalidError):
            await bind_workspace_pack_slots_conn(
                conn, ws_uuid=WS_UUID, bundle_row=bundle_row, bindings=[bad], actor_id="u-1"
            )

    state["ds"] = None
    with pytest.raises(PackSlotBindingInvalidError):
        await bind_workspace_pack_slots_conn(
            conn,
            ws_uuid=WS_UUID,
            bundle_row=bundle_row,
            bindings=[
                SlotBindingInput(
                    slot_key="repo",
                    target_kind=PackSlotTargetKind.WORKSPACE_DATASOURCE,
                    target_id=DS_UUID,
                )
            ],
            actor_id="u-1",
        )
    state["ds"] = (DS_UUID, "db")
    with pytest.raises(PackSlotBindingInvalidError):
        await bind_workspace_pack_slots_conn(
            conn,
            ws_uuid=WS_UUID,
            bundle_row=bundle_row,
            bindings=[
                SlotBindingInput(
                    slot_key="repo",
                    target_kind=PackSlotTargetKind.WORKSPACE_DATASOURCE,
                    target_id=DS_UUID,
                )
            ],
            actor_id="u-1",
        )
    state["ds"] = (DS_UUID, "git")
    with pytest.raises(PackSlotBindingInvalidError):
        await bind_workspace_pack_slots_conn(
            conn,
            ws_uuid=WS_UUID,
            bundle_row=bundle_row,
            bindings=[
                SlotBindingInput(
                    slot_key="repo",
                    target_kind=PackSlotTargetKind.WORKSPACE_DATASOURCE,
                    target_id=DS_UUID,
                    connector_scheme="db",
                )
            ],
            actor_id="u-1",
        )

    state["ec"] = (EC_UUID, False, "GITLAB")
    with pytest.raises(PackSlotBindingInvalidError):
        await bind_workspace_pack_slots_conn(
            conn,
            ws_uuid=WS_UUID,
            bundle_row=bundle_row,
            bindings=[
                SlotBindingInput(
                    slot_key="ec",
                    target_kind=PackSlotTargetKind.ENTERPRISE_CONNECTOR,
                    target_id=EC_UUID,
                )
            ],
            actor_id="u-1",
        )
    state["ec"] = (EC_UUID, True, "S3_OBJECT_STORE")
    with pytest.raises(PackSlotBindingInvalidError):
        await bind_workspace_pack_slots_conn(
            conn,
            ws_uuid=WS_UUID,
            bundle_row=bundle_row,
            bindings=[
                SlotBindingInput(
                    slot_key="ec",
                    target_kind=PackSlotTargetKind.ENTERPRISE_CONNECTOR,
                    target_id=EC_UUID,
                )
            ],
            actor_id="u-1",
        )
    state["ec"] = (EC_UUID, True, "GITLAB")
    with pytest.raises(PackSlotBindingInvalidError):
        await bind_workspace_pack_slots_conn(
            conn,
            ws_uuid=WS_UUID,
            bundle_row=bundle_row,
            bindings=[
                SlotBindingInput(
                    slot_key="ec",
                    target_kind=PackSlotTargetKind.ENTERPRISE_CONNECTOR,
                    target_id=EC_UUID,
                    connector_scheme="db",
                )
            ],
            actor_id="u-1",
        )
    state["scheme_ok"] = False
    with pytest.raises(PackSlotBindingInvalidError):
        await bind_workspace_pack_slots_conn(
            conn,
            ws_uuid=WS_UUID,
            bundle_row=bundle_row,
            bindings=[
                SlotBindingInput(
                    slot_key="ec",
                    target_kind=PackSlotTargetKind.ENTERPRISE_CONNECTOR,
                    target_id=EC_UUID,
                    connector_scheme="git",
                )
            ],
            actor_id="u-1",
        )

    state["scheme_ok"] = True
    res = await bind_workspace_pack_slots_sql(
        FakeSqlEngine(_h),  # type: ignore[arg-type]
        workspace_id=WS_UUID,
        pack_slug="alpha",
        bindings=[
            SlotBindingInput(
                slot_key="repo",
                target_kind=PackSlotTargetKind.WORKSPACE_DATASOURCE,
                target_id=DS_UUID,
            ),
            SlotBindingInput(
                slot_key="ec",
                target_kind=PackSlotTargetKind.ENTERPRISE_CONNECTOR,
                target_id=EC_UUID,
            ),
            SlotBindingInput(slot_key="int", target_kind=PackSlotTargetKind.INTERNAL),
            SlotBindingInput(slot_key="opt", target_kind=PackSlotTargetKind.UNBOUND),
        ],
        actor_id="u-1",
    )
    assert res == []

    with pytest.raises(PackSlotBindingInvalidError):
        await bind_workspace_pack_slots_sql(
            FakeSqlEngine(_h, commit_exc=_dbapi_err("fk fail")),  # type: ignore[arg-type]
            workspace_id=WS_UUID,
            pack_slug="alpha",
            bindings=[SlotBindingInput(slot_key="opt", target_kind=PackSlotTargetKind.UNBOUND)],
            actor_id="u-1",
        )
