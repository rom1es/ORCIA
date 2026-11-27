"""Unit tests for `scripts/generate_tlr_index.py` and TLR frontmatter/HTML-comment compatibility."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GEN_SCRIPT = REPO_ROOT / "scripts" / "generate_tlr_index.py"
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check_implementation_docs.py"
PARSERS_DIR = REPO_ROOT / "infra" / "scripts"


def _load_module(path: Path, name: str):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    if name in sys.modules:
        return sys.modules[name]
    return __import__(name)


def _valid_body(title: str = "My Report", date: str = "2026-11-27") -> str:
    return (
        f"# {title}\n\n"
        f"- **Date**: {date}\n\n"
        "<!-- frozen-after-approval:start -->\n"
        "## 1. Needs Analysis & Tech Lead Impact Study\n\nOk.\n\n"
        "<!-- frozen-after-approval:end -->\n\n"
        "## 2. Implementation Plan\n\n- [ ] Task\n\n"
        "## 3. Summary of Changes & Results\n\nDone.\n"
    )


def test_metadata_precedence_truncation_pipes_sorting_and_exclusions(tmp_path: Path) -> None:
    gen = _load_module(GEN_SCRIPT, "generate_tlr_index")
    reports_dir = tmp_path / "docs" / "implementation-artifacts" / "tech-lead-reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "archive").mkdir()
    (reports_dir / "archive" / "ignored-tech-lead-report.md").write_text(
        _valid_body("Archived"), encoding="utf-8"
    )
    (reports_dir / "_raw.md").write_text("# Raw\n", encoding="utf-8")
    (reports_dir / "notes.md").write_text("# Notes\n", encoding="utf-8")

    # 1. Frontmatter wins over legacy JSON (also exercises comments, blank lines, quotes)
    long_sum = "A" * 230
    (reports_dir / "b-fm-tech-lead-report.md").write_text(
        "---\n"
        "# comment\n"
        "bad_line_without_colon\n"
        "date: '2026-11-25'\n"
        'story: "Story 99.1"\n'
        "domain: Core | API\n"
        f"summary: {long_sum}\n"
        "---\n\n" + _valid_body("Ignored H1"),
        encoding="utf-8",
    )
    # 2. Legacy JSON fallback when no frontmatter
    (reports_dir / "a-legacy-tech-lead-report.md").write_text(
        _valid_body("H1 Fallback"), encoding="utf-8"
    )
    # 3. Body/filename fallback when neither frontmatter nor legacy JSON
    (reports_dir / "2026-11-24-fallback-tech-lead-report.md").write_text(
        "# 2026-11-24 — Fallback Feature\n\n"
        "## 1. Needs Analysis\n\n## 2. Implementation Plan\n\n## 3. Summary of Changes\n",
        encoding="utf-8",
    )

    legacy_path = tmp_path / "legacy.json"
    legacy_path.write_text(
        json.dumps(
            {
                "b-fm-tech-lead-report.md": {
                    "date": "2020-01-01",
                    "story": "Old",
                    "domain": "Old",
                    "summary": "Old summary",
                },
                "a-legacy-tech-lead-report.md": {
                    "date": "2026-11-25",
                    "story": "Story 1.1",
                    "domain": "Legacy | Domain",
                    "summary": "Legacy summary",
                },
            }
        ),
        encoding="utf-8",
    )

    rendered = gen.render_tlr_index(reports_dir, legacy_path=legacy_path)
    assert gen.GENERATED_BANNER in rendered
    rows = [row for row in rendered.splitlines() if row.startswith("| **202")]
    assert len(rows) == 3

    # Sorted by (date, filename): 2026-11-24, then a-legacy, then b-fm
    assert "2026-11-24-fallback-tech-lead-report.md" in rows[0]
    assert "a-legacy-tech-lead-report.md" in rows[1]
    assert "b-fm-tech-lead-report.md" in rows[2]

    # Frontmatter won + pipes replaced + summary truncated to <= 200 chars with ellipsis
    assert "Story 99.1" in rows[2]
    assert "Old summary" not in rows[2]
    assert ("A" * 199 + "…") in rows[2]
    assert rows[2].count("|") == 6
    assert rows[1].count("|") == 6
    assert "_raw.md" not in rendered
    assert "notes.md" not in rendered
    assert "ignored-tech-lead-report.md" not in rendered


def test_check_mode_passes_when_synced_and_fails_on_drift(tmp_path: Path) -> None:
    gen = _load_module(GEN_SCRIPT, "generate_tlr_index")
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "1-1-sample-tech-lead-report.md").write_text(
        "---\ndate: 2026-11-27\nstory: Story 1.1\ndomain: Core\nsummary: Short\n---\n"
        + _valid_body(),
        encoding="utf-8",
    )
    legacy_path = tmp_path / "legacy.json"
    legacy_path.write_text("{}", encoding="utf-8")

    assert gen.run(reports_dir, legacy_path=legacy_path, check=True) == 1
    assert gen.run(reports_dir, legacy_path=legacy_path, check=False) == 0
    assert gen.run(reports_dir, legacy_path=legacy_path, check=True) == 0

    (reports_dir / "README.md").write_text("stale\n", encoding="utf-8")
    assert gen.run(reports_dir, legacy_path=legacy_path, check=True) == 1
    assert gen.collect_entries(tmp_path / "missing", legacy_path=None) == []
    assert gen.main(["--check"]) == 0


@pytest.mark.asyncio
async def test_frontmatter_and_frozen_comments_compatible_with_consumers(tmp_path: Path) -> None:
    gen = _load_module(GEN_SCRIPT, "generate_tlr_index")
    chk = _load_module(CHECK_SCRIPT, "check_implementation_docs")
    if str(PARSERS_DIR) not in sys.path:
        sys.path.insert(0, str(PARSERS_DIR))
    from _site_repo_parsers import parse_tech_lead_reports  # type: ignore[import-not-found]

    from orcia_core.orchestration.help_generator_and_validator import (
        HelpGenerationAndHotAttachmentService,
    )

    reports_dir = tmp_path / "docs" / "implementation-artifacts" / "tech-lead-reports"
    reports_dir.mkdir(parents=True)
    tlr_file = reports_dir / "2026-11-27-compat-tech-lead-report.md"
    tlr_file.write_text(
        "---\n"
        "date: 2026-11-27\n"
        "story: Story 13.9\n"
        "domain: Harness\n"
        "summary: Compat check\n"
        "status: ready-for-dev\n"
        "route: dispatch\n"
        "baseline_commit: abc1234\n"
        "review_loop_iteration: 0\n"
        "---\n\n" + _valid_body("Compat Check"),
        encoding="utf-8",
    )
    legacy_path = tmp_path / "legacy.json"
    legacy_path.write_text("{}", encoding="utf-8")
    assert gen.run(reports_dir, legacy_path=legacy_path, check=False) == 0

    assert chk.check_docs(docs_dir=reports_dir, legacy_path=legacy_path) == 0

    parsed = parse_tech_lead_reports(reports_dir / "README.md")
    assert len(parsed) == 1
    assert parsed[0]["reportFile"] == tlr_file.name
    assert parsed[0]["phaseOrStory"] == "Story 13.9"

    svc = HelpGenerationAndHotAttachmentService()
    report = await svc.run_generate_orcia_documentation_workflow(
        actor_role="ARCHITECT",
        repo_root=tmp_path,
        export_root_dir=tmp_path / "export",
    )
    assert report.tech_lead_reports_count == 1
