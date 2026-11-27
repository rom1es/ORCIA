"""Unit tests for `runner_exec`, `static_gates`, and `env` edge cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.agent_check_lib.env import (
    ToolchainEnv,
    load_pyproject_pythonpath,
    resolve_repo_root,
    resolve_venv_dir,
)
from scripts.agent_check_lib.runner_exec import (
    CommandResult,
    emit_check_failure,
    run_cmd,
    run_pytest_suite,
    run_vitest_suite,
)
from scripts.agent_check_lib.static_gates import (
    SPINE_SCRIPT_REL,
    SPINE_WORKSPACE_REL,
    autofix_touched_python,
    build_static_gates,
    resolve_mypy_targets,
    resolve_ts_packages,
    run_single_cmd,
)


def _env_for(repo: Path) -> ToolchainEnv:
    return ToolchainEnv(
        repo_root=repo,
        venv_dir=repo / ".venv",
        python_bin=Path(sys.executable),
        ruff_bin=repo / ".venv" / "bin" / "ruff",
        mypy_bin=repo / ".venv" / "bin" / "mypy",
        lint_imports_bin=repo / ".venv" / "bin" / "lint-imports",
        pnpm_bin="pnpm",
        node_bin="node",
        pythonpath=str(repo),
    )


def test_env_fallbacks_without_git_pyproject_or_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sub = tmp_path / "no_git" / "nested"
    sub.mkdir(parents=True)
    # Without git or pyproject.toml -> falls back to anchor
    assert resolve_repo_root(sub) == sub.resolve()
    assert load_pyproject_pythonpath(sub) == [sub]

    # With pyproject.toml in parent -> walks parents
    (tmp_path / "no_git" / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    assert resolve_repo_root(sub) == (tmp_path / "no_git").resolve()

    # Missing both .venv and ORCIA_VENV -> RuntimeError
    monkeypatch.delenv("ORCIA_VENV", raising=False)
    with pytest.raises(RuntimeError, match="ORCIA_VENV"):
        resolve_venv_dir(sub)

    env_info = _env_for(tmp_path / "no_git")
    sub_env = env_info.subprocess_env()
    assert sub_env["PYTHONPATH"] == str(tmp_path / "no_git")
    assert str(env_info.venv_dir / "bin") in sub_env["PATH"]


def test_run_cmd_and_run_single_cmd_real_python(tmp_path: Path) -> None:
    res = run_cmd([sys.executable, "-c", "print('hello')"], tmp_path, {})
    assert res.returncode == 0
    assert res.stdout.strip() == "hello"
    res2 = run_single_cmd([sys.executable, "-c", "import sys; sys.exit(2)"], tmp_path, {})
    assert res2.returncode == 2


def test_run_pytest_suite_passes_collect_zero_maxfail_and_fallback_failure(tmp_path: Path) -> None:
    env_info = _env_for(tmp_path)

    with patch(
        "scripts.agent_check_lib.runner_exec.run_cmd",
        return_value=CommandResult(returncode=5, stdout="no tests ran", stderr=""),
    ) as mocked:
        rc, msg = run_pytest_suite(
            env_info,
            stage="impact",
            check_key="pytest:impact",
            targets=["tests/unit/test_x.py"],
            extra_args=["-m", "not contract_fuzz"],
            maxfail=2,
        )
        assert rc == 0
        assert "0 tests collected" in msg
        assert "--maxfail=2" in mocked.call_args.args[0]

    # Failure with empty/absent JUnit XML triggers fallback failing_ids
    with patch(
        "scripts.agent_check_lib.runner_exec.run_cmd",
        return_value=CommandResult(returncode=1, stdout="boom stdout", stderr="boom stderr"),
    ):
        rc_fail, msg_fail = run_pytest_suite(
            env_info,
            stage="impact",
            check_key="pytest:impact",
            targets=["tests/unit/test_x.py"],
            extra_args=[],
        )
        assert rc_fail == 1
        assert "FAIL [impact]: 1 failed" in msg_fail
        assert "  - pytest:impact" in msg_fail
        assert "LOG: .agent_check/logs/impact-" in msg_fail


def test_run_vitest_suite_parses_json_and_handles_empty_fallback(tmp_path: Path) -> None:
    env_info = _env_for(tmp_path)

    def _fail_with_json(cmd: list[str], _cwd: Path, _env: dict[str, str]) -> CommandResult:
        out_flag = next(c for c in cmd if c.startswith("--outputFile="))
        out_path = Path(out_flag.split("=", 1)[1])
        out_path.write_text(
            json.dumps(
                {
                    "testResults": [
                        {
                            "name": "a.test.ts",
                            "status": "failed",
                            "assertionResults": [],
                            "message": "Transform failed\nline 2",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return CommandResult(returncode=1, stdout="fail", stderr="")

    with patch("scripts.agent_check_lib.runner_exec.run_cmd", side_effect=_fail_with_json):
        rc, msg = run_vitest_suite(
            env_info, stage="full-vitest", pkg_rel="apps/web", files=None, t0=0.0
        )
        assert rc == 1 and msg is not None
        assert "a.test.ts" in msg
        assert "Transform failed" in msg

    with patch(
        "scripts.agent_check_lib.runner_exec.run_cmd",
        return_value=CommandResult(returncode=1, stdout="", stderr="crash"),
    ):
        rc2, msg2 = run_vitest_suite(
            env_info, stage="impact", pkg_rel="packages/ui", files=["src/a.tsx"], t0=0.0
        )
        assert rc2 == 1 and msg2 is not None
        assert "vitest:packages/ui" in msg2


def test_emit_check_failure_empty_and_populated(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = emit_check_failure(
        tmp_path, "static", "mypy", CommandResult(returncode=1, stdout="", stderr=""), 0.5
    )
    assert rc == 1
    out = capsys.readouterr().out
    assert "FAIL [static]: mypy failed" in out
    assert "  - mypy" in out


def test_static_gates_mypy_ts_spine_secrets_and_autofix(tmp_path: Path) -> None:
    (tmp_path / "packages" / "orcia-core" / "src").mkdir(parents=True)
    (tmp_path / "packages" / "orcia-core" / "src" / "a.py").write_text("x=1\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "tool.py").write_text("y=1\n", encoding="utf-8")
    (tmp_path / "scripts" / "export_openapi.py").write_text("# openapi\n", encoding="utf-8")
    (tmp_path / "apps" / "web").mkdir(parents=True)
    (tmp_path / "apps" / "web" / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "packages" / "ui").mkdir(parents=True)
    (tmp_path / "packages" / "ui" / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / SPINE_SCRIPT_REL).parent.mkdir(parents=True)
    (tmp_path / SPINE_SCRIPT_REL).write_text("# spine\n", encoding="utf-8")
    (tmp_path / SPINE_WORKSPACE_REL).mkdir(parents=True)
    (tmp_path / ".secrets.baseline").write_text("{}", encoding="utf-8")
    hook = tmp_path / ".venv" / "bin" / "detect-secrets-hook"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/bin/sh\n", encoding="utf-8")

    # resolve_mypy_targets
    assert resolve_mypy_targets(tmp_path, ["pyproject.toml"]) == ["packages/orcia-core"]
    assert resolve_mypy_targets(
        tmp_path, ["packages/orcia-core/src/a.py", "scripts/tool.py", "README.md"]
    ) == ["packages/orcia-core", "scripts/tool.py"]

    # resolve_ts_packages
    assert resolve_ts_packages(tmp_path, ["package.json"], force_all=False) == [
        "@orcia/ui",
        "@orcia/web",
    ]
    assert resolve_ts_packages(tmp_path, ["README.md"], force_all=False) == []
    assert resolve_ts_packages(tmp_path / "empty", [], force_all=False) == []

    env_info = _env_for(tmp_path)
    gates, warnings = build_static_gates(
        env_info,
        touched_files=["scripts/tool.py", "apps/web/package.json"],
        no_skip=False,
    )
    gate_names = [name for name, _ in gates]
    assert "mypy" in gate_names
    assert "openapi-check" in gate_names
    assert "lint-spine" in gate_names
    assert "detect-secrets" in gate_names
    assert "ts-lint:@orcia/web" in gate_names
    assert warnings == []

    assert autofix_touched_python(env_info, [], {}) == []
