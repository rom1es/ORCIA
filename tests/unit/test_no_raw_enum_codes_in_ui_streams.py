"""Unit guardrails against raw enum/internal markers in UI streams and legacy E2E env flags."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from orcia_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_DIR_NAMES = frozenset(
    {"__pycache__", "dist", "generated", "node_modules", ".venv", "__tests__"}
)


def _iter_source_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix in suffixes:
            files.append(path)
    return sorted(files)


def test_forbids_legacy_pg_bootstrap_sync_disable_flag_in_apps_and_packages() -> None:
    offenders: list[str] = []
    for base in (REPO_ROOT / "apps", REPO_ROOT / "packages"):
        for path in _iter_source_files(base, (".py", ".ts", ".tsx", ".js")):
            content = path.read_text(encoding="utf-8", errors="ignore")
            if "ORCIA_DISABLE_PG_BOOTSTRAP_SYNC" in content:
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_forbids_e2e_seed_fixtures_flag_across_apps_packages_and_e2e_scripts() -> None:
    offenders: list[str] = []
    bases = (
        REPO_ROOT / "apps",
        REPO_ROOT / "packages",
        REPO_ROOT / "infra" / "scripts" / "e2e",
    )
    for base in bases:
        for path in _iter_source_files(base, (".py", ".ts", ".tsx", ".js")):
            content = path.read_text(encoding="utf-8", errors="ignore")
            if "ORCIA_E2E_SEED_FIXTURES" in content:
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == []


def test_forbids_layer_5_markers_in_api_response_schemas_and_sse_ui_routers() -> None:
    schemas_dir = REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "schemas"
    routers_dir = REPO_ROOT / "apps" / "api" / "src" / "orcia_api" / "routers"

    schema_offenders: list[str] = []
    for path in _iter_source_files(schemas_dir, (".py",)):
        if "[LAYER_5_" in path.read_text(encoding="utf-8"):
            schema_offenders.append(str(path.relative_to(REPO_ROOT)))

    # `assistant_llm_prompts.py` builds internal LLM system instructions only;
    # no HTTP/SSE router or UI stream serializer may emit `[LAYER_5_*]` markers.
    router_offenders: list[str] = []
    for path in _iter_source_files(routers_dir, (".py",)):
        if path.name == "assistant_llm_prompts.py":
            continue
        if "[LAYER_5_" in path.read_text(encoding="utf-8"):
            router_offenders.append(str(path.relative_to(REPO_ROOT)))

    assert schema_offenders == []
    assert router_offenders == []


def test_e2e_evict_memory_caches_returns_404_outside_e2e_and_200_in_e2e(
    monkeypatch: object,
) -> None:
    prev_env = os.environ.get("ORCIA_ENV")
    try:
        os.environ["ORCIA_ENV"] = "dev"
        app = create_app()
        client = TestClient(app, raise_server_exceptions=False)
        res_non_e2e = client.post("/api/v1/_e2e/evict-memory-caches")
        assert res_non_e2e.status_code == 404

        os.environ["ORCIA_ENV"] = "e2e"
        res_e2e = client.post("/api/v1/_e2e/evict-memory-caches")
        assert res_e2e.status_code == 200
        payload = res_e2e.json()
        assert payload["evicted"] is True
        assert isinstance(payload["cleared_caches"], list)
        assert isinstance(payload["trace_id"], str) and len(payload["trace_id"]) > 0
    finally:
        if prev_env is None:
            os.environ.pop("ORCIA_ENV", None)
        else:
            os.environ["ORCIA_ENV"] = prev_env
