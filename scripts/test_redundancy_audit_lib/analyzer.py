"""SQLite `.coverage` dynamic-context analyzer and before/after safety gate (`T-D11`)."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from coverage import CoverageData

DEFAULT_PROD_PREFIXES: tuple[str, ...] = (
    "packages/orcia-core/src/",
    "packages/orcia-connectors/src/",
    "apps/api/src/",
    "apps/worker/src/",
)


@dataclass(frozen=True, slots=True)
class TestContribution:
    """Unique and total coverage units contributed by one test context."""

    context: str
    total_units: int
    unique_units: int


@dataclass(frozen=True, slots=True)
class ModuleCoverageSummary:
    """Covered arcs/lines snapshot for a single production module."""

    rel_path: str
    covered_arcs: tuple[tuple[int, int], ...]
    covered_lines: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class RedundancyAuditReport:
    """Full per-test contribution and per-module coverage snapshot."""

    has_arcs: bool
    total_tests: int
    zero_unique_tests: tuple[str, ...]
    contributions: tuple[TestContribution, ...]
    modules: dict[str, ModuleCoverageSummary]


@dataclass(frozen=True, slots=True)
class SafetyRegression:
    """Single module branch/line loss detected between before and after snapshots."""

    rel_path: str
    lost_arcs_count: int
    lost_lines_count: int
    sample_lost_arcs: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class SafetyDiffReport:
    """Comparison result between pre-prune and post-prune coverage snapshots."""

    passed: bool
    before_total_arcs: int
    after_total_arcs: int
    before_total_lines: int
    after_total_lines: int
    regressions: tuple[SafetyRegression, ...]


def _normalize_rel_path(raw_path: str, repo_root: Path) -> str:
    norm = raw_path.replace("\\", "/")
    root_str = repo_root.resolve().as_posix().rstrip("/") + "/"
    if norm.startswith(root_str):
        return norm[len(root_str) :]
    for prefix in DEFAULT_PROD_PREFIXES:
        idx = norm.find(prefix)
        if idx >= 0:
            return norm[idx:]
    return norm


def _is_target_prod_file(rel_path: str, include_prefixes: tuple[str, ...]) -> bool:
    if "/tests/" in f"/{rel_path}" or rel_path.startswith("tests/"):
        return False
    return any(rel_path.startswith(prefix) for prefix in include_prefixes)


def _normalize_test_context(raw_ctx: str) -> str:
    ctx = raw_ctx.strip()
    if "|" in ctx:
        return ctx.split("|", 1)[0]
    return ctx


def analyze_coverage_db(
    db_path: Path,
    *,
    repo_root: Path,
    include_prefixes: tuple[str, ...] = DEFAULT_PROD_PREFIXES,
) -> RedundancyAuditReport:
    """Inspect a `.coverage` DB with `dynamic_context = test_function` via `CoverageData`."""
    if not db_path.is_file():
        raise FileNotFoundError(f"Coverage database not found: {db_path}")

    cov_data = CoverageData(basename=str(db_path.resolve()))
    cov_data.read()
    has_arcs = bool(cov_data.has_arcs())

    target_files: dict[str, str] = {}
    for raw_file in cov_data.measured_files():
        rel = _normalize_rel_path(str(raw_file), repo_root)
        if _is_target_prod_file(rel, include_prefixes):
            target_files[str(raw_file)] = rel

    unit_to_tests: dict[tuple[str, int, int], set[str]] = defaultdict(set)
    test_to_units: dict[str, set[tuple[str, int, int]]] = defaultdict(set)
    module_arcs: dict[str, set[tuple[int, int]]] = defaultdict(set)
    module_lines: dict[str, set[int]] = defaultdict(set)

    # First capture all arcs/lines across all contexts (including import-time `""` context).
    cov_data.set_query_contexts(None)
    for raw_file, rel in target_files.items():
        if has_arcs:
            for fromno, tono in cov_data.arcs(raw_file) or ():
                arc = (int(fromno), int(tono))
                module_arcs[rel].add(arc)
                if int(fromno) > 0:
                    module_lines[rel].add(int(fromno))
                if int(tono) > 0:
                    module_lines[rel].add(int(tono))
        else:
            for lineno in cov_data.lines(raw_file) or ():
                module_lines[rel].add(int(lineno))

    all_tests_set: set[str] = {
        _normalize_test_context(str(c or ""))
        for c in cov_data.measured_contexts()
        if _normalize_test_context(str(c or ""))
    }
    for raw_file, rel in target_files.items():
        cov_data.set_query_contexts(None)
        ctx_by_line = cov_data.contexts_by_lineno(raw_file)
        file_contexts = {
            str(c) for ctxs in ctx_by_line.values() for c in ctxs if str(c or "").strip()
        }
        for raw_ctx in file_contexts:
            norm_ctx = _normalize_test_context(raw_ctx)
            if not norm_ctx:
                continue
            all_tests_set.add(norm_ctx)
            cov_data.set_query_context(raw_ctx)
            if has_arcs:
                for fromno, tono in cov_data.arcs(raw_file) or ():
                    unit = (rel, int(fromno), int(tono))
                    unit_to_tests[unit].add(norm_ctx)
                    test_to_units[norm_ctx].add(unit)
            else:
                for lineno in cov_data.lines(raw_file) or ():
                    unit = (rel, int(lineno), 0)
                    unit_to_tests[unit].add(norm_ctx)
                    test_to_units[norm_ctx].add(unit)

    all_tests = sorted(all_tests_set)
    contributions: list[TestContribution] = []
    zero_unique: list[str] = []
    for test_name in all_tests:
        units = test_to_units.get(test_name, set())
        unique_cnt = sum(1 for u in units if len(unit_to_tests[u]) == 1)
        contributions.append(
            TestContribution(
                context=test_name,
                total_units=len(units),
                unique_units=unique_cnt,
            )
        )
        if unique_cnt == 0:
            zero_unique.append(test_name)

    modules: dict[str, ModuleCoverageSummary] = {}
    for rel in sorted(set(module_arcs.keys()) | set(module_lines.keys())):
        modules[rel] = ModuleCoverageSummary(
            rel_path=rel,
            covered_arcs=tuple(sorted(module_arcs.get(rel, set()))),
            covered_lines=tuple(sorted(module_lines.get(rel, set()))),
        )

    contributions.sort(key=lambda c: (c.unique_units, c.total_units, c.context))
    return RedundancyAuditReport(
        has_arcs=has_arcs,
        total_tests=len(all_tests),
        zero_unique_tests=tuple(sorted(zero_unique)),
        contributions=tuple(contributions),
        modules=modules,
    )


def save_baseline_snapshot(report: RedundancyAuditReport, out_path: Path) -> None:
    """Serialize module coverage snapshot to JSON for before/after safety verification."""
    payload = {
        "has_arcs": report.has_arcs,
        "total_tests": report.total_tests,
        "zero_unique_count": len(report.zero_unique_tests),
        "zero_unique_tests": list(report.zero_unique_tests),
        "modules": {
            rel: {
                "covered_arcs": [list(a) for a in mod.covered_arcs],
                "covered_lines": list(mod.covered_lines),
            }
            for rel, mod in sorted(report.modules.items())
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_baseline_snapshot(path: Path) -> dict[str, ModuleCoverageSummary]:
    """Load module coverage snapshot from JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    modules_raw = raw.get("modules", {})
    result: dict[str, ModuleCoverageSummary] = {}
    for rel, entry in modules_raw.items():
        arcs = tuple((int(a[0]), int(a[1])) for a in entry.get("covered_arcs", []))
        lines = tuple(int(x) for x in entry.get("covered_lines", []))
        result[str(rel)] = ModuleCoverageSummary(
            rel_path=str(rel),
            covered_arcs=arcs,
            covered_lines=lines,
        )
    return result


def compare_baselines(
    before_modules: dict[str, ModuleCoverageSummary],
    after_modules: dict[str, ModuleCoverageSummary],
    *,
    scope_prefixes: tuple[str, ...] = (),
    ignore_modules: set[str] | None = None,
) -> SafetyDiffReport:
    """Verify zero production branch/line loss between before and after snapshots."""
    ignored = ignore_modules or set()
    regressions: list[SafetyRegression] = []
    before_arcs_total = 0
    after_arcs_total = 0
    before_lines_total = 0
    after_lines_total = 0

    all_rels = sorted(set(before_modules.keys()) | set(after_modules.keys()))
    for rel in all_rels:
        if rel in ignored:
            continue
        if scope_prefixes and not any(rel.startswith(p) for p in scope_prefixes):
            continue
        b_mod, a_mod = before_modules.get(rel), after_modules.get(rel)
        b_arcs = set(b_mod.covered_arcs) if b_mod else set()
        a_arcs = set(a_mod.covered_arcs) if a_mod else set()
        b_lines = set(b_mod.covered_lines) if b_mod else set()
        a_lines = set(a_mod.covered_lines) if a_mod else set()

        before_arcs_total += len(b_arcs)
        after_arcs_total += len(a_arcs)
        before_lines_total += len(b_lines)
        after_lines_total += len(a_lines)

        lost_arcs, lost_lines = sorted(b_arcs - a_arcs), sorted(b_lines - a_lines)
        if lost_arcs or lost_lines:
            regressions.append(
                SafetyRegression(rel, len(lost_arcs), len(lost_lines), tuple(lost_arcs[:10]))
            )

    return SafetyDiffReport(
        passed=not regressions,
        before_total_arcs=before_arcs_total,
        after_total_arcs=after_arcs_total,
        before_total_lines=before_lines_total,
        after_total_lines=after_lines_total,
        regressions=tuple(regressions),
    )


def format_audit_summary(report: RedundancyAuditReport, *, top_n: int = 20) -> str:
    """Format a compact human-readable redundancy audit summary."""
    total_arcs = sum(len(m.covered_arcs) for m in report.modules.values())
    total_lines = sum(len(m.covered_lines) for m in report.modules.values())
    shown = min(top_n, len(report.zero_unique_tests))
    lines = [
        f"Tests analyzed: {report.total_tests}",
        f"Zero-unique-contribution tests: {len(report.zero_unique_tests)}",
        f"Production modules: {len(report.modules)} (arcs={total_arcs}, lines={total_lines})",
    ]
    if report.zero_unique_tests:
        lines.append(f"Sample zero-unique tests (first {shown}):")
        lines.extend(f"  - {ctx}" for ctx in report.zero_unique_tests[:top_n])
    return "\n".join(lines)
