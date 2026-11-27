#!/usr/bin/env python3
"""Validation script for Tech Lead implementation reports in ORCIA.

Ensures:
1. Each report in docs/implementation-artifacts/tech-lead-reports/ (excluding README.md
   and underscore-prefixed annexes) matches *-tech-lead-report.md
2. Contains the 3 mandatory sections (in English or legacy French for immutable historical reports):
   - Needs Analysis / Analyse du Besoin
   - Implementation Plan / Plan d'Implémentation
   - Summary of Changes / Bilan des Modifications
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

MANDATORY_SECTIONS = [
    re.compile(
        r"^##\s+1\.\s+.*(analyse\s+du\s+besoin|needs\s+analysis)",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^##\s+2\.\s+.*(plan\s+d['’]impl[ée]mentation|implementation\s+plan)",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^##\s+3\.\s+.*(bilan\s+des\s+modifications|summary\s+of\s+changes)",
        re.IGNORECASE | re.MULTILINE,
    ),
]


def check_docs(
    docs_dir: Path = DOCS_DIR,
    *,
    legacy_path: Path | None = None,
) -> int:
    if not docs_dir.exists():
        print(f"❌ Directory not found: {docs_dir}")
        return 1

    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import generate_tlr_index  # type: ignore[import-not-found]

    errors: list[str] = []

    files = [
        f
        for f in docs_dir.glob("*.md")
        if f.name not in ("README.md",) and not f.name.startswith("_")
    ]

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

        content = file_path.read_text(encoding="utf-8")
        for section_pattern in MANDATORY_SECTIONS:
            if not section_pattern.search(content):
                errors.append(
                    f"[{file_path.name}] Missing mandatory section matching: "
                    f"{section_pattern.pattern}"
                )

    gen_kwargs = {"legacy_path": legacy_path} if legacy_path is not None else {}
    if generate_tlr_index.run(docs_dir, check=True, **gen_kwargs) != 0:
        errors.append(
            "docs/implementation-artifacts/tech-lead-reports/README.md is out of sync "
            "(run `.venv/bin/python scripts/generate_tlr_index.py` or `pnpm site:sync`)"
        )

    if errors:
        print("❌ Tech Lead Implementation Documentation Check Failed:")
        for err in errors:
            print(f"   - {err}")
        return 1

    print(
        f"✅ All {len(files)} Tech Lead report(s) comply with standards and README.md is in sync."
    )
    return 0


if __name__ == "__main__":
    sys.exit(check_docs())
