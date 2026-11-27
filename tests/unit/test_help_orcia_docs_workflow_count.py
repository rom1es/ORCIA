"""Unit tests ensuring help workflow counts only valid Tech Lead Reports."""

from __future__ import annotations

from pathlib import Path

import pytest

from orcia_core.orchestration.help_generator_and_validator import (
    HelpGenerationAndHotAttachmentService,
)


@pytest.mark.asyncio
async def test_help_workflow_excludes_annexes_readme_and_archive_from_tlr_count(
    tmp_path: Path,
) -> None:
    """Ensure `_*.md`, `README.md`, non-TLR markdown, and `archive/` are excluded."""
    reports_dir = tmp_path / "docs" / "implementation-artifacts" / "tech-lead-reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "archive").mkdir()

    (reports_dir / "1-1-alpha-tech-lead-report.md").write_text("# A\n", encoding="utf-8")
    (reports_dir / "2026-11-27-beta-tech-lead-report.md").write_text(
        "---\ndate: 2026-11-27\n---\n# B\n", encoding="utf-8"
    )
    (reports_dir / "README.md").write_text("# Index\n", encoding="utf-8")
    (reports_dir / "_i18n-audit-inventory-raw.md").write_text("# Raw dump\n", encoding="utf-8")
    (reports_dir / "_private-tech-lead-report.md").write_text("# Annex\n", encoding="utf-8")
    (reports_dir / "random-notes.md").write_text("# Notes\n", encoding="utf-8")
    (reports_dir / "archive" / "old-tech-lead-report.md").write_text(
        "# Archived\n", encoding="utf-8"
    )

    svc = HelpGenerationAndHotAttachmentService()
    report = await svc.run_generate_orcia_documentation_workflow(
        actor_role="ARCHITECT",
        repo_root=tmp_path,
        export_root_dir=tmp_path / "export",
    )
    assert report.tech_lead_reports_count == 2
