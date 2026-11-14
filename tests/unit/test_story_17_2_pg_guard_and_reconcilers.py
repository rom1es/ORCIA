"""Story 17.2 & 2026-11-14 — Unit tests for PostgreSQL Schema Guard, 503 & Setup Reconcilers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import sqlalchemy.exc as sa_exc
from fastapi.testclient import TestClient

from orcia_api.dependencies.core_and_lifespan import initialize_app_services
from orcia_api.main import create_app
from orcia_core.bootstrap._internal.sql_platform_setup_reconcilers import (
    reconcile_workspaces_on_load,
)
from orcia_core.permissions import (
    AttachedWorkspaceRef,
    OrgUnitNode,
    WorkspaceEntity,
    list_evaluator_org_unit_summaries,
)


def _build_test_client() -> TestClient:
    app = create_app()
    initialize_app_services(app)
    app.state.auth_service.evaluator.replace_org_units(())
    return TestClient(app)


def test_org_units_pg_schema_drift_raises_503_without_seeds_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outdated PostgreSQL schema (ProgrammingError) must return HTTP 503 without seeds fallback."""
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    async def _mock_drift_error(_engine: object) -> list[object]:
        orig = Exception("column o.billing_enabled does not exist")
        orig.pgcode = "42703"
        raise sa_exc.ProgrammingError("SELECT o.billing_enabled FROM org_units", {}, orig)

    monkeypatch.setattr(
        "orcia_api.routers.org_units.list_org_units_from_postgres18",
        _mock_drift_error,
    )
    client = _build_test_client()
    resp = client.get(
        "/api/v1/org-units",
        headers={"X-Orcia-Persona": "karim"},
    )
    assert resp.status_code == 503
    payload = resp.json()
    assert payload["error_code"] == "ERR_ORG_STORAGE_SCHEMA_OUTDATED"
    assert "Alembic" in payload["detail"] or "alembic" in payload["detail"].lower()
    # Ensure demo seeds are never injected on schema drift
    assert "Solution Paiement" not in resp.text


def test_org_units_pg_connectivity_loss_triggers_fallback_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Connection refusal (network down) must preserve memory evaluator fallback."""
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    async def _mock_conn_error(_engine: object) -> list[object]:
        raise ConnectionRefusedError("Connection to 127.0.0.1:5432 refused")

    monkeypatch.setattr(
        "orcia_api.routers.org_units.list_org_units_from_postgres18",
        _mock_conn_error,
    )
    client = _build_test_client()
    resp = client.get(
        "/api/v1/org-units",
        headers={"X-Orcia-Persona": "karim"},
    )
    assert resp.status_code == 200
    assert "org_units" in resp.json()


@pytest.mark.asyncio
async def test_reconcile_workspaces_merges_sql_rows_when_jsonb_not_empty() -> None:
    """Relational workspaces must be merged even when JSONB snapshot is not empty."""
    existing_ws = [
        {
            "workspaceId": "ws-rts",
            "slug": "rts",
            "name": "RTS MonCompte",
            "visibilityMode": "STANDARD",
            "lifecyclePhase": "RUN",
            "ownerOrgUnitId": "org-2",
        }
    ]
    org_units = [
        {"id": "org-1", "slug": "direction-produit", "name": "Direction Produit", "level": "BU"},
        {
            "id": "org-2",
            "slug": "moncompte",
            "name": "MonCompte",
            "level": "TEAM",
            "parentId": "org-1",
        },
    ]

    sql_ws_uuid_1 = uuid4()
    sql_ws_uuid_2 = uuid4()

    async def _fake_execute(stmt: object) -> MagicMock:
        res = MagicMock()
        res.fetchall.return_value = [
            # RTS already in JSONB snapshot (must not be duplicated)
            (
                sql_ws_uuid_1,
                "rts",
                "RTS MonCompte",
                "org-2",
                "STANDARD",
                0.0,
                '{"ui_workspace_id": "ws-rts"}',
                "MonCompte",
                "moncompte",
                "TEAM",
            ),
            # Additional workspace in SQL table (must be merged)
            (
                sql_ws_uuid_2,
                "checkout-core",
                "Checkout Core Service",
                "org-2",
                "STANDARD",
                12.5,
                '{"ui_workspace_id": "ws-checkout"}',
                "MonCompte",
                "moncompte",
                "TEAM",
            ),
        ]
        return res

    conn = AsyncMock()
    conn.execute.side_effect = _fake_execute

    reconciled = await reconcile_workspaces_on_load(conn, existing_ws, org_units)
    assert len(reconciled) == 2
    ws_ids = {w["workspaceId"] for w in reconciled}
    assert ws_ids == {"ws-rts", "ws-checkout"}
    checkout_ws = next(w for w in reconciled if w["workspaceId"] == "ws-checkout")
    assert checkout_ws["slug"] == "checkout-core"
    assert checkout_ws["ownerOrgUnitName"] == "MonCompte"


def test_list_evaluator_org_units_populates_attached_workspaces() -> None:
    """Evaluator summaries must populate attached_workspaces refs."""
    team = OrgUnitNode(id="team-1", slug="eq-checkout", name="Équipe Checkout", unit_type="TEAM")
    ws1 = WorkspaceEntity(
        id="ws-1", slug="pay-flow", name="Payment Flow", owner_org_unit_id="team-1"
    )
    ws2 = WorkspaceEntity(
        id="ws-2", slug="billing-api", name="Billing API", owner_org_unit_id="team-1"
    )

    summaries = list_evaluator_org_unit_summaries(
        [team],
        workspace_owner_ids=["team-1", "team-1"],
        workspaces=[ws1, ws2],
    )
    assert len(summaries) == 1
    item = summaries[0]
    assert item.attached_workspaces_count == 2
    assert len(item.attached_workspaces) == 2
    assert item.attached_workspaces[0] == AttachedWorkspaceRef(
        id="ws-2", slug="billing-api", name="Billing API"
    )
    assert item.attached_workspaces[1] == AttachedWorkspaceRef(
        id="ws-1", slug="pay-flow", name="Payment Flow"
    )
