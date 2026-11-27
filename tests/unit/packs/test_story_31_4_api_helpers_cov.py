"""Branch coverage tests for Story 31.4 FastAPI run-state, lock & guard helpers (<= 300 L)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from orcia_api.routers._workflows_pack_lock_helpers import (
    enforce_and_snapshot_workspace_packs,
    execute_get_run_lock_handler,
    pin_and_sync_v2_run_lock,
    sync_v2_run_status_if_pg,
)
from orcia_api.routers._workflows_run_state_helpers import (
    extract_workflow_actor_slug,
    load_or_rehydrate_run_state,
    persist_workflow_v2_run_state,
    remember_run_workspace,
)
from orcia_api.routers._workspace_packs_guards import (
    enforce_workspace_packs_access,
    refresh_workspace_catalog_consistency,
)
from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowRunState
from orcia_core.packs import WorkspacePacksService
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ScopeAccessDeniedError,
)
from orcia_core.permissions.models import UserIdentity, WorkspaceEntity
from orcia_core.workflows.schemas_v2 import WorkflowDefinitionV2

WS_UUID = "0195f000-0000-7000-8000-000000000701"
RUN_UUID = "0195f000-0000-7000-8000-000000000777"
RUN_ID = f"run-{RUN_UUID}"


def _make_req(app: Any, path: str = "/api/v1/workspaces/ws/packs") -> Request:
    return Request({"type": "http", "method": "POST", "path": path, "headers": [], "app": app})


@pytest.mark.asyncio
async def test_api_run_state_lock_and_guard_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    wf = WorkflowDefinitionV2(
        id="wf-1",
        slug="wf-1",
        title="WF1",
        version="1.0.0",
        pack_id="orcia-pack-p",
        global_system_prompt_or_ref="orcia://packs/p/agents/coder.md#v1",
    )
    assert extract_workflow_actor_slug(wf) == "coder"

    class _WsDict(dict[str, BoundedWorkflowRunState]):
        def __init__(self) -> None:
            super().__init__()
            self.workspaces: dict[str, str | None] = {}

    store = _WsDict()
    rs = BoundedWorkflowRunState(
        run_id=RUN_ID,
        workflow_id="wf-1",
        workflow_slug="wf-1",
        workflow_title="WF1",
        workflow_version="1.0.0",
        orchestration_type=wf.orchestration_type,
        execution_mode=wf.execution_mode,
        status="RUNNING",
    )
    remember_run_workspace(store, RUN_ID, WS_UUID)
    sql_runs = SimpleNamespace(upsert_run=AsyncMock(), get_run=AsyncMock(return_value=None))
    await persist_workflow_v2_run_state(sql_runs, run_state=rs, workflow=wf, workspace_id=WS_UUID)  # type: ignore[arg-type]
    sql_runs.upsert_run.assert_awaited_once()

    assert await load_or_rehydrate_run_state(store, sql_runs, RUN_ID) == (None, None)  # type: ignore[arg-type]
    store[RUN_ID] = rs
    assert (await load_or_rehydrate_run_state(store, sql_runs, RUN_ID))[1] == WS_UUID  # type: ignore[arg-type]
    store.workspaces.clear()
    sql_runs.get_run = AsyncMock(
        return_value={**rs.model_dump(mode="json"), "workspace_id": WS_UUID}
    )
    assert (await load_or_rehydrate_run_state(store, sql_runs, RUN_ID))[1] == WS_UUID  # type: ignore[arg-type]
    store.workspaces.clear()
    sql_runs.get_run = AsyncMock(return_value=None)
    assert (await load_or_rehydrate_run_state(store, sql_runs, RUN_ID))[1] is None  # type: ignore[arg-type]
    store.clear()
    sql_runs.get_run = AsyncMock(
        return_value={**rs.model_dump(mode="json"), "workspace_id": WS_UUID}
    )
    assert (await load_or_rehydrate_run_state(store, sql_runs, RUN_ID))[1] == WS_UUID  # type: ignore[arg-type]

    app = SimpleNamespace(state=SimpleNamespace(workspace_packs_service=WorkspacePacksService()))
    req = _make_req(app)
    monkeypatch.setattr(
        "orcia_api.routers._workflows_pack_lock_helpers.is_pg_runtime_active", lambda _r: False
    )
    assert await enforce_and_snapshot_workspace_packs(req, workspace_id=WS_UUID, workflow=wf) == []
    assert not await pin_and_sync_v2_run_lock(
        req, run_state=rs, workflow=wf, workspace_id=WS_UUID, actor_user_id=None, pinned_packs=[]
    )
    await sync_v2_run_status_if_pg(req, run_id=RUN_ID, status="RUNNING")
    monkeypatch.setattr(
        "orcia_api.routers._workflows_pack_lock_helpers.is_pg_runtime_active", lambda _r: True
    )
    assert await enforce_and_snapshot_workspace_packs(req, workspace_id=WS_UUID, workflow=wf) == []
    assert not await pin_and_sync_v2_run_lock(
        req, run_state=rs, workflow=wf, workspace_id=WS_UUID, actor_user_id=None, pinned_packs=[]
    )
    await sync_v2_run_status_if_pg(req, run_id=RUN_ID, status="RUNNING")

    monkeypatch.setattr(
        "orcia_api.routers._workflows_pack_lock_helpers.resolve_request_user",
        lambda _r, persona_key=None: UserIdentity(
            id="u-1",
            email="u@t",
            display_name="U",
            auth_mode="LOCAL",
            human_profile_archetype="ARCHITECT",
            platform_role="PLATFORM_ADMIN",
            primary_org_unit_id="ou-1",
        ),
    )
    with pytest.raises(HTTPException) as exc404:
        await execute_get_run_lock_handler(
            RUN_ID,
            req,
            store,
            SimpleNamespace(_session_maker=object(), get_run=AsyncMock(return_value=None)),  # type: ignore[arg-type]
        )
    assert exc404.value.status_code == 404

    ws_priv = WorkspaceEntity(
        id=WS_UUID,
        slug="priv",
        name="Priv",
        owner_org_unit_id="ou-1",
        visibility_mode="STANDARD",
        ui_visibility_mode="PRIVATE_USER",
        personal_owner_user_id="other",
    )
    ev: Any = SimpleNamespace(
        get_workspace=lambda _w: None,
        resolve_workspace_access=lambda _u, _w: SimpleNamespace(access_mode="READ_ONLY_OBSERVER"),
    )
    monkeypatch.setattr(
        "orcia_api.routers._workspace_packs_guards.resolve_request_user",
        lambda _r, persona_key=None: UserIdentity(
            id="u-1",
            email="u@t",
            display_name="U",
            auth_mode="LOCAL",
            human_profile_archetype="ARCHITECT",
            platform_role="CONTRIBUTOR",
            primary_org_unit_id="ou-1",
        ),
    )
    monkeypatch.setattr(
        "orcia_api.routers._workspace_packs_guards.get_auth_service",
        lambda _r: SimpleNamespace(evaluator=ev),
    )
    monkeypatch.setattr(
        "orcia_api.routers._workspace_packs_guards.sync_evaluator_topology_from_pg", AsyncMock()
    )
    with pytest.raises(ResourceNotFoundError):
        await enforce_workspace_packs_access(req, WS_UUID, require_write=False)
    ev.get_workspace = lambda _w: ws_priv
    with pytest.raises(ScopeAccessDeniedError):
        await enforce_workspace_packs_access(req, WS_UUID, require_write=False)
    ws_std = WorkspaceEntity(id=WS_UUID, slug="std", name="S", owner_org_unit_id="ou-1")
    ev.get_workspace = lambda _w: ws_std
    with pytest.raises(ObserverModeReadOnlyError):
        await enforce_workspace_packs_access(req, WS_UUID, require_write=True)
    monkeypatch.setattr(
        "orcia_api.routers._workspace_packs_guards.is_pg_runtime_active", lambda _r: True
    )
    monkeypatch.setattr(
        "orcia_api.routers._workspace_packs_guards.get_agents_and_skills_service",
        lambda _r: object(),
    )
    sync_spy = AsyncMock()
    monkeypatch.setattr(
        "orcia_api.routers._workspace_packs_guards.sync_from_postgres18_if_enabled", sync_spy
    )
    await refresh_workspace_catalog_consistency(req, WS_UUID)
    sync_spy.assert_awaited_once()
