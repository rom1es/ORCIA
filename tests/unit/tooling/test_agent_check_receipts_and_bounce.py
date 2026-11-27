"""Unit tests for `agent_check` environment resolution, receipts, and bounce rule."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from scripts.agent_check_lib.changes import detect_changed_files
from scripts.agent_check_lib.env import resolve_toolchain_env
from scripts.agent_check_lib.receipts import (
    BounceDecision,
    compute_worktree_digest,
    evaluate_bounce_rule,
    has_matching_receipt,
    record_failure_state,
    write_receipt,
)


def _init_temp_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@orcia.local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "ORCIA Test"], cwd=repo, check=True)

    (repo / ".gitignore").write_text(".agent_check/\n.venv/\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["packages/a/src", "."]\n',
        encoding="utf-8",
    )
    (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (repo / "packages" / "a" / "src" / "pkg_a").mkdir(parents=True)
    (repo / "packages" / "a" / "src" / "pkg_a" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "packages" / "a" / "src" / "pkg_a" / "mod.py").write_text(
        "VALUE = 1\n", encoding="utf-8"
    )
    (repo / "docs").mkdir()
    (repo / "docs" / "note.md").write_text("# Note\n", encoding="utf-8")
    (repo / "scripts" / "agent_check_lib").mkdir(parents=True)
    (repo / "scripts" / "agent_check.py").write_text("# runner\n", encoding="utf-8")
    (repo / "scripts" / "agent_check_lib" / "__init__.py").write_text("", encoding="utf-8")

    venv_bin = repo / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    python_exe = venv_bin / "python"
    python_exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_exe.chmod(0o755)
    sp = repo / ".venv" / "lib" / "python3.12" / "site-packages"
    (sp / "ruff-0.8.0.dist-info").mkdir(parents=True)
    (sp / "ruff-0.8.0.dist-info" / "METADATA").write_text(
        "Name: ruff\nVersion: 0.8.0\n", encoding="utf-8"
    )

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


def test_resolve_toolchain_env_auto_builds_pythonpath_and_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_temp_git_repo(tmp_path)
    monkeypatch.delenv("ORCIA_VENV", raising=False)
    monkeypatch.setenv("PYTHONPATH", "/unrelated/path")

    env_info = resolve_toolchain_env(repo)
    assert env_info.venv_dir == repo / ".venv"
    assert env_info.python_bin == repo / ".venv" / "bin" / "python"
    expected_prefix = f"{repo / 'packages' / 'a' / 'src'}{os.pathsep}{repo}"
    assert env_info.pythonpath.startswith(expected_prefix)


def test_resolve_toolchain_env_uses_orcia_venv_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_temp_git_repo(tmp_path)
    alt_venv = tmp_path / "alt_venv"
    (alt_venv / "bin").mkdir(parents=True)
    alt_py = alt_venv / "bin" / "python"
    alt_py.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    alt_py.chmod(0o755)
    # Remove local .venv
    for child in sorted((repo / ".venv").rglob("*"), reverse=True):
        child.unlink() if child.is_file() else child.rmdir()
    (repo / ".venv").rmdir()
    monkeypatch.setenv("ORCIA_VENV", str(alt_venv))

    env_info = resolve_toolchain_env(repo)
    assert env_info.venv_dir == alt_venv


def test_receipt_digest_determinism_and_single_byte_invalidation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _init_temp_git_repo(tmp_path)
    monkeypatch.setenv("ORCIA_SECRET_TOKEN", "super-secret-value-123")
    env_info = resolve_toolchain_env(repo)

    d1 = compute_worktree_digest(repo, env_info, node_version="v22.0.0")
    d2 = compute_worktree_digest(repo, env_info, node_version="v22.0.0")
    assert d1 == d2
    assert len(d1) == 64

    receipt_path = write_receipt(repo, "static", d1, summary="5 gates in 0.5s")
    assert receipt_path.name == f"static-{d1}.json"
    receipt_text = receipt_path.read_text(encoding="utf-8")
    assert "super-secret-value-123" not in receipt_text
    assert json.loads(receipt_text)["digest"] == d1
    assert has_matching_receipt(repo, "static", d1) is True

    # 1. Single-byte edit to tracked file invalidates
    (repo / "packages" / "a" / "src" / "pkg_a" / "mod.py").write_text(
        "VALUE = 2\n", encoding="utf-8"
    )
    d_mod = compute_worktree_digest(repo, env_info, node_version="v22.0.0")
    assert d_mod != d1
    assert has_matching_receipt(repo, "static", d_mod) is False

    # 2. Untracked non-ignored file invalidates
    (repo / "untracked.py").write_text("x = 1\n", encoding="utf-8")
    d_untracked = compute_worktree_digest(repo, env_info, node_version="v22.0.0")
    assert d_untracked != d_mod

    # 3. ORCIA_* env var change invalidates
    monkeypatch.setenv("ORCIA_SECRET_TOKEN", "super-secret-value-124")
    d_env = compute_worktree_digest(repo, env_info, node_version="v22.0.0")
    assert d_env != d_untracked

    # 4. pnpm-lock.yaml change invalidates
    (repo / "pnpm-lock.yaml").write_text("lockfileVersion: '9.1'\n", encoding="utf-8")
    d_lock = compute_worktree_digest(repo, env_info, node_version="v22.0.0")
    assert d_lock != d_env

    # 5. .venv dist-info change invalidates
    sp = repo / ".venv" / "lib" / "python3.12" / "site-packages"
    (sp / "ruff-0.8.0.dist-info" / "METADATA").write_text(
        "Name: ruff\nVersion: 0.8.1\n", encoding="utf-8"
    )
    d_venv = compute_worktree_digest(repo, env_info, node_version="v22.0.0")
    assert d_venv != d_lock

    # 6. Runner source hash change invalidates
    (repo / "scripts" / "agent_check.py").write_text("# runner v2\n", encoding="utf-8")
    d_runner = compute_worktree_digest(repo, env_info, node_version="v22.0.0")
    assert d_runner != d_venv


def test_detect_changed_files_and_bounce_rule(tmp_path: Path) -> None:
    repo = _init_temp_git_repo(tmp_path)
    assert detect_changed_files(repo) == []

    # Record a failure on unit test
    record_failure_state(
        repo,
        stage="impact",
        failed_check="pytest:tests/unit/test_mod.py",
        failed_tests=["tests/unit/test_mod.py::test_fail"],
    )

    # Docs-only change -> rerun ONLY the failed check
    (repo / "docs" / "note.md").write_text("# Updated Note\n", encoding="utf-8")
    assert detect_changed_files(repo) == ["docs/note.md"]
    decision_docs = evaluate_bounce_rule(repo)
    assert decision_docs.mode == BounceDecision.ONLY_FAILED_CHECK
    assert decision_docs.failed_check == "pytest:tests/unit/test_mod.py"

    # Non-docs change -> rerun Stage 1 + Stage 2 + failed check
    (repo / "packages" / "a" / "src" / "pkg_a" / "mod.py").write_text(
        "VALUE = 99\n", encoding="utf-8"
    )
    decision_code = evaluate_bounce_rule(repo)
    assert decision_code.mode == BounceDecision.STAGE1_STAGE2_AND_FAILED
