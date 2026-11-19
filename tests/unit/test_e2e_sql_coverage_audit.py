"""Static audit ensuring 100% of Playwright E2E `test(...)` blocks assert PostgreSQL 18 state."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
E2E_DIR = REPO_ROOT / "apps" / "web" / "e2e"

TEST_BLOCK_START_RE = re.compile(r"(?<!\.)\btest\s*\(")
SQL_ASSERTION_TOKENS = ("expectDbRowExists", "expectDbRowCount", "queryDbRows")


def test_all_e2e_specs_invoke_postgresql_18_assertions_in_every_test_block() -> None:
    specs = sorted(E2E_DIR.glob("*.spec.ts"))
    assert len(specs) == 24

    total_blocks = 0
    blocks_missing_sql: list[str] = []
    cold_reload_consumers = 0

    for spec_path in specs:
        content = spec_path.read_text(encoding="utf-8")
        if "reloadColdFromPg" in content:
            cold_reload_consumers += 1

        starts = [match.start() for match in TEST_BLOCK_START_RE.finditer(content)]
        for idx, start in enumerate(starts):
            total_blocks += 1
            end = starts[idx + 1] if idx + 1 < len(starts) else len(content)
            body = content[start:end]
            if not any(token in body for token in SQL_ASSERTION_TOKENS):
                line_no = content[:start].count("\n") + 1
                blocks_missing_sql.append(f"{spec_path.name}:{line_no}")

    assert total_blocks == 55
    assert blocks_missing_sql == []
    assert cold_reload_consumers >= 1
