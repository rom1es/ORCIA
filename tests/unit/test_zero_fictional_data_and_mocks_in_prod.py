"""Production Zero-Mock & Zero-Fictional-Data Non-Regression Suite (`AD-10`, `AD-17`, `AD-19`).

Verifies that:
1. `TwoSpeedFederatedSearchService()` starts with `0` fictional candidates and returns `0` hits
   by default in production (`GET /api/v1/search` returns `[]` on a blank Day-0 instance).
2. `create_app()` / `initialize_app_services()` wires `LiteLLMAdapter` (and NOT
   `DeterministicCassetteLLM`) as the default `app.state.llm_gateway` when
   `ORCIA_USE_CASSETTE_LLM` is not set.
3. `infra/scripts/maintenance/04_backfill_system_bootstrap.py` (`pnpm db:seed`) contains `0`
   fictional users (`karim.admin@orcia.io`, `marc.lead@orcia.io`, `nadia.dev@orcia.io`),
   `0` fictional org units/workspaces, and executes `0` user/org/workspace inserts.
4. `apps/web/src/components/ShellContainer.tsx` has no hardcoded `DEFAULT_SEARCH_HITS`, and
   the unused `apps/web/src/components/ontologyFixtures.ts` file is absent.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.bootstrap import LiteLLMAdapter
from orcia_core.rag import TwoSpeedFederatedSearchService
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_04() -> Any:
    script_path = (
        REPO_ROOT / "infra" / "scripts" / "maintenance" / "04_backfill_system_bootstrap.py"
    )
    spec = importlib.util.spec_from_file_location("zero_mock_script_04", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_two_speed_federated_search_service_has_zero_fictional_results_by_default() -> None:
    """Verify `TwoSpeedFederatedSearchService()` has 0 pre-populated candidates by default."""
    svc = TwoSpeedFederatedSearchService()
    report = svc.execute_search(
        query="architecture paiement sepa",
        scope="ALL_WORKSPACES",
        active_workspace_id="ws-claims-alpha",
        active_screen_route="/cockpit",
        user_role="PLATFORM_ADMIN",
        include_speed2=True,
        force_semantic=True,
    )
    assert report.hits == ()

    app = create_app()
    client = TestClient(app)
    resp = client.get(
        "/api/v1/search",
        params={
            "q": "architecture",
            "scope": "ALL_WORKSPACES",
            "include_speed2": "true",
            "force_semantic": "true",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["hits"] == []


def test_create_app_wires_litellm_adapter_by_default_outside_test_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `create_app()` wires `LiteLLMAdapter` unless `ORCIA_USE_CASSETTE_LLM` is set."""
    monkeypatch.delenv("ORCIA_USE_CASSETTE_LLM", raising=False)
    app = create_app()
    assert isinstance(app.state.llm_gateway, LiteLLMAdapter)
    assert not isinstance(app.state.llm_gateway, DeterministicCassetteLLM)

    # Explicit test flag switches to DeterministicCassetteLLM
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app_test_flag = create_app()
    assert isinstance(app_test_flag.state.llm_gateway, DeterministicCassetteLLM)


async def test_04_backfill_system_bootstrap_has_zero_fictional_users() -> None:
    """Verify `04_backfill_system_bootstrap.py` defines and inserts 0 fictional users."""
    script_path = (
        REPO_ROOT / "infra" / "scripts" / "maintenance" / "04_backfill_system_bootstrap.py"
    )
    source = script_path.read_text(encoding="utf-8")

    for forbidden in (
        "_REFERENCE_USERS",
        "karim.admin@orcia.io",
        "marc.lead@orcia.io",
        "nadia.dev@orcia.io",
        "INSERT INTO users",
        "DEFAULT_ORG_UNIT_SEEDS",
        "DEFAULT_WORKSPACE_SEEDS",
        "DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS",
        "DEFAULT_USER_ONBOARDING_STATE_SEEDS",
    ):
        assert forbidden not in source, f"Forbidden fictional seed {forbidden!r} in script 04"

    mod04 = _load_script_04()
    assert not hasattr(mod04, "_REFERENCE_USERS")

    executed_sql_statements: list[str] = []
    mock_conn = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar.return_value = 0

    async def _capture_execute(stmt: Any, params: Any = None) -> Any:
        executed_sql_statements.append(str(stmt))
        return mock_res

    mock_conn.execute.side_effect = _capture_execute
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_ctx

    report = await mod04.backfill_system_bootstrap(mock_engine, apply_changes=False)
    assert report.dry_run is True
    assert report.committed is False
    assert all("INSERT INTO users" not in sql for sql in executed_sql_statements)
    assert all("INSERT INTO org_units" not in sql for sql in executed_sql_statements)
    assert all("INSERT INTO workspaces" not in sql for sql in executed_sql_statements)


def test_web_shell_container_and_components_have_zero_fictional_fixtures() -> None:
    """Verify `ShellContainer.tsx` has no `DEFAULT_SEARCH_HITS` and no `ontologyFixtures.ts`."""
    shell_path = REPO_ROOT / "apps" / "web" / "src" / "components" / "ShellContainer.tsx"
    shell_source = shell_path.read_text(encoding="utf-8")
    assert "DEFAULT_SEARCH_HITS" not in shell_source

    ontology_fixtures_path = (
        REPO_ROOT / "apps" / "web" / "src" / "components" / "ontologyFixtures.ts"
    )
    assert not ontology_fixtures_path.exists()
