"""Subprocess execution and test-suite runner helpers for `agent_check`."""

from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.output import (
    FailureDigest,
    format_failure_digest,
    format_pass_line,
    parse_pytest_junitxml,
    parse_vitest_json,
    write_stage_log,
)
from scripts.agent_check_lib.receipts import record_failure_state

PYTEST_BASE_FLAGS: tuple[str, ...] = (
    "-q",
    "--tb=short",
    "--no-header",
    "-p",
    "no:cacheprovider",
    "--no-cov",
)


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Captured result from executing a subprocess tool."""

    returncode: int
    stdout: str
    stderr: str


def run_cmd(cmd: list[str], cwd: Path, env: dict[str, str]) -> CommandResult:
    """Run a command synchronously and capture stdout/stderr."""
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    return CommandResult(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def run_pytest_suite(
    env_info: ToolchainEnv,
    *,
    stage: str,
    check_key: str,
    targets: list[str],
    extra_args: list[str],
    maxfail: int | None = None,
) -> tuple[int, str]:
    """Execute pytest with JUnit XML parsing and bounded failure digest."""
    root = env_info.repo_root
    sub_env = env_info.subprocess_env()
    t0 = time.monotonic()
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp_xml:
        xml_path = Path(tmp_xml.name)
    try:
        cmd = [
            str(env_info.python_bin),
            "-m",
            "pytest",
            *targets,
            *PYTEST_BASE_FLAGS,
            *extra_args,
            f"--junitxml={xml_path}",
        ]
        if maxfail is not None and maxfail > 0:
            cmd.append(f"--maxfail={maxfail}")
        res = run_cmd(cmd, root, sub_env)
        elapsed = time.monotonic() - t0
        if res.returncode in (0, 5):
            summary = f"{len(targets)} target(s)" if res.returncode == 0 else "0 tests collected"
            return 0, format_pass_line(stage, summary, elapsed)

        failing_ids, tracebacks = parse_pytest_junitxml(xml_path)
        combined = f"{res.stdout}\n{res.stderr}".strip()
        if not failing_ids:
            failing_ids = [check_key]
            tracebacks = [combined[:800]] if combined else []
        log_path = write_stage_log(root, stage, combined)
        record_failure_state(root, stage=stage, failed_check=check_key, failed_tests=failing_ids)
        digest_text = format_failure_digest(
            FailureDigest(
                stage, f"{len(failing_ids)} failed", elapsed, failing_ids, tracebacks, log_path
            )
        )
        return 1, digest_text
    finally:
        xml_path.unlink(missing_ok=True)


def run_vitest_suite(
    env_info: ToolchainEnv,
    *,
    stage: str,
    pkg_rel: str,
    files: list[str] | None,
    t0: float,
) -> tuple[int, str | None]:
    """Execute Vitest (`related` when `files` given, else full `run`) with JSON failure digest."""
    root = env_info.repo_root
    sub_env = env_info.subprocess_env()
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_json:
        json_path = Path(tmp_json.name)
    try:
        sub_cmd = ["related", *files, "--run"] if files else ["run"]
        cmd = [
            env_info.pnpm_bin,
            "--filter",
            f"./{pkg_rel}",
            "exec",
            "vitest",
            *sub_cmd,
            "--reporter=json",
            f"--outputFile={json_path}",
        ]
        res = run_cmd(cmd, root, sub_env)
        if res.returncode == 0:
            return 0, None
        failing_ids, tracebacks = parse_vitest_json(json_path)
        combined = f"{res.stdout}\n{res.stderr}".strip()
        if not failing_ids:
            failing_ids = [f"vitest:{pkg_rel}"]
        log_path = write_stage_log(root, f"{stage}-vitest", combined)
        record_failure_state(
            root, stage=stage, failed_check=f"vitest:{pkg_rel}", failed_tests=failing_ids
        )
        msg = format_failure_digest(
            FailureDigest(
                stage,
                f"{len(failing_ids)} vitest failed",
                time.monotonic() - t0,
                failing_ids,
                tracebacks,
                log_path,
            )
        )
        return 1, msg
    finally:
        json_path.unlink(missing_ok=True)


def emit_check_failure(
    root: Path, stage: str, gate_name: str, res: CommandResult, elapsed_s: float
) -> int:
    """Emit a bounded failure digest and record failure state for a non-pytest gate."""
    combined = f"{res.stdout}\n{res.stderr}".strip()
    lines = [ln.strip() for ln in combined.splitlines() if ln.strip()]
    failing_ids = [f"{gate_name}: {ln}" for ln in lines[:20]] or [gate_name]
    tracebacks = ["\n".join(lines[:12])] if lines else []
    log_path = write_stage_log(root, f"{stage}-{gate_name}", combined)
    record_failure_state(
        root, stage=stage, failed_check=f"{stage}:{gate_name}", failed_tests=failing_ids
    )
    print(
        format_failure_digest(
            FailureDigest(
                stage, f"{gate_name} failed", elapsed_s, failing_ids, tracebacks, log_path
            )
        )
    )
    return 1


def run_vitest_related(
    env_info: ToolchainEnv,
    *,
    pkg_rel: str,
    files: list[str],
    t0: float,
) -> tuple[int, str | None]:
    """Execute `vitest related` for a workspace package with JSON failure parsing."""
    return run_vitest_suite(env_info, stage="impact", pkg_rel=pkg_rel, files=files, t0=t0)
