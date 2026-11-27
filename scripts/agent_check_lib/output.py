"""Token-first output formatting and machine-readable test failure parsing."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

MAX_TRACEBACKS = 3
MAX_TB_LINES = 14


@dataclass(frozen=True, slots=True)
class FailureDigest:
    """Compact bounded failure report for stdout."""

    stage: str
    summary: str
    elapsed_s: float
    failing_ids: list[str]
    tracebacks: list[str]
    log_path: Path


def format_pass_line(stage: str, summary: str, elapsed_s: float) -> str:
    """Format the single-line PASS banner."""
    return f"PASS [{stage}]: {summary} in {elapsed_s:.2f}s"


def format_skip_line(stage: str, digest: str) -> str:
    """Format the single-line SKIP receipt banner."""
    return f"SKIP [{stage}]: receipt {digest[:12]}"


def _compact_traceback(raw_text: str) -> str:
    lines = [ln.rstrip() for ln in raw_text.strip().splitlines() if ln.strip()]
    if len(lines) > MAX_TB_LINES:
        lines = [*lines[:4], "...", *lines[-(MAX_TB_LINES - 5) :]]
    return "\n".join(lines)


def parse_pytest_junitxml(xml_path: Path) -> tuple[list[str], list[str]]:
    """Extract all failing test IDs and up to 3 compact tracebacks from JUnit XML."""
    if not xml_path.is_file():
        return [], []
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return [], []
    root = tree.getroot()
    failing_ids: list[str] = []
    tracebacks: list[str] = []

    for testcase in root.iter("testcase"):
        failure = testcase.find("failure")
        error = testcase.find("error")
        node = failure if failure is not None else error
        if node is None:
            continue
        classname = testcase.attrib.get("classname", "").strip()
        name = testcase.attrib.get("name", "").strip()
        test_id = f"{classname}::{name}" if classname else name
        failing_ids.append(test_id)
        if len(tracebacks) < MAX_TRACEBACKS:
            raw_tb = (node.text or "").strip() or node.attrib.get("message", "").strip()
            if raw_tb:
                tracebacks.append(_compact_traceback(raw_tb))
    return failing_ids, tracebacks


def parse_vitest_json(json_path: Path) -> tuple[list[str], list[str]]:
    """Extract all failing test IDs and up to 3 compact tracebacks from Vitest JSON."""
    if not json_path.is_file():
        return [], []
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], []

    failing_ids: list[str] = []
    tracebacks: list[str] = []
    for suite in payload.get("testResults", []):
        suite_name = str(suite.get("name", "")).strip()
        assertions = suite.get("assertionResults", [])
        if suite.get("status") == "failed" and not assertions:
            failing_ids.append(suite_name or "vitest-suite-error")
            msg = str(suite.get("message", "")).strip()
            if msg and len(tracebacks) < MAX_TRACEBACKS:
                tracebacks.append(_compact_traceback(msg))
            continue
        for item in assertions:
            if item.get("status") != "failed":
                continue
            full_name = str(item.get("fullName") or item.get("title") or "unknown").strip()
            failing_ids.append(full_name)
            msgs = item.get("failureMessages") or []
            if msgs and len(tracebacks) < MAX_TRACEBACKS:
                tracebacks.append(_compact_traceback("\n".join(str(m) for m in msgs)))
    return failing_ids, tracebacks


def write_stage_log(repo_root: Path, stage: str, content: str) -> Path:
    """Write full raw output to `.agent_check/logs/<stage>-<ts>.log` and return repo-rel path."""
    logs_dir = repo_root / ".agent_check" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    log_file = logs_dir / f"{stage}-{ts}.log"
    log_file.write_text(content, encoding="utf-8")
    try:
        return log_file.relative_to(repo_root)
    except ValueError:
        return log_file


def format_failure_digest(digest: FailureDigest) -> str:
    """Render failure header, every failing ID (one per line), <= 3 tracebacks, and log path."""
    lines: list[str] = [f"FAIL [{digest.stage}]: {digest.summary} in {digest.elapsed_s:.2f}s"]
    for fid in digest.failing_ids:
        lines.append(f"  - {fid}")
    capped_tbs = digest.tracebacks[:MAX_TRACEBACKS]
    total_tb = len(capped_tbs)
    for idx, tb in enumerate(capped_tbs, start=1):
        lines.append(f"--- Traceback {idx}/{total_tb} ---")
        lines.append(tb)
    lines.append(f"LOG: {digest.log_path.as_posix()}")
    return "\n".join(lines)
