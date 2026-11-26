"""Unit tests for Story 31.5 composer SQL CRUD & status guards (`<= 260 L`)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_core.packs._internal._sql_pack_composer import (
    create_draft_pack_sql,
    update_draft_pack_sql,
)
from orcia_core.packs._internal._sql_pack_composer_members import (
    delete_draft_pack_sql,
    set_draft_pack_members_sql,
)
from orcia_core.packs._internal._sql_pack_composer_reads import (
    get_draft_pack_sql,
    list_draft_packs_sql,
)
from orcia_core.packs.composer_models import PackDraftMemberInput
from orcia_core.packs.errors import (
    PackBundleNotFoundError,
    PackScopeEscalationForbiddenError,
    PackSystemDeleteForbiddenError,
    PackVersionConflictError,
)
from orcia_core.packs.models import PackDraftEntityType, PackScopeType


@pytest.mark.asyncio
async def test_composer_sql_crud_and_status_guards() -> None:
    """Verify create, list, get, update, set_members & delete SQL invariants."""
    ws_id, bundle_id, uid = str(uuid7()), str(uuid7()), str(uuid7())
    now = datetime.now(UTC)
    bundle_row = {
        "id": bundle_id,
        "pack_id": "orcia-pack-c1",
        "slug": "c1",
        "name": "C1",
        "version": "0.1.0",
        "rbac_namespace": "c1",
        "bundle_kind": "CUSTOM",
        "scope_type": "WORKSPACE",
        "scope_id": ws_id,
        "status": "DRAFT",
        "source_origin": "ORCIA_COMPOSER",
        "archive_sha256": "a" * 64,
        "cas_object_key": None,
        "manifest_jsonb": {"description": "Desc", "author": "Alice"},
        "declared_slots_jsonb": [],
        "author": "Alice",
        "description": "Desc",
        "created_by_user_id": None,
        "published_at": None,
        "updated_at": now,
    }
    state = {"exists": False, "kind": "CUSTOM", "status": "DRAFT", "missing": False}

    def handler(sql: str, _params: dict[str, Any]) -> FakeSqlResult:
        if "SELECT 1 FROM declarative_pack_bundles" in sql:
            return FakeSqlResult(scalar_val=1 if state["exists"] else None, has_scalar=True)
        if "declarative_pack_bundles" in sql:
            if state["missing"]:
                return FakeSqlResult(mappings=[])
            return FakeSqlResult(
                mappings=[{**bundle_row, "bundle_kind": state["kind"], "status": state["status"]}]
            )
        if "FROM pack_draft_memberships" in sql:
            return FakeSqlResult(mappings=[])
        if "FROM workspaces" in sql:
            return FakeSqlResult(rows=[(ws_id, None)])
        if "FROM catalog_items" in sql:
            return FakeSqlResult(
                mappings=[
                    {
                        "uid": uid,
                        "eid": "ag-1",
                        "title": "Ag",
                        "bid": None,
                        "ws_id": ws_id,
                        "metadata_jsonb": {},
                    }
                ]
            )
        return FakeSqlResult()

    eng = FakeSqlEngine(handler)
    with pytest.raises(PackScopeEscalationForbiddenError):
        await create_draft_pack_sql(
            eng,  # type: ignore[arg-type]
            slug="c1",
            name="C1",
            version="0.1.0",
            description="",
            author="",
            maintainers=(),
            license_name="",
            scope_type=PackScopeType.GLOBAL,
            scope_id="global",
            declared_slots=(),
            quick_actions=(),
            actor_id="u1",
            actor_email=None,
            trace_id=None,
        )
    created = await create_draft_pack_sql(
        eng,  # type: ignore[arg-type]
        slug="c1",
        name="C1",
        version="0.1.0",
        description="Desc",
        author="Alice",
        maintainers=(),
        license_name="Apache-2.0",
        scope_type=PackScopeType.WORKSPACE,
        scope_id=ws_id,
        declared_slots=(),
        quick_actions=(),
        actor_id=str(uuid7()),
        actor_email="alice@test.local",
        trace_id="t1",
    )
    assert created.slug == "c1"

    state["exists"] = True
    with pytest.raises(PackVersionConflictError):
        await create_draft_pack_sql(
            eng,  # type: ignore[arg-type]
            slug="c1",
            name="C1",
            version="0.1.0",
            description="",
            author="",
            maintainers=(),
            license_name="",
            scope_type=PackScopeType.WORKSPACE,
            scope_id=ws_id,
            declared_slots=(),
            quick_actions=(),
            actor_id="u1",
            actor_email=None,
            trace_id=None,
        )

    assert (
        len(await list_draft_packs_sql(eng, scope_type=PackScopeType.WORKSPACE, scope_id=ws_id))
        == 1
    )  # type: ignore[arg-type]
    assert (await get_draft_pack_sql(eng, bundle_id)).bundle_id == bundle_id  # type: ignore[arg-type]
    upd = await update_draft_pack_sql(
        eng,
        bundle_id,
        name="C1 v2",
        maintainers=["Bob"],
        license_name="MIT",  # type: ignore[arg-type]
    )
    assert upd.bundle_id == bundle_id
    mem = await set_draft_pack_members_sql(
        eng,  # type: ignore[arg-type]
        bundle_id,
        [PackDraftMemberInput(entity_type=PackDraftEntityType.AGENT, entity_id="ag-1")],
        actor_id="u1",
        actor_email=None,
        trace_id=None,
    )
    assert mem.bundle_id == bundle_id
    deleted = await delete_draft_pack_sql(
        eng, bundle_id, actor_id="u1", actor_email=None, trace_id=None
    )  # type: ignore[arg-type]
    assert deleted["bundle_id"] == bundle_id

    state["kind"] = "SYSTEM"
    with pytest.raises(PackSystemDeleteForbiddenError):
        await delete_draft_pack_sql(eng, bundle_id, actor_id="u1", actor_email=None, trace_id=None)  # type: ignore[arg-type]
    state["kind"], state["status"] = "CUSTOM", "PUBLISHED"
    with pytest.raises(PackVersionConflictError):
        await update_draft_pack_sql(eng, bundle_id, name="Nope")  # type: ignore[arg-type]
    state["missing"] = True
    with pytest.raises(PackBundleNotFoundError):
        await get_draft_pack_sql(eng, "missing")  # type: ignore[arg-type]
