"""Unit tests for `stages`, `changes`, `output`, and `impact` edge cases."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.agent_check_lib.changes import (
    detect_changed_files,
    hash_file_bytes,
    normalize_file_args,
)
from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.impact import (
    _build_reverse_import_graph,
    _collect_router_paths,
    _extract_imported_modules,
    _module_name_for_path,
    select_impacted_targets,
)
from scripts.agent_check_lib.output import (
    _compact_traceback,
    parse_pytest_junitxml,
    parse_vitest_json,
    write_stage_log,
)
from scripts.agent_check_lib.receipts import record_failure_state
from scripts.agent_check_lib.runner_exec import CommandResult
from scripts.agent_check_lib.stages import (
    _has_package_script,
    run_stage_full,
    run_stage_fuzz,
    run_stage_impact,
    run_stage_static,
    run_with_bounce,
)


def _setup_repo(tmp_path: Path) -> tuple[Path, ToolchainEnv]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["packages/a/src", "."]\n', encoding="utf-8"
    )
    (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (repo / "package.json").write_text('{"scripts": {"site:check": "echo ok"}}\n', encoding="utf-8")
    (repo / "scripts" / "agent_check_lib").mkdir(parents=True)
    (repo / "scripts" / "agent_check.py").write_text("# cli\n", encoding="utf-8")
    (repo / "scripts" / "agent_check_lib" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "scripts" / "check_implementation_docs.py").write_text("# docs\n", encoding="utf-8")
    (repo / "tests" / "unit").mkdir(parents=True)
    (repo / "tests" / "unit" / "test_sample.py").write_text(
        "def test_ok(): assert True\n", encoding="utf-8"
    )
    (repo / "apps" / "web" / "src").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text("{}", encoding="utf-8")
    (repo / "apps" / "web" / "src" / "a.tsx").write_text("export const x = 1;\n", encoding="utf-8")
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


def test_changes_no_head_normalize_args_and_deleted_hash(tmp_path: Path) -> None:
    repo = tmp_path / "git_no_head"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / "staged.py").write_text("a = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "staged.py"], cwd=repo, check=True)
    (repo / "untracked.py").write_text("b = 2\n", encoding="utf-8")

    assert detect_changed_files(repo) == ["staged.py", "untracked.py"]
    abs_in = str(repo / "staged.py")
    abs_out = str(tmp_path / "external.py")
    norm = normalize_file_args(repo, [f" {abs_in} , , ./untracked.py", abs_out])
    assert norm == [abs_out, "staged.py", "untracked.py"]
    assert hash_file_bytes(repo / "missing.py") == "DELETED"


def test_output_edge_cases_corrupt_files_and_long_traceback(tmp_path: Path) -> None:
    assert parse_pytest_junitxml(tmp_path / "missing.xml") == ([], [])
    bad_xml = tmp_path / "bad.xml"
    bad_xml.write_text("<unclosed", encoding="utf-8")
    assert parse_pytest_junitxml(bad_xml) == ([], [])

    assert parse_vitest_json(tmp_path / "missing.json") == ([], [])
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{not-json", encoding="utf-8")
    assert parse_vitest_json(bad_json) == ([], [])

    long_tb = "\n".join(f"line {i}" for i in range(25))
    compacted = _compact_traceback(long_tb)
    assert "..." in compacted
    assert len(compacted.splitlines()) <= 14

    outside = write_stage_log(tmp_path / "root", "impact", "raw log")
    assert outside.as_posix().endswith(".log")


def test_impact_ast_and_module_edge_cases(tmp_path: Path) -> None:
    repo = tmp_path / "imp"
    (repo / "packages" / "a" / "src" / "pkg").mkdir(parents=True)
    (repo / "packages" / "a" / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "packages" / "a" / "src" / "pkg" / ".venv").mkdir()
    (repo / "packages" / "a" / "src" / "pkg" / ".venv" / "ignored.py").write_text(
        "x = 1\n", encoding="utf-8"
    )
    bad_py = repo / "packages" / "a" / "src" / "pkg" / "broken.py"
    bad_py.write_text("def oops(:\n", encoding="utf-8")
    star_py = repo / "packages" / "a" / "src" / "pkg" / "star.py"
    star_py.write_text("import os\nfrom math import *\n", encoding="utf-8")
    (repo / "tests" / "unit").mkdir(parents=True)
    (repo / "tests" / "unit" / "test_star.py").write_text(
        "from pkg.star import *\ndef test_s(): pass\n", encoding="utf-8"
    )

    roots = [repo / "packages" / "a" / "src"]
    assert (
        _module_name_for_path(repo / "packages" / "a" / "src" / "pkg" / "__init__.py", roots)
        == "pkg"
    )
    assert _module_name_for_path(repo / "README.md", roots) is None
    assert _extract_imported_modules(bad_py) == set()
    assert "os" in _extract_imported_modules(star_py)
    assert _collect_router_paths(repo / "nonexistent.py") == set()

    rev, mod_to_rel = _build_reverse_import_graph(repo, roots)
    assert "pkg.star" in rev
    assert "pkg.star" in mod_to_rel

    plan = select_impacted_targets(
        repo, touched_files=["tests/unit/test_star.py", "packages/a/src/pkg/star.py"]
    )
    assert "tests/unit/test_star.py" in plan.python_tests


def test_stages_static_impact_full_fuzz_and_bounce_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, env_info = _setup_repo(tmp_path)

    # _has_package_script branches
    assert _has_package_script(tmp_path / "absent", "site:check") is False
    corrupt_repo = tmp_path / "corrupt"
    corrupt_repo.mkdir()
    (corrupt_repo / "package.json").write_text("{bad", encoding="utf-8")
    assert _has_package_script(corrupt_repo, "site:check") is False

    # 1. Stage static failure
    with (
        patch("scripts.agent_check_lib.stages._run_cmd", return_value=CommandResult(1, "E501", "")),
        patch(
            "scripts.agent_check_lib.static_gates.run_cmd", return_value=CommandResult(0, "", "")
        ),
    ):
        assert run_stage_static(env_info, touched_files=[], no_skip=True) == 1
        assert "FAIL [static]: ruff-check failed" in capsys.readouterr().out

    # 2. Stage impact explain + python failure + vitest failure + pass
    with patch(
        "scripts.agent_check_lib.stages.run_pytest_suite",
        return_value=(1, "FAIL [impact]: 1 failed"),
    ):
        assert (
            run_stage_impact(
                env_info, touched_files=["tests/unit/test_sample.py"], maxfail=1, explain=True
            )
            == 1
        )
        out = capsys.readouterr().out
        assert "EXPLAIN tests/unit/test_sample.py:" in out
        assert "FAIL [impact]: 1 failed" in out

    with (
        patch("scripts.agent_check_lib.stages.run_pytest_suite", return_value=(0, "PASS")),
        patch("scripts.agent_check_lib.stages.run_vitest_related", return_value=(1, "FAIL vitest")),
    ):
        assert (
            run_stage_impact(
                env_info, touched_files=["apps/web/src/a.tsx"], maxfail=None, explain=False
            )
            == 1
        )
        assert "FAIL vitest" in capsys.readouterr().out

    with (
        patch("scripts.agent_check_lib.stages.run_pytest_suite", return_value=(0, "PASS")),
        patch("scripts.agent_check_lib.stages.run_vitest_related", return_value=(0, None)),
    ):
        assert (
            run_stage_impact(
                env_info, touched_files=["apps/web/src/a.tsx"], maxfail=None, explain=False
            )
            == 0
        )
        assert "PASS [impact]:" in capsys.readouterr().out

    # 3. Stage full failure branches (unit fail, esc fail, vitest fail, site:check fail)
    with patch("scripts.agent_check_lib.stages.run_pytest_suite", return_value=(1, "FAIL unit")):
        assert run_stage_full(env_info, no_skip=True) == 1

    with patch(
        "scripts.agent_check_lib.stages.run_pytest_suite",
        side_effect=[(0, "PASS unit"), (1, "FAIL esc")],
    ):
        assert run_stage_full(env_info, no_skip=True) == 1

    with (
        patch(
            "scripts.agent_check_lib.stages.run_pytest_suite",
            side_effect=[(0, "PASS unit"), (0, "PASS esc")],
        ),
        patch("scripts.agent_check_lib.stages.run_vitest_suite", return_value=(1, "FAIL vitest")),
    ):
        assert run_stage_full(env_info, no_skip=True) == 1

    with (
        patch(
            "scripts.agent_check_lib.stages.run_pytest_suite",
            side_effect=[(0, "PASS unit"), (0, "PASS esc")],
        ),
        patch("scripts.agent_check_lib.stages.run_vitest_suite", return_value=(0, None)),
        patch(
            "scripts.agent_check_lib.stages._run_cmd",
            side_effect=[CommandResult(0, "ok", ""), CommandResult(1, "site err", "")],
        ),
    ):
        assert run_stage_full(env_info, no_skip=True) == 1

    # 4. Stage fuzz + run_with_bounce paths
    with patch("scripts.agent_check_lib.stages.run_pytest_suite", return_value=(0, "PASS [fuzz]:")):
        assert run_stage_fuzz(env_info) == 0

    record_failure_state(
        repo,
        stage="impact",
        failed_check="pytest:tests/unit/test_sample.py",
        failed_tests=["tests.unit.test_sample::test_ok"],
    )
    with patch(
        "scripts.agent_check_lib.stages.run_pytest_suite", return_value=(0, "PASS [bounce]:")
    ):
        assert (
            run_with_bounce(
                env_info, stage="impact", touched_files=[], no_skip=False, maxfail=1, explain=False
            )
            == 0
        )

    # Non-docs bounce + `all` stage dispatch
    with (
        patch("scripts.agent_check_lib.stages.run_stage_static", return_value=0),
        patch("scripts.agent_check_lib.stages.run_stage_impact", return_value=0),
        patch("scripts.agent_check_lib.stages.run_stage_full", return_value=0),
    ):
        assert (
            run_with_bounce(
                env_info, stage="all", touched_files=[], no_skip=True, maxfail=None, explain=False
            )
            == 0
        )
        assert (
            run_with_bounce(
                env_info, stage="full", touched_files=[], no_skip=True, maxfail=None, explain=False
            )
            == 0
        )
    with patch("scripts.agent_check_lib.stages.run_stage_fuzz", return_value=0):
        assert (
            run_with_bounce(
                env_info, stage="fuzz", touched_files=[], no_skip=True, maxfail=None, explain=False
            )
            == 0
        )
