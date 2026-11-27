"""Unit tests for Stage 3 combined coverage, xdist subprocess hook, and impact recall."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.agent_check_lib.coverage_gate import (
    cleanup_coverage_artifacts,
    prepare_coverage_env,
    run_combined_diff_cover,
)
from scripts.agent_check_lib.env import ToolchainEnv, load_pyproject_pythonpath
from scripts.agent_check_lib.impact import _build_reverse_import_graph, select_impacted_targets
from scripts.agent_check_lib.runner_exec import CommandResult

pytestmark = pytest.mark.story("32.3")
REPO_ROOT = Path(__file__).resolve().parents[3]


def test_prepare_coverage_env_xdist_subprocess_hook_and_cleanup(tmp_path: Path) -> None:
    repo = tmp_path / "cov_repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        "[tool.coverage.run]\nbranch = true\nparallel = true\n",
        encoding="utf-8",
    )
    (repo / "mod_cov.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8"
    )
    (repo / "test_mod_cov.py").write_text(
        "from mod_cov import add\n\n"
        "def test_add_one():\n    assert add(1, 2) == 3\n\n"
        "def test_add_two():\n    assert add(3, 4) == 7\n",
        encoding="utf-8",
    )

    cov_env = prepare_coverage_env(
        repo, {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(repo)}
    )
    assert (repo / ".agent_check" / "cov_hook" / "sitecustomize.py").is_file()
    assert cov_env["COVERAGE_PROCESS_START"] == str(repo / "pyproject.toml")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "--branch",
            "--source",
            str(repo),
            "-m",
            "pytest",
            "test_mod_cov.py",
            "-n",
            "2",
            "--dist",
            "loadfile",
            "--no-cov",
            "-q",
        ],
        cwd=repo,
        env=cov_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    worker_shards = list(repo.glob(".coverage.*"))
    assert len(worker_shards) >= 2, f"Expected xdist worker shards, found: {worker_shards}"

    comb = subprocess.run(
        [sys.executable, "-m", "coverage", "combine"],
        cwd=repo,
        env=cov_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert comb.returncode == 0, comb.stdout + comb.stderr
    cleanup_coverage_artifacts(repo)
    assert not (repo / ".coverage").exists()
    assert list(repo.glob(".coverage.*")) == []


def test_run_combined_diff_cover_passes_zero_changes_and_fails_on_low_cov(tmp_path: Path) -> None:
    repo = tmp_path / "dc_repo"
    repo.mkdir()
    env_info = ToolchainEnv(
        repo_root=repo,
        venv_dir=repo / ".venv",
        python_bin=Path(sys.executable),
        ruff_bin=Path("ruff"),
        mypy_bin=Path("mypy"),
        lint_imports_bin=Path("lint-imports"),
        pnpm_bin="pnpm",
        node_bin="node",
        pythonpath=str(repo),
    )
    rc_skip, msg_skip = run_combined_diff_cover(
        env_info,
        run_cmd_fn=lambda *_a: CommandResult(0, "", ""),
        cov_env={},
    )
    assert rc_skip == 0
    assert "0 Python source lines changed" in msg_skip

    with patch("scripts.agent_check_lib.coverage_gate.build_diff_cover_patch", return_value=True):
        rc_fail, _ = run_combined_diff_cover(
            env_info,
            run_cmd_fn=lambda cmd, *_a: (
                CommandResult(1, "Total: 50%", "")
                if "diff_cover.diff_cover_tool" in cmd
                else CommandResult(0, "", "")
            ),
            cov_env={},
        )
        assert rc_fail == 1


def test_impact_selector_selects_pg18_integration_and_epic30_31_recall() -> None:
    graph = _build_reverse_import_graph(REPO_ROOT, load_pyproject_pythonpath(REPO_ROOT))
    hub_files = [
        "apps/api/src/orcia_api/__init__.py",
        "apps/api/src/orcia_api/main.py",
        "apps/api/src/orcia_api/_router_registry.py",
        "apps/api/src/orcia_api/dependencies/__init__.py",
        "apps/api/src/orcia_api/dependencies/_lazy_exports.py",
        "packages/orcia-core/src/orcia_core/bootstrap/__init__.py",
        "packages/orcia-core/src/orcia_core/bootstrap/_lazy_exports.py",
        "packages/orcia-core/src/orcia_core/orchestration/__init__.py",
        "packages/orcia-core/src/orcia_core/orchestration/_lazy_exports.py",
    ]
    plan_hub_only = select_impacted_targets(
        REPO_ROOT,
        touched_files=hub_files,
        precomputed_graph=graph,
    )
    assert plan_hub_only.integration_tests == []
    assert "tests/unit/tooling/test_shared_test_infra.py" in plan_hub_only.python_tests
    assert (
        "tests/unit/test_story_7_0c_openshift_scc_kustomize_and_ready.py"
        in plan_hub_only.python_tests
    )
    assert "tests/unit/test_openapi_security.py" in plan_hub_only.python_tests

    plan_hub_plus_pg18 = select_impacted_targets(
        REPO_ROOT,
        touched_files=[*hub_files, "tests/integration/db/test_shared_topology_pg18.py"],
        precomputed_graph=graph,
    )
    assert plan_hub_plus_pg18.integration_tests == [
        "tests/integration/db/test_shared_topology_pg18.py"
    ]

    # Epic 30-31 A2/B 8/8 recall validation (SQL, router, migration, perm, MCP, lifespan, agent)
    recall_cases: list[tuple[str, str, bool]] = [
        (
            "packages/orcia-core/src/orcia_core/workflows/_internal/_sql_workflow_v2_pending_query.py",
            "tests/integration/api/test_story_30_3_pending_runs_and_live_guard_postgres18.py",
            True,
        ),
        (
            "apps/api/src/orcia_api/routers/workflows.py",
            "tests/integration/api/test_story_30_3_pending_runs_and_live_guard_postgres18.py",
            True,
        ),
        (
            "infra/migrations/versions/20261125_303_workflow_v2_runs.py",
            "tests/integration/db/test_alembic_migrations_core_pg18.py",
            True,
        ),
        (
            "infra/migrations/versions/20261125_303_workflow_v2_runs.py",
            "tests/integration/db/test_alembic_migrations_governance_pg18.py",
            True,
        ),
        (
            "packages/orcia-core/src/orcia_core/permissions/evaluator.py",
            "tests/unit/test_permissions_and_auth.py",
            False,
        ),
        (
            "packages/orcia-core/src/orcia_core/agents/governed_tool_router.py",
            "tests/unit/test_story_26_6b_governed_tool_router_and_catalog.py",
            False,
        ),
        (
            "apps/api/src/orcia_api/dependencies/_lifespan_infra.py",
            "tests/unit/tooling/test_shared_test_infra.py",
            False,
        ),
        (
            "packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py",
            "tests/integration/api/test_story_30_5_agent_governance_and_lifecycle_pg18.py",
            True,
        ),
        (
            "apps/api/src/orcia_api/routers/assistant_workspace_governance.py",
            "tests/unit/test_story_30_1_assistant_settings_empty_instructions.py",
            False,
        ),
    ]
    for touched_rel, expected_test, is_pg18 in recall_cases:
        plan = select_impacted_targets(
            REPO_ROOT,
            touched_files=[touched_rel],
            precomputed_graph=graph,
        )
        pool = plan.integration_tests if is_pg18 else plan.python_tests
        assert expected_test in pool, f"Recall miss for {touched_rel}: expected {expected_test}"
