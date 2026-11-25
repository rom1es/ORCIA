"""Story 29.2 (Layer 1a) — Unit tests for P1 workspace patch, PRIVATE_USER & topology sync."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from orcia_api.dependencies._topology_sync import sync_evaluator_topology_from_pg
from orcia_api.errors._registry_classes import DOMAIN_ERROR_CLASSES
from orcia_api.main import create_app
from orcia_api.routers._workspace_patch_helpers import (
    enforce_workspace_patch_access,
    execute_workspace_patch,
)
from orcia_api.schemas.org_and_workspaces import WorkspacePatchRequest
from orcia_core.kernel.errors import TransientInfraError
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    PrivateWorkspaceVisibilityLockedError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import (
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)


def _user(uid: str, role: str, ou: str = "ou-1", *, roles: tuple[str, ...] = ()) -> UserIdentity:
    return UserIdentity(
        id=uid,
        email=f"{uid}@orcia.test",
        display_name=uid,
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id=ou,
        roles=roles or (role,),
    )


@pytest.mark.asyncio
async def test_patch_helpers_observer_error_no_escalation_and_phase_preservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-1: observer gets ObserverModeReadOnlyError; contributor cannot escalate; phase kept."""
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_ENV", "local")

    app = create_app()
    svc = app.state.auth_service
    ws_id = "0195f292-0000-7000-8000-000000001301"
    svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_id,
            slug="ws-conf-p11",
            name="Conf P11",
            owner_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
            visibility_mode="CONFIDENTIAL_RESTRICTED",
            lifecycle_phase="RUN",
        )
    )
    obs_member = _user("obs-mem", "CONTRIBUTOR")
    esc_member = _user("esc-mem", "CONTRIBUTOR", roles=("CONTRIBUTOR", "TEAM_LEAD"))
    lead_member = _user("lead-mem", "TEAM_LEAD")
    svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-obs",
            workspace_id=ws_id,
            role="CONTRIBUTOR",
            access_mode="READ_ONLY_OBSERVER",
            user_id=obs_member.id,
        )
    )
    svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-esc",
            workspace_id=ws_id,
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            user_id=esc_member.id,
        )
    )
    svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="m-lead",
            workspace_id=ws_id,
            role="TEAM_LEAD",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            user_id=lead_member.id,
        )
    )
    req = Request(
        {"type": "http", "app": app, "headers": [], "path": f"/api/v1/workspaces/{ws_id}"}
    )
    payload = WorkspacePatchRequest(name="Renamed Conf")
    with pytest.raises(ObserverModeReadOnlyError):
        enforce_workspace_patch_access(req, svc, obs_member, ws_id, payload)
    with pytest.raises(ScopeAccessDeniedError):
        enforce_workspace_patch_access(req, svc, esc_member, ws_id, payload)

    patched = await execute_workspace_patch(
        req, svc=svc, user=lead_member, workspace_id=ws_id, payload=payload
    )
    assert patched.lifecycle_phase == "RUN"


@pytest.mark.asyncio
async def test_post_workspaces_private_user_and_error_registry_and_topology_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-2/P1-3/P1-5: PRIVATE_USER creation, error registry, authoritative sync prune & fail."""
    assert PrivateWorkspaceVisibilityLockedError in DOMAIN_ERROR_CLASSES

    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_ENV", "local")
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_priv = await client.post(
            "/api/v1/workspaces",
            params={"persona_key": "nadia"},
            json={
                "name": "Mon Espace Privé",
                "slug": "mon-espace-prive-292",
                "visibility_mode": "PRIVATE_USER",
                "lifecycle_phase": "BUILD",
            },
        )
        assert r_priv.status_code == 201, r_priv.text
        ws_priv_id = r_priv.json()["id"]
        assert r_priv.json()["visibility_mode"] == "PRIVATE_USER"

        # Non-owner PLATFORM_ADMIN cannot read or patch this PRIVATE_USER workspace
        r_ds = await client.get(
            f"/api/v1/workspaces/{ws_priv_id}/datasources",
            params={"persona": "karim"},
        )
        assert r_ds.status_code == 403

    # Topology sync prunes stale memberships and fails closed when authoritative_pg_only=True
    auth_svc = app.state.auth_service
    auth_svc.evaluator.upsert_membership(
        WorkspaceMembershipEntity(
            id="stale-mem",
            workspace_id="0192c4e0-0000-7000-8000-000000000203",
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            user_id="stale-user",
        )
    )
    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    req_sync = SimpleNamespace(
        state=SimpleNamespace(_orcia_topology_synced=False), url=SimpleNamespace(path="/")
    )

    class _GoodEngine:
        def connect(self) -> Any:
            class _Ctx:
                async def __aenter__(self) -> Any:
                    c = AsyncMock()

                    async def _exec(stmt: Any, _p: Any = None) -> MagicMock:
                        sql = str(stmt)
                        r = MagicMock()
                        m = MagicMock()
                        m.all.return_value = (
                            [
                                {
                                    "id": "0192c4e0-0000-7000-8000-000000000101",
                                    "slug": "root",
                                    "name": "Root",
                                    "unit_type": "ENTERPRISE",
                                    "parent_id": None,
                                    "lead_user_id": None,
                                    "lead_user_ids_jsonb": json.dumps([]),
                                    "member_user_ids_jsonb": json.dumps([]),
                                }
                            ]
                            if "FROM org_units" in sql
                            else []
                        )
                        r.mappings.return_value = m
                        return r

                    c.execute.side_effect = _exec
                    return c

                async def __aexit__(self, *_args: object) -> None:
                    return None

            return _Ctx()

    monkeypatch.setattr(
        "orcia_api.dependencies._topology_sync.get_configured_db_engine",
        lambda _r: _GoodEngine(),
    )
    await sync_evaluator_topology_from_pg(req_sync, auth_svc, force=True)  # type: ignore[arg-type]
    assert not any(m.id == "stale-mem" for m in auth_svc.evaluator.list_memberships())

    class _BrokenEngine:
        def connect(self) -> Any:
            raise RuntimeError("pg offline")

    monkeypatch.setattr(
        "orcia_api.dependencies._topology_sync.get_configured_db_engine",
        lambda _r: _BrokenEngine(),
    )
    with pytest.raises(TransientInfraError):
        await sync_evaluator_topology_from_pg(req_sync, auth_svc, force=True)  # type: ignore[arg-type]
