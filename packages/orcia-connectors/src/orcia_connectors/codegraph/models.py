"""Normalized Read-Only Code Graph MCP Models & Validation (`models.py`).

Defines the 5 normalized read-only codegraph tools:
1. `codegraph_locate_symbol`
2. `codegraph_get_call_hierarchy`
3. `codegraph_find_references`
4. `codegraph_calculate_blast_radius`
5. `codegraph_read_span` (bounded <= 250 lines, anti-path-traversal)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DriftWarningType = Literal["GRAPH_MOVED_SINCE_RUN_LOCK"]
CallDirectionType = Literal["callers", "callees", "both"]
BlastRadiusRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

MAX_CODE_SPAN_LINES = 250


def compute_drift_warning(
    *,
    indexed_commit_sha: str | None,
    run_lock_commit_sha: str | None,
) -> DriftWarningType | None:
    """Return `GRAPH_MOVED_SINCE_RUN_LOCK` if run-lock commit differs from indexed commit."""
    if not run_lock_commit_sha or not indexed_commit_sha:
        return None
    c_run = run_lock_commit_sha.strip()
    c_idx = indexed_commit_sha.strip()
    if c_run and c_idx and c_run != c_idx:
        return "GRAPH_MOVED_SINCE_RUN_LOCK"
    return None


def validate_read_span_params(file_path: str, start_line: int, end_line: int) -> None:
    """Validate file path and line bounds for `codegraph_read_span`."""
    cleaned = (file_path or "").strip()
    if not cleaned:
        raise ValueError("file_path cannot be empty")
    if "\x00" in cleaned or ".." in cleaned or cleaned.startswith("/") or cleaned.startswith("\\"):
        raise ValueError(
            f"Invalid file_path for codegraph_read_span: traversal or absolute path detected: "
            f"{file_path!r}"
        )
    if start_line < 1:
        raise ValueError(f"start_line must be >= 1, got {start_line}")
    if end_line < start_line:
        raise ValueError(f"end_line ({end_line}) cannot be less than start_line ({start_line})")
    count = end_line - start_line + 1
    if count > MAX_CODE_SPAN_LINES:
        raise ValueError(
            f"Line span exceeds maximum limit of {MAX_CODE_SPAN_LINES} lines "
            f"(requested {count} lines: {start_line}..{end_line})"
        )


class SymbolLocation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    symbol_name: str
    kind: str | None = None


class SymbolLocationResult(BaseModel):
    repo_alias: str
    query: str
    kind: str | None = None
    symbols: list[SymbolLocation] = Field(default_factory=list)
    indexed_commit_sha: str | None = None
    drift_warning: DriftWarningType | None = None


class CallHierarchyNode(BaseModel):
    symbol: str
    file_path: str
    line: int
    callers: list[str] = Field(default_factory=list)
    callees: list[str] = Field(default_factory=list)


class CallGraphResult(BaseModel):
    repo_alias: str
    symbol: str
    file_path: str
    direction: CallDirectionType = "both"
    nodes: list[CallHierarchyNode] = Field(default_factory=list)
    indexed_commit_sha: str | None = None
    drift_warning: DriftWarningType | None = None


class ReferenceLocation(BaseModel):
    file_path: str
    line: int
    context_snippet: str | None = None


class ReferenceLocationList(BaseModel):
    repo_alias: str
    symbol: str
    references: list[ReferenceLocation] = Field(default_factory=list)
    indexed_commit_sha: str | None = None
    drift_warning: DriftWarningType | None = None


class ImpactReport(BaseModel):
    repo_alias: str
    modified_files: list[str] = Field(default_factory=list)
    run_lock_commit_sha: str | None = None
    indexed_commit_sha: str | None = None
    impacted_files: list[str] = Field(default_factory=list)
    impacted_symbols: list[str] = Field(default_factory=list)
    blast_radius_score: float = 0.0
    risk_level: BlastRadiusRiskLevel = "LOW"
    drift_warning: DriftWarningType | None = None


class CodeSpanResult(BaseModel):
    repo_alias: str
    file_path: str
    start_line: int
    end_line: int
    total_lines: int
    content: str
    indexed_commit_sha: str | None = None
    drift_warning: DriftWarningType | None = None


__all__ = [
    "MAX_CODE_SPAN_LINES",
    "BlastRadiusRiskLevel",
    "CallDirectionType",
    "CallGraphResult",
    "CallHierarchyNode",
    "CodeSpanResult",
    "DriftWarningType",
    "ImpactReport",
    "ReferenceLocation",
    "ReferenceLocationList",
    "SymbolLocation",
    "SymbolLocationResult",
    "compute_drift_warning",
    "validate_read_span_params",
]
