"""Traceability checks linking campaign failures, audit items, and remediation plans."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "e2e-campaign-epic-21"
MASTER_PLAN_PATH = (
    REPO_ROOT
    / "docs"
    / "planning-artifacts"
    / "sprint-change-proposal-2026-11-18-epic-22-remediation-plan.md"
)
REPORTS_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "tech-lead-reports"
REPORTS_INDEX_PATH = REPORTS_DIR / "README.md"
CAPABILITIES_PATH = REPO_ROOT / "docs" / "product" / "capabilities.yaml"
SPRINT_STATUS_PATH = REPO_ROOT / "docs" / "implementation-artifacts" / "sprint-status.yaml"
EPICS_PATH = REPO_ROOT / "docs" / "planning-artifacts" / "epics.md"


def _collect_failing_spec_files(suites: list[dict[str, Any]]) -> set[str]:
    failing: set[str] = set()
    for suite in suites:
        for spec in suite.get("specs", []):
            spec_file = str(spec.get("file", "")).strip()
            for test in spec.get("tests", []):
                for result in test.get("results", []):
                    if result.get("status") in {"failed", "timedOut"} and spec_file:
                        failing.add(spec_file)
        sub_suites = suite.get("suites", [])
        if isinstance(sub_suites, list):
            failing |= _collect_failing_spec_files(sub_suites)
    return failing


def _load_remediation_reports() -> dict[str, str]:
    reports = sorted(REPORTS_DIR.glob("22-*-tech-lead-report.md"))
    return {path.name: path.read_text(encoding="utf-8") for path in reports}


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_campaign_deliverables_and_remediation_master_plan_exist_and_are_non_empty() -> None:
    required_paths = (
        CAMPAIGN_DIR / "playwright-results.json",
        CAMPAIGN_DIR / "manifest.jsonl",
        CAMPAIGN_DIR / "bilan-execution-tests-e2e-epic-21.md",
        CAMPAIGN_DIR / "notes-audit-sally-ux.md",
        CAMPAIGN_DIR / "notes-audit-winston-architecture.md",
        CAMPAIGN_DIR / "synthese-remediation-sally-winston-epic-21.md",
        MASTER_PLAN_PATH,
    )
    for artifact in required_paths:
        assert artifact.is_file(), f"Missing campaign deliverable: {artifact}"
        assert artifact.stat().st_size > 0, f"Empty campaign deliverable: {artifact}"
        assert artifact.read_text(encoding="utf-8").strip(), (
            f"Whitespace-only deliverable: {artifact}"
        )

    manifest_lines = [
        line
        for line in (CAMPAIGN_DIR / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(manifest_lines) == 110
    for line in manifest_lines:
        entry = json.loads(line)
        assert isinstance(entry, dict)
        assert entry.get("spec")
        assert entry.get("status") in {"passed", "failed", "timedOut", "skipped"}


def test_every_failing_browser_spec_is_mapped_to_master_plan_and_tech_lead_reports() -> None:
    results = json.loads((CAMPAIGN_DIR / "playwright-results.json").read_text(encoding="utf-8"))
    failing_specs = sorted(_collect_failing_spec_files(results.get("suites", [])))
    assert len(failing_specs) == 14

    master_plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    reports_text = "\n".join(_load_remediation_reports().values())

    for spec_file in failing_specs:
        spec_stem = spec_file.removesuffix(".spec.ts")
        assert spec_file in master_plan_text, f"Spec {spec_file} absent from master plan"
        assert spec_file in reports_text or spec_stem in reports_text, (
            f"Spec {spec_file} absent from remediation tech-lead reports"
        )


def test_every_cross_audit_remediation_item_is_mapped_to_master_plan_and_tech_lead_reports() -> (
    None
):
    synthesis_text = (CAMPAIGN_DIR / "synthese-remediation-sally-winston-epic-21.md").read_text(
        encoding="utf-8"
    )
    remediation_ids = sorted(set(re.findall(r"\bREM-\d{2}\b", synthesis_text)))
    assert remediation_ids == [f"REM-{idx:02d}" for idx in range(1, 35)]

    master_plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    reports_by_name = _load_remediation_reports()
    assert len(reports_by_name) == 8

    for rem_id in remediation_ids:
        assert rem_id in master_plan_text, f"{rem_id} missing from master plan"
        assert any(rem_id in text for text in reports_by_name.values()), (
            f"{rem_id} missing from all 22-*-tech-lead-report.md files"
        )


def test_every_failed_capability_points_to_valid_sprint_key_and_report() -> None:
    capabilities_data = _load_yaml_mapping(CAPABILITIES_PATH)
    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)

    valid_keys = {k for k in dev_status if isinstance(k, str) and k.startswith("22-")}
    failed_caps = [
        cap
        for cap in capabilities_data.get("capabilities", [])
        if isinstance(cap, dict) and cap.get("verification") == "failed_e2e"
    ]
    assert len(failed_caps) == 51

    for cap in failed_caps:
        cap_id = cap.get("id")
        ref = cap.get("e2e_remediation_ref")
        assert isinstance(ref, str) and ref in valid_keys, (
            f"Capability {cap_id} has invalid e2e_remediation_ref={ref!r}"
        )
        report_path = REPORTS_DIR / f"{ref}-tech-lead-report.md"
        assert report_path.is_file(), (
            f"Capability {cap_id} points to missing report {report_path.name}"
        )


def test_every_remediation_sprint_key_has_backlog_definition_report_and_index_entry() -> None:
    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)

    remediation_keys = sorted(
        key for key in dev_status if isinstance(key, str) and key.startswith("22-")
    )
    assert len(remediation_keys) == 8

    epics_text = EPICS_PATH.read_text(encoding="utf-8")
    index_text = REPORTS_INDEX_PATH.read_text(encoding="utf-8")

    for key in remediation_keys:
        parts = key.split("-", 2)
        story_marker = f"### Story {parts[0]}.{parts[1]}:"
        assert story_marker in epics_text, f"Missing '{story_marker}' section in epics.md for {key}"
        report_filename = f"{key}-tech-lead-report.md"
        report_path = REPORTS_DIR / report_filename
        assert report_path.is_file(), f"Missing tech-lead report {report_filename}"
        assert report_path.stat().st_size > 0, f"Empty tech-lead report {report_filename}"
        assert report_filename in index_text, (
            f"Report {report_filename} not indexed in tech-lead-reports/README.md"
        )
