"""Traceability checks linking Epic 22 campaign outputs to Epic 23 plans and reports."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "e2e-campaign-epic-22"
CAMPAIGN_23_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "e2e-campaign-epic-23"
SCREENSHOTS_DIR = CAMPAIGN_DIR / "screenshots"
MASTER_PLAN_PATH = (
    REPO_ROOT
    / "docs"
    / "planning-artifacts"
    / "sprint-change-proposal-2026-11-18-epic-23-remediation-plan.md"
)
REPORTS_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "tech-lead-reports"
REPORTS_INDEX_PATH = REPORTS_DIR / "README.md"
CAPABILITIES_PATH = REPO_ROOT / "docs" / "product" / "capabilities.yaml"
SPRINT_STATUS_PATH = REPO_ROOT / "docs" / "implementation-artifacts" / "sprint-status.yaml"
EPICS_PATH = REPO_ROOT / "docs" / "planning-artifacts" / "epics.md"

MAX_PNG_BYTES = 450 * 1024

DEFERRED_STORY_23_6_KEY = (
    "23-6-campagne-e2e-integrale-mobile-companion-audit-et-62-capacites-runtime"
)
ACTION_ITEM_23_6_ID = "ACTION_ITEM-23.6"

EPIC_23_KEYS = (
    "23-1-reset-jour0-e2e-truncate-cascade-connector-schemes-et-redis",
    "23-2-transport-sse-authentifie-createrequestsse-smoke-00-et-diagnostic-401",
    "23-3-zone-4-aide-contextuelle-fidele-a-la-route-et-4-blocs-design-md",
    "23-4-unification-accostage-x-sur-6-fin-fantomes-jour0-et-modale-admin",
    "23-5-sobriete-cockpit-topbar-sans-doublon-assistant-et-login",
    "23-6a-durcissement-anti-goodhart-gardes-openapi-ast-geometrie-et-reset-pg18",
)
STORY_23_7_KEY = "23-7-campagne-e2e-integrale-captures-png-bilan-et-audit-croise-sally-winston"
STORY_23_8_KEY = "23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24"


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


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _load_epic23_reports() -> dict[str, str]:
    reports = sorted(REPORTS_DIR.glob("23-*-tech-lead-report.md"))
    return {path.name: path.read_text(encoding="utf-8") for path in reports}


def _extract_table_rows_containing(plan_text: str, needle: str) -> list[str]:
    return [
        line for line in plan_text.splitlines() if line.lstrip().startswith("|") and needle in line
    ]


def test_campaign_deliverables_manifest_and_screenshots_are_valid() -> None:
    required_paths = (
        CAMPAIGN_DIR / "playwright-results.json",
        CAMPAIGN_DIR / "manifest.jsonl",
        CAMPAIGN_DIR / "bilan-execution-tests-e2e-epic-22.md",
        CAMPAIGN_DIR / "notes-audit-sally-ux.md",
        CAMPAIGN_DIR / "notes-audit-winston-architecture.md",
        CAMPAIGN_DIR / "synthese-remediation-sally-winston-epic-22.md",
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

    manifest_pngs: set[Path] = set()
    for line in manifest_lines:
        entry = json.loads(line)
        assert isinstance(entry, dict)
        assert entry.get("spec")
        assert entry.get("status") in {"passed", "failed", "timedOut", "skipped"}
        rel_shot = str(entry.get("screenshot_path", "")).strip()
        assert rel_shot.startswith(
            "docs/implementation-artifacts/e2e-campaign-epic-22/screenshots/"
        ), f"Unexpected screenshot path in manifest: {rel_shot!r}"
        shot_path = REPO_ROOT / rel_shot
        assert shot_path.is_file(), f"Missing screenshot referenced in manifest: {shot_path}"
        assert 0 < shot_path.stat().st_size < MAX_PNG_BYTES, (
            f"Screenshot {shot_path.name} exceeds size budget: {shot_path.stat().st_size} bytes"
        )
        manifest_pngs.add(shot_path.resolve())

    disk_pngs = {p.resolve() for p in SCREENSHOTS_DIR.rglob("*.png")}
    assert len(disk_pngs) == 110
    assert disk_pngs == manifest_pngs
    for png_path in disk_pngs:
        assert 0 < png_path.stat().st_size < MAX_PNG_BYTES


def test_every_failing_spec_is_attached_to_epic23_key_in_master_plan() -> None:
    results = json.loads((CAMPAIGN_DIR / "playwright-results.json").read_text(encoding="utf-8"))
    failing_specs = sorted(_collect_failing_spec_files(results.get("suites", [])))
    assert len(failing_specs) == 24

    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)
    valid_keys = {k for k in dev_status if isinstance(k, str) and k.startswith("23-")}
    assert set(EPIC_23_KEYS).issubset(valid_keys)
    valid_plan_keys = valid_keys | {DEFERRED_STORY_23_6_KEY, ACTION_ITEM_23_6_ID}

    plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    for spec_file in failing_specs:
        matching_rows = _extract_table_rows_containing(plan_text, f"`{spec_file}`")
        assert matching_rows, f"Spec {spec_file} missing from Epic 23 master plan matrix"
        assert any(any(key in row for key in valid_plan_keys) for row in matching_rows), (
            f"Spec {spec_file} is not linked to a valid 23-* sprint key"
        )


def test_every_remediation_ux_and_arch_item_is_mapped_to_master_plan_and_reports() -> None:
    synthesis_text = (CAMPAIGN_DIR / "synthese-remediation-sally-winston-epic-22.md").read_text(
        encoding="utf-8"
    )
    sally_text = (CAMPAIGN_DIR / "notes-audit-sally-ux.md").read_text(encoding="utf-8")
    winston_text = (CAMPAIGN_DIR / "notes-audit-winston-architecture.md").read_text(
        encoding="utf-8"
    )

    remediation_ids = sorted(set(re.findall(r"\bREM23-\d{2}\b", synthesis_text)))
    assert remediation_ids == [f"REM23-{idx:02d}" for idx in range(1, 14)]

    ux_ids = sorted(set(re.findall(r"\bP[0-3]-UX-\d+\b", sally_text)))
    assert len(ux_ids) == 12

    arch_ids = sorted(set(re.findall(r"\bARCH23-\d{2}\b", winston_text)))
    assert arch_ids == [f"ARCH23-{idx:02d}" for idx in range(1, 11)]

    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)
    valid_keys = {k for k in dev_status if isinstance(k, str) and k.startswith("23-")}
    assert DEFERRED_STORY_23_6_KEY not in dev_status
    valid_plan_keys = valid_keys | {DEFERRED_STORY_23_6_KEY, ACTION_ITEM_23_6_ID}

    plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
    reports_by_name = _load_epic23_reports()
    core_report_names = {f"{key}-tech-lead-report.md" for key in EPIC_23_KEYS}
    assert core_report_names.issubset(set(reports_by_name.keys()))
    assert len(reports_by_name) >= len(EPIC_23_KEYS)
    expected_report_names = {f"{key}-tech-lead-report.md" for key in valid_keys}
    archived_23_6_report = f"{DEFERRED_STORY_23_6_KEY}-tech-lead-report.md"
    assert expected_report_names.issubset(set(reports_by_name.keys()))
    assert set(reports_by_name.keys()) <= (expected_report_names | {archived_23_6_report})

    for rem_id in remediation_ids:
        rows = _extract_table_rows_containing(plan_text, f"`{rem_id}`")
        assert rows, f"{rem_id} missing from master plan"
        assert any(any(key in row for key in valid_plan_keys) for row in rows), (
            f"{rem_id} has no 23-* sprint key in master plan"
        )
        assert any(rem_id in text for text in reports_by_name.values()), (
            f"{rem_id} missing from 23-*-tech-lead-report.md"
        )

    for ux_id in ux_ids:
        rows = _extract_table_rows_containing(plan_text, f"`{ux_id}`")
        assert rows, f"{ux_id} missing from master plan"
        assert any(any(key in row for key in valid_plan_keys) for row in rows), (
            f"{ux_id} has no 23-* sprint key in master plan"
        )
        assert any(ux_id in text for text in reports_by_name.values()), (
            f"{ux_id} missing from 23-*-tech-lead-report.md"
        )

    for arch_id in arch_ids:
        rows = _extract_table_rows_containing(plan_text, f"`{arch_id}`")
        assert rows, f"{arch_id} missing from master plan"
        assert any(any(key in row for key in valid_plan_keys) for row in rows), (
            f"{arch_id} has no 23-* sprint key in master plan"
        )
        assert any(arch_id in text for text in reports_by_name.values()), (
            f"{arch_id} missing from 23-*-tech-lead-report.md"
        )


def test_every_failed_capability_points_to_epic23_key_master_plan_and_report() -> None:
    capabilities_data = _load_yaml_mapping(CAPABILITIES_PATH)
    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)
    action_items = [item for item in sprint_data.get("action_items", []) if isinstance(item, dict)]
    action_item_ids = {str(item.get("id", "")).strip() for item in action_items}

    capabilities = [
        cap for cap in capabilities_data.get("capabilities", []) if isinstance(cap, dict)
    ]
    is_23_7_done = dev_status.get(STORY_23_7_KEY) == "done"

    if not is_23_7_done:
        failed_caps = [cap for cap in capabilities if cap.get("verification") == "failed_e2e"]
        assert len(failed_caps) == 62

        allowed_pre237_refs = set(EPIC_23_KEYS) | {DEFERRED_STORY_23_6_KEY, ACTION_ITEM_23_6_ID}
        plan_text = MASTER_PLAN_PATH.read_text(encoding="utf-8")
        for cap in failed_caps:
            cap_id = str(cap.get("id", "")).strip()
            ref = cap.get("e2e_remediation_ref")
            assert isinstance(ref, str) and ref in allowed_pre237_refs, (
                f"Capability {cap_id} has invalid e2e_remediation_ref={ref!r}"
            )
            rows = _extract_table_rows_containing(plan_text, f"`{cap_id}`")
            if ref == ACTION_ITEM_23_6_ID:
                assert ACTION_ITEM_23_6_ID in action_item_ids
                assert any(
                    ACTION_ITEM_23_6_ID in row or DEFERRED_STORY_23_6_KEY in row for row in rows
                ), f"Capability {cap_id} -> {ref} missing from Epic 23 master plan table"
            else:
                assert any(ref in row for row in rows), (
                    f"Capability {cap_id} -> {ref} missing from Epic 23 master plan table"
                )
                report_path = REPORTS_DIR / f"{ref}-tech-lead-report.md"
                assert report_path.is_file(), (
                    f"Capability {cap_id} points to missing report {report_path.name}"
                )

        runtime_caps = [cap for cap in capabilities if cap.get("verification") == "runtime"]
        assert len(runtime_caps) == 3
        for cap in runtime_caps:
            cap_id = cap.get("id")
            assert not cap.get("e2e_remediation_ref"), (
                f"Runtime capability {cap_id} must not retain e2e_remediation_ref"
            )
        return

    live_caps = [cap for cap in capabilities if cap.get("status") == "live"]
    assert len(live_caps) == 65
    for cap in live_caps:
        cap_id = str(cap.get("id", "")).strip()
        verification = cap.get("verification")
        assert verification in {"runtime", "failed_e2e"}, (
            f"Capability {cap_id} has unexpected verification={verification!r} after Story 23.7"
        )
        if verification == "runtime":
            verified_at = str(cap.get("verified_at") or "").strip()
            assert verified_at, f"Runtime capability {cap_id} missing verified_at"
            assert not cap.get("e2e_remediation_ref"), (
                f"Runtime capability {cap_id} must not retain e2e_remediation_ref"
            )
        else:
            post_ref = cap.get("e2e_remediation_ref")
            is_23_8_done = dev_status.get(STORY_23_8_KEY) == "done"
            if is_23_8_done:
                assert dev_status.get("epic-23") == "done"
                if cap_id == "CAP-042":
                    assert post_ref == ACTION_ITEM_23_6_ID
                else:
                    assert (
                        isinstance(post_ref, str)
                        and post_ref.startswith("24-")
                        and post_ref in dev_status
                    ), (
                        f"Capability {cap_id} must transfer from 23-* to 24-* after Story 23.8 "
                        f"(got {post_ref!r})"
                    )
            else:
                is_valid_epic24_ref = (
                    isinstance(post_ref, str)
                    and (post_ref.startswith("23-8-") or post_ref.startswith("24-"))
                    and post_ref in dev_status
                )
                is_valid_deferred_ref = isinstance(post_ref, str) and post_ref in {
                    DEFERRED_STORY_23_6_KEY,
                    ACTION_ITEM_23_6_ID,
                }
                assert is_valid_epic24_ref or is_valid_deferred_ref, (
                    f"Capability {cap_id} has invalid post-23.7 e2e_remediation_ref={post_ref!r}"
                )
            if post_ref == ACTION_ITEM_23_6_ID:
                assert ACTION_ITEM_23_6_ID in action_item_ids
            elif isinstance(post_ref, str):
                report_path = REPORTS_DIR / f"{post_ref}-tech-lead-report.md"
                assert report_path.is_file(), (
                    f"Capability {cap_id} points to missing report {report_path.name}"
                )

    cap_042 = next((c for c in live_caps if c.get("id") == "CAP-042"), None)
    assert cap_042 is not None
    assert cap_042.get("verification") == "failed_e2e"
    assert cap_042.get("e2e_remediation_ref") == ACTION_ITEM_23_6_ID

    results_23_path = CAMPAIGN_23_DIR / "playwright-results.json"
    results_23 = json.loads(results_23_path.read_text(encoding="utf-8"))
    failing_23_basenames = _collect_failing_spec_files(results_23.get("suites", []))
    failing_23_paths = {f"apps/web/e2e/{Path(f).name}" for f in failing_23_basenames}
    for cap in live_caps:
        cap_id = str(cap.get("id", "")).strip()
        cap_tests = {str(t) for t in (cap.get("tests") or [])}
        if cap_tests & failing_23_paths:
            assert cap.get("verification") == "failed_e2e", (
                f"Fraudulent promotion: {cap_id} references failing spec(s) "
                f"{sorted(cap_tests & failing_23_paths)}"
            )


def test_every_epic23_sprint_key_has_story_report_and_index_entry() -> None:
    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)

    remediation_keys = sorted(
        key for key in dev_status if isinstance(key, str) and key.startswith("23-")
    )
    assert (set(EPIC_23_KEYS) | {STORY_23_7_KEY, STORY_23_8_KEY}).issubset(set(remediation_keys))
    assert DEFERRED_STORY_23_6_KEY not in remediation_keys
    if dev_status.get(STORY_23_8_KEY) == "done":
        assert dev_status.get("epic-23") == "done"
        assert all(dev_status.get(key) == "done" for key in remediation_keys)

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


def test_story_23_6_and_mobile_companion_are_deferred_to_action_item_23_6() -> None:
    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)
    assert DEFERRED_STORY_23_6_KEY not in dev_status

    action_items = [item for item in sprint_data.get("action_items", []) if isinstance(item, dict)]
    matching = [item for item in action_items if item.get("id") == ACTION_ITEM_23_6_ID]
    assert len(matching) == 1
    item = matching[0]
    assert item.get("story_ref") == DEFERRED_STORY_23_6_KEY
    assert item.get("status") == "open"

    archived_report = f"{DEFERRED_STORY_23_6_KEY}-tech-lead-report.md"
    assert (REPORTS_DIR / archived_report).is_file()
    assert archived_report in REPORTS_INDEX_PATH.read_text(encoding="utf-8")
    assert "### Story 23.6:" in EPICS_PATH.read_text(encoding="utf-8")


def test_epic23_desktop_campaign_deliverables_and_registry_counts_when_23_7_done() -> None:
    sprint_data = _load_yaml_mapping(SPRINT_STATUS_PATH)
    dev_status = sprint_data.get("development_status", {})
    assert isinstance(dev_status, dict)
    if dev_status.get(STORY_23_7_KEY) != "done":
        return

    for artifact_name in (
        "playwright-results.json",
        "manifest.jsonl",
        "bilan-execution-tests-e2e-epic-23.md",
        "notes-audit-sally-ux.md",
        "notes-audit-winston-architecture.md",
        "synthese-remediation-sally-winston-epic-23.md",
    ):
        artifact = CAMPAIGN_23_DIR / artifact_name
        assert artifact.is_file(), f"Missing Epic 23 campaign deliverable: {artifact}"
        assert 0 < artifact.stat().st_size < MAX_PNG_BYTES

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
        assert (REPO_ROOT / rel_shot).is_file()

    disk_pngs = list((CAMPAIGN_23_DIR / "screenshots").rglob("*.png"))
    assert len(disk_pngs) == 58
    assert all(0 < p.stat().st_size < MAX_PNG_BYTES for p in disk_pngs)

    capabilities = _load_yaml_mapping(CAPABILITIES_PATH).get("capabilities", [])
    runtime_caps = [c for c in capabilities if c.get("verification") == "runtime"]
    failed_caps = [c for c in capabilities if c.get("verification") == "failed_e2e"]
    assert len(runtime_caps) == 39
    assert len(failed_caps) == 26
