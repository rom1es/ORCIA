"""Tests for UJ <-> Capability <-> Functional E2E coverage gate and script modularity."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "infra" / "scripts"
UJ_COVERAGE_PATH = SCRIPTS_DIR / "uj_e2e_coverage.py"
REGISTRY_PATH = SCRIPTS_DIR / "capabilities_registry.py"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_prd(tmp_path: Path, journey_ids: list[str]) -> Path:
    prd_path = tmp_path / "prd.md"
    lines = ["# PRD", *(f"#### {uj_id}. Parcours" for uj_id in journey_ids)]
    prd_path.write_text("\n".join(lines), encoding="utf-8")
    return prd_path


def _write_e2e_spec(repo_root: Path, filename: str, header: str = "// spec\n") -> str:
    e2e_dir = repo_root / "apps" / "web" / "e2e"
    e2e_dir.mkdir(parents=True, exist_ok=True)
    (e2e_dir / filename).write_text(header, encoding="utf-8")
    return f"apps/web/e2e/{filename}"


def _feature_cap(cap_id: str = "CAP-001", **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": cap_id,
        "title": "Capacité métier",
        "origin": "epic",
        "origin_ref": "1-1",
        "status": "live",
        "kind": "feature",
        "uj": ["UJ-1"],
        "db_tables": ["users"],
        "tests": ["tests/unit/test_sample.py"],
    }
    base.update(extra)
    return base


def _run_uj_check(
    uj_mod: Any,
    tmp_path: Path,
    prd_path: Path,
    data: dict[str, Any],
    results_path: Path | None = None,
) -> list[str]:
    result_file = results_path if results_path is not None else tmp_path / "missing-results.json"
    errors: list[str] = uj_mod.check_uj_e2e_coverage(
        data,
        prd_path=prd_path,
        e2e_dir=tmp_path / "apps" / "web" / "e2e",
        playwright_results_path=result_file,
        repo_root=tmp_path,
    )
    return errors


def test_feature_capability_without_prd_user_journey_is_blocked(tmp_path: Path) -> None:
    uj_mod = _load_module("uj_e2e_coverage", UJ_COVERAGE_PATH)
    prd_path = _write_prd(tmp_path, ["UJ-1"])
    func_spec = _write_e2e_spec(tmp_path, "01-auth.spec.ts")
    data = {
        "capabilities": [
            _feature_cap("CAP-001", uj=["UJ-1"], tests=[func_spec], verification="runtime"),
            _feature_cap("CAP-002", uj=["UJ-99"], tests=[func_spec], verification="runtime"),
        ]
    }
    errors = _run_uj_check(uj_mod, tmp_path, prd_path, data)
    assert any("CAP-002" in err and "UJ-99" in err for err in errors)


def test_prd_user_journey_without_feature_capability_is_blocked(tmp_path: Path) -> None:
    uj_mod = _load_module("uj_e2e_coverage", UJ_COVERAGE_PATH)
    prd_path = _write_prd(tmp_path, ["UJ-1", "UJ-2"])
    func_spec = _write_e2e_spec(tmp_path, "01-auth.spec.ts")
    data = {
        "capabilities": [
            _feature_cap("CAP-001", uj=["UJ-1"], tests=[func_spec], verification="runtime"),
            {
                "id": "CAP-006",
                "title": "Socle technique",
                "origin": "epic",
                "origin_ref": "1-1",
                "status": "live",
                "kind": "foundation",
                "uj": ["UJ-2"],
                "e2e_exempt_reason": "Transverse foundation",
            },
        ]
    }
    errors = _run_uj_check(uj_mod, tmp_path, prd_path, data)
    assert any("UJ-2" in err and "kind: feature" in err for err in errors)


def test_live_feature_with_smoke_only_and_no_exemption_is_blocked(tmp_path: Path) -> None:
    uj_mod = _load_module("uj_e2e_coverage", UJ_COVERAGE_PATH)
    prd_path = _write_prd(tmp_path, ["UJ-1"])
    smoke_spec = _write_e2e_spec(tmp_path, "11-screens-smoke-without-server-errors.spec.ts")
    blocked_data = {
        "capabilities": [
            _feature_cap("CAP-001", uj=["UJ-1"], tests=[smoke_spec], verification="docs")
        ]
    }
    errors = _run_uj_check(uj_mod, tmp_path, prd_path, blocked_data)
    assert len(errors) == 1
    assert "CAP-001" in errors[0]
    assert "11-screens-smoke-without-server-errors.spec.ts" in errors[0]

    exempt_data = {
        "capabilities": [
            _feature_cap(
                "CAP-001",
                uj=["UJ-1"],
                tests=[smoke_spec],
                verification="docs",
                e2e_backlog_story="21-5",
            )
        ]
    }
    assert _run_uj_check(uj_mod, tmp_path, prd_path, exempt_data) == []


def test_runtime_verification_requires_passing_functional_e2e_spec(tmp_path: Path) -> None:
    uj_mod = _load_module("uj_e2e_coverage", UJ_COVERAGE_PATH)
    prd_path = _write_prd(tmp_path, ["UJ-1"])
    smoke_spec = _write_e2e_spec(tmp_path, "11-screens-smoke-without-server-errors.spec.ts")
    func_spec = _write_e2e_spec(tmp_path, "02-workflow.spec.ts")

    smoke_runtime = {"capabilities": [_feature_cap(tests=[smoke_spec], verification="runtime")]}
    smoke_errors = _run_uj_check(uj_mod, tmp_path, prd_path, smoke_runtime)
    assert any("`verification: runtime` interdit" in err for err in smoke_errors)

    backlog_runtime = {
        "capabilities": [
            _feature_cap(tests=[func_spec], verification="runtime", e2e_backlog_story="21-6")
        ]
    }
    backlog_errors = _run_uj_check(uj_mod, tmp_path, prd_path, backlog_runtime)
    assert any("incompatible avec" in err for err in backlog_errors)

    results_path = tmp_path / "playwright-results.json"
    failed_suite = {
        "suites": [
            {
                "file": "02-workflow.spec.ts",
                "specs": [
                    {
                        "ok": False,
                        "tests": [{"outcome": "unexpected", "results": [{"status": "failed"}]}],
                    }
                ],
            }
        ]
    }
    results_path.write_text(json.dumps(failed_suite), encoding="utf-8")
    runtime_data = {"capabilities": [_feature_cap(tests=[func_spec], verification="runtime")]}
    fail_errors = _run_uj_check(uj_mod, tmp_path, prd_path, runtime_data, results_path)
    assert any("playwright-results.json" in err and func_spec in err for err in fail_errors)

    passing_suite = {
        "suites": [
            {
                "file": "02-workflow.spec.ts",
                "specs": [
                    {
                        "ok": True,
                        "tests": [{"outcome": "expected", "results": [{"status": "passed"}]}],
                    }
                ],
            }
        ]
    }
    results_path.write_text(json.dumps(passing_suite), encoding="utf-8")
    assert _run_uj_check(uj_mod, tmp_path, prd_path, runtime_data, results_path) == []


def test_registry_check_passes_on_real_repository_and_blocks_smoke_only_live_feature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reg = _load_module("capabilities_registry", REGISTRY_PATH)
    assert reg.run_registry_check() == []

    monkeypatch.setattr(
        reg,
        "load_registry",
        lambda: {
            "capabilities": [
                _feature_cap(
                    "CAP-001",
                    uj=["UJ-1"],
                    tests=["apps/web/e2e/11-screens-smoke-without-server-errors.spec.ts"],
                    verification="docs",
                )
            ]
        },
    )
    monkeypatch.setattr(reg, "discover_routes", lambda: [])
    monkeypatch.setattr(reg, "discover_routers", lambda: [])
    errors = reg.run_registry_check()
    assert any("CAP-001" in err and "11-screens-smoke" in err for err in errors)
    assert any("sans capacité `kind: feature` rattachée" in err for err in errors)


def test_e2e_spec_header_parsing_and_enriched_capability_test_stats(tmp_path: Path) -> None:
    uj_mod = _load_module("uj_e2e_coverage", UJ_COVERAGE_PATH)
    reg = _load_module("capabilities_registry", REGISTRY_PATH)
    prd_path = _write_prd(tmp_path, ["UJ-1", "UJ-2", "UJ-3"])
    _write_e2e_spec(tmp_path, "01-auth.spec.ts", "/** @uj UJ-1, UJ-2 | @cap CAP-001 */\n")
    _write_e2e_spec(tmp_path, "02-ops.spec.ts", "/**\n * @uj UJ-3\n * @cap CAP-002\n */\n")
    _write_e2e_spec(
        tmp_path,
        "11-screens-smoke-without-server-errors.spec.ts",
        "/** @uj UJ-1 | @cap CAP-003 */\n",
    )
    e2e_dir = tmp_path / "apps" / "web" / "e2e"

    headers = uj_mod.parse_e2e_spec_headers(e2e_dir)
    assert headers["apps/web/e2e/01-auth.spec.ts"] == {
        "ujs": ["UJ-1", "UJ-2"],
        "caps": ["CAP-001"],
        "functional": True,
    }
    assert headers["apps/web/e2e/02-ops.spec.ts"]["ujs"] == ["UJ-3"]
    smoke_key = "apps/web/e2e/11-screens-smoke-without-server-errors.spec.ts"
    assert headers[smoke_key]["functional"] is False

    data = {
        "capabilities": [
            _feature_cap("CAP-001", uj=["UJ-1", "UJ-2"], tests=[]),
            _feature_cap("CAP-002", uj=["UJ-3"], tests=[], e2e_backlog_story="21-5"),
            _feature_cap("CAP-003", uj=["UJ-1"], tests=[smoke_key], e2e_backlog_story="21-6"),
            _feature_cap("CAP-004", uj=["UJ-1"], tests=[]),
        ]
    }
    stats = reg.capability_test_stats(data, include_uj_e2e=True, e2e_dir=e2e_dir, prd_path=prd_path)
    assert stats["live"] == 4
    assert stats["with_tests"] == 3
    assert stats["without_tests"] == ["CAP-004"]
    assert stats["userJourneysCount"] == 3
    assert stats["coveredUserJourneysCount"] == 3
    assert stats["liveFeaturesCount"] == 4
    assert stats["e2eCoveredCapabilitiesCount"] == 2
    assert stats["e2eBacklogExemptCapabilitiesCount"] == 1
    assert stats["e2eHeaderTaggedSpecsCount"] == 3


def test_site_catalog_and_registry_modules_stay_below_line_limit() -> None:
    modules = (
        "sync_site_catalog.py",
        "_site_repo_parsers.py",
        "_site_html_renderer.py",
        "_site_html_styles.py",
        "_site_html_template.py",
        "uj_e2e_coverage.py",
        "capabilities_registry.py",
    )
    for filename in modules:
        path = SCRIPTS_DIR / filename
        assert path.is_file(), f"Missing module {path}"
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count < 350, f"{filename} has {line_count} lines (limit < 350)"
