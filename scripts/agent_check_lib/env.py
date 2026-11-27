"""Toolchain and PYTHONPATH resolution for ORCIA worktrees."""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ToolchainEnv:
    """Resolved virtual environment, binaries, and PYTHONPATH for a repository root."""

    repo_root: Path
    venv_dir: Path
    python_bin: Path
    ruff_bin: Path
    mypy_bin: Path
    lint_imports_bin: Path
    pnpm_bin: str
    node_bin: str
    pythonpath: str

    def subprocess_env(self) -> dict[str, str]:
        """Return an environment mapping with resolved PYTHONPATH and venv PATH."""
        env = dict(os.environ)
        env["PYTHONPATH"] = self.pythonpath
        venv_bin = str(self.venv_dir / "bin")
        current_path = env.get("PATH", "")
        env["PATH"] = f"{venv_bin}{os.pathsep}{current_path}" if current_path else venv_bin
        env.setdefault("ORCIA_ENV", "test")
        return env


def resolve_repo_root(start: Path | None = None) -> Path:
    """Resolve git top-level root from `start` (or current working directory)."""
    anchor = (start or Path.cwd()).resolve()
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=anchor,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    for candidate in (anchor, *anchor.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return anchor


def load_pyproject_pythonpath(repo_root: Path) -> list[Path]:
    """Read `[tool.pytest.ini_options].pythonpath` from `pyproject.toml`."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.is_file():
        return [repo_root]
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    raw_paths = (
        data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("pythonpath", ["."])
    )
    resolved: list[Path] = []
    for entry in raw_paths:
        target = (repo_root / str(entry)).resolve()
        if target not in resolved:
            resolved.append(target)
    if repo_root.resolve() not in resolved:
        resolved.append(repo_root.resolve())
    return resolved


def resolve_venv_dir(repo_root: Path) -> Path:
    """Resolve `.venv` inside `repo_root` or via `ORCIA_VENV` fallback."""
    local_venv = repo_root / ".venv"
    if (local_venv / "bin" / "python").exists():
        return local_venv
    env_override = os.environ.get("ORCIA_VENV", "").strip()
    if env_override:
        override_path = Path(env_override).expanduser()
        if (override_path / "bin" / "python").exists():
            return override_path
    raise RuntimeError(
        "Unable to locate project virtualenv (expected `<repo>/.venv` or `ORCIA_VENV`)."
    )


def resolve_toolchain_env(repo_root: Path | None = None) -> ToolchainEnv:
    """Build a complete `ToolchainEnv` from repository configuration."""
    root = resolve_repo_root(repo_root)
    venv_dir = resolve_venv_dir(root)
    bin_dir = venv_dir / "bin"
    python_paths = load_pyproject_pythonpath(root)
    pythonpath = os.pathsep.join(str(p) for p in python_paths)

    pnpm_bin = shutil.which("pnpm") or "pnpm"
    node_bin = shutil.which("node") or "node"

    return ToolchainEnv(
        repo_root=root,
        venv_dir=venv_dir,
        python_bin=bin_dir / "python",
        ruff_bin=bin_dir / "ruff",
        mypy_bin=bin_dir / "mypy",
        lint_imports_bin=bin_dir / "lint-imports",
        pnpm_bin=pnpm_bin,
        node_bin=node_bin,
        pythonpath=pythonpath,
    )
