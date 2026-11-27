"""Raw `--no-cov` suite wall-time budgets and per-unit-test JUnit duration checks."""

from __future__ import annotations

import json
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.output import (
    FailureDigest,
    format_failure_digest,
    format_pass_line,
    write_stage_log,
)
from scripts.agent_check_lib.runner_exec import PYTEST_BASE_FLAGS, run_cmd

DEFAULT_UNIT_BUDGET_S = 120.0
DEFAULT_ESC_BUDGET_S = 45.0
DEFAULT_MAX_UNIT_TEST_S = 1.0


@dataclass(frozen=True, slots=True)
class BudgetConfig:
    """Loaded raw suite wall-time and per-test slowness thresholds."""

    unit_budget_s: float
    esc_budget_s: float
    max_unit_test_s: float
    slow_unit_allowlist: frozenset[str]


def load_budget_config(repo_root: Path) -> BudgetConfig:
    """Load `scripts/test_budgets.json` if present, else return defaults."""
    cfg_path = repo_root / "scripts" / "test_budgets.json"
    if not cfg_path.is_file():
        return BudgetConfig(
            unit_budget_s=DEFAULT_UNIT_BUDGET_S,
            esc_budget_s=DEFAULT_ESC_BUDGET_S,
            max_unit_test_s=DEFAULT_MAX_UNIT_TEST_S,
            slow_unit_allowlist=frozenset(),
        )
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    suites = raw.get("raw_suite_budgets_s", {})
    return BudgetConfig(
        unit_budget_s=float(suites.get("tests/unit", DEFAULT_UNIT_BUDGET_S)),
        esc_budget_s=float(suites.get("evals_security_contract", DEFAULT_ESC_BUDGET_S)),
        max_unit_test_s=float(raw.get("max_unit_test_duration_s", DEFAULT_MAX_UNIT_TEST_S)),
        slow_unit_allowlist=frozenset(str(x) for x in raw.get("slow_unit_test_allowlist", [])),
    )


def parse_slow_unit_tests(
    xml_path: Path,
    *,
    max_duration_s: float = DEFAULT_MAX_UNIT_TEST_S,
    allowlist: frozenset[str] = frozenset(),
) -> list[tuple[str, float]]:
    """Return sorted `(test_id, duration_s)` exceeding `max_duration_s` outside `allowlist`."""
    if not xml_path.is_file():
        return []
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return []

    slow: list[tuple[str, float]] = []
    for testcase in tree.getroot().iter("testcase"):
        classname = testcase.attrib.get("classname", "").strip()
        name = testcase.attrib.get("name", "").strip()
        test_id = f"{classname}::{name}" if classname else name
        base_name = name.split("[", 1)[0]
        base_id = f"{classname}::{base_name}" if classname else base_name
        if test_id in allowlist or base_id in allowlist:
            continue
        try:
            dur = float(testcase.attrib.get("time", "0") or 0.0)
        except ValueError:
            continue
        if dur > max_duration_s:
            slow.append((test_id, dur))
    return sorted(slow, key=lambda item: (-item[1], item[0]))


def find_stale_allowlist_ids(
    xml_path: Path,
    *,
    allowlist: frozenset[str],
) -> list[str]:
    """Return sorted `allowlist` entries absent from JUnit XML `<testcase>` IDs."""
    if not allowlist or not xml_path.is_file():
        return []
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return []

    seen_ids: set[str] = set()
    for testcase in tree.getroot().iter("testcase"):
        classname = testcase.attrib.get("classname", "").strip()
        name = testcase.attrib.get("name", "").strip()
        test_id = f"{classname}::{name}" if classname else name
        base_name = name.split("[", 1)[0]
        base_id = f"{classname}::{base_name}" if classname else base_name
        seen_ids.add(test_id)
        seen_ids.add(base_id)
    return sorted(entry for entry in allowlist if entry not in seen_ids)


def check_raw_suite_budget(
    suite_key: str, elapsed_s: float, *, config: BudgetConfig
) -> tuple[bool, str]:
    """Validate raw `--no-cov` wall-time against configured suite ceiling."""
    limit = config.unit_budget_s if suite_key == "tests/unit" else config.esc_budget_s
    ok = elapsed_s <= limit
    status = "PASS" if ok else "FAIL"
    return ok, f"{status} [budget:{suite_key}]: {elapsed_s:.2f}s <= {limit:.2f}s"


def _run_raw_budget_suite(
    env_info: ToolchainEnv,
    *,
    suite_key: str,
    targets: list[str],
    extra_args: list[str],
    check_slow_tests: bool,
    config: BudgetConfig,
) -> tuple[int, str]:
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
        res = run_cmd(cmd, root, sub_env)
        elapsed = time.monotonic() - t0
        if res.returncode not in (0, 5):
            combined = f"{res.stdout}\n{res.stderr}".strip()
            log_path = write_stage_log(root, f"budget-{suite_key.replace('/', '_')}", combined)
            return 1, format_failure_digest(
                FailureDigest(
                    "budget", f"{suite_key} pytest failed", elapsed, [suite_key], [], log_path
                )
            )
        ok_time, msg_time = check_raw_suite_budget(suite_key, elapsed, config=config)
        slow_hits = (
            parse_slow_unit_tests(
                xml_path,
                max_duration_s=config.max_unit_test_s,
                allowlist=config.slow_unit_allowlist,
            )
            if check_slow_tests
            else []
        )
        stale_ids = (
            find_stale_allowlist_ids(xml_path, allowlist=config.slow_unit_allowlist)
            if check_slow_tests
            else []
        )
        if not ok_time or slow_hits or stale_ids:
            failing_ids = [msg_time] if not ok_time else []
            failing_ids.extend(
                f"SLOW ({dur:.2f}s > {config.max_unit_test_s:.1f}s): {tid}"
                for tid, dur in slow_hits
            )
            failing_ids.extend(f"STALE_ALLOWLIST_ID: {tid}" for tid in stale_ids)
            log_path = write_stage_log(root, "budget", "\n".join(failing_ids))
            return 1, format_failure_digest(
                FailureDigest(
                    "budget", f"{suite_key} budget exceeded", elapsed, failing_ids, [], log_path
                )
            )
        return 0, msg_time
    finally:
        xml_path.unlink(missing_ok=True)


def run_stage_budget(env_info: ToolchainEnv) -> int:
    """Execute raw `--no-cov` wall-time and per-unit-test `<= 1.0 s` budget checks."""
    config = load_budget_config(env_info.repo_root)
    t0 = time.monotonic()
    rc_u, msg_u = _run_raw_budget_suite(
        env_info,
        suite_key="tests/unit",
        targets=["tests/unit"],
        extra_args=["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"],
        check_slow_tests=True,
        config=config,
    )
    print(msg_u)
    if rc_u != 0:
        return rc_u

    rc_e, msg_e = _run_raw_budget_suite(
        env_info,
        suite_key="evals_security_contract",
        targets=["tests/evals", "tests/security", "tests/contract"],
        extra_args=["-n", "4", "--dist", "loadfile", "-m", "not contract_fuzz"],
        check_slow_tests=False,
        config=config,
    )
    print(msg_e)
    if rc_e != 0:
        return rc_e

    print(
        format_pass_line(
            "budget", "raw unit<=120s, esc<=45s, unit_test<=1.0s", time.monotonic() - t0
        )
    )
    return 0
