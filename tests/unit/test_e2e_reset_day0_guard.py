"""Layer 1a unit tests for Story 23.1 (`09_reset_db_first_boot`, `reset_day0`, `e2e_test_hooks`)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RESET_FIRST_BOOT_PATH = (
    REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
)
RESET_DAY0_PATH = REPO_ROOT / "infra" / "scripts" / "e2e" / "reset_day0.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_09_reset_db_first_boot_protects_connector_schemes_and_append_only_tables() -> None:
    mod = _load_module("test_mod_09_reset", RESET_FIRST_BOOT_PATH)
    assert "connector_schemes" in mod.PROTECTED_TABLES
    assert {
        "alembic_version",
        "blackboard_snapshots",
        "audit_ledger",
        "connector_schemes",
        "declarative_pack_bundles",
    } <= set(mod.PROTECTED_TABLES)
    assert {
        "assistant_folder_shares",
        "assistant_threads",
        "assistant_folders",
        "workspace_exception_waivers",
        "vsm_definitions_v2",
        "claim_check_artifacts",
        "datasource_webhook_deliveries",
        "rag_reindexing_pending_ingestions",
        "rag_reindexing_jobs",
    } <= set(mod.ORDERED_MUTABLE_TABLES_TO_CLEAR)
    assert len(mod.BASE_CONNECTOR_SCHEMES) >= 7
    args = mod.build_arg_parser().parse_args([])
    assert args.dry_run is True
    assert args.apply is False


@pytest.mark.asyncio
async def test_09_reset_db_first_boot_rejects_append_only_restrict_refs() -> None:
    mod = _load_module("test_mod_09_reset_guard", RESET_FIRST_BOOT_PATH)
    mock_conn = AsyncMock()
    res_target_exists = MagicMock()
    res_target_exists.scalar.return_value = True
    res_fk = MagicMock()
    res_fk.fetchall.return_value = [("blackboard_snapshots",)]
    res_ref_exists = MagicMock()
    res_ref_exists.scalar.return_value = True
    mock_conn.execute.side_effect = [res_target_exists, res_fk, res_ref_exists]

    with pytest.raises(RuntimeError, match="ON DELETE RESTRICT"):
        await mod._assert_no_append_only_restrict_refs(
            mock_conn,
            "step_executions",
            {"step_executions", "blackboard_snapshots"},
        )


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "postgresql+asyncpg://orcia:pw@127.0.0.1:5432/orcia_e2e",  # pragma: allowlist secret
        "postgresql+asyncpg://orcia:pw@127.0.0.1:5433/orcia_e2e",  # pragma: allowlist secret
        "postgresql+asyncpg://orcia:pw@localhost:5432/orcia_e2e",  # pragma: allowlist secret
        "postgresql+asyncpg://orcia:pw@127.0.0.1:49321/orcia",  # pragma: allowlist secret
        "postgresql+asyncpg://orcia:pw@127.0.0.1:49321/orcia_dev",  # pragma: allowlist secret
        (
            "postgresql+asyncpg://orcia:pw"  # pragma: allowlist secret
            "@db.staging.internal:49321/orcia_e2e"
        ),
        "postgresql+asyncpg://orcia:pw@10.0.0.12:49321/orcia_e2e",  # pragma: allowlist secret
    ],
)
def test_reset_day0_refuses_non_isolated_or_dev_urls_immediately(
    bad_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module("test_mod_reset_day0_guard", RESET_DAY0_PATH)
    called = False

    async def _fail_if_called(_url: str) -> tuple[list[str], list[str], int]:
        nonlocal called
        called = True
        return [], [], 0

    monkeypatch.setattr(mod, "_reset_postgres_e2e", _fail_if_called)

    with pytest.raises(RuntimeError, match="REFUS"):
        mod.reset_day0_environment(database_url=bad_url)
    assert called is False


def test_reset_day0_evict_api_caches_handles_connect_error_vs_http_4xx_and_200(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module("test_mod_reset_day0_evict", RESET_DAY0_PATH)
    valid_url = (
        "postgresql+asyncpg://orcia:pw@127.0.0.1:49321/orcia_e2e"  # pragma: allowlist secret
    )

    async def _fake_reset_pg(_url: str) -> tuple[list[str], list[str], int]:
        return ["users", "workflow_runs"], ["workflow_status"], 0

    flushed_urls: list[str] = []

    def _fake_flush(redis_url: str) -> None:
        flushed_urls.append(redis_url)

    monkeypatch.setattr(mod, "_reset_postgres_e2e", _fake_reset_pg)
    monkeypatch.setattr(mod, "_flush_redis", _fake_flush)

    # 1. ConnectError -> api_caches_evicted is False (non-blocking when API is down)
    def _raise_connect_error(*_args: Any, **_kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(mod.httpx, "post", _raise_connect_error)
    res_connect = mod.reset_day0_environment(
        state={
            "database_url": valid_url,
            "redis_url": "redis://127.0.0.1:49322/0",
            "api_port": 49323,
        }
    )
    assert res_connect["api_caches_evicted"] is False
    assert res_connect["redis_flushed"] is True
    assert res_connect["remaining_users_count"] == 0
    assert flushed_urls == ["redis://127.0.0.1:49322/0"]

    # 2. HTTP >= 400 (e.g. 404 when API was not launched with ORCIA_ENV=e2e) -> RuntimeError
    def _return_404(*_args: Any, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(404, text='{"detail":"not e2e"}')

    monkeypatch.setattr(mod.httpx, "post", _return_404)
    with pytest.raises(RuntimeError, match="HTTP 404"):
        mod.reset_day0_environment(
            database_url=valid_url,
            redis_url="",
            api_port=49323,
        )

    # 3. HTTP 200 -> api_caches_evicted is True
    def _return_200(*_args: Any, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(200, json={"evicted": True, "cleared_caches": [], "trace_id": "t"})

    monkeypatch.setattr(mod.httpx, "post", _return_200)
    res_ok = mod.reset_day0_environment(
        database_url=valid_url,
        redis_url="redis://127.0.0.1:49322/0",
        api_port=49323,
    )
    assert res_ok["api_caches_evicted"] is True


def test_e2e_evict_memory_caches_never_evicts_critical_infra_attrs() -> None:
    from orcia_api.routers.e2e_test_hooks import _E2E_EVICTABLE_STATE_ATTRS

    critical_infra_attrs = {
        "db_engine",
        "session_maker",
        "reflexive_session_maker",
        "http_client",
        "redis_client",
        "sse_broker",
        "dbos_uow",
        "dbos_datasource",
    }
    overlap = critical_infra_attrs & set(_E2E_EVICTABLE_STATE_ATTRS)
    assert overlap == set(), f"Attributs infra critiques interdits dans eviction: {overlap}"


def test_reset_day0_helpers_and_cli_main_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module("test_mod_reset_day0_cli", RESET_DAY0_PATH)

    assert (
        mod._normalize_async_pg_url("postgresql://u:p@127.0.0.1:1/orcia_e2e")
        == "postgresql+asyncpg://u:p@127.0.0.1:1/orcia_e2e"
    )
    assert (
        mod._normalize_async_pg_url("postgresql+psycopg://u:p@127.0.0.1:1/orcia_e2e")
        == "postgresql+asyncpg://u:p@127.0.0.1:1/orcia_e2e"
    )
    assert mod._quote_table("public", "users") == '"public"."users"'
    with pytest.raises(ValueError, match="Identifiant SQL invalide"):
        mod._quote_table("public; DROP TABLE users", "users")

    # Test _run_async outside running event loop
    async def _sample_coro() -> tuple[list[str], list[str], int]:
        return ["users"], [], 0

    assert mod._run_async(_sample_coro()) == (["users"], [], 0)

    # Test main() exit codes: 0 on clean reset, 1 if users remain, 2 on error
    monkeypatch.setattr(
        mod,
        "reset_day0_environment",
        lambda: {"remaining_users_count": 0},
    )
    assert mod.main() == 0

    monkeypatch.setattr(
        mod,
        "reset_day0_environment",
        lambda: {"remaining_users_count": 2},
    )
    assert mod.main() == 1

    def _raise_runtime() -> dict[str, Any]:
        raise RuntimeError("REFUS")

    monkeypatch.setattr(mod, "reset_day0_environment", _raise_runtime)
    assert mod.main() == 2


def test_reset_day0_environment_reads_state_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module("test_mod_reset_day0_read_state", RESET_DAY0_PATH)
    monkeypatch.setattr(
        mod,
        "read_state",
        lambda: {
            "database_url": (
                "postgresql+asyncpg://orcia:pw"  # pragma: allowlist secret
                "@127.0.0.1:49321/orcia_e2e"
            ),
            "redis_url": "",
            "api_port": None,
        },
    )

    async def _fake_reset_pg(_url: str) -> tuple[list[str], list[str], int]:
        return ["users"], [], 0

    monkeypatch.setattr(mod, "_reset_postgres_e2e", _fake_reset_pg)
    res = mod.reset_day0_environment()
    assert res["remaining_users_count"] == 0
    assert res["api_caches_evicted"] is False


@pytest.mark.asyncio
async def test_09_reset_db_first_boot_early_returns_and_dry_run_vs_apply() -> None:
    mod = _load_module("test_mod_09_reset_full", RESET_FIRST_BOOT_PATH)
    mock_conn = AsyncMock()
    # Non-guarded table returns immediately without executing queries
    await mod._assert_no_append_only_restrict_refs(mock_conn, "users", {"users"})
    mock_conn.execute.assert_not_called()

    # Guarded table with 0 rows returns without checking pg_constraint
    res_empty = MagicMock()
    res_empty.scalar.return_value = False
    mock_conn.execute.return_value = res_empty
    await mod._assert_no_append_only_restrict_refs(
        mock_conn, "workflow_runs", {"workflow_runs", "blackboard_snapshots"}
    )
    assert mock_conn.execute.call_count == 1

    # reset_platform_auth_settings_and_system_seed discovers existing_tables when omitted
    seed_conn = AsyncMock()
    res_tables = MagicMock()
    res_tables.fetchall.return_value = [("platform_auth_settings",), ("connector_schemes",)]
    seed_conn.execute.return_value = res_tables
    await mod.reset_platform_auth_settings_and_system_seed(seed_conn)
    assert seed_conn.execute.call_count == 1 + 1 + len(mod.BASE_CONNECTOR_SCHEMES)


def test_09_reset_db_first_boot_cli_main_dry_run_and_apply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_module("test_mod_09_cli_main", RESET_FIRST_BOOT_PATH)

    class _DisposableHandle:
        def __init__(self) -> None:
            self.disposed = False

        async def dispose(self) -> None:
            self.disposed = True

    fake_engine = _DisposableHandle()
    monkeypatch.setattr(mod, "create_async_engine", lambda _url: fake_engine)

    async def _fake_reset(_engine: Any, *, apply_changes: bool) -> Any:
        return mod.FirstBootResetReport(
            cleared_tables_count=3,
            deleted_rows_total=5,
            remaining_users_count=0,
            remaining_org_units_count=0,
            remaining_workspaces_count=0,
            dry_run=not apply_changes,
            committed=apply_changes,
        )

    monkeypatch.setattr(mod, "reset_database_to_first_boot", _fake_reset)
    assert mod.main(["--database-url", "postgresql+asyncpg://u:p@127.0.0.1:49321/orcia_e2e"]) == 0
    assert fake_engine.disposed is True

    fake_engine2 = _DisposableHandle()
    monkeypatch.setattr(mod, "create_async_engine", lambda _url: fake_engine2)
    assert (
        mod.main(
            [
                "--database-url",
                "postgresql+asyncpg://u:p@127.0.0.1:49321/orcia_e2e",
                "--apply",
            ]
        )
        == 0
    )
    assert fake_engine2.disposed is True
