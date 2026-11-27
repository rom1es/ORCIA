"""Unit tests for `agent_check` output digest formatting and static impact selection."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.agent_check_lib.impact import select_impacted_targets
from scripts.agent_check_lib.output import (
    FailureDigest,
    format_failure_digest,
    format_pass_line,
    format_skip_line,
    parse_pytest_junitxml,
    parse_vitest_json,
)


def test_pass_and_skip_single_line_formatting() -> None:
    assert format_pass_line("static", "5 gates", 1.234) == "PASS [static]: 5 gates in 1.23s"
    sample_hash = "abc123" + "def456" + "7890"
    assert format_skip_line("static", sample_hash) == "SKIP [static]: receipt abc123def456"


def test_parse_pytest_junitxml_lists_all_ids_and_caps_tracebacks_at_three(
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "junit.xml"
    cases = []
    for i in range(5):
        cases.append(
            f'<testcase classname="tests.unit.test_sample" name="test_case_{i}">'
            f'<failure message="assert {i} == 99">Traceback line 1\nE assert {i} == 99</failure>'
            "</testcase>"
        )
    xml_path.write_text(
        f'<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite>{"".join(cases)}'
        "</testsuite></testsuites>",
        encoding="utf-8",
    )

    failing_ids, tracebacks = parse_pytest_junitxml(xml_path)
    assert len(failing_ids) == 5
    assert failing_ids[0] == "tests.unit.test_sample::test_case_0"
    assert failing_ids[4] == "tests.unit.test_sample::test_case_4"
    assert len(tracebacks) == 3

    rendered = format_failure_digest(
        FailureDigest(
            stage="impact",
            summary="5 failed",
            elapsed_s=2.5,
            failing_ids=failing_ids,
            tracebacks=tracebacks,
            log_path=Path(".agent_check/logs/impact-123.log"),
        )
    )
    lines = rendered.splitlines()
    assert lines[0] == "FAIL [impact]: 5 failed in 2.50s"
    for fid in failing_ids:
        assert any(fid in ln for ln in lines)
    assert rendered.count("--- Traceback") == 3
    assert "LOG: .agent_check/logs/impact-123.log" in rendered


def test_parse_vitest_json_lists_all_failures_and_caps_tracebacks(tmp_path: Path) -> None:
    json_path = tmp_path / "vitest.json"
    payload = {
        "testResults": [
            {
                "name": "/repo/apps/web/src/__tests__/a.test.tsx",
                "assertionResults": [
                    {
                        "fullName": f"suite > case {i}",
                        "status": "failed",
                        "failureMessages": [f"Error: boom {i}\n  at line {i}"],
                    }
                    for i in range(4)
                ],
            }
        ]
    }
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    failing_ids, tracebacks = parse_vitest_json(json_path)
    assert failing_ids == [
        "suite > case 0",
        "suite > case 1",
        "suite > case 2",
        "suite > case 3",
    ]
    assert len(tracebacks) == 3


def test_impact_selection_import_graph_router_prefix_and_vitest(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "packages" / "core" / "src" / "my_core").mkdir(parents=True)
    (repo / "apps" / "api" / "src" / "my_api" / "routers").mkdir(parents=True)
    (repo / "tests" / "unit").mkdir(parents=True)
    (repo / "apps" / "web" / "src" / "features" / "items").mkdir(parents=True)

    (repo / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["packages/core/src", "apps/api/src", "."]\n',
        encoding="utf-8",
    )

    (repo / "packages" / "core" / "src" / "my_core" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (repo / "packages" / "core" / "src" / "my_core" / "leaf.py").write_text(
        "def helper() -> int:\n    return 1\n", encoding="utf-8"
    )
    (repo / "packages" / "core" / "src" / "my_core" / "mid.py").write_text(
        "from my_core.leaf import helper\n", encoding="utf-8"
    )
    (repo / "apps" / "api" / "src" / "my_api" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "apps" / "api" / "src" / "my_api" / "routers" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (repo / "apps" / "api" / "src" / "my_api" / "routers" / "items.py").write_text(
        'from fastapi import APIRouter\nrouter = APIRouter(prefix="/api/v1/items")\n'
        '@router.get("/list")\ndef list_items(): pass\n',
        encoding="utf-8",
    )

    (repo / "tests" / "unit" / "test_mid.py").write_text(
        "from my_core.mid import helper\ndef test_m(): assert helper() == 1\n",
        encoding="utf-8",
    )
    (repo / "tests" / "unit" / "test_items_http.py").write_text(
        'def test_items_route(client):\n    client.get("/api/v1/items/list")\n',
        encoding="utf-8",
    )
    (repo / "tests" / "unit" / "test_unrelated.py").write_text(
        "def test_other(): assert True\n", encoding="utf-8"
    )
    (repo / "tests" / "unit" / "test_capabilities_registry.py").write_text(
        "def test_cap(): assert True\n", encoding="utf-8"
    )

    web_file = repo / "apps" / "web" / "src" / "features" / "items" / "ItemsPanel.tsx"
    web_file.write_text("export const ItemsPanel = () => null;\n", encoding="utf-8")

    plan = select_impacted_targets(
        repo,
        touched_files=[
            "packages/core/src/my_core/leaf.py",
            "apps/api/src/my_api/routers/items.py",
            "apps/web/src/features/items/ItemsPanel.tsx",
        ],
        always_run_audits=("tests/unit/test_capabilities_registry.py",),
    )

    assert "tests/unit/test_mid.py" in plan.python_tests
    assert "tests/unit/test_items_http.py" in plan.python_tests
    assert "tests/unit/test_capabilities_registry.py" in plan.python_tests
    assert "tests/unit/test_unrelated.py" not in plan.python_tests
    assert "apps/web" in plan.vitest_files_by_pkg
    assert "src/features/items/ItemsPanel.tsx" in plan.vitest_files_by_pkg["apps/web"]
    assert any(r.startswith("reverse_import:") for r in plan.reasons["tests/unit/test_mid.py"])
    assert any(
        r.startswith("router_prefix:") for r in plan.reasons["tests/unit/test_items_http.py"]
    )
    assert "always_run_audit" in plan.reasons["tests/unit/test_capabilities_registry.py"]
