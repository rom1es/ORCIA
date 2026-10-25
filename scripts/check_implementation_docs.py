#!/usr/bin/env python3
"""Validation script for Tech Lead implementation reports in ORCIA.

Ensures:
1. Each report in docs/implementation-artifacts/tech-lead-reports/ matches *-tech-lead-report.md
2. Contains the 3 mandatory sections:
   - Analyse du Besoin
   - Plan d'Implémentation
   - Bilan des Modifications
3. Is indexed in docs/implementation-artifacts/tech-lead-reports/README.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS_DIR = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "implementation-artifacts"
    / "tech-lead-reports"
)
README_FILE = DOCS_DIR / "README.md"

MANDATORY_SECTIONS = [
    re.compile(r"^##\s+1\.\s+.*analyse\s+du\s+besoin", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^##\s+2\.\s+.*plan\s+d['’]impl[ée]mentation", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^##\s+3\.\s+.*bilan\s+des\s+modifications", re.IGNORECASE | re.MULTILINE),
]


def check_docs() -> int:
    if not DOCS_DIR.exists():
        print(f"❌ Directory not found: {DOCS_DIR}")
        return 1

    readme_content = README_FILE.read_text(encoding="utf-8") if README_FILE.exists() else ""
    errors: list[str] = []

    files = [f for f in DOCS_DIR.glob("*.md") if f.name not in ("README.md",)]

    if not files:
        print("⚠️ No Tech Lead implementation reports found.")
        return 0

    name_pattern = re.compile(r"^[\w\-]+-tech-lead-report\.md$", re.UNICODE)

    for file_path in sorted(files):
        if not name_pattern.match(file_path.name):
            errors.append(
                f"[{file_path.name}] Filename does not follow convention "
                "'<story-key>-tech-lead-report.md'"
            )

        if file_path.name not in readme_content:
            errors.append(
                f"[{file_path.name}] Not referenced in "
                "docs/implementation-artifacts/tech-lead-reports/README.md index"
            )

        content = file_path.read_text(encoding="utf-8")
        for section_pattern in MANDATORY_SECTIONS:
            if not section_pattern.search(content):
                errors.append(
                    f"[{file_path.name}] Missing mandatory section matching: "
                    f"{section_pattern.pattern}"
                )

    if errors:
        print("❌ Tech Lead Implementation Documentation Check Failed:")
        for err in errors:
            print(f"   - {err}")
        return 1

    print(
        f"✅ All {len(files)} Tech Lead report(s) comply with standards "
        "and are indexed in README.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(check_docs())
