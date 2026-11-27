"""Hygiene guard verifying superseded E2E campaign binaries/dumps stay purged."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CAMPAIGNS_ROOT = REPO_ROOT / "docs" / "implementation-artifacts"
PURGED_CAMPAIGNS = (
    "e2e-campaign-epic-21",
    "e2e-campaign-epic-22",
    "e2e-campaign-epic-23",
    "e2e-campaign-epic-24",
)


def test_e2e_campaign_screenshots_and_manifests_are_purged() -> None:
    retained_reports = 0
    for folder in PURGED_CAMPAIGNS:
        campaign_dir = CAMPAIGNS_ROOT / folder
        assert campaign_dir.is_dir(), f"Missing campaign folder: {campaign_dir}"
        assert not (campaign_dir / "screenshots").exists(), f"Unexpected screenshots/ in {folder}"
        assert list(campaign_dir.rglob("*.png")) == [], f"Unexpected PNG files in {folder}"
        assert not (campaign_dir / "manifest.jsonl").exists(), (
            f"Unexpected manifest.jsonl in {folder}"
        )
        md_reports = sorted(p.name for p in campaign_dir.glob("*.md"))
        assert len(md_reports) == 4, f"Expected 4 audit .md reports in {folder}, got {md_reports}"
        retained_reports += len(md_reports)
    assert retained_reports == 16


def test_obsolete_playwright_results_purged_and_epic24_preserved() -> None:
    for folder in PURGED_CAMPAIGNS[:-1]:
        assert not (CAMPAIGNS_ROOT / folder / "playwright-results.json").exists(), (
            f"Unexpected playwright-results.json in {folder}"
        )

    epic24_results = CAMPAIGNS_ROOT / "e2e-campaign-epic-24" / "playwright-results.json"
    assert epic24_results.is_file(), f"Missing live playwright-results.json: {epic24_results}"
    payload = json.loads(epic24_results.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert isinstance(payload.get("suites"), list)
