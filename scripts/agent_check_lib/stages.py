"""Staged execution for `static`, `impact`, `full`, `all`, and `fuzz`."""

from __future__ import annotations

import time

from scripts.agent_check_lib.bounce import (
    _has_package_script as _has_package_script,
)
from scripts.agent_check_lib.bounce import (
    execute_bounce_plan,
    run_full_vitest_and_docs,
)
from scripts.agent_check_lib.coverage_gate import (
    build_diff_cover_patch,
    cleanup_coverage_artifacts,
    prepare_coverage_env,
    resolve_impacted_pg18_tests,
    run_combined_diff_cover,
)
from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.impact import select_impacted_targets
from scripts.agent_check_lib.output import format_pass_line, format_skip_line
from scripts.agent_check_lib.receipts import (
    BounceDecision,
    clear_failure_state,
    clear_failure_state_if_matches,
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
    autofix_touched_python,
    build_static_gates,
    validate_gate_result,
)

_run_cmd = run_cmd


def run_stage_static(
    env_info: ToolchainEnv,
    *,
    touched_files: list[str],
    no_skip: bool,
    scoped_files: bool = False,
) -> int:
    """Run Stage 1 (`static`): autofix touched `.py`, then check-only gates with receipt."""
    root = env_info.repo_root
    if not no_skip and not scoped_files:
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

    post_digest = compute_worktree_digest(root, env_info)
    if not no_skip and not scoped_files and has_matching_receipt(root, "static", post_digest):
        print(format_skip_line("static", post_digest))
        return 0

    gates, warnings = build_static_gates(env_info, touched_files=touched_files, no_skip=no_skip)
    for warn in warnings:
        print(warn)

    for gate_name, cmd in gates:
        res = validate_gate_result(gate_name, _run_cmd(cmd, root, sub_env))
        if res.returncode != 0:
            return emit_check_failure(root, "static", gate_name, res, time.monotonic() - t0)

    elapsed = time.monotonic() - t0
    summary = f"{len(gates)} gates"
    if not scoped_files:
        write_receipt(root, "static", post_digest, summary=summary)
    clear_failure_state_if_matches(root, prefixes=("static:",))
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
        impact_extra = (
            ["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"]
            if len(plan.python_tests) >= 20
            else ["-m", "not contract_fuzz"]
        )
        rc, msg = run_pytest_suite(
            env_info,
            stage="impact",
            check_key="pytest:impact",
            targets=plan.python_tests,
            extra_args=impact_extra,
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

    clear_failure_state_if_matches(root, prefixes=("static:", "impact:", "pytest:impact"))
    summary = f"{len(plan.python_tests)} py + {len(plan.vitest_files_by_pkg)} vitest pkg(s)"
    print(format_pass_line("impact", summary, time.monotonic() - t0))
    return 0


def run_stage_full(env_info: ToolchainEnv, *, no_skip: bool) -> int:
    """Run Stage 3 (`full`): unit(-n 4)+PG18+ESC under coverage, `diff-cover`, Vitest, docs."""
    root = env_info.repo_root
    sub_env = env_info.subprocess_env()
    digest = compute_worktree_digest(root, env_info)
    patch_path = root / ".agent_check" / "diff_cover.patch"
    has_py_changes = build_diff_cover_patch(root, out_path=patch_path)
    can_skip_unit = (
        not no_skip
        and has_matching_receipt(root, "full-unit", digest)
        and (not has_py_changes or has_matching_receipt(root, "full-diff-cover", digest))
    )

    cleanup_coverage_artifacts(root)
    try:
        cov_env = prepare_coverage_env(root, sub_env)
        if can_skip_unit:
            print(format_skip_line("full-unit", digest))
        else:
            rc, msg = run_pytest_suite(
                env_info, stage="full-unit", check_key="pytest:tests/unit",
                targets=["tests/unit"],
                extra_args=["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"],
                coverage_parallel=True, env_override=cov_env,
            )  # fmt: skip
            print(msg)
            if rc != 0:
                return rc

        esc_env = cov_env if not can_skip_unit else None
        rc2, msg2 = run_pytest_suite(
            env_info, stage="full", check_key="pytest:evals-security-contract",
            targets=["tests/evals", "tests/security", "tests/contract"],
            extra_args=["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"],
            coverage_parallel=not can_skip_unit, env_override=esc_env,
        )  # fmt: skip
        print(msg2)
        if rc2 != 0:
            return rc2

        if not can_skip_unit:
            impacted_pg18 = resolve_impacted_pg18_tests(root)
            if impacted_pg18:
                pg18_extra = (
                    ["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"]
                    if len(impacted_pg18) > 1
                    else ["-m", "not contract_fuzz"]
                )
                rc_pg, msg_pg = run_pytest_suite(
                    env_info, stage="full-pg18", check_key="pytest:tests/integration",
                    targets=impacted_pg18, extra_args=pg18_extra,
                    coverage_parallel=True, env_override=cov_env,
                )  # fmt: skip
                print(msg_pg)
                if rc_pg != 0:
                    return rc_pg

            rc_dc, msg_dc = run_combined_diff_cover(env_info, run_cmd_fn=_run_cmd, cov_env=cov_env)
            if msg_dc:
                print(msg_dc)
            if rc_dc != 0:
                return rc_dc
            write_receipt(root, "full-unit", digest, summary="tests/unit")
            if has_py_changes:
                write_receipt(root, "full-diff-cover", digest, summary="diff-cover>=90")
    finally:
        cleanup_coverage_artifacts(root)

    rc_vd = run_full_vitest_and_docs(
        env_info,
        digest=digest,
        no_skip=no_skip,
        sub_env=sub_env,
        run_cmd_fn=_run_cmd,
        run_vitest_fn=run_vitest_suite,
    )
    if rc_vd != 0:
        return rc_vd
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
    scoped_files: bool = False,
) -> int:
    """Apply bounce rule when an active failure exists, else execute requested stage."""
    root = env_info.repo_root
    bounce = evaluate_bounce_rule(root)
    if not no_skip and bounce.mode != BounceDecision.NONE and stage in ("impact", "full", "all"):
        return execute_bounce_plan(
            env_info,
            bounce,
            touched_files=touched_files,
            no_skip=no_skip,
            maxfail=maxfail,
            explain=explain,
            scoped_files=scoped_files,
            run_static_fn=run_stage_static,
            run_impact_fn=run_stage_impact,
            run_full_fn=run_stage_full,
            run_pytest_fn=run_pytest_suite,
            run_vitest_fn=run_vitest_suite,
        )

    if stage == "static":
        return run_stage_static(
            env_info, touched_files=touched_files, no_skip=no_skip, scoped_files=scoped_files
        )
    if stage == "impact":
        return run_stage_impact(
            env_info, touched_files=touched_files, maxfail=maxfail, explain=explain
        )
    if stage == "full":
        return run_stage_full(env_info, no_skip=no_skip)
    if stage == "all":
        rc1 = run_stage_static(
            env_info, touched_files=touched_files, no_skip=no_skip, scoped_files=scoped_files
        )
        if rc1 != 0:
            return rc1
        rc2 = run_stage_impact(
            env_info, touched_files=touched_files, maxfail=maxfail, explain=explain
        )
        if rc2 != 0:
            return rc2
        return run_stage_full(env_info, no_skip=no_skip)
    return run_stage_fuzz(env_info)
