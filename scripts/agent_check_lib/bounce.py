"""Bounce-rule target resolution and re-execution helpers (`T-D5`)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from scripts.agent_check_lib.coverage_gate import resolve_impacted_pg18_tests
from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.output import format_pass_line, format_skip_line
from scripts.agent_check_lib.receipts import (
    BounceDecision,
    BouncePlan,
    clear_failure_state,
    has_matching_receipt,
    write_receipt,
)
from scripts.agent_check_lib.runner_exec import (
    CommandResult,
    emit_check_failure,
    run_pytest_suite,
    run_vitest_suite,
)
from scripts.agent_check_lib.static_gates import TS_PACKAGE_FILTERS


def resolve_junit_test_file(repo_root: Path, test_id: str) -> str | None:
    """Resolve JUnit `classname::test_name` (including `.TestClass`) to a repo test file."""
    raw_mod = test_id.split("::", 1)[0].strip()
    if not raw_mod:
        return None
    if raw_mod.endswith(".py") and (repo_root / raw_mod).is_file():
        return raw_mod
    parts = [part for part in raw_mod.split(".") if part]
    for end_idx in range(len(parts), 0, -1):
        candidate = "/".join(parts[:end_idx]) + ".py"
        if (repo_root / candidate).is_file():
            return candidate
    return None


def _run_failed_check_target(
    env_info: ToolchainEnv,
    bounce: BouncePlan,
    *,
    maxfail: int | None,
    no_skip: bool,
    touched_files: list[str],
    scoped_files: bool,
    only_failing_files: bool,
    run_static_fn: Callable[..., int],
    run_full_fn: Callable[..., int],
    run_pytest_fn: Callable[..., tuple[int, str]] = run_pytest_suite,
    run_vitest_fn: Callable[..., tuple[int, str | None]] = run_vitest_suite,
) -> int:
    root = env_info.repo_root
    failed_check = bounce.failed_check or ""
    if only_failing_files and failed_check.startswith("pytest:") and bounce.failed_tests:
        resolved = {
            path for tid in bounce.failed_tests if (path := resolve_junit_test_file(root, tid))
        }
        if resolved:
            rc, msg = run_pytest_fn(
                env_info,
                stage="bounce",
                check_key=failed_check,
                targets=sorted(resolved),
                extra_args=["-m", "not contract_fuzz"],
                maxfail=maxfail,
            )
            print(msg)
            if rc == 0:
                clear_failure_state(root)
            return rc

    if failed_check == "pytest:tests/unit":
        rc, msg = run_pytest_fn(
            env_info,
            stage="full-unit",
            check_key=failed_check,
            targets=["tests/unit"],
            extra_args=["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"],
            maxfail=maxfail,
        )
        print(msg)
        if rc == 0:
            clear_failure_state(root)
        return rc

    if failed_check == "pytest:evals-security-contract":
        rc, msg = run_pytest_fn(
            env_info,
            stage="full",
            check_key=failed_check,
            targets=["tests/evals", "tests/security", "tests/contract"],
            extra_args=["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"],
            maxfail=maxfail,
        )
        print(msg)
        if rc == 0:
            clear_failure_state(root)
        return rc

    if failed_check == "pytest:tests/integration":
        impacted_pg18 = resolve_impacted_pg18_tests(root)
        if not impacted_pg18 and bounce.failed_tests:
            impacted_pg18 = sorted(
                {
                    path
                    for tid in bounce.failed_tests
                    if (path := resolve_junit_test_file(root, tid))
                }
            )
        if not impacted_pg18:
            clear_failure_state(root)
            return 0
        extra = (
            ["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"]
            if len(impacted_pg18) > 1
            else ["-m", "not contract_fuzz"]
        )
        rc, msg = run_pytest_fn(
            env_info,
            stage="full-pg18",
            check_key=failed_check,
            targets=impacted_pg18,
            extra_args=extra,
            maxfail=maxfail,
        )
        print(msg)
        if rc == 0:
            clear_failure_state(root)
        return rc

    if failed_check.startswith("vitest:"):
        pkg_rel = failed_check.split(":", 1)[1]
        rc, msg_v = run_vitest_fn(
            env_info, stage="bounce", pkg_rel=pkg_rel, files=None, t0=time.monotonic()
        )
        if msg_v:
            print(msg_v)
        if rc == 0:
            clear_failure_state(root)
        return rc

    if failed_check.startswith("static:"):
        return run_static_fn(
            env_info, touched_files=touched_files, no_skip=no_skip, scoped_files=scoped_files
        )

    return run_full_fn(env_info, no_skip=no_skip)


def execute_bounce_plan(
    env_info: ToolchainEnv,
    bounce: BouncePlan,
    *,
    touched_files: list[str],
    no_skip: bool,
    maxfail: int | None,
    explain: bool,
    scoped_files: bool,
    run_static_fn: Callable[..., int],
    run_impact_fn: Callable[..., int],
    run_full_fn: Callable[..., int],
    run_pytest_fn: Callable[..., tuple[int, str]] = run_pytest_suite,
    run_vitest_fn: Callable[..., tuple[int, str | None]] = run_vitest_suite,
) -> int:
    """Execute `ONLY_FAILED_CHECK` or `STAGE1_STAGE2_AND_FAILED` bounce strategy."""
    root = env_info.repo_root
    if bounce.mode == BounceDecision.ONLY_FAILED_CHECK:
        return _run_failed_check_target(
            env_info,
            bounce,
            maxfail=maxfail,
            no_skip=no_skip,
            touched_files=touched_files,
            scoped_files=scoped_files,
            only_failing_files=True,
            run_static_fn=run_static_fn,
            run_full_fn=run_full_fn,
            run_pytest_fn=run_pytest_fn,
            run_vitest_fn=run_vitest_fn,
        )

    rc1 = run_static_fn(
        env_info, touched_files=touched_files, no_skip=no_skip, scoped_files=scoped_files
    )
    if rc1 != 0:
        return rc1
    rc2 = run_impact_fn(env_info, touched_files=touched_files, maxfail=maxfail, explain=explain)
    if rc2 != 0:
        return rc2

    failed_check = bounce.failed_check or ""
    if failed_check.startswith("static:") or failed_check == "pytest:impact":
        clear_failure_state(root)
        return 0

    return _run_failed_check_target(
        env_info,
        bounce,
        maxfail=maxfail,
        no_skip=no_skip,
        touched_files=touched_files,
        scoped_files=scoped_files,
        only_failing_files=False,
        run_static_fn=run_static_fn,
        run_full_fn=run_full_fn,
        run_pytest_fn=run_pytest_fn,
        run_vitest_fn=run_vitest_fn,
    )


def _has_package_script(repo_root: Path, script_name: str) -> bool:
    pkg_json = repo_root / "package.json"
    if not pkg_json.is_file():
        return False
    try:
        scripts = json.loads(pkg_json.read_text(encoding="utf-8")).get("scripts", {})
    except (OSError, json.JSONDecodeError):
        return False
    return script_name in scripts


def run_full_vitest_and_docs(
    env_info: ToolchainEnv,
    *,
    digest: str,
    no_skip: bool,
    sub_env: dict[str, str],
    run_cmd_fn: Callable[[list[str], Path, dict[str, str]], CommandResult],
    run_vitest_fn: Callable[..., tuple[int, str | None]] = run_vitest_suite,
) -> int:
    """Execute full Vitest packages (`full-vitest`) and docs/site closure checks."""
    root = env_info.repo_root
    ts_pkgs = [p for p, _ in TS_PACKAGE_FILTERS if (root / p / "package.json").is_file()]
    if ts_pkgs:
        if not no_skip and has_matching_receipt(root, "full-vitest", digest):
            print(format_skip_line("full-vitest", digest))
        else:
            t_vitest = time.monotonic()
            for pkg_rel in ts_pkgs:
                rc_v, msg_v = run_vitest_fn(
                    env_info, stage="full-vitest", pkg_rel=pkg_rel, files=None, t0=t_vitest
                )
                if rc_v != 0 and msg_v:
                    print(msg_v)
                    return rc_v
            write_receipt(root, "full-vitest", digest, summary=f"{len(ts_pkgs)} pkg(s)")
            print(
                format_pass_line(
                    "full-vitest", f"{len(ts_pkgs)} pkg(s)", time.monotonic() - t_vitest
                )
            )
    closure_checks: list[tuple[str, list[str]]] = []
    if (root / "scripts" / "check_implementation_docs.py").is_file():
        closure_checks.append(
            ("check-impl-docs", [str(env_info.python_bin), "scripts/check_implementation_docs.py"])
        )
    if _has_package_script(root, "site:check"):
        closure_checks.append(("site-check", [env_info.pnpm_bin, "site:check"]))
    if closure_checks:
        t_close = time.monotonic()
        for gate_name, cmd in closure_checks:
            res = run_cmd_fn(cmd, root, sub_env)
            if res.returncode != 0:
                return emit_check_failure(
                    root,
                    "full",
                    gate_name,
                    res,
                    time.monotonic() - t_close,
                )
        print(
            format_pass_line(
                "full-docs-site", f"{len(closure_checks)} checks", time.monotonic() - t_close
            )
        )
    return 0
