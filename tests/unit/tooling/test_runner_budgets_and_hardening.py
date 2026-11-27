"""Unit tests for Epic 32 Architect Review Majors #1–#4, #6, and suite budgets (`Story 32.5`)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.agent_check_lib.bounce import resolve_junit_test_file
from scripts.agent_check_lib.budgets import (
    BudgetConfig,
    check_raw_suite_budget,
    find_stale_allowlist_ids,
    parse_slow_unit_tests,
)
from scripts.agent_check_lib.coverage_gate import build_diff_cover_patch
from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.receipts import (
    BounceDecision,
    evaluate_bounce_rule,
    record_failure_state,
)
from scripts.agent_check_lib.runner_exec import CommandResult
from scripts.agent_check_lib.stages import run_stage_static, run_with_bounce
from scripts.agent_check_lib.static_gates import validate_gate_result
from scripts.lint_tests_lib.diff_and_routes import find_unguarded_workspace_or_run_routes

pytestmark = pytest.mark.story("32.5")
REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_repo(tmp_path: Path) -> tuple[Path, ToolchainEnv]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (repo / "scripts" / "agent_check_lib").mkdir(parents=True)
    (repo / "packages" / "orcia-core" / "src").mkdir(parents=True)
    (repo / "packages" / "orcia-core" / "src" / "m.py").write_text("x = 1\n", encoding="utf-8")
    env_info = ToolchainEnv(
        repo_root=repo,
        venv_dir=repo / ".venv",
        python_bin=Path("/usr/bin/python3"),
        ruff_bin=Path("/usr/bin/ruff"),
        mypy_bin=Path("/usr/bin/mypy"),
        lint_imports_bin=Path("/usr/bin/lint-imports"),
        pnpm_bin="pnpm",
        node_bin="node",
        pythonpath=str(repo),
    )
    return repo, env_info


def test_major1_scoped_files_never_writes_or_reads_static_receipt(tmp_path: Path) -> None:
    repo, env_info = _make_repo(tmp_path)
    ok_res = CommandResult(0, "", "")
    with (
        patch("scripts.agent_check_lib.stages._run_cmd", return_value=ok_res),
        patch("scripts.agent_check_lib.static_gates.run_cmd", return_value=ok_res),
    ):
        rc = run_stage_static(
            env_info,
            touched_files=["packages/orcia-core/src/m.py"],
            no_skip=False,
            scoped_files=True,
        )
    assert rc == 0
    assert list((repo / ".agent_check" / "receipts").glob("static-*.json")) == []


def test_major2_static_preserves_stage3_failure_and_resolves_class_junit_and_bounce(
    tmp_path: Path,
) -> None:
    repo, env_info = _make_repo(tmp_path)
    (repo / "tests" / "unit").mkdir(parents=True)
    test_file = repo / "tests" / "unit" / "test_alpha.py"
    test_file.write_text(
        "class TestAlpha:\n    def test_one(self): assert True\n", encoding="utf-8"
    )

    assert (
        resolve_junit_test_file(repo, "tests.unit.test_alpha.TestAlpha::test_one")
        == "tests/unit/test_alpha.py"
    )

    with patch(
        "scripts.agent_check_lib.receipts.snapshot_dirty_hashes",
        return_value=("h1", {"a": "1"}, {}),
    ):
        record_failure_state(
            repo,
            stage="full",
            failed_check="pytest:evals-security-contract",
            failed_tests=["tests.evals.test_x::test_y"],
        )

    ok_res = CommandResult(0, "", "")
    with (
        patch("scripts.agent_check_lib.stages._run_cmd", return_value=ok_res),
        patch("scripts.agent_check_lib.static_gates.run_cmd", return_value=ok_res),
    ):
        assert run_stage_static(env_info, touched_files=[], no_skip=False) == 0

    state_file = repo / ".agent_check" / "state" / "last_failure.json"
    assert state_file.is_file(), "Stage 1 pass must preserve Stage 3 last_failure.json"

    with patch(
        "scripts.agent_check_lib.receipts.snapshot_dirty_hashes",
        return_value=("h1", {"a": "2"}, {}),
    ):
        plan = evaluate_bounce_rule(repo)
        assert plan.mode == BounceDecision.STAGE1_STAGE2_AND_FAILED

    called_suites: list[str] = []

    def fake_pytest(_env, *, stage, check_key, targets, **_kw):  # type: ignore[no-untyped-def]
        called_suites.append(check_key)
        return 0, f"PASS [{stage}]"

    with (
        patch("scripts.agent_check_lib.stages.run_stage_static", return_value=0),
        patch("scripts.agent_check_lib.stages.run_stage_impact", return_value=0),
        patch("scripts.agent_check_lib.stages.run_pytest_suite", side_effect=fake_pytest),
        patch(
            "scripts.agent_check_lib.receipts.snapshot_dirty_hashes",
            return_value=("h1", {"a": "2"}, {}),
        ),
    ):
        rc = run_with_bounce(
            env_info,
            stage="full",
            touched_files=[],
            no_skip=False,
            maxfail=None,
            explain=False,
        )
    assert rc == 0
    assert called_suites == ["pytest:evals-security-contract"]
    assert not state_file.exists()


def test_minor2_pg18_bounce_falls_back_to_junit_failed_tests_when_impact_empty(
    tmp_path: Path,
) -> None:
    repo, env_info = _make_repo(tmp_path)
    pg_file = repo / "tests" / "integration" / "test_pg_sample.py"
    pg_file.parent.mkdir(parents=True)
    pg_file.write_text("def test_pg(): assert True\n", encoding="utf-8")

    with patch(
        "scripts.agent_check_lib.receipts.snapshot_dirty_hashes",
        return_value=("h1", {"a": "1"}, {}),
    ):
        record_failure_state(
            repo,
            stage="full-pg18",
            failed_check="pytest:tests/integration",
            failed_tests=["tests.integration.test_pg_sample::test_pg"],
        )

    ran_targets: list[list[str]] = []

    def fake_pg_pytest(_env, *, stage, check_key, targets, **_kw):  # type: ignore[no-untyped-def]
        ran_targets.append(list(targets))
        return 0, f"PASS [{stage}]"

    with (
        patch("scripts.agent_check_lib.stages.run_stage_static", return_value=0),
        patch("scripts.agent_check_lib.stages.run_stage_impact", return_value=0),
        patch("scripts.agent_check_lib.bounce.resolve_impacted_pg18_tests", return_value=[]),
        patch("scripts.agent_check_lib.stages.run_pytest_suite", side_effect=fake_pg_pytest),
        patch(
            "scripts.agent_check_lib.receipts.snapshot_dirty_hashes",
            return_value=("h1", {"a": "2"}, {}),
        ),
    ):
        rc = run_with_bounce(
            env_info, stage="full", touched_files=[], no_skip=False, maxfail=None, explain=False
        )
    assert rc == 0
    assert ran_targets == [["tests/integration/test_pg_sample.py"]]


def test_major3_diff_cover_patch_includes_new_untracked_directory_py_files(tmp_path: Path) -> None:
    repo = tmp_path / "git_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ci@orcia.local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "ORCIA CI"], cwd=repo, check=True)
    (repo / "packages" / "orcia-core" / "src").mkdir(parents=True)
    init_file = repo / "packages" / "orcia-core" / "src" / "__init__.py"
    init_file.write_text("", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    new_dir = repo / "packages" / "orcia-core" / "src" / "brand_new_pkg"
    new_dir.mkdir()
    (new_dir / "module.py").write_text("def hello() -> int:\n    return 42\n", encoding="utf-8")

    patch_path = repo / ".agent_check" / "diff_cover.patch"
    assert build_diff_cover_patch(repo, out_path=patch_path) is True
    patch_text = patch_path.read_text(encoding="utf-8")
    assert "packages/orcia-core/src/brand_new_pkg/module.py" in patch_text


def test_major4_lint_spine_json_ok_false_fails_even_with_exit_zero() -> None:
    bad = CommandResult(0, json.dumps({"ok": False, "total_findings": 2}), "")
    checked = validate_gate_result("lint-spine", bad)
    assert checked.returncode == 1

    good = CommandResult(0, json.dumps({"ok": True, "total_findings": 0}), "")
    assert validate_gate_result("lint-spine", good).returncode == 0


def test_major6_assistant_routes_are_not_false_flagged_and_module_scoped_helpers(
    tmp_path: Path,
) -> None:
    ratchet_cfg = json.loads(
        (REPO_ROOT / "scripts" / "lint_tests_ratchet.json").read_text(encoding="utf-8")
    )
    allowlist = ratchet_cfg["unguarded_routes_allowlist"]
    assert not any("assistant_" in entry for entry in allowlist)
    assert len(allowlist) <= 18

    mini = tmp_path / "api_repo"
    routers = mini / "apps" / "api" / "src" / "orcia_api" / "routers"
    deps = mini / "apps" / "api" / "src" / "orcia_api" / "dependencies"
    routers.mkdir(parents=True)
    deps.mkdir(parents=True)
    (deps / "guards.py").write_text(
        "def enforce_ws(ws_id):\n    return evaluator.resolve_workspace_access(ws_id)\n",
        encoding="utf-8",
    )
    (routers / "a_guarded.py").write_text(
        "def _helper(ws_id):\n    return enforce_ws(ws_id)\n"
        "@router.get('/a/{workspace_id}')\n"
        "def route_a(workspace_id: str):\n"
        "    return _helper(workspace_id)\n",
        encoding="utf-8",
    )
    (routers / "b_unguarded.py").write_text(
        "def _helper(ws_id):\n    return ws_id\n"
        "@router.get('/b/{workspace_id}')\n"
        "def route_b(workspace_id: str):\n"
        "    return _helper(workspace_id)\n",
        encoding="utf-8",
    )
    flagged = find_unguarded_workspace_or_run_routes(mini)
    assert flagged == ["apps/api/src/orcia_api/routers/b_unguarded.py:route_b"]


def test_budgets_module_validates_raw_suite_ceilings_slow_tests_and_stale_ids(
    tmp_path: Path,
) -> None:
    cfg = BudgetConfig(
        unit_budget_s=120.0,
        esc_budget_s=45.0,
        max_unit_test_s=1.0,
        slow_unit_allowlist=frozenset({"tests.unit.test_slow::test_allowed"}),
    )
    ok_u, _ = check_raw_suite_budget("tests/unit", 110.5, config=cfg)
    assert ok_u is True
    bad_u, msg_u = check_raw_suite_budget("tests/unit", 125.0, config=cfg)
    assert bad_u is False and "FAIL" in msg_u
    ok_e, _ = check_raw_suite_budget("evals_security_contract", 32.0, config=cfg)
    assert ok_e is True

    xml_path = tmp_path / "junit.xml"
    xml_path.write_text(
        "<testsuite>"
        '<testcase classname="tests.unit.test_fast" name="test_ok" time="0.15"/>'
        '<testcase classname="tests.unit.test_slow" name="test_allowed" time="1.45"/>'
        '<testcase classname="tests.unit.test_slow" name="test_too_slow" time="1.85"/>'
        "</testsuite>",
        encoding="utf-8",
    )
    slow = parse_slow_unit_tests(
        xml_path, max_duration_s=cfg.max_unit_test_s, allowlist=cfg.slow_unit_allowlist
    )
    assert slow == [("tests.unit.test_slow::test_too_slow", 1.85)]
    assert find_stale_allowlist_ids(xml_path, allowlist=cfg.slow_unit_allowlist) == []
    stale = find_stale_allowlist_ids(
        xml_path,
        allowlist=frozenset({"tests.unit.test_slow::test_allowed", "tests.unit.missing::test_x"}),
    )
    assert stale == ["tests.unit.missing::test_x"]
