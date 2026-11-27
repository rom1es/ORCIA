"""Modular checks for `scripts/lint_tests.py` (`T-D10` ratchet anti-bloat & security linter)."""

from __future__ import annotations

__all__ = [
    "check_fake_sql_engines",
    "check_legacy_story_test_files",
    "check_removed_assertions",
    "check_unguarded_routes",
    "compute_proportionality_report",
]

from scripts.lint_tests_lib.checks import (
    check_fake_sql_engines,
    check_legacy_story_test_files,
    compute_proportionality_report,
)
from scripts.lint_tests_lib.diff_and_routes import (
    check_removed_assertions,
    check_unguarded_routes,
)
