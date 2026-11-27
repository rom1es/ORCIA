"""Coverage dynamic-context redundancy audit and safety-gate helpers (`T-D11`)."""

from scripts.test_redundancy_audit_lib.analyzer import (
    ModuleCoverageSummary,
    RedundancyAuditReport,
    SafetyDiffReport,
    analyze_coverage_db,
    compare_baselines,
    format_audit_summary,
    load_baseline_snapshot,
    save_baseline_snapshot,
)

__all__ = [
    "ModuleCoverageSummary",
    "RedundancyAuditReport",
    "SafetyDiffReport",
    "analyze_coverage_db",
    "compare_baselines",
    "format_audit_summary",
    "load_baseline_snapshot",
    "save_baseline_snapshot",
]
