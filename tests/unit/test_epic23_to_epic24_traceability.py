"""Traceability checks linking Epic 23 campaign outputs to Epic 24 plans and reports."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_23_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "e2e-campaign-epic-23"
MASTER_PLAN_PATH = (
    REPO_ROOT
    / "docs"
    / "planning-artifacts"
    / "sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md"
)
REPORTS_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "tech-lead-reports"
REPORTS_INDEX_PATH = REPORTS_DIR / "README.md"
CAPABILITIES_PATH = REPO_ROOT / "docs" / "product" / "capabilities.yaml"
SPRINT_STATUS_PATH = REPO_ROOT / "docs" / "implementation-artifacts" / "sprint-status.yaml"
EPICS_PATH = REPO_ROOT / "docs" / "planning-artifacts" / "epics.md"

MAX_PNG_BYTES = 450 * 1024
STORY_23_8_KEY = "23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24"
ACTION_ITEM_23_6_ID = "ACTION_ITEM-23.6"

EPIC_24_KEYS = (
    "24-1-persistance-pg18-actions-jira-staged-mcp-et-vsm-v2",
    "24-2-triggers-uuidv7-sans-collision-waivers-await-adn-pg18-et-fin-default-ws",
    "24-3-banc-mcp-audit-ledger-fin-pass-optimiste-et-assainissement-composition-root",
    "24-4-refonte-css-tailwind-tokens-modales-rgaa-contraste-onglets-et-shell",
    "24-5-identite-accostage-cockpit-sync-navigation-zone4-et-coherence-jour0",
    "24-6-recherche-cmdk-filtre-langue-purge-jargon-packs-et-microcopy",
    "24-7-reconciliation-e2e-captures-jalons-campagne-52-sur-52-et-cloture-epic-24",
)

EXPECTED_FAILING_SCENARIOS: dict[str, tuple[str, ...]] = {
    "#15": ("06-gates-review-and-anti-rubber-stamping.spec.ts", "06"),
    "#16": ("07-spaces-org-and-workspace-persistence.spec.ts", "07"),
    "#40": ("17-workspace-sources-codegraph-dna-and-ontology.spec.ts", "17#3"),
    "#41": ("18-catalog-packs-wizards-and-mcp-bench.spec.ts", "18#1"),
    "#45": ("18-catalog-packs-wizards-and-mcp-bench.spec.ts", "18#5"),
    "#47": ("19-orchestration-whatif-replay-and-gates.spec.ts", "19#2"),
    "#48": ("20-process-studio-v2-finops-and-log-sink.spec.ts", "20#1"),
    "#49": ("20-process-studio-v2-finops-and-log-sink.spec.ts", "20#2"),
}

USER_BUG_TARGETS: dict[str, tuple[str, str]] = {
    "USER24-BUG-1": (
        "24-4",
        "24-4-refonte-css-tailwind-tokens-modales-rgaa-contraste-onglets-et-shell",
    ),
    "USER24-BUG-2": (
        "24-5",
        "24-5-identite-accostage-cockpit-sync-navigation-zone4-et-coherence-jour0",
    ),
    "USER24-BUG-3": (
        "24-6",
        "24-6-recherche-cmdk-filtre-langue-purge-jargon-packs-et-microcopy",
    ),
    "USER24-BUG-4A": (
        "24-4",
        "24-4-refonte-css-tailwind-tokens-modales-rgaa-contraste-onglets-et-shell",
    ),
    "USER24-BUG-4B": (
        "24-4",
        "24-4-refonte-css-tailwind-tokens-modales-rgaa-contraste-onglets-et-shell",
    ),
    "USER24-BUG-5": (
        "24-4",
        "24-4-refonte-css-tailwind-tokens-modales-rgaa-contraste-onglets-et-shell",
    ),
    "USER24-BUG-6": (
        "24-2",
        "24-2-triggers-uuidv7-sans-collision-waivers-await-adn-pg18-et-fin-default-ws",
    ),
}

ALLOWED_EPIC_24_STATUSES = frozenset({"backlog", "in-progress", "done"})
ALLOWED_STORY_24_STATUSES = frozenset({"backlog", "ready-for-dev", "in-progress", "review", "done"})


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _collect_failing_scenarios(suites: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    failing: list[tuple[str, str, str]] = []
    for suite in suites:
        for spec in suite.get("specs", []):
            spec_file = str(spec.get("file", "")).strip()
            spec_title = str(spec.get("title", "")).strip()
            for test in spec.get("tests", []):
                for result in test.get("results", []):
                    status = str(result.get("status", "")).strip()
                    if status in {"failed", "timedOut"} and spec_file:
                        failing.append((spec_file, spec_title, status))
        sub_suites = suite.get("suites", [])
        if isinstance(sub_suites, list):
            failing.extend(_collect_failing_scenarios(sub_suites))
    return failing


def _expand_ux_ids_in_text(text: str) -> set[str]:
    ids = set(re.findall(r"\bUX23-\d{2}\b", text))
    for start_str, end_str in re.findall(r"\bUX23-(\d{2})\.\.(\d{2})\b", text):
        for idx in range(int(start_str), int(end_str) + 1):
            ids.add(f"UX23-{idx:02d}")
    return ids


def _expand_user_bug_ids_in_text(text: str) -> set[str]:
    ids = set(re.findall(r"\bUSER24-BUG-(?:4A|4B|[1-6])\b", text))
    if re.search(r"\bUSER24-BUG-1\.\.6\b", text):
        ids.update(USER_BUG_TARGETS.keys())
    return ids


def _load_epic24_reports() -> dict[str, str]:
    reports = sorted(REPORTS_DIR.glob("24-*-tech-lead-report.md"))
    return {path.name: path.read_text(encoding="utf-8") for path in reports}


def _extract_table_rows_containing(text: str, needle: str) -> list[str]:
    return [line for line in text.splitlines() if line.lstrip().startswith("|") and needle in line]


def test_epic23_campaign_deliverables_and_epic24_master_plan_are_valid() -> None:
    required_paths = (
        CAMPAIGN_23_DIR / "playwright-results.json",
        CAMPAIGN_23_DIR / "manifest.jsonl",
        CAMPAIGN_23_DIR / "bilan-execution-tests-e2e-epic-23.md",
        CAMPAIGN_23_DIR / "notes-audit-sally-ux.md",
        CAMPAIGN_23_DIR / "notes-audit-winston-architecture.md",
        CAMPAIGN_23_DIR / "synthese-remediation-sally-winston-epic-23.md",
        MASTER_PLAN_PATH,
    )
    for artifact in required_paths:
        assert artifact.is_file(), f"Missing deliverable: {artifact}"
        assert 0 < artifact.stat().st_size < MAX_PNG_BYTES
        assert artifact.read_text(encoding="utf-8").strip()

    manifest_lines = [
        line
        for line in (CAMPAIGN_23_DIR / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(manifest_lines) == 55
    for line in manifest_lines:
        entry = json.loads(line)
        rel_shot = str(entry.get("screenshot_path", "")).strip()
        assert rel_shot.startswith(
            "docs/implementation-artifacts/e2e-campaign-epic-23/screenshots/"
        )
        shot_path = REPO_ROOT / rel_shot
        assert shot_path.is_file(), f"Missing screenshot: {shot_path}"
        assert 0 < shot_path.stat().st_size < MAX_PNG_BYTES

    disk_pngs = list((CAMPAIGN_23_DIR / "screenshots").rglob("*.png"))
    assert len(disk_pngs) == 58
    assert all(0 < p.stat().st_size < MAX_PNG_BYTES for p in disk_pngs)


def test_all_8_failures_ux23_arch24_and_rem24_are_mapped_to_epic24() -> None:
    results = json.loads((CAMPAIGN_23_DIR / "playwright-results.json").read_text(encoding="utf-8"))
    failing_cases = _collect_failing_scenarios(results.get("suites", []))
    assert len(failing_cases) == 8

    expected_spec_files = {spec_file for spec_file, _ in EXPECTED_FAILING_SCENARIOS.values()}
    assert {case[0] for case in failing_cases} == expected_spec_files

    sally_text = (CAMPAIGN_23_DIR / "notes-audit-sally-ux.md").read_text(encoding="utf-8")
    winston_text = (CAMPAIGN_23_DIR / "notes-audit-winston-architecture.md").read_text(
        encoding="utf-8"
    )
    synthesis_text = (CAMPAIGN_23_DIR / "synthese-remediation-sally-winston-epic-23.md").read_text(
        encoding="utf-8"
    )

    ux_ids = sorted(set(re.findall(r"\bUX23-\d{2}\b", sally_text)))
    arch_ids = sorted(set(re.findall(r"\bARCH24-\d{2}\b", winston_text)))
    rem_ids = sorted(set(re.findall(r"\bREM24-\d{2}\b", synthesis_text)))
    assert ux_ids == [f"UX23-{idx:02d}" for idx in range(1, 18)]
    assert arch_ids == [f"ARCH24-{idx:02d}" for idx in range(1, 13)]
    assert rem_ids == [f"REM24-{idx:02d}" for idx in range(1, 13)]

    plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    epics_text = EPICS_PATH.read_text(encoding="utf-8")
    reports_by_name = _load_epic24_reports()
    assert set(reports_by_name.keys()) == {f"{key}-tech-lead-report.md" for key in EPIC_24_KEYS}
    all_reports_text = "\n".join(reports_by_name.values())
    epic24_epics_section = epics_text.split("## Epic 24:", maxsplit=1)[1]
    epics_ux_ids = _expand_ux_ids_in_text(epic24_epics_section)

    for scenario_num, (spec_file, spec_prefix) in EXPECTED_FAILING_SCENARIOS.items():
        rows = _extract_table_rows_containing(plan_text, scenario_num)
        assert rows, f"Scenario {scenario_num} ({spec_file}) missing from Epic 24 master plan"
        assert any(any(key in row for key in EPIC_24_KEYS) for row in rows), (
            f"Scenario {scenario_num} not linked to a 24-* sprint key in master plan"
        )
        assert scenario_num in epic24_epics_section, f"{scenario_num} missing from Epic 24 epics.md"
        assert scenario_num in all_reports_text and spec_prefix in all_reports_text, (
            f"Scenario {spec_prefix} {scenario_num} missing from 24-* tech-lead reports"
        )

    for ux_id in ux_ids:
        assert ux_id in plan_text, f"{ux_id} missing from Epic 24 master plan"
        assert ux_id in epics_ux_ids, f"{ux_id} missing from Epic 24 section of epics.md"
        assert ux_id in all_reports_text, f"{ux_id} missing from 24-* tech-lead reports"

    for arch_id in arch_ids:
        rows = _extract_table_rows_containing(plan_text, f"`{arch_id}`")
        assert rows, f"{arch_id} missing from Epic 24 master plan"
        assert any(any(key in row for key in EPIC_24_KEYS) for row in rows)
        assert arch_id in epic24_epics_section, f"{arch_id} missing from Epic 24 epics.md"
        assert arch_id in all_reports_text, f"{arch_id} missing from 24-* tech-lead reports"

    for rem_id in rem_ids:
        rows = _extract_table_rows_containing(plan_text, f"`{rem_id}`")
        assert rows, f"{rem_id} missing from Epic 24 master plan"
        assert any(any(key in row for key in EPIC_24_KEYS) for row in rows)
        assert rem_id in epic24_epics_section, f"{rem_id} missing from Epic 24 epics.md"
        assert rem_id in all_reports_text, f"{rem_id} missing from 24-* tech-lead reports"


def test_user24_bugs_are_mapped_to_epic24_plan_epics_and_reports() -> None:
    plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    epic24_epics_section = EPICS_PATH.read_text(encoding="utf-8").split("## Epic 24:", maxsplit=1)[
        1
    ]
    reports_by_name = _load_epic24_reports()
    report_24_7_key = EPIC_24_KEYS[-1]
    assert report_24_7_key.startswith("24-7-")
    report_24_7_ids = _expand_user_bug_ids_in_text(
        reports_by_name[f"{report_24_7_key}-tech-lead-report.md"]
    )
    epics_user_bug_ids = _expand_user_bug_ids_in_text(epic24_epics_section)

    for bug_id, (story_prefix, target_key) in USER_BUG_TARGETS.items():
        rows = _extract_table_rows_containing(plan_text, f"`{bug_id}`")
        assert rows, f"{bug_id} missing from Epic 24 master plan"
        assert any(story_prefix in row and "24-7" in row for row in rows), (
            f"{bug_id} not linked to {story_prefix} and 24-7 in master plan"
        )
        assert bug_id in epics_user_bug_ids, f"{bug_id} missing from Epic 24 section of epics.md"
        assert bug_id in reports_by_name[f"{target_key}-tech-lead-report.md"], (
            f"{bug_id} missing from {target_key}-tech-lead-report.md"
        )
        assert bug_id in report_24_7_ids, (
            f"{bug_id} missing from {report_24_7_key}-tech-lead-report.md"
        )


def test_desktop_failed_capabilities_transfer_to_epic24_and_cap042_stays_deferred() -> None:
    capabilities = _load_yaml_mapping(CAPABILITIES_PATH).get("capabilities", [])
    assert isinstance(capabilities, list)
    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)

    runtime_caps = [c for c in capabilities if c.get("verification") == "runtime"]
    epic26_api_caps = [
        c
        for c in capabilities
        if c.get("verification") == "api" and c.get("id") in {"CAP-022", "CAP-070", "CAP-072"}
    ]
    failed_caps = [c for c in capabilities if c.get("verification") == "failed_e2e"]
    assert 39 <= len(runtime_caps) + len(epic26_api_caps) <= 64
    assert len(failed_caps) + len(runtime_caps) + len(epic26_api_caps) == 65
    assert all(not c.get("e2e_remediation_ref") for c in runtime_caps)

    plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    epics_text = EPICS_PATH.read_text(encoding="utf-8").split("## Epic 24:", maxsplit=1)[1]
    reports_by_name = _load_epic24_reports()

    desktop_failed = [c for c in failed_caps if c.get("id") != "CAP-042"]
    assert len(desktop_failed) == len(failed_caps) - 1
    assert 0 <= len(desktop_failed) <= 25
    for cap in desktop_failed:
        cap_id = str(cap.get("id", ""))
        ref = str(cap.get("e2e_remediation_ref", ""))
        assert ref in EPIC_24_KEYS, f"{cap_id} has non-Epic-24 ref {ref!r}"
        assert not ref.startswith("23-"), f"{cap_id} retains residual 23-* ref {ref!r}"
        assert ref in dev_status, f"{cap_id} ref {ref!r} missing from sprint-status.yaml"
        assert cap_id in plan_text, f"{cap_id} missing from Epic 24 master plan"
        assert cap_id in epics_text, f"{cap_id} missing from Epic 24 epics.md"
        assert cap_id in reports_by_name[f"{ref}-tech-lead-report.md"], (
            f"{cap_id} missing from {ref}-tech-lead-report.md"
        )

    cap_042 = next((c for c in failed_caps if c.get("id") == "CAP-042"), None)
    assert cap_042 is not None
    assert cap_042.get("e2e_remediation_ref") == ACTION_ITEM_23_6_ID
    assert all(
        c.get("e2e_remediation_ref") != ACTION_ITEM_23_6_ID
        for c in capabilities
        if c.get("id") != "CAP-042"
    )

    if dev_status.get("epic-24") == "done":
        assert all(dev_status.get(key) == "done" for key in EPIC_24_KEYS)
        assert len(runtime_caps) + len(epic26_api_caps) == 64
        assert len(failed_caps) == 1
        assert [c.get("id") for c in failed_caps] == ["CAP-042"]


def test_sprint_status_epics_and_reports_index_for_epic23_closure_and_epic24_init() -> None:
    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)

    assert dev_status.get("epic-23") == "done"
    assert dev_status.get(STORY_23_8_KEY) == "done"
    assert dev_status.get("epic-24") in ALLOWED_EPIC_24_STATUSES

    epic24_keys = sorted(k for k in dev_status if isinstance(k, str) and k.startswith("24-"))
    assert epic24_keys == sorted(EPIC_24_KEYS)
    assert all(dev_status.get(key) in ALLOWED_STORY_24_STATUSES for key in EPIC_24_KEYS)
    if dev_status.get("epic-24") == "done":
        assert all(dev_status.get(key) == "done" for key in EPIC_24_KEYS)

    epics_text = EPICS_PATH.read_text(encoding="utf-8")
    index_text = REPORTS_INDEX_PATH.read_text(encoding="utf-8")
    assert "## Epic 24:" in epics_text

    for key in EPIC_24_KEYS:
        parts = key.split("-", 2)
        assert f"### Story {parts[0]}.{parts[1]}:" in epics_text
        report_name = f"{key}-tech-lead-report.md"
        report_path = REPORTS_DIR / report_name
        assert report_path.is_file()
        assert 0 < report_path.stat().st_size < MAX_PNG_BYTES
        assert report_name in index_text

    report_23_8 = REPORTS_DIR / f"{STORY_23_8_KEY}-tech-lead-report.md"
    assert report_23_8.is_file()
    assert f"{STORY_23_8_KEY}-tech-lead-report.md" in index_text
