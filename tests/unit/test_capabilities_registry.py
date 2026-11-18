"""Tests for `infra/scripts/capabilities_registry.py` (CAP-ACT-1)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infra" / "scripts" / "capabilities_registry.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("capabilities_registry", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cap(cap_id: str = "CAP-001", **extra: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": cap_id,
        "title": "t",
        "origin": "epic",
        "origin_ref": "1-1",
        "status": "live",
        "kind": "feature",
        "uj": ["UJ-1"],
        "db_tables": ["users"],
    }
    base.update(extra)
    return base


def test_real_registry_is_valid_and_covers_all_surfaces() -> None:
    mod = _load()
    assert mod.run_registry_check() == []


def test_duplicate_ids_and_bad_enums_are_reported() -> None:
    mod = _load()
    data = {"capabilities": [_cap(), _cap(), _cap("CAP-002", status="weird", origin="x")]}
    errors = mod.validate_registry(data)
    assert any("dupliqué" in e for e in errors)
    assert any("status" in e for e in errors)
    assert any("origin" in e for e in errors)


def test_missing_required_field_and_undeclared_proposed_fr() -> None:
    mod = _load()
    broken = _cap()
    del broken["title"]
    data = {
        "proposed_fr": {"FR-31": "x"},
        "capabilities": [broken, _cap("CAP-002", fr=["FR-99"])],
    }
    errors = mod.validate_registry(data, max_fr=36)
    assert any("title" in e for e in errors)
    assert any("FR-99" in e for e in errors)


def test_uncovered_surface_is_reported_and_exemption_works() -> None:
    mod = _load()
    data = {
        "capabilities": [_cap(surfaces={"route": "/inbox", "api": "inbox_and_leases.py"})],
        "coverage_exemptions": [{"surface": "/login", "reason": "r"}],
    }
    errors = mod.check_coverage(
        data, routes=["/inbox", "/login", "/new"], routers=["inbox_and_leases", "ghost"]
    )
    joined = "\n".join(errors)
    assert "/new" in joined and "ghost" in joined
    assert "/login" not in joined and "/inbox" not in joined


def test_prd_defines_fr_up_to_36() -> None:
    assert _load().prd_max_fr() >= 36


def test_exemption_without_reason_is_rejected() -> None:
    mod = _load()
    data = {"capabilities": [_cap()], "coverage_exemptions": [{"surface": "/x"}]}
    assert any("reason" in e for e in mod.validate_registry(data))


def test_declared_test_paths_must_exist(tmp_path: Path) -> None:
    mod = _load()
    (tmp_path / "ok.spec.ts").write_text("//", encoding="utf-8")
    data = {
        "capabilities": [
            _cap(tests=["ok.spec.ts"]),
            _cap("CAP-002", tests=["absent.spec.ts"]),
        ]
    }
    errors = mod.validate_registry(data, max_fr=36, repo_root=tmp_path)
    assert any("absent.spec.ts" in e for e in errors)
    assert not any("ok.spec.ts" in e for e in errors)


def test_runtime_verification_requires_a_test_reference() -> None:
    mod = _load()
    data = {"capabilities": [_cap(verification="runtime")]}
    assert any("runtime" in e for e in mod.validate_registry(data, max_fr=36))


def test_capability_test_stats_counts_live_capabilities_without_tests() -> None:
    mod = _load()
    data = {
        "capabilities": [
            _cap(tests=["a"]),
            _cap("CAP-002"),
            _cap("CAP-003", status="planned"),
        ]
    }
    stats = mod.capability_test_stats(data)
    assert stats == {"live": 2, "with_tests": 1, "without_tests": ["CAP-002"]}


def test_real_registry_classifies_features_and_foundations_without_errors() -> None:
    mod = _load()
    data = mod.load_registry()
    errors = mod.validate_registry(data)
    assert errors == []
    capabilities = data["capabilities"]
    foundations = [c for c in capabilities if c.get("kind") == "foundation"]
    features = [c for c in capabilities if c.get("kind") == "feature"]
    assert len(capabilities) == 65
    assert len(foundations) == 3
    assert len(features) == 62


def test_missing_or_invalid_capability_kind_is_rejected() -> None:
    mod = _load()
    missing_kind = _cap("CAP-001")
    del missing_kind["kind"]
    invalid_kind = _cap("CAP-002", kind="unknown")
    errors = mod.validate_registry({"capabilities": [missing_kind, invalid_kind]}, max_fr=36)
    assert any(e.startswith("CAP-001:") and "kind" in e for e in errors)
    assert any(e.startswith("CAP-002:") and "kind" in e for e in errors)


def test_foundation_capability_requires_non_empty_exemption_reason() -> None:
    mod = _load()
    missing_reason = _cap("CAP-001", kind="foundation")
    blank_reason = _cap("CAP-002", kind="foundation", e2e_exempt_reason="   ")
    valid_foundation = _cap("CAP-003", kind="foundation", e2e_exempt_reason="Transverse guard")
    errors = mod.validate_registry(
        {"capabilities": [missing_reason, blank_reason, valid_foundation]},
        max_fr=36,
    )
    assert any(e.startswith("CAP-001:") and "e2e_exempt_reason" in e for e in errors)
    assert any(e.startswith("CAP-002:") and "e2e_exempt_reason" in e for e in errors)
    assert not any(e.startswith("CAP-003:") for e in errors)


def test_feature_capability_requires_non_empty_valid_journeys() -> None:
    mod = _load()
    missing_journeys = _cap("CAP-001")
    del missing_journeys["uj"]
    empty_journeys = _cap("CAP-002", uj=[])
    bad_pattern = _cap("CAP-003", uj=["UJ-0", "BAD-1", "UJ-100"])
    errors = mod.validate_registry(
        {"capabilities": [missing_journeys, empty_journeys, bad_pattern]},
        max_fr=36,
    )
    assert any(e.startswith("CAP-001:") and "uj" in e for e in errors)
    assert any(e.startswith("CAP-002:") and "uj" in e for e in errors)
    assert any(e.startswith("CAP-003:") and "UJ-0" in e for e in errors)
    assert any(e.startswith("CAP-003:") and "BAD-1" in e for e in errors)
    assert any(e.startswith("CAP-003:") and "UJ-100" in e for e in errors)


def test_feature_capability_requires_db_tables_or_read_only_surface() -> None:
    mod = _load()
    missing_tables = _cap("CAP-001")
    del missing_tables["db_tables"]
    empty_tables = _cap("CAP-002", db_tables=[])
    read_only = _cap("CAP-003", read_only_surface=True)
    del read_only["db_tables"]
    errors = mod.validate_registry(
        {"capabilities": [missing_tables, empty_tables, read_only]},
        max_fr=36,
    )
    assert any(e.startswith("CAP-001:") and "db_tables" in e for e in errors)
    assert any(e.startswith("CAP-002:") and "db_tables" in e for e in errors)
    assert not any(e.startswith("CAP-003:") for e in errors)
