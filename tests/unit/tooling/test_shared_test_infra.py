"""Unit tests for shared unit/PG18 fixtures, PEP 562 lazy imports, and AST index."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from tests.integration._shared_topology_fixture import (
    clone_worker_database_from_template,
    resolve_worker_identity,
)
from tests.unit.fakes.test_app_helpers import (
    RepoSourceIndex,
    create_seeded_test_app,
    run_with_lifespan,
)

pytestmark = pytest.mark.story("32.3")
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_seeded_test_app_fixture_isolation_step1(seeded_test_app: FastAPI) -> None:
    assert isinstance(seeded_test_app, FastAPI)
    seeded_test_app.dependency_overrides[object] = lambda: "mutated"  # type: ignore[dict-item]
    seeded_test_app.state.custom_transient_flag = "leaked"


def test_seeded_test_app_fixture_isolation_step2(seeded_test_app: FastAPI) -> None:
    assert seeded_test_app.dependency_overrides == {}
    assert not hasattr(seeded_test_app.state, "custom_transient_flag")
    assert len(seeded_test_app.state.workflows_v2_sql_store._memory_fallback) >= 1


@pytest.mark.asyncio
async def test_create_seeded_test_app_and_run_with_lifespan() -> None:
    app = create_seeded_test_app()
    async with run_with_lifespan(app) as booted:
        assert booted is app
        assert hasattr(booted.state, "auth_service")


def test_repo_source_index_caches_files_text_and_ast(repo_source_index: RepoSourceIndex) -> None:
    files = repo_source_index.files_under("scripts/agent_check_lib")
    assert any(p.name == "stages.py" for p in files)
    stages_path = next(p for p in files if p.name == "stages.py")
    assert repo_source_index.read_text(stages_path) is repo_source_index.read_text(stages_path)
    assert repo_source_index.parse_ast(stages_path) is repo_source_index.parse_ast(stages_path)


def test_pep562_lazy_exports_resolve_all_symbols() -> None:
    from orcia_api.dependencies import _lazy_exports as dep_lazy
    from orcia_core.bootstrap import _lazy_exports as boot_lazy
    from orcia_core.orchestration import _lazy_exports as orch_lazy

    for pkg_name, lazy_mod in (
        ("orcia_api.dependencies", dep_lazy),
        ("orcia_core.bootstrap", boot_lazy),
        ("orcia_core.orchestration", orch_lazy),
    ):
        pkg = importlib.import_module(pkg_name)
        assert set(pkg.__all__) == set(lazy_mod.ALL_EXPORTS)
        for sym in lazy_mod.ALL_EXPORTS:
            assert hasattr(pkg, sym), f"{pkg_name}.{sym} failed lazy resolution"
        missing_attr = "__nonexistent_symbol_32_3__"
        with pytest.raises(AttributeError):
            getattr(pkg, missing_attr)


def test_orcia_api_main_lazy_app_and_entrypoint_compatibility() -> None:
    code = (
        "import sys; "
        "import orcia_api.main as m; "
        "assert m._LAZY_APP is None; "
        "import orcia_api; "
        "assert callable(orcia_api.create_app); "
        "assert m.app is orcia_api.app; "
        "assert m._LAZY_APP is not None"
    )
    py_paths = os.pathsep.join(
        str(REPO_ROOT / p)
        for p in (
            "packages/orcia-core/src",
            "packages/orcia-connectors/src",
            "apps/api/src",
            "apps/worker/src",
            ".",
        )
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": py_paths},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_integration_worker_isolation_and_flock_template_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw2")
    assert resolve_worker_identity() == ("gw2", 2)
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)
    assert resolve_worker_identity() == ("master", 0)

    executed_sql: list[str] = []

    class _Conn:
        def execute(self, stmt: Any, _params: Any = None) -> None:
            executed_sql.append(str(stmt))

        def __enter__(self) -> _Conn:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    fake_engine = MagicMock()
    fake_engine.connect.return_value = _Conn()
    lock_file = tmp_path / "tpl.lock"
    with patch(
        "tests.integration._shared_topology_fixture.sa.create_engine",
        return_value=fake_engine,
    ):
        clone_worker_database_from_template(
            "postgresql+psycopg://u:p@/postgres",  # pragma: allowlist secret
            template_db="orcia_template",
            app_db_name="orcia_test_gw2",
            dbos_db_name="orcia_dbos_gw2",
            lock_path=lock_file,
        )
    assert lock_file.exists()
    assert any(
        'CREATE DATABASE "orcia_test_gw2" TEMPLATE "orcia_template"' in s for s in executed_sql
    )
    assert any('CREATE DATABASE "orcia_dbos_gw2"' in s for s in executed_sql)
    fake_engine.dispose.assert_called_once()
    assert isinstance(SimpleNamespace(ok=True), SimpleNamespace)
