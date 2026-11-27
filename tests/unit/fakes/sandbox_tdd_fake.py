"""Test-only child shim for `tier2_runner.py` stubbing only `pytest`/`ruff` `subprocess.run`."""

from __future__ import annotations

import pathlib

TIER2_SHIM_TEMPLATE = """from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import types
from typing import Any

_REPO_ROOT = pathlib.Path(__REPO_ROOT__)
_RUNNER_PATH = _REPO_ROOT / "infra" / "sandbox" / "tier2_runner.py"
_SPEC = importlib.util.spec_from_file_location("_real_tier2_runner", _RUNNER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_REAL_RUNNER = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_REAL_RUNNER)


def _eval_scratch_pytest(scratch_dir: str) -> tuple[int, str]:
    root = pathlib.Path(scratch_dir)
    test_files = sorted(root.glob("test_*.py"))
    if not test_files:
        return 5, "no tests ran"
    injected: dict[str, types.ModuleType | None] = {}
    try:
        for py_file in sorted(root.glob("*.py")):
            if py_file.name.startswith("test_"):
                continue
            mod_name = py_file.stem
            injected.setdefault(mod_name, sys.modules.get(mod_name))
            mod = types.ModuleType(mod_name)
            exec(compile(py_file.read_text(encoding="utf-8"), str(py_file), "exec"), mod.__dict__)
            sys.modules[mod_name] = mod

        for tf in test_files:
            ns: dict[str, Any] = {"__name__": tf.stem}
            exec(compile(tf.read_text(encoding="utf-8"), str(tf), "exec"), ns)
            for fn_name, fn_obj in ns.items():
                if fn_name.startswith("test_") and callable(fn_obj):
                    try:
                        fn_obj()
                    except AssertionError as exc:
                        return 1, f"FAILED {tf.name}::{fn_name}: {exc}"
        return 0, "1 passed"
    finally:
        for mod_name, prev in injected.items():
            if prev is None:
                sys.modules.pop(mod_name, None)
            else:
                sys.modules[mod_name] = prev


def _stub_subprocess_run(
    cmd: list[str], *, cwd: str, **_kwargs: Any
) -> subprocess.CompletedProcess[str]:
    if "pytest" in cmd:
        code, out = _eval_scratch_pytest(cwd)
        return subprocess.CompletedProcess(cmd, code, stdout=out, stderr="")
    return subprocess.CompletedProcess(cmd, 0, stdout="All checks passed!", stderr="")


_REAL_RUNNER.subprocess.run = _stub_subprocess_run

if __name__ == "__main__":
    raise SystemExit(_REAL_RUNNER.main())
"""


def write_tier2_subprocess_shim(tmp_dir: pathlib.Path, repo_root: pathlib.Path) -> pathlib.Path:
    """Write a `tier2_runner.py` wrapper that stubs only `pytest`/`ruff` `subprocess.run`."""
    shim_path = tmp_dir / "tier2_runner_shim.py"
    shim_path.write_text(
        TIER2_SHIM_TEMPLATE.replace("__REPO_ROOT__", repr(str(repo_root))), encoding="utf-8"
    )
    return shim_path
