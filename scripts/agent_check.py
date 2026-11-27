#!/usr/bin/env python3
"""Token-first staged check runner for ORCIA (`T-D4`, `T-D5`, `T-D6`)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.agent_check_lib.budgets import run_stage_budget  # noqa: E402
from scripts.agent_check_lib.changes import normalize_file_args  # noqa: E402
from scripts.agent_check_lib.env import resolve_toolchain_env  # noqa: E402
from scripts.agent_check_lib.stages import run_with_bounce  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent_check.py",
        description=(
            "ORCIA token-first staged check runner (static | impact | full | all | fuzz | budget)."
        ),
    )
    parser.add_argument(
        "stage",
        choices=("static", "impact", "full", "all", "fuzz", "budget"),
        help="Execution stage to run.",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="Explicit touched file paths (defaults to git diff vs HEAD + untracked).",
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Ignore deterministic receipts and force execution.",
    )
    parser.add_argument(
        "--maxfail",
        type=int,
        default=None,
        help="Abort Stage 2 (impact) after N failures (rejected for `full`).",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Print why each test was selected in Stage 2 (impact).",
    )
    parser.add_argument(
        "--budget",
        action="store_true",
        help="Also verify raw `--no-cov` wall-time and per-unit-test `<= 1.0 s` budgets.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.maxfail is not None and args.stage == "full":
        parser.error("--maxfail is only supported on Stage 2 (`impact`), never `full`.")

    env_info = resolve_toolchain_env(_REPO_ROOT)
    if args.stage == "budget":
        return run_stage_budget(env_info)
    touched = normalize_file_args(env_info.repo_root, args.files)
    rc = run_with_bounce(
        env_info,
        stage=args.stage,
        touched_files=touched,
        no_skip=bool(args.no_skip),
        maxfail=args.maxfail,
        explain=bool(args.explain),
        scoped_files=bool(args.files),
    )
    if rc == 0 and args.budget:
        return run_stage_budget(env_info)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
