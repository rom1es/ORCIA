"""Unit tests for `scripts/test_redundancy_audit.py` (`T-D11`, Story 32.4)."""

from __future__ import annotations

from pathlib import Path

import pytest
from coverage import CoverageData
from scripts.test_redundancy_audit import main as audit_main
from scripts.test_redundancy_audit_lib.analyzer import (
    analyze_coverage_db,
    compare_baselines,
    load_baseline_snapshot,
    save_baseline_snapshot,
)

pytestmark = pytest.mark.story("32.4")


def _create_arc_db(
    db_path: Path,
    *,
    repo_root: Path,
    entries: list[tuple[str, str, list[tuple[int, int]]]],
) -> None:
    data = CoverageData(basename=str(db_path))
    for rel_file, ctx_name, arcs in entries:
        abs_file = (repo_root / rel_file).as_posix()
        data.set_context(ctx_name)
        data.add_arcs({abs_file: arcs})
    data.write()


def test_redundancy_audit_flags_zero_unique_and_excludes_test_files(tmp_path: Path) -> None:
    """Zero-unique tests are flagged while unique-branch tests and prod prefixes are respected."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    db_path = tmp_path / ".coverage"
    _create_arc_db(
        db_path,
        repo_root=repo_root,
        entries=[
            (
                "packages/orcia-core/src/mod_a.py",
                "tests/unit/test_a.py::test_full|run",
                [(1, 2), (2, 3), (3, 4)],
            ),
            (
                "packages/orcia-core/src/mod_a.py",
                "tests/unit/test_a.py::test_redundant|run",
                [(1, 2), (2, 3)],
            ),
            ("tests/unit/test_a.py", "tests/unit/test_a.py::test_redundant|run", [(10, 11)]),
            ("packages/orcia-core/src/mod_a.py", "", [(1, 2)]),
        ],
    )

    report = analyze_coverage_db(db_path, repo_root=repo_root)
    assert report.has_arcs is True
    assert report.total_tests == 2
    assert report.zero_unique_tests == ("tests/unit/test_a.py::test_redundant",)
    by_ctx = {c.context: c for c in report.contributions}
    assert by_ctx["tests/unit/test_a.py::test_full"].unique_units == 1
    assert by_ctx["tests/unit/test_a.py::test_redundant"].unique_units == 0
    assert list(report.modules.keys()) == ["packages/orcia-core/src/mod_a.py"]


def test_redundancy_audit_safety_gate_detects_branch_regression(tmp_path: Path) -> None:
    """Before/after safety comparison fails when a branch arc is lost and passes when kept."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    before_db = tmp_path / "before.coverage"
    after_ok_db = tmp_path / "after_ok.coverage"
    after_bad_db = tmp_path / "after_bad.coverage"

    _create_arc_db(
        before_db,
        repo_root=repo_root,
        entries=[
            ("apps/api/src/orcia_api/routes.py", "test_1", [(10, 11), (11, 12)]),
            ("apps/api/src/orcia_api/routes.py", "test_2", [(10, 11)]),
        ],
    )
    _create_arc_db(
        after_ok_db,
        repo_root=repo_root,
        entries=[
            ("apps/api/src/orcia_api/routes.py", "test_1", [(10, 11), (11, 12)]),
        ],
    )
    _create_arc_db(
        after_bad_db,
        repo_root=repo_root,
        entries=[
            ("apps/api/src/orcia_api/routes.py", "test_2", [(10, 11)]),
        ],
    )

    baseline_json = tmp_path / "baseline.json"
    rc_save = audit_main(
        [
            "--coverage-db",
            str(before_db),
            "--repo-root",
            str(repo_root),
            "--save-baseline",
            str(baseline_json),
        ]
    )
    assert rc_save == 0
    loaded = load_baseline_snapshot(baseline_json)
    assert "apps/api/src/orcia_api/routes.py" in loaded

    rc_pass = audit_main(
        [
            "--coverage-db",
            str(after_ok_db),
            "--repo-root",
            str(repo_root),
            "--verify-against",
            str(baseline_json),
        ]
    )
    assert rc_pass == 0

    rc_fail = audit_main(
        [
            "--coverage-db",
            str(after_bad_db),
            "--repo-root",
            str(repo_root),
            "--verify-against",
            str(baseline_json),
        ]
    )
    assert rc_fail == 1


def test_redundancy_audit_supports_line_mode_and_ignore_modules(tmp_path: Path) -> None:
    """Line-only `.coverage` DBs and `ignore_modules` filter work deterministically."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    db_path = tmp_path / "lines.coverage"
    data = CoverageData(basename=str(db_path))
    data.set_context("test_line")
    data.add_lines({(repo_root / "packages/orcia-connectors/src/c.py").as_posix(): [5, 6, 7]})
    data.write()

    report = analyze_coverage_db(db_path, repo_root=repo_root)
    assert report.has_arcs is False
    assert report.modules["packages/orcia-connectors/src/c.py"].covered_lines == (5, 6, 7)

    baseline_path = tmp_path / "line_base.json"
    save_baseline_snapshot(report, baseline_path)
    diff = compare_baselines(
        load_baseline_snapshot(baseline_path),
        {},
        ignore_modules={"packages/orcia-connectors/src/c.py"},
    )
    assert diff.passed is True
