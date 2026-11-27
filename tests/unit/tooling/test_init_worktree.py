"""Unit tests for `scripts/init_worktree.sh` (worktree + post-merge main modes)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
INIT_SCRIPT = REPO_ROOT / "scripts" / "init_worktree.sh"


def _git(cwd: Path, *args: str) -> str:
    res = subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return res.stdout.strip()


def _seed_main_repo(tmp_path: Path, *, with_bmad_custom: bool = True) -> Path:
    main = tmp_path / "main-repo"
    main.mkdir(parents=True)
    _git(main, "init", "-b", "main")
    _git(main, "config", "user.email", "test@example.com")
    _git(main, "config", "user.name", "Test")
    (main / ".gitignore").write_text(
        ".venv/\n/.venv\n.secrets.baseline\n_bmad/\n.agents/bmad-custom/*.user.toml\n",
        encoding="utf-8",
    )
    if with_bmad_custom:
        (main / ".agents" / "bmad-custom").mkdir(parents=True)
        (main / ".agents" / "bmad-custom" / "config.toml").write_text(
            "[workflow]\npersistent_facts = []\n", encoding="utf-8"
        )
    _git(main, "add", ".")
    _git(main, "commit", "-q", "-m", "init")

    # Ignored local tools in main checkout
    (main / ".venv" / "bin").mkdir(parents=True)
    (main / ".venv" / "bin" / "python").write_text("#!/bin/sh\n", encoding="utf-8")
    (main / ".secrets.baseline").write_text("{}\n", encoding="utf-8")
    (main / "_bmad" / "scripts").mkdir(parents=True)
    (main / "_bmad" / "config.toml").write_text("[core]\n", encoding="utf-8")
    (main / "_bmad" / "scripts" / "resolve_config.py").write_text("# r\n", encoding="utf-8")
    (main / "_bmad" / "custom").mkdir(parents=True)
    (main / "_bmad" / "custom" / "config.toml").write_text("[workflow]\n", encoding="utf-8")
    (main / "_bmad" / "custom" / "config.user.toml").write_text(
        "[core]\nuser_name = 'Tester'\n", encoding="utf-8"
    )
    return main


def test_worktree_bootstrap_links_idempotency_and_main_isolation(tmp_path: Path) -> None:
    assert INIT_SCRIPT.is_file(), f"Missing {INIT_SCRIPT}"
    main = _seed_main_repo(tmp_path, with_bmad_custom=True)
    wt = tmp_path / "wt-feature"
    _git(main, "worktree", "add", "-q", "-b", "feat", str(wt))

    env = {**os.environ, "ORCIA_BMAD_BACKUP_DIR": str(tmp_path / "bak1")}
    for _ in range(2):
        res = subprocess.run(
            ["bash", str(INIT_SCRIPT)], cwd=wt, env=env, capture_output=True, text=True
        )
        assert res.returncode == 0, res.stderr

    assert (wt / ".venv").is_symlink()
    assert (wt / ".venv").resolve() == (main / ".venv").resolve()
    assert (wt / ".secrets.baseline").is_symlink()
    assert (wt / ".secrets.baseline").resolve() == (main / ".secrets.baseline").resolve()
    assert (wt / "_bmad").is_dir() and not (wt / "_bmad").is_symlink()
    assert (wt / "_bmad" / "config.toml").is_symlink()
    assert (wt / "_bmad" / "scripts").is_symlink()
    assert (wt / "_bmad" / "custom").is_symlink()
    assert os.readlink(wt / "_bmad" / "custom") == "../.agents/bmad-custom"
    assert (wt / ".agents" / "bmad-custom" / "config.user.toml").is_symlink()

    # Main checkout must remain completely untouched
    assert (main / "_bmad" / "custom").is_dir()
    assert not (main / "_bmad" / "custom").is_symlink()
    assert _git(wt, "status", "--porcelain") == ""

    # Existing real file is never overwritten
    (wt / ".secrets.baseline").unlink()
    (wt / ".secrets.baseline").write_text('{"local": true}\n', encoding="utf-8")
    res_skip = subprocess.run(
        ["bash", str(INIT_SCRIPT)], cwd=wt, env=env, capture_output=True, text=True
    )
    assert res_skip.returncode == 0
    assert not (wt / ".secrets.baseline").is_symlink()
    assert '{"local": true}' in (wt / ".secrets.baseline").read_text(encoding="utf-8")


def test_main_checkout_pre_merge_noop_and_post_merge_switchover(tmp_path: Path) -> None:
    assert INIT_SCRIPT.is_file(), f"Missing {INIT_SCRIPT}"
    main_pre = _seed_main_repo(tmp_path / "pre", with_bmad_custom=False)
    (tmp_path / "pre").mkdir(exist_ok=True)
    res_pre = subprocess.run(
        ["bash", str(INIT_SCRIPT)], cwd=main_pre, capture_output=True, text=True
    )
    assert res_pre.returncode == 0
    assert not (main_pre / "_bmad" / "custom").is_symlink()

    backup_dir = tmp_path / "bak-main"
    main_post = _seed_main_repo(tmp_path / "post", with_bmad_custom=True)
    res_post = subprocess.run(
        ["bash", str(INIT_SCRIPT)],
        cwd=main_post,
        env={**os.environ, "ORCIA_BMAD_BACKUP_DIR": str(backup_dir)},
        capture_output=True,
        text=True,
    )
    assert res_post.returncode == 0, res_post.stderr
    assert (main_post / "_bmad" / "custom").is_symlink()
    assert os.readlink(main_post / "_bmad" / "custom") == "../.agents/bmad-custom"
    assert (main_post / ".agents" / "bmad-custom" / "config.user.toml").is_file()
    assert (backup_dir / "config.toml").is_file()
    assert _git(main_post, "status", "--porcelain") == ""
