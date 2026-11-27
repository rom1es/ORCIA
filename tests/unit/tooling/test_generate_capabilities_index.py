"""Unit tests for `scripts/generate_capabilities_index.py` and archive hygiene."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
GEN_SCRIPT = REPO_ROOT / "scripts" / "generate_capabilities_index.py"
LIVE_REGISTRY = REPO_ROOT / "docs" / "product" / "capabilities.yaml"
LIVE_INDEX = REPO_ROOT / "docs" / "product" / "capabilities-index.md"
LIVE_SPRINT_STATUS = REPO_ROOT / "docs" / "implementation-artifacts" / "sprint-status.yaml"
ARCHIVE_SPRINT_STATUS = (
    REPO_ROOT
    / "docs"
    / "implementation-artifacts"
    / "archive"
    / "sprint-status-epics-01-32-archive.yaml"
)


def _load_generator() -> Any:
    if "generate_capabilities_index" in sys.modules:
        return sys.modules["generate_capabilities_index"]
    spec = importlib.util.spec_from_file_location("generate_capabilities_index", GEN_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["generate_capabilities_index"] = module
    spec.loader.exec_module(module)
    return module


def test_render_table_sorting_truncation_pipes_and_e2e_counts(tmp_path: Path) -> None:
    gen = _load_generator()
    reg_path = tmp_path / "capabilities.yaml"
    long_title = "A" * 85
    payload = {
        "capabilities": [
            {
                "id": "CAP-10",
                "title": "Feature Ten | With Pipe",
                "kind": "feature",
                "status": "live",
                "verification": "runtime",
                "uj": ["UJ-2", "UJ-5"],
                "tests": [
                    "tests/unit/test_a.py",
                    "apps/web/e2e/11-smoke.spec.ts",
                    "apps/web/e2e/21-feature.spec.ts",
                ],
            },
            {
                "id": "CAP-2",
                "title": long_title,
                "kind": "foundation",
                "status": "planned",
                "verification": "docs",
                "tests": ["tests/unit/test_foundation.py"],
            },
            {
                "id": "CAP-MISC",
                "title": "Misc Cap",
                "kind": "feature",
                "status": "live",
                "verification": "api",
                "uj": [],
            },
        ]
    }
    reg_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    rendered = gen.render_capabilities_index(reg_path)
    assert gen.GENERATED_BANNER in rendered
    assert "Total: **3** capabilities (**2** live, **1** runtime)" in rendered
    assert "Grep `CAP-xxx` in `docs/product/capabilities.yaml`" in rendered

    rows = [line for line in rendered.splitlines() if line.startswith("| `CAP-")]
    assert len(rows) == 3
    # Numeric sort puts CAP-2 before CAP-10, and non-numeric fallback last
    assert rows[0].startswith("| `CAP-2` |")
    assert rows[1].startswith("| `CAP-10` |")
    assert rows[2].startswith("| `CAP-MISC` |")

    # Truncation <= 70 chars with ellipsis & foundation empty UJs -> "—"
    assert ("A" * 69 + "…") in rows[0]
    assert "| foundation | planned | docs | — | 0 |" in rows[0]
    # Pipe sanitized to " / " and E2E spec count == 2
    assert "Feature Ten / With Pipe" in rows[1]
    assert "| feature | live | runtime | UJ-2, UJ-5 | 2 |" in rows[1]


def test_check_mode_passes_when_synced_and_fails_on_drift_or_invalid_yaml(tmp_path: Path) -> None:
    gen = _load_generator()
    reg_path = tmp_path / "capabilities.yaml"
    index_path = tmp_path / "capabilities-index.md"
    reg_path.write_text(
        yaml.safe_dump(
            {
                "capabilities": [
                    {
                        "id": "CAP-001",
                        "title": "Sample",
                        "kind": "feature",
                        "status": "live",
                        "verification": "runtime",
                        "uj": ["UJ-1"],
                        "tests": ["apps/web/e2e/14-auth.spec.ts"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    # Missing index -> exit 1
    assert gen.run(reg_path, index_path, check=True) == 1
    # Generate -> exit 0, then check -> exit 0
    assert gen.run(reg_path, index_path, check=False) == 0
    assert gen.run(reg_path, index_path, check=True) == 0
    # Drift -> exit 1
    index_path.write_text("stale\n", encoding="utf-8")
    assert gen.run(reg_path, index_path, check=True) == 1

    # Invalid YAML structure raises ValueError
    reg_path.write_text("not_a_list: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="capabilities"):
        gen.collect_rows(reg_path)

    # CLI main check on live repo
    assert gen.main(["--check"]) == 0


def test_live_capabilities_index_parity_and_size_budget() -> None:
    reg_data = yaml.safe_load(LIVE_REGISTRY.read_text(encoding="utf-8"))
    caps = reg_data["capabilities"]
    index_text = LIVE_INDEX.read_text(encoding="utf-8")
    gen = _load_generator()

    assert gen.GENERATED_BANNER in index_text
    assert LIVE_INDEX.stat().st_size <= 10_240

    rows = [line for line in index_text.splitlines() if line.startswith("| `CAP-")]
    assert len(rows) == len(caps)
    for cap in caps:
        assert f"| `{cap['id']}` |" in index_text


def test_sprint_status_archive_hygiene_and_no_duplicates() -> None:
    live = yaml.safe_load(LIVE_SPRINT_STATUS.read_text(encoding="utf-8"))
    archive = yaml.safe_load(ARCHIVE_SPRINT_STATUS.read_text(encoding="utf-8"))

    live_dev = live.get("development_status", {})
    arch_dev = archive.get("development_status", {})
    assert set(live_dev) & set(arch_dev) == set()

    # Zero non-done epics/stories in archive
    for key, val in arch_dev.items():
        if key.endswith("-retrospective"):
            assert val in ("done", "optional")
        else:
            assert val == "done"

    # Zero closed epics in live (epic-N: done with all stories done)
    epics = [k for k in live_dev if k.startswith("epic-") and not k.endswith("-retrospective")]
    for ep in epics:
        ep_num = ep.split("-", 1)[1]
        stories = [v for k, v in live_dev.items() if k.startswith(f"{ep_num}-")]
        assert not (live_dev[ep] == "done" and all(s == "done" for s in stories)), ep

    live_ai = live.get("action_items", [])
    arch_ai = archive.get("action_items", [])
    live_ids = {item["id"] for item in live_ai}
    arch_ids = {item["id"] for item in arch_ai}
    assert len(live_ids) == len(live_ai)
    assert len(arch_ids) == len(arch_ai)
    assert live_ids & arch_ids == set()
    assert all(item["status"] != "done" for item in live_ai)
    assert all(item["status"] == "done" for item in arch_ai)
