"""Stage 3 combined Unit + PG18 coverage (`coverage combine` + `diff-cover >= 90%`)."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from scripts.agent_check_lib.changes import detect_changed_files
from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.impact import select_impacted_targets
from scripts.agent_check_lib.output import format_pass_line
from scripts.agent_check_lib.runner_exec import CommandResult, emit_check_failure

COV_SOURCE_DIRS: tuple[str, ...] = ("packages", "apps", "scripts")
DIFF_COVER_MIN_PERCENT = 90

SITECUSTOMIZE_HOOK = """\"\"\"Auto-start coverage in xdist worker subprocesses during Stage 3.\"\"\"
import os

if os.environ.get("COVERAGE_PROCESS_START"):
    try:
        import coverage

        coverage.process_startup()
    except Exception:
        pass
"""


def prepare_coverage_env(repo_root: Path, base_env: dict[str, str]) -> dict[str, str]:
    """Create `.agent_check/cov_hook/sitecustomize.py` and return subprocess coverage env."""
    hook_dir = repo_root / ".agent_check" / "cov_hook"
    hook_dir.mkdir(parents=True, exist_ok=True)
    hook_file = hook_dir / "sitecustomize.py"
    if not hook_file.is_file() or hook_file.read_text(encoding="utf-8") != SITECUSTOMIZE_HOOK:
        hook_file.write_text(SITECUSTOMIZE_HOOK, encoding="utf-8")

    env = dict(base_env)
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{hook_dir}{os.pathsep}{existing_pp}" if existing_pp else str(hook_dir)
    env["COVERAGE_PROCESS_START"] = str(repo_root / "pyproject.toml")
    env["COVERAGE_FILE"] = str(repo_root / ".coverage")
    return env


def cleanup_coverage_artifacts(repo_root: Path) -> None:
    """Remove `.coverage` and `.coverage.*` data files from `repo_root`."""
    cov_main = repo_root / ".coverage"
    if cov_main.is_file():
        cov_main.unlink(missing_ok=True)
    for item in repo_root.glob(".coverage.*"):
        if item.is_file():
            item.unlink(missing_ok=True)


def _git_output(repo_root: Path, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout


def _extract_untracked_py_diff(repo_root: Path, rel_path: str) -> str:
    proc = subprocess.run(
        ["git", "diff", "--no-index", "--", "/dev/null", rel_path],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout or ""
    if not out:
        return ""
    return out.replace(f"+++ b/{rel_path}", f"+++ b/{rel_path}").replace(
        f"diff --git a/dev/null b/{rel_path}", f"diff --git a/{rel_path} b/{rel_path}"
    )


def _patch_has_python_changes(patch_text: str) -> bool:
    for line in patch_text.splitlines():
        if line.startswith(("+++ b/", "--- a/")) and line.endswith(".py"):
            return True
    return False


def _committed_branch_diff_range(repo_root: Path) -> str:
    base_ref: str | None = None
    for candidate in ("origin/main", "main"):
        rc_mb, mb_out = _git_output(repo_root, ["merge-base", candidate, "HEAD"])
        if rc_mb == 0 and mb_out.strip():
            base_ref = mb_out.strip()
            break
    return f"{base_ref}..HEAD" if base_ref else "HEAD~1..HEAD"


def build_diff_cover_patch(repo_root: Path, *, out_path: Path) -> bool:
    """Write unified diff for changed `.py` files under `packages/`, `apps/`, `scripts/`."""
    if not (repo_root / ".git").exists():
        return False
    rc_status, status_out = _git_output(
        repo_root, ["status", "--porcelain", "-uall", "--", *COV_SOURCE_DIRS]
    )
    chunks: list[str] = []
    if rc_status == 0 and status_out.strip():
        _rc_diff, diff_out = _git_output(repo_root, ["diff", "HEAD", "--", *COV_SOURCE_DIRS])
        if diff_out:
            chunks.append(diff_out)
        for line in status_out.splitlines():
            if line.startswith("?? "):
                rel = line[3:].strip().strip('"')
                if rel.endswith(".py") and (repo_root / rel).is_file():
                    untracked_diff = _extract_untracked_py_diff(repo_root, rel)
                    if untracked_diff:
                        chunks.append(untracked_diff)
    else:
        diff_range = _committed_branch_diff_range(repo_root)
        rc_cmp, cmp_out = _git_output(repo_root, ["diff", diff_range, "--", *COV_SOURCE_DIRS])
        if rc_cmp == 0 and cmp_out:
            chunks.append(cmp_out)

    combined = "\n".join(c for c in chunks if c.strip())
    if not _patch_has_python_changes(combined):
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(combined + "\n", encoding="utf-8")
    return True


def run_combined_diff_cover(
    env_info: ToolchainEnv,
    *,
    run_cmd_fn: Callable[[list[str], Path, dict[str, str]], CommandResult],
    cov_env: dict[str, str],
) -> tuple[int, str]:
    """Combine parallel `.coverage.*` files, emit XML, and run `diff-cover --fail-under=90`."""
    root = env_info.repo_root
    t0 = time.monotonic()
    patch_path = root / ".agent_check" / "diff_cover.patch"
    if not build_diff_cover_patch(root, out_path=patch_path):
        return 0, format_pass_line("full-diff-cover", "0 Python source lines changed", 0.0)

    combine_res = run_cmd_fn([str(env_info.python_bin), "-m", "coverage", "combine"], root, cov_env)
    if combine_res.returncode != 0:
        rc = emit_check_failure(
            root, "full", "coverage-combine", combine_res, time.monotonic() - t0
        )
        return rc, ""

    xml_path = root / ".agent_check" / "coverage.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_res = run_cmd_fn(
        [str(env_info.python_bin), "-m", "coverage", "xml", "-o", str(xml_path)],
        root,
        cov_env,
    )
    if xml_res.returncode != 0:
        rc = emit_check_failure(root, "full", "coverage-xml", xml_res, time.monotonic() - t0)
        return rc, ""

    dc_res = run_cmd_fn(
        [
            str(env_info.python_bin),
            "-m",
            "diff_cover.diff_cover_tool",
            str(xml_path),
            "--diff-file",
            str(patch_path),
            f"--fail-under={DIFF_COVER_MIN_PERCENT}",
        ],
        root,
        cov_env,
    )
    elapsed = time.monotonic() - t0
    if dc_res.returncode != 0:
        rc = emit_check_failure(root, "full", "diff-cover", dc_res, elapsed)
        return rc, ""

    cov_line = next(
        (ln.strip() for ln in dc_res.stdout.splitlines() if "Coverage:" in ln),
        f">={DIFF_COVER_MIN_PERCENT}%",
    )
    return 0, format_pass_line("full-diff-cover", cov_line, elapsed)


def resolve_impacted_pg18_tests(repo_root: Path) -> list[str]:
    """Return impacted `tests/integration/` files for changed worktree or branch files."""
    if not (repo_root / ".git").exists():
        return []
    touched = detect_changed_files(repo_root)
    if not touched:
        diff_range = _committed_branch_diff_range(repo_root)
        rc_cmp, cmp_out = _git_output(repo_root, ["diff", "--name-only", diff_range])
        if rc_cmp == 0 and cmp_out.strip():
            touched = [ln.strip() for ln in cmp_out.splitlines() if ln.strip()]
    if not touched:
        return []
    return select_impacted_targets(repo_root, touched_files=touched).integration_tests
