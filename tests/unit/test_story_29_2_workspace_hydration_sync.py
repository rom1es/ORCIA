"""Story 29.2 — Unit tests for workspace PG18 reconciliation & GET /api/v1/workspaces phase."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_api.dependencies import get_embedding_port, require_rag_available
from orcia_api.main import create_app
from orcia_core.bootstrap._internal.sql_platform_setup_reconcilers import (
    reconcile_workspaces_on_load,
)
from orcia_core.permissions.models import OrgUnitNode, UserIdentity, WorkspaceEntity


@pytest.mark.asyncio
async def test_reconcile_workspaces_merges_relational_pg18_updates_into_snapshot() -> None:
    """Authoritative PG18 row updates name/visibility/phase even if JSONB snapshot exists."""
    ws_uuid = "0195f292-0000-7000-8000-000000000210"
    stale_snapshot: list[dict[str, Any]] = [
        {
            "workspaceId": ws_uuid,
            "slug": "team-space",
            "name": "Old Name",
            "visibilityMode": "STANDARD",
            "lifecyclePhase": "BUILD",
            "ownerOrgUnitId": "org-1",
            "suggestedWorkflows": ["wf-01"],
        }
    ]
    org_units: list[dict[str, Any]] = [
        {"id": "org-1", "slug": "team-a", "name": "Team A", "level": "TEAM"}
    ]

    async def _fake_execute(_stmt: object) -> MagicMock:
        res = MagicMock()
        res.fetchall.return_value = [
            (
                ws_uuid,
                "team-space",
                "Updated Space Name",
                "org-1",
                "CONFIDENTIAL_RESTRICTED",
                42.5,
                json.dumps(
                    {
                        "ui_workspace_id": ws_uuid,
                        "ui_visibility_mode": "CONFIDENTIAL_RESTRICTED",
                        "lifecycle_phase": "RUN",
                    }
                ),
                "Team A",
                "team-a",
                "TEAM",
            )
        ]
        return res

    conn = AsyncMock()
    conn.execute.side_effect = _fake_execute

    reconciled = await reconcile_workspaces_on_load(conn, stale_snapshot, org_units)
    assert len(reconciled) == 1
    ws = reconciled[0]
    assert ws["workspaceId"] == ws_uuid
    assert ws["name"] == "Updated Space Name"
    assert ws["visibilityMode"] == "CONFIDENTIAL_RESTRICTED"
    assert ws["lifecyclePhase"] == "RUN"
    assert ws["finopsCostUsd"] == 42.5
    assert ws["suggestedWorkflows"] == ["wf-01"]


@pytest.mark.asyncio
async def test_get_workspaces_returns_patched_lifecycle_phase_and_visibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/v1/workspaces reflects patched lifecycle_phase and visibility_mode."""
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")

    app = create_app()
    app.dependency_overrides[get_embedding_port] = FakeDeterministicEmbeddingAdapter
    app.dependency_overrides[require_rag_available] = FakeDeterministicEmbeddingAdapter

    auth_svc = app.state.auth_service
    team_id = "0195f292-0000-7000-8000-000000000051"
    ws_id = "0195f292-0000-7000-8000-000000000251"
    lead = UserIdentity(
        id="0195f292-0000-7000-8000-000000000351",
        email="lead.hyd@orcia.test",
        display_name="Lead Hyd",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id=team_id,
        roles=("TEAM_LEAD",),
    )
    auth_svc.register_user(lead)
    auth_svc.evaluator.upsert_org_unit(
        OrgUnitNode(id=team_id, slug="team-hyd", name="Team Hyd", unit_type="TEAM")
    )
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_id,
            slug="ws-hyd",
            name="Workspace Hyd",
            owner_org_unit_id=team_id,
            visibility_mode="STANDARD",
            lifecycle_phase="BUILD",
        )
    )
    token = auth_svc.jwt_manager.issue_token_pair(
        user_id=lead.id,
        email=lead.email,
        role=lead.platform_role,
        org_unit_id=team_id,
        archetype=lead.human_profile_archetype,
        auth_mode="LOCAL",
    ).access_token

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        patch_res = await client.patch(
            f"/api/v1/workspaces/{ws_id}",
            json={"visibility_mode": "CONFIDENTIAL_RESTRICTED", "lifecycle_phase": "RUN"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert patch_res.status_code == 200
        list_res = await client.get(
            "/api/v1/workspaces",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_res.status_code == 200
        items = list_res.json()["workspaces"]
        matched = next(item for item in items if item["id"] == ws_id)
        assert matched["visibility_mode"] == "CONFIDENTIAL_RESTRICTED"
        assert matched["lifecycle_phase"] == "RUN"
