"""Layer 1a unit tests for Story 23.6a dynamic PostgreSQL reset introspection guards."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RESET_FIRST_BOOT_PATH = (
    REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
)
RESET_DAY0_PATH = REPO_ROOT / "infra" / "scripts" / "e2e" / "reset_day0.py"
GUARDS_PATH = RESET_FIRST_BOOT_PATH.parent / "_first_boot_reset_guards.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_09_reset_rejects_orphan_alembic_tables_and_disabled_triggers() -> None:
    mod = _load_module("test_mod_09_orphan_guard", RESET_FIRST_BOOT_PATH)
    mock_conn = AsyncMock()
    mock_trans = AsyncMock()
    mock_trans.is_active = True
    mock_conn.begin.return_value = mock_trans
    res_schema = MagicMock()
    res_schema.fetchall.return_value = [("public", "users"), ("public", "unclassified_new_table")]
    mock_conn.execute.return_value = res_schema

    class _FakeConnectCtx:
        async def __aenter__(self) -> AsyncMock:
            return mock_conn

        async def __aexit__(self, *_args: Any) -> None:
            return None

    fake_engine = MagicMock()
    fake_engine.connect.return_value = _FakeConnectCtx()
    with pytest.raises(RuntimeError, match="Tables Alembic orphelines"):
        await mod.reset_database_to_first_boot(fake_engine, apply_changes=False)

    guards_mod = _load_module("_first_boot_reset_guards", GUARDS_PATH)
    assert guards_mod.quote_sql_ident("dbos", "workflow_status") == '"dbos"."workflow_status"'
    assert any(scheme[1] == "pack" for scheme in guards_mod.BASE_CONNECTOR_SCHEMES)
    assert {
        "workspace_pack_slot_bindings",
        "workspace_pack_activations",
        "pack_draft_memberships",
        "pack_dna_mechanisms",
    } <= set(guards_mod.ORDERED_MUTABLE_TABLES_TO_CLEAR)
    with pytest.raises(ValueError, match="Identifiant SQL invalide"):
        guards_mod.quote_sql_ident("bad;schema", "users")

    assert await guards_mod.inspect_append_only_guards(AsyncMock(), set()) == set()

    # assert_no_append_only_restrict_refs passes when ref_table has 0 rows or is absent
    empty_ref_conn = AsyncMock()
    res_true = MagicMock()
    res_true.scalar.return_value = True
    res_fks = MagicMock()
    res_fks.fetchall.return_value = [("audit_ledger",)]
    res_false = MagicMock()
    res_false.scalar.return_value = False
    empty_ref_conn.execute.side_effect = [res_true, res_fks, res_false]
    await guards_mod.assert_no_append_only_restrict_refs(
        empty_ref_conn,
        "step_executions",
        {"step_executions", "audit_ledger"},
    )

    trig_conn = AsyncMock()
    res_trig = MagicMock()
    res_trig.fetchall.return_value = [("audit_ledger", "prevent_audit_ledger_mutation", "D")]
    trig_conn.execute.return_value = res_trig
    with pytest.raises(RuntimeError, match="Trigger append-only désactivé"):
        await guards_mod.inspect_append_only_guards(trig_conn, {"audit_ledger"})


def test_09_reset_flush_redis_if_configured_handles_unset_ok_and_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import redis

    mod = _load_module("test_mod_09_flush_redis", RESET_FIRST_BOOT_PATH)

    monkeypatch.delenv("REDIS_URL", raising=False)
    mod._flush_redis_if_configured()

    flushed = False

    class _FakeRedisOk:
        def flushdb(self) -> None:
            nonlocal flushed
            flushed = True

        def close(self) -> None:
            return None

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:49322/0")
    monkeypatch.setattr(mod.redis.Redis, "from_url", lambda *_a, **_kw: _FakeRedisOk())
    mod._flush_redis_if_configured()
    assert flushed is True

    closed_on_err = False

    class _FakeRedisErr:
        def flushdb(self) -> None:
            raise redis.RedisError("connection down")

        def close(self) -> None:
            nonlocal closed_on_err
            closed_on_err = True

    monkeypatch.setattr(mod.redis.Redis, "from_url", lambda *_a, **_kw: _FakeRedisErr())
    mod._flush_redis_if_configured()
    assert closed_on_err is True


@pytest.mark.asyncio
async def test_reset_day0_verify_post_reset_invariants_and_pg_constraint_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module("test_mod_reset_day0_invariants_b3", RESET_DAY0_PATH)

    class _FakeRedisLeftover:
        def flushdb(self) -> None:
            return None

        def dbsize(self) -> int:
            return 1

        def close(self) -> None:
            return None

    monkeypatch.setattr(mod.redis.Redis, "from_url", lambda *_a, **_kw: _FakeRedisLeftover())
    with pytest.raises(RuntimeError, match="Redis DBSIZE != 0"):
        mod._flush_redis("redis://127.0.0.1:49322/0")

    def _make_engine(results: list[Any]) -> Any:
        mock_conn = AsyncMock()
        mock_conn.execute.side_effect = results

        class _Ctx:
            async def __aenter__(self) -> AsyncMock:
                return mock_conn

            async def __aexit__(self, *_args: Any) -> None:
                return None

        eng = MagicMock()
        eng.connect.return_value = _Ctx()
        return eng

    # 1. Disabled trigger raises RuntimeError
    res_bad_trig = MagicMock()
    res_bad_trig.fetchall.return_value = [("audit_ledger", "prevent_audit_ledger_mutation", "D")]
    with pytest.raises(RuntimeError, match="Triggers append-only invalides"):
        await mod._verify_post_reset_invariants(
            _make_engine([res_bad_trig]),
            ["audit_ledger"],
            [],
        )

    # 2. Missing ON DELETE RESTRICT fk on blackboard_snapshots raises RuntimeError
    res_ok_trig = MagicMock()
    res_ok_trig.fetchall.return_value = [
        ("blackboard_snapshots", "trg_blackboard_snapshots_append_only", "O")
    ]
    res_missing_fk = MagicMock()
    res_missing_fk.fetchall.return_value = [("unrelated_restrict_fkey",)]
    with pytest.raises(RuntimeError, match="Contraintes ON DELETE RESTRICT attendues manquantes"):
        await mod._verify_post_reset_invariants(
            _make_engine([res_ok_trig, res_missing_fk]),
            ["blackboard_snapshots"],
            [],
        )

    # 3. Valid trigger + valid pg_constraint passes, then non-empty dbos.* fails
    res_ok_fk = MagicMock()
    res_ok_fk.fetchall.return_value = [("blackboard_snapshots_step_execution_id_fkey",)]
    res_dbos_nonempty = MagicMock()
    res_dbos_nonempty.scalar.return_value = 3
    with pytest.raises(RuntimeError, match="Table runtime dbos.workflow_status non vide"):
        await mod._verify_post_reset_invariants(
            _make_engine([res_ok_trig, res_ok_fk, res_dbos_nonempty]),
            ["blackboard_snapshots"],
            ["workflow_status"],
        )

    # 4. Incomplete connector_schemes raises RuntimeError
    res_schemes_low = MagicMock()
    res_schemes_low.scalar.return_value = 2
    with pytest.raises(RuntimeError, match="Seed connector_schemes incomplet"):
        await mod._verify_post_reset_invariants(
            _make_engine([res_schemes_low]),
            ["connector_schemes"],
            [],
        )

    # 5. Missing declarative_pack_bundles raises RuntimeError
    res_packs_low = MagicMock()
    res_packs_low.scalar.return_value = 0
    with pytest.raises(RuntimeError, match="Seed declarative_pack_bundles absent"):
        await mod._verify_post_reset_invariants(
            _make_engine([res_packs_low]),
            ["declarative_pack_bundles"],
            [],
        )
