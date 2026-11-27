#!/usr/bin/env python3
"""Anti-bloat & security ratchet test linter (`T-D10`, Story 32.3).

Usage:
    .venv/bin/python scripts/lint_tests.py --ratchet
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.lint_tests_lib.checks import (  # noqa: E402
    check_fake_sql_engines,
    check_legacy_story_test_files,
    compute_proportionality_report,
    find_fake_sql_engine_files,
    find_story_test_files,
)
from scripts.lint_tests_lib.diff_and_routes import (  # noqa: E402
    check_removed_assertions,
    check_unguarded_routes,
    collect_git_test_diff,
    find_unguarded_workspace_or_run_routes,
)

DEFAULT_RATCHET_PATH = Path("scripts/lint_tests_ratchet.json")


def load_ratchet_config(ratchet_path: Path) -> dict[str, list[str]]:
    """Load ratchet allow-lists from JSON config."""
    if not ratchet_path.is_file():
        return {
            "fake_sql_engine_files": [],
            "legacy_story_test_files": [],
            "redundancy_audit_exempt_files": [],
            "unguarded_routes_allowlist": [],
        }
    raw = json.loads(ratchet_path.read_text(encoding="utf-8"))
    return {
        "fake_sql_engine_files": list(raw.get("fake_sql_engine_files", [])),
        "legacy_story_test_files": list(raw.get("legacy_story_test_files", [])),
        "redundancy_audit_exempt_files": list(raw.get("redundancy_audit_exempt_files", [])),
        "unguarded_routes_allowlist": list(raw.get("unguarded_routes_allowlist", [])),
    }


def generate_baseline(repo_root: Path, ratchet_path: Path) -> dict[str, list[str]]:
    """Scan current repo state and write initial ratchet allow-lists."""
    existing = load_ratchet_config(ratchet_path)
    payload = {
        "fake_sql_engine_files": find_fake_sql_engine_files(repo_root),
        "legacy_story_test_files": find_story_test_files(repo_root),
        "redundancy_audit_exempt_files": sorted(set(existing["redundancy_audit_exempt_files"])),
        "unguarded_routes_allowlist": find_unguarded_workspace_or_run_routes(repo_root),
    }
    ratchet_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def run_ratchet(
    repo_root: Path,
    ratchet_path: Path,
    *,
    diff_text: str | None = None,
) -> tuple[int, list[str]]:
    """Execute all 5 ratchet checks; return `(exit_code, output_lines)`."""
    cfg = load_ratchet_config(ratchet_path)
    failures: list[str] = []

    for rel in check_fake_sql_engines(repo_root, set(cfg["fake_sql_engine_files"])):
        failures.append(f"[fake-sql] New fake SQL engine in tests/unit: {rel}")

    for rel in check_legacy_story_test_files(repo_root, set(cfg["legacy_story_test_files"])):
        failures.append(
            f"[story-filename] New test_story_* file forbidden (use @pytest.mark.story): {rel}"
        )

    effective_diff = collect_git_test_diff(repo_root) if diff_text is None else diff_text
    for msg in check_removed_assertions(
        effective_diff,
        redundancy_audit_allowlist=set(cfg["redundancy_audit_exempt_files"]),
    ):
        failures.append(f"[removed-assert] {msg}")

    for entry in check_unguarded_routes(repo_root, set(cfg["unguarded_routes_allowlist"])):
        failures.append(f"[unguarded-route] Missing workspace/run access guard: {entry}")

    test_loc, prod_loc, ratio = compute_proportionality_report(repo_root)
    lines = [
        f"INFO [lint-tests] proportionality: test_loc={test_loc} "
        f"prod_loc={prod_loc} ratio={ratio:.2f}"
    ]
    if failures:
        lines.extend(f"FAIL [lint-tests] {f}" for f in failures)
        return 1, lines

    lines.append(
        "PASS [lint-tests]: 0 ratchet violations "
        f"(allowlists: fake_sql={len(cfg['fake_sql_engine_files'])}, "
        f"story_files={len(cfg['legacy_story_test_files'])}, "
        f"unguarded_routes={len(cfg['unguarded_routes_allowlist'])})"
    )
    return 0, lines


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for `scripts/lint_tests.py`."""
    parser = argparse.ArgumentParser(description="ORCIA anti-bloat & security test linter.")
    parser.add_argument(
        "--ratchet", action="store_true", help="Run ratchet checks against allowlist"
    )
    parser.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Generate/refresh scripts/lint_tests_ratchet.json from current repo state",
    )
    parser.add_argument(
        "--ratchet-file",
        type=Path,
        default=DEFAULT_RATCHET_PATH,
        help="Path to ratchet JSON allowlist",
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    ratchet_path = (
        args.ratchet_file if args.ratchet_file.is_absolute() else repo_root / args.ratchet_file
    )

    if args.generate_baseline:
        payload = generate_baseline(repo_root, ratchet_path)
        print(
            "GENERATED "
            f"fake_sql={len(payload['fake_sql_engine_files'])} "
            f"story_files={len(payload['legacy_story_test_files'])} "
            f"unguarded_routes={len(payload['unguarded_routes_allowlist'])}"
        )
        return 0

    if not args.ratchet:
        parser.error("Specify --ratchet or --generate-baseline")

    rc, lines = run_ratchet(repo_root, ratchet_path)
    for ln in lines:
        print(ln)
    return rc


if __name__ == "__main__":
    sys.exit(main())
