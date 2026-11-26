"""Story 31.1 Layer 1a unit tests for `SqlPackBundleV2Repository` and lifecycle helpers."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import pytest

from orcia_core.packs import (
    EntityReferencedByPackDraftError,
    LoadedPackBundleV2,
    PackDnaMechanismSpec,
    PackManifestV2,
    PackScopeType,
    ResourcePinnedByActiveRunsError,
    SqlPackBundleV2Repository,
)
from orcia_core.packs._internal._sql_pack_lifecycle import (
    _parse_json_dict_or_none,
    upsert_pack_dna_mechanisms_sql,
)


class _FakeResult:
    def __init__(
        self, rows: list[tuple[Any, ...]] | None = None, *, scalar_val: Any = None
    ) -> None:
        self._rows = rows or []
        self._scalar = scalar_val

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._rows[0] if self._rows else None

    def scalar(self) -> Any:
        if self._scalar is not None:
            return self._scalar
        return self._rows[0][0] if self._rows else None

    def scalar_one(self) -> Any:
        return self._scalar if self._scalar is not None else self._rows[0][0]


class _FakeConn:
    def __init__(self, handler: Any) -> None:
        self._handler = handler

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        return self._handler(str(stmt), params or {})


class _FakeCtx:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(self, *_args: Any) -> None:
        return None


class _FakeEngine:
    def __init__(self, handler: Any) -> None:
        self._conn = _FakeConn(handler)

    def begin(self) -> _FakeCtx:
        return _FakeCtx(self._conn)

    def connect(self) -> _FakeCtx:
        return _FakeCtx(self._conn)


@pytest.mark.asyncio
async def test_sql_pack_bundle_v2_repository_crud_and_fail_closed() -> None:
    mech = PackDnaMechanismSpec(
        mechanism_slug="m1",
        name="M1",
        starlark_source=(
            "def evaluate(p):\n"
            "    orcia_sys.assert_rule(rule_id='R', condition=True, message='ok')\n"
        ),
        source_sha256=hashlib.sha256(b"m1").hexdigest(),
        passing_test_payload={"a": 1},
        failing_test_payload={"a": 0},
    )
    bundle = LoadedPackBundleV2(
        manifest=PackManifestV2(
            id="orcia-pack-edge",
            slug="edge",
            name="Edge Pack",
            version="1.0.0",
            author="dev@example.org",
            description="Edge desc",
        ),
        archive_sha256=hashlib.sha256(b"edge").hexdigest(),
        manifest_yaml="name: edge\nversion: 1.0.0\n",
        dna_mechanisms=[mech],
    )

    none_repo = SqlPackBundleV2Repository(None)
    with pytest.raises(RuntimeError, match="AsyncEngine"):
        await none_repo.upsert_bundle_v2(bundle)
    with pytest.raises(RuntimeError, match="AsyncEngine"):
        await none_repo.list_bundles_v2()
    with pytest.raises(RuntimeError, match="AsyncEngine"):
        await none_repo.get_bundle_v2("edge")
    with pytest.raises(RuntimeError, match="AsyncEngine"):
        await none_repo.delete_bundle("b1")

    stored_rows: list[tuple[Any, ...]] = []
    mech_rows: list[tuple[Any, ...]] = []
    now = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)

    def _handler(sql: str, params: dict[str, Any]) -> _FakeResult:
        if "INSERT INTO declarative_pack_bundles" in sql:
            stored_rows.clear()
            stored_rows.append(
                (
                    params["id"],
                    params["pack_id"],
                    params["slug"],
                    params["name"],
                    params["version"],
                    params["rbac_namespace"],
                    params["bundle_sha256"],
                    params["bundle_kind"],
                    params["scope_type"],
                    params["scope_id"],
                    params["status"],
                    params["archive_sha256"],
                    params["cas_object_key"],
                    params["source_origin"],
                    '[{"slot_key": "s1"}]',
                    params["author"],
                    params["description"],
                    now,
                    params["created_by_user_id"],
                    now,
                    now,
                )
            )
            return _FakeResult(scalar_val=params["id"])
        if "INSERT INTO pack_dna_mechanisms" in sql:
            mech_rows.clear()
            mech_rows.append(
                (
                    params["mechanism_slug"],
                    params["name"],
                    params["starlark_source"],
                    params["source_sha256"],
                    params["input_schema"],
                    params["output_schema"],
                    params["passing_payload"],
                    params["failing_payload"],
                )
            )
            return _FakeResult()
        if "FROM pack_dna_mechanisms" in sql:
            return _FakeResult(mech_rows)
        if "FROM declarative_pack_bundles" in sql:
            return _FakeResult(stored_rows)
        return _FakeResult()

    repo = SqlPackBundleV2Repository()
    repo.set_engine(_FakeEngine(_handler))  # type: ignore[arg-type]
    upserted = await repo.upsert_bundle_v2(bundle, cas_object_key="cas/edge")
    assert upserted.id == "orcia-pack-edge"

    listed = await repo.list_bundles_v2(scope_type=PackScopeType.WORKSPACE, scope_id="global")
    assert len(listed) == 1
    assert listed[0]["status"] == "PUBLISHED"
    assert listed[0]["declared_slots"] == [{"slot_key": "s1"}]

    fetched = await repo.get_bundle_v2("edge")
    assert fetched is not None
    assert fetched["cas_object_key"] == "cas/edge"
    assert await repo.get_bundle_v2("   ") is None

    loaded_mechs = await repo.list_dna_mechanisms(pack_bundle_id="b1")
    assert len(loaded_mechs) == 1
    assert loaded_mechs[0].passing_test_payload == {"a": 1}
    assert loaded_mechs[0].failing_test_payload == {"a": 0}


@pytest.mark.asyncio
async def test_sql_pack_bundle_v2_delete_guards_runs_drafts_and_deactivated() -> None:
    deleted_calls: list[str] = []

    def _make_delete_repo(mode: str) -> SqlPackBundleV2Repository:
        def _handler(sql: str, _params: dict[str, Any]) -> _FakeResult:
            if "FROM workspace_pack_activations" in sql and mode == "active_ws":
                return _FakeResult(scalar_val=1)
            if "FROM run_lock_manifests" in sql and mode == "active_run":
                return _FakeResult(scalar_val=1)
            if "JOIN pack_dna_mechanisms" in sql and mode == "mech_draft":
                return _FakeResult(scalar_val=1)
            if (
                "FROM pack_draft_memberships m" in sql
                and "JOIN pack_dna_mechanisms" not in sql
                and mode == "other_draft"
            ):
                return _FakeResult(scalar_val=1)
            if sql.strip().startswith("DELETE FROM"):
                deleted_calls.append(sql.strip())
            return _FakeResult()

        return SqlPackBundleV2Repository(_FakeEngine(_handler))  # type: ignore[arg-type]

    with pytest.raises(ResourcePinnedByActiveRunsError, match="active workspace"):
        await _make_delete_repo("active_ws").delete_bundle("b-1")
    with pytest.raises(ResourcePinnedByActiveRunsError, match="active workflow runs"):
        await _make_delete_repo("active_run").delete_bundle("b-1")
    with pytest.raises(EntityReferencedByPackDraftError, match="another pack draft"):
        await _make_delete_repo("other_draft").delete_bundle("b-1")
    with pytest.raises(EntityReferencedByPackDraftError, match="DNA mechanisms"):
        await _make_delete_repo("mech_draft").delete_bundle("b-1")

    await _make_delete_repo("ok").delete_bundle("b-1")
    assert len(deleted_calls) == 3
    assert any("pack_draft_memberships" in stmt for stmt in deleted_calls)
    assert any(
        "workspace_pack_activations" in stmt and "is_active = FALSE" in stmt
        for stmt in deleted_calls
    )
    assert any("declarative_pack_bundles" in stmt for stmt in deleted_calls)

    deactivated_sqls: list[str] = []

    def _deactivated_handler(sql: str, _params: dict[str, Any]) -> _FakeResult:
        if "AND is_active = TRUE" in sql:
            return _FakeResult(scalar_val=None)
        if sql.strip().startswith("DELETE FROM"):
            deactivated_sqls.append(" ".join(sql.split()))
        return _FakeResult()

    await SqlPackBundleV2Repository(_FakeEngine(_deactivated_handler)).delete_bundle(  # type: ignore[arg-type]
        "b-deactivated"
    )
    assert len(deactivated_sqls) == 3
    assert any(
        "workspace_pack_activations" in s and "is_active = FALSE" in s for s in deactivated_sqls
    )


@pytest.mark.asyncio
async def test_sql_pack_lifecycle_helper_edge_cases() -> None:
    assert _parse_json_dict_or_none({"k": "v"}) == {"k": "v"}
    assert _parse_json_dict_or_none({}) is None
    assert _parse_json_dict_or_none("{bad-json") is None
    assert _parse_json_dict_or_none(42) is None

    called = False

    def _never(_sql: str, _params: dict[str, Any]) -> _FakeResult:
        nonlocal called
        called = True
        return _FakeResult()

    await upsert_pack_dna_mechanisms_sql(
        _FakeEngine(_never),  # type: ignore[arg-type]
        pack_bundle_id="b-1",
        mechanisms=[],
    )
    assert called is False
