"""Unit tests for `agent_check` CLI and Stage 1/2/3 execution behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.agent_check import main as cli_main
from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.receipts import compute_worktree_digest
from scripts.agent_check_lib.runner_exec import CommandResult
from scripts.agent_check_lib.stages import run_stage_full, run_stage_static


def _make_fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["packages/orcia-core/src", "."]\n',
        encoding="utf-8",
    )
    (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (repo / "package.json").write_text('{"scripts": {"site:check": "echo ok"}}\n', encoding="utf-8")
    (repo / "scripts" / "agent_check_lib").mkdir(parents=True)
    (repo / "scripts" / "agent_check.py").write_text("# runner\n", encoding="utf-8")
    (repo / "scripts" / "agent_check_lib" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "scripts" / "check_implementation_docs.py").write_text("# docs\n", encoding="utf-8")
    (repo / "packages" / "orcia-core" / "src").mkdir(parents=True)
    (repo / "packages" / "orcia-core" / "src" / "sample.py").write_text("x=1\n", encoding="utf-8")
    (repo / "apps" / "web" / "src").mkdir(parents=True)
    (repo / "apps" / "web" / "package.json").write_text(
        '{"name": "@orcia/web"}\n', encoding="utf-8"
    )
    (repo / "apps" / "web" / "src" / "App.tsx").write_text(
        "export const A = 1;\n", encoding="utf-8"
    )
    return repo


def _fake_env(repo: Path) -> ToolchainEnv:
    return ToolchainEnv(
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


def test_cli_rejects_maxfail_on_full_stage() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["full", "--maxfail", "2"])
    assert exc_info.value.code == 2


def test_stage_static_autofixes_writes_post_fix_receipt_and_skips_repeat(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _make_fake_repo(tmp_path)
    env_info = _fake_env(repo)
    executed_cmds: list[list[str]] = []

    def fake_exec(cmd: list[str], cwd: Path, env: dict[str, str]) -> CommandResult:
        executed_cmds.append(cmd)
        if "ruff" in cmd[0] and "format" in cmd and "--check" not in cmd:
            target = repo / "packages" / "orcia-core" / "src" / "sample.py"
            target.write_text("x = 1\n", encoding="utf-8")
        return CommandResult(returncode=0, stdout="", stderr="")

    touched = ["packages/orcia-core/src/sample.py", "apps/web/src/App.tsx"]
    with (
        patch("scripts.agent_check_lib.stages._run_cmd", side_effect=fake_exec),
        patch("scripts.agent_check_lib.static_gates.run_cmd", side_effect=fake_exec),
    ):
        rc1 = run_stage_static(env_info, touched_files=touched, no_skip=False)
        out1 = capsys.readouterr().out
        assert rc1 == 0
        assert "AUTOFIXED: packages/orcia-core/src/sample.py" in out1
        assert "WARN [static]: .secrets.baseline absent" in out1
        assert "PASS [static]:" in out1
        assert all("--unsafe-fixes" not in c for c in executed_cmds)
        assert any("lint" in c and "@orcia/web" in c for c in executed_cmds)
        assert any("typecheck" in c and "@orcia/web" in c for c in executed_cmds)
        assert not any("site:check" in c for c in executed_cmds)

        post_digest = compute_worktree_digest(repo, env_info)
        executed_cmds.clear()
        rc2 = run_stage_static(env_info, touched_files=touched, no_skip=False)
        out2 = capsys.readouterr().out
        assert rc2 == 0
        assert f"SKIP [static]: receipt {post_digest[:12]}" in out2
        assert executed_cmds == []


def test_stage_full_runs_unit_esc_vitest_docs_and_site_check_and_skips_unit_vitest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _make_fake_repo(tmp_path)
    env_info = _fake_env(repo)
    cmds: list[list[str]] = []

    def fake_exec(cmd: list[str], cwd: Path, env: dict[str, str]) -> CommandResult:
        cmds.append(cmd)
        return CommandResult(returncode=0, stdout="", stderr="")

    with (
        patch("scripts.agent_check_lib.runner_exec.run_cmd", side_effect=fake_exec),
        patch("scripts.agent_check_lib.stages._run_cmd", side_effect=fake_exec),
    ):
        rc1 = run_stage_full(env_info, no_skip=False)
        out1 = capsys.readouterr().out
        assert rc1 == 0
        assert "PASS [full-unit]:" in out1
        assert "PASS [full-vitest]:" in out1
        assert "PASS [full-docs-site]:" in out1
        assert any("check_implementation_docs.py" in " ".join(c) for c in cmds)
        assert any("site:check" in c for c in cmds)

        cmds.clear()
        rc2 = run_stage_full(env_info, no_skip=False)
        out2 = capsys.readouterr().out
        assert rc2 == 0
        assert "SKIP [full-unit]: receipt" in out2
        assert "SKIP [full-vitest]: receipt" in out2
        # Non-skippable evals+security+contract and docs/site still execute
        assert any("tests/evals" in c for c in cmds)
        assert any("site:check" in c for c in cmds)
