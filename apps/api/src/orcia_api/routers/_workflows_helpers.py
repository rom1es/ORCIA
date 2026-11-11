"""Internal store & RBAC helpers for `orcia_api.routers.workflows` (`Story 16.3`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers.auth import resolve_request_user
from orcia_api.routers.packs import load_declarative_pack_bundles
from orcia_connectors.bounded_workflow_v2 import BoundedWorkflowRunState
from orcia_core.agents.errors import ObserverModeReadOnlyError
from orcia_core.permissions import UserIdentity
from orcia_core.workflows import SqlWorkflowDefinitionsV2Store
from orcia_core.workflows.schemas_v2 import (
    ValueStreamMapSpec,
    WorkflowDefinitionV2,
    WorkflowLifecycleStatus,
)

_OBSERVER_PERSONAS: frozenset[str] = frozenset({"claire", "observer"})


def enforce_not_observer(
    request: Request,
    *,
    persona_key: str | None = None,
    workspace_id: str | None = None,
) -> UserIdentity:
    """Reject `READ_ONLY_OBSERVER` actors on all mutation routes with `HTTP 403`."""
    user = resolve_request_user(request, persona_key=persona_key)
    access_hdr = (request.headers.get("x-orcia-access-mode") or "").strip().upper()
    if (
        user.platform_role in ("OBSERVER", "BU_DIRECTOR")
        or (persona_key or "").strip().lower() in _OBSERVER_PERSONAS
        or access_hdr == "READ_ONLY_OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    if workspace_id:
        ws_access = get_auth_service(request).evaluator.resolve_workspace_access(user, workspace_id)
        if ws_access is not None and ws_access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=str(request.url.path))
    return user


async def load_workflows_store(
    request: Request,
    sql_store: SqlWorkflowDefinitionsV2Store,
) -> dict[str, WorkflowDefinitionV2]:
    """Merge pack-loaded workflow definitions with PostgreSQL 18 persisted overrides."""
    store: dict[str, WorkflowDefinitionV2] | None = getattr(
        request.app.state, "workflows_v2_store", None
    )
    if store is None:
        store = {}
        bundles = load_declarative_pack_bundles(request)
        for bundle in bundles.values():
            for wf in bundle.workflows:
                store[wf.id] = wf
                store[wf.slug] = wf
        request.app.state.workflows_v2_store = store

    persisted = await sql_store.list_persisted_workflows()
    for saved in persisted:
        store[saved.id] = saved
        store[saved.slug] = saved
        if saved.status == WorkflowLifecycleStatus.DRAFT:
            store[f"{saved.id}:draft"] = saved
    return store


def get_vsm_store(request: Request) -> dict[str, ValueStreamMapSpec]:
    """Return cached `ValueStreamMapSpec` dictionary seeded from declarative packs."""
    store: dict[str, ValueStreamMapSpec] | None = getattr(request.app.state, "vsm_v2_store", None)
    if store is None:
        store = {}
        bundles = load_declarative_pack_bundles(request)
        for bundle in bundles.values():
            for vsm in bundle.vsm_specs:
                store[vsm.id] = vsm
                store[vsm.slug] = vsm
        request.app.state.vsm_v2_store = store
    return store


def get_runs_store(request: Request) -> dict[str, BoundedWorkflowRunState]:
    """Return in-memory `BoundedWorkflowRunState` dictionary for active run inspection."""
    store: dict[str, BoundedWorkflowRunState] | None = getattr(
        request.app.state, "workflow_v2_runs_store", None
    )
    if store is None:
        store = {}
        request.app.state.workflow_v2_runs_store = store
    return store
