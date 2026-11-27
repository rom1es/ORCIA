#!/usr/bin/env python3
"""Per-test coverage dynamic-context redundancy audit & safety gate (`T-D11`, Story 32.4).

Usage:
    .venv/bin/python scripts/test_redundancy_audit.py --coverage-db .coverage
    .venv/bin/python scripts/test_redundancy_audit.py --save-baseline base.json
    .venv/bin/python scripts/test_redundancy_audit.py --verify-against base.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.test_redundancy_audit_lib.analyzer import (  # noqa: E402
    DEFAULT_PROD_PREFIXES,
    analyze_coverage_db,
    compare_baselines,
    format_audit_summary,
    load_baseline_snapshot,
    save_baseline_snapshot,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test_redundancy_audit.py",
        description="Inspect `.coverage` dynamic contexts and verify zero branch regression.",
    )
    parser.add_argument(
        "--coverage-db",
        type=Path,
        default=Path(".coverage"),
        help="Path to combined SQLite `.coverage` database.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Repository root path for normalizing module paths.",
    )
    parser.add_argument(
        "--save-baseline",
        type=Path,
        default=None,
        help="Write module branch/line snapshot + zero-unique test list to JSON.",
    )
    parser.add_argument(
        "--verify-against",
        type=Path,
        default=None,
        help="Compare `--coverage-db` against a saved baseline JSON and fail on branch loss.",
    )
    parser.add_argument(
        "--scope-prefix",
        action="append",
        default=[],
        help="Optional module prefix filter when verifying safety (repeatable).",
    )
    parser.add_argument(
        "--ignore-module",
        action="append",
        default=[],
        help="Optional relative module path to exclude from safety diff (repeatable).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Max zero-unique test contexts to print in summary.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for redundancy audit & before/after coverage safety gate."""
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    report = analyze_coverage_db(
        args.coverage_db,
        repo_root=repo_root,
        include_prefixes=DEFAULT_PROD_PREFIXES,
    )
    print(format_audit_summary(report, top_n=max(1, int(args.top))))

    if args.save_baseline is not None:
        save_baseline_snapshot(report, args.save_baseline)
        print(f"Saved coverage safety baseline to {args.save_baseline}")

    if args.verify_against is not None:
        before = load_baseline_snapshot(args.verify_against)
        diff = compare_baselines(
            before,
            report.modules,
            scope_prefixes=tuple(args.scope_prefix),
            ignore_modules=set(args.ignore_module),
        )
        print(
            f"Safety gate: before_arcs={diff.before_total_arcs} "
            f"after_arcs={diff.after_total_arcs} "
            f"before_lines={diff.before_total_lines} "
            f"after_lines={diff.after_total_lines} "
            f"regressions={len(diff.regressions)}"
        )
        if not diff.passed:
            for reg in diff.regressions:
                print(
                    f"FAIL [safety-gate] {reg.rel_path}: "
                    f"lost_arcs={reg.lost_arcs_count} lost_lines={reg.lost_lines_count} "
                    f"sample={list(reg.sample_lost_arcs)}"
                )
            return 1
        print("PASS [safety-gate]: zero branch/line regression on production modules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
