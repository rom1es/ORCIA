"""Branch coverage tests for Story 31.4 activation, deactivation & reorder (<= 300 L)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.exc import DBAPIError
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult

from orcia_core.packs._internal._sql_workspace_pack_mutations import (
    activate_workspace_pack_sql,
    deactivate_workspace_pack_sql,
)
from orcia_core.packs._internal._sql_workspace_pack_reorder import (
    map_pack_activation_db_error,
    reorder_workspace_packs_sql,
)
from orcia_core.packs.errors import PackActivationInvalidError, PackBundleNotFoundError
from orcia_core.packs.models import PackSlotTargetKind
from orcia_core.packs.slot_guard import SlotBindingInput
from orcia_core.permissions.errors import ScopeAccessDeniedError

WS_UUID = "0195f000-0000-7000-8000-000000000701"
OU_UUID = "0195f000-0000-7000-8000-000000000702"
B_UUID = "0195f000-0000-7000-8000-000000000703"


def _dbapi_err(msg: str) -> DBAPIError:
    return DBAPIError("stmt", {}, Exception(msg))


@pytest.mark.asyncio
async def test_activate_deactivate_and_reorder_all_branches() -> None:
    assert isinstance(
        map_pack_activation_db_error(
            _dbapi_err("Cross-workspace pack activation forbidden"), instance="/x"
        ),
        ScopeAccessDeniedError,
    )
    assert isinstance(
        map_pack_activation_db_error(_dbapi_err("uq"), instance="/x"), PackActivationInvalidError
    )

    now = datetime(2026, 11, 26, tzinfo=UTC)
    bundle_row = {
        "id": B_UUID,
        "slug": "alpha",
        "version": "1.0.0",
        "scope_type": "WORKSPACE",
        "scope_id": WS_UUID,
        "status": "PUBLISHED",
        "declared_slots_jsonb": [{"slot_key": "opt", "scheme": "internal", "required": False}],
    }
    cfg: dict[str, Any] = {
        "existing": (2, True),
        "conflict": None,
        "deact_row": (B_UUID, B_UUID),
        "active": [("alpha", B_UUID), ("beta", B_UUID)],
    }

    def _h(sql: str, _p: dict[str, Any]) -> FakeSqlResult:
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(WS_UUID, OU_UUID)])
        if "FROM declarative_pack_bundles" in sql:
            return FakeSqlResult(mappings=[bundle_row])
        if "FROM workspace_pack_slot_bindings" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "id": "sb-old",
                        "workspace_id": WS_UUID,
                        "pack_bundle_id": B_UUID,
                        "pack_slug": "alpha",
                        "slot_key": "obsolete",
                        "target_kind": "INTERNAL",
                        "target_id": "x",
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
                    }
                ]
            )
        if "SELECT priority_order, is_active FROM workspace_pack_activations" in sql:
            return FakeSqlResult(rows=[cfg["existing"]] if cfg["existing"] else [])
        if "SELECT COALESCE(MAX(priority_order)" in sql:
            return FakeSqlResult(scalar_val=1, has_scalar=True)
        if "SELECT pack_slug FROM workspace_pack_activations" in sql:
            return FakeSqlResult(scalar_val=cfg["conflict"], has_scalar=True)
        if "INSERT INTO workspace_pack_activations" in sql:
            return FakeSqlResult(rows=[("act-1", now)])
        if "UPDATE workspace_pack_activations" in sql and "is_active = FALSE" in sql:
            return FakeSqlResult(rows=[cfg["deact_row"]] if cfg["deact_row"] else [])
        if "SELECT pack_slug, pack_bundle_id::text FROM workspace_pack_activations" in sql:
            return FakeSqlResult(rows=cfg["active"])
        return FakeSqlResult()

    with pytest.raises(PackActivationInvalidError):
        await activate_workspace_pack_sql(
            FakeSqlEngine(_h),
            workspace_id=WS_UUID,
            pack_slug="alpha",
            priority_order=0,
            actor_id="u-1",
        )  # type: ignore[arg-type]

    act1 = await activate_workspace_pack_sql(
        FakeSqlEngine(_h),  # type: ignore[arg-type]
        workspace_id=WS_UUID,
        pack_slug="alpha",
        slot_bindings=[SlotBindingInput(slot_key="opt", target_kind=PackSlotTargetKind.INTERNAL)],
        actor_id="u-1",
    )
    assert act1["priority_order"] == 2
    cfg["existing"] = None
    act2 = await activate_workspace_pack_sql(
        FakeSqlEngine(_h), workspace_id=WS_UUID, pack_slug="alpha", actor_id="u-1"
    )  # type: ignore[arg-type]
    assert act2["priority_order"] == 2

    cfg["conflict"] = "beta"
    with pytest.raises(PackActivationInvalidError):
        await activate_workspace_pack_sql(
            FakeSqlEngine(_h), workspace_id=WS_UUID, pack_slug="alpha", actor_id="u-1"
        )  # type: ignore[arg-type]
    cfg["conflict"] = None
    with pytest.raises(ScopeAccessDeniedError):
        await activate_workspace_pack_sql(
            FakeSqlEngine(_h, commit_exc=_dbapi_err("Cross-workspace pack activation forbidden")),  # type: ignore[arg-type]
            workspace_id=WS_UUID,
            pack_slug="alpha",
            actor_id="u-1",
        )

    deact = await deactivate_workspace_pack_sql(
        FakeSqlEngine(_h), workspace_id=WS_UUID, pack_slug="alpha", actor_id="u-1"
    )  # type: ignore[arg-type]
    assert deact["is_active"] is False
    cfg["deact_row"] = None
    with pytest.raises(PackBundleNotFoundError):
        await deactivate_workspace_pack_sql(
            FakeSqlEngine(_h), workspace_id=WS_UUID, pack_slug="alpha", actor_id="u-1"
        )  # type: ignore[arg-type]
    cfg["deact_row"] = (B_UUID, B_UUID)
    with pytest.raises(PackActivationInvalidError):
        await deactivate_workspace_pack_sql(
            FakeSqlEngine(_h, commit_exc=_dbapi_err("db fail")),  # type: ignore[arg-type]
            workspace_id=WS_UUID,
            pack_slug="alpha",
            actor_id="u-1",
        )

    with pytest.raises(PackActivationInvalidError):
        await reorder_workspace_packs_sql(
            FakeSqlEngine(_h), workspace_id=WS_UUID, ordered_pack_slugs=["a", "a"], actor_id="u-1"
        )  # type: ignore[arg-type]
    with pytest.raises(PackActivationInvalidError):
        await reorder_workspace_packs_sql(
            FakeSqlEngine(_h), workspace_id=WS_UUID, ordered_pack_slugs=["only"], actor_id="u-1"
        )  # type: ignore[arg-type]
    reord = await reorder_workspace_packs_sql(
        FakeSqlEngine(_h),
        workspace_id=WS_UUID,
        ordered_pack_slugs=["beta", "alpha"],
        actor_id="u-1",  # type: ignore[arg-type]
    )
    assert [r["pack_slug"] for r in reord] == ["beta", "alpha"]
    with pytest.raises(PackActivationInvalidError):
        await reorder_workspace_packs_sql(
            FakeSqlEngine(_h, commit_exc=_dbapi_err("uq")),  # type: ignore[arg-type]
            workspace_id=WS_UUID,
            ordered_pack_slugs=["beta", "alpha"],
            actor_id="u-1",
        )
