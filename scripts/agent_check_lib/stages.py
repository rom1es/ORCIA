"""Staged execution for `static`, `impact`, `full`, `all`, and `fuzz`."""

from __future__ import annotations

import json
import time
from pathlib import Path

from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.impact import select_impacted_targets
from scripts.agent_check_lib.output import format_pass_line, format_skip_line
from scripts.agent_check_lib.receipts import (
    BounceDecision,
    clear_failure_state,
    compute_worktree_digest,
    evaluate_bounce_rule,
    has_matching_receipt,
    write_receipt,
)
from scripts.agent_check_lib.runner_exec import (
    emit_check_failure,
    run_cmd,
    run_pytest_suite,
    run_vitest_related,
    run_vitest_suite,
)
from scripts.agent_check_lib.static_gates import (
    TS_PACKAGE_FILTERS,
    autofix_touched_python,
    build_static_gates,
)

_run_cmd = run_cmd


def run_stage_static(env_info: ToolchainEnv, *, touched_files: list[str], no_skip: bool) -> int:
    """Run Stage 1 (`static`): autofix touched `.py`, then check-only gates with receipt."""
    root = env_info.repo_root
    if not no_skip:
        pre_digest = compute_worktree_digest(root, env_info)
        if has_matching_receipt(root, "static", pre_digest):
            print(format_skip_line("static", pre_digest))
            return 0

    t0 = time.monotonic()
    sub_env = env_info.subprocess_env()
    touched_py = [f for f in touched_files if f.endswith(".py") and (root / f).is_file()]
    autofixed = autofix_touched_python(env_info, touched_py, sub_env)
    if autofixed:
        print(f"AUTOFIXED: {', '.join(autofixed)}")

    # Compute digest AFTER auto-fix and BEFORE check-only gates so receipts never self-invalidate
    post_digest = compute_worktree_digest(root, env_info)
    if not no_skip and has_matching_receipt(root, "static", post_digest):
        print(format_skip_line("static", post_digest))
        return 0

    gates, warnings = build_static_gates(env_info, touched_files=touched_files, no_skip=no_skip)
    for warn in warnings:
        print(warn)

    for gate_name, cmd in gates:
        res = _run_cmd(cmd, root, sub_env)
        if res.returncode != 0:
            return emit_check_failure(root, "static", gate_name, res, time.monotonic() - t0)

    elapsed = time.monotonic() - t0
    summary = f"{len(gates)} gates"
    write_receipt(root, "static", post_digest, summary=summary)
    clear_failure_state(root)
    print(format_pass_line("static", summary, elapsed))
    return 0


def run_stage_impact(
    env_info: ToolchainEnv,
    *,
    touched_files: list[str],
    maxfail: int | None,
    explain: bool,
) -> int:
    """Run Stage 2 (`impact`): selected Python tests + `vitest related`."""
    root = env_info.repo_root
    plan = select_impacted_targets(root, touched_files=touched_files)
    if explain:
        for target, target_reasons in plan.reasons.items():
            print(f"EXPLAIN {target}: {', '.join(target_reasons)}")

    t0 = time.monotonic()
    if plan.python_tests:
        rc, msg = run_pytest_suite(
            env_info,
            stage="impact",
            check_key="pytest:impact",
            targets=plan.python_tests,
            extra_args=["-m", "not contract_fuzz"],
            maxfail=maxfail,
        )
        if rc != 0:
            print(msg)
            return rc

    for pkg_rel, files in plan.vitest_files_by_pkg.items():
        rc, vitest_err = run_vitest_related(env_info, pkg_rel=pkg_rel, files=files, t0=t0)
        if rc != 0 and vitest_err:
            print(vitest_err)
            return rc

    clear_failure_state(root)
    summary = f"{len(plan.python_tests)} py + {len(plan.vitest_files_by_pkg)} vitest pkg(s)"
    print(format_pass_line("impact", summary, time.monotonic() - t0))
    return 0


def _has_package_script(repo_root: Path, script_name: str) -> bool:
    pkg_json = repo_root / "package.json"
    if not pkg_json.is_file():
        return False
    try:
        scripts = json.loads(pkg_json.read_text(encoding="utf-8")).get("scripts", {})
    except (OSError, json.JSONDecodeError):
        return False
    return script_name in scripts


def run_stage_full(env_info: ToolchainEnv, *, no_skip: bool) -> int:
    """Run Stage 3 (`full`): unit, evals+security+contract, Vitest, docs, `site:check`."""
    root = env_info.repo_root
    sub_env = env_info.subprocess_env()
    # Extension point for Story 32-3-combined-coverage-diff-cover-shared-pg18-infra-and-ratchet-lint
    digest = compute_worktree_digest(root, env_info)

    if not no_skip and has_matching_receipt(root, "full-unit", digest):
        print(format_skip_line("full-unit", digest))
    else:
        rc, msg = run_pytest_suite(
            env_info,
            stage="full-unit",
            check_key="pytest:tests/unit",
            targets=["tests/unit"],
            extra_args=["-m", "not contract_fuzz"],
            maxfail=None,
        )
        print(msg)
        if rc != 0:
            return rc
        write_receipt(root, "full-unit", digest, summary="tests/unit")

    rc2, msg2 = run_pytest_suite(
        env_info,
        stage="full",
        check_key="pytest:evals-security-contract",
        targets=["tests/evals", "tests/security", "tests/contract"],
        extra_args=["-m", "not contract_fuzz"],
        maxfail=None,
    )
    print(msg2)
    if rc2 != 0:
        return rc2

    ts_pkgs = [p for p, _ in TS_PACKAGE_FILTERS if (root / p / "package.json").is_file()]
    if ts_pkgs:
        if not no_skip and has_matching_receipt(root, "full-vitest", digest):
            print(format_skip_line("full-vitest", digest))
        else:
            t_vitest = time.monotonic()
            for pkg_rel in ts_pkgs:
                rc_v, msg_v = run_vitest_suite(
                    env_info, stage="full-vitest", pkg_rel=pkg_rel, files=None, t0=t_vitest
                )
                if rc_v != 0 and msg_v:
                    print(msg_v)
                    return rc_v
            elapsed_v = time.monotonic() - t_vitest
            write_receipt(root, "full-vitest", digest, summary=f"{len(ts_pkgs)} pkg(s)")
            print(format_pass_line("full-vitest", f"{len(ts_pkgs)} pkg(s)", elapsed_v))

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
            res = _run_cmd(cmd, root, sub_env)
            if res.returncode != 0:
                return emit_check_failure(root, "full", gate_name, res, time.monotonic() - t_close)
        print(
            format_pass_line(
                "full-docs-site", f"{len(closure_checks)} checks", time.monotonic() - t_close
            )
        )

    clear_failure_state(root)
    return 0


def run_stage_fuzz(env_info: ToolchainEnv) -> int:
    """Run slow Schemathesis contract fuzzing (`-m contract_fuzz`)."""
    rc, msg = run_pytest_suite(
        env_info,
        stage="fuzz",
        check_key="pytest:contract_fuzz",
        targets=["tests/contract"],
        extra_args=["-m", "contract_fuzz"],
        maxfail=None,
    )
    print(msg)
    return rc


def run_with_bounce(
    env_info: ToolchainEnv,
    *,
    stage: str,
    touched_files: list[str],
    no_skip: bool,
    maxfail: int | None,
    explain: bool,
) -> int:
    """Apply bounce rule when an active failure exists, else execute requested stage."""
    root = env_info.repo_root
    bounce = evaluate_bounce_rule(root)
    if not no_skip and bounce.mode == BounceDecision.ONLY_FAILED_CHECK and bounce.failed_check:
        if bounce.failed_check.startswith("pytest:") and bounce.failed_tests:
            node_targets = sorted(
                {t.split("::", 1)[0].replace(".", "/") + ".py" for t in bounce.failed_tests}
            )
            existing = [t for t in node_targets if (root / t).is_file()]
            if existing:
                rc, msg = run_pytest_suite(
                    env_info,
                    stage="bounce",
                    check_key=bounce.failed_check,
                    targets=existing,
                    extra_args=["-m", "not contract_fuzz"],
                    maxfail=maxfail,
                )
                print(msg)
                if rc == 0:
                    clear_failure_state(root)
                return rc
    elif (
        not no_skip and bounce.mode == BounceDecision.STAGE1_STAGE2_AND_FAILED and stage == "impact"
    ):
        rc1 = run_stage_static(env_info, touched_files=touched_files, no_skip=no_skip)
        if rc1 != 0:
            return rc1
        return run_stage_impact(
            env_info, touched_files=touched_files, maxfail=maxfail, explain=explain
        )

    if stage == "static":
        return run_stage_static(env_info, touched_files=touched_files, no_skip=no_skip)
    if stage == "impact":
        return run_stage_impact(
            env_info, touched_files=touched_files, maxfail=maxfail, explain=explain
        )
    if stage == "full":
        return run_stage_full(env_info, no_skip=no_skip)
    if stage == "all":
        rc1 = run_stage_static(env_info, touched_files=touched_files, no_skip=no_skip)
        if rc1 != 0:
            return rc1
        rc2 = run_stage_impact(
            env_info, touched_files=touched_files, maxfail=maxfail, explain=explain
        )
        if rc2 != 0:
            return rc2
        return run_stage_full(env_info, no_skip=no_skip)
    return run_stage_fuzz(env_info)
