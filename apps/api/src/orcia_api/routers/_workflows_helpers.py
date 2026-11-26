"""Internal store & RBAC helpers for `orcia_api.routers.workflows` (`Story 16.3`, `31.2`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies import (
    get_auth_service,
    get_help_generation_and_attachment_service,
    get_trigger_dispatcher_service,
)
from orcia_api.routers._finops_scope_guards import validate_uuid
from orcia_api.routers.auth import resolve_request_user
from orcia_core.agents.errors import ObserverModeReadOnlyError
from orcia_core.kernel.events import WorkflowPublished
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import UserIdentity
from orcia_core.workflows import SqlVsmDefinitionsV2Store, SqlWorkflowDefinitionsV2Store
from orcia_core.workflows.schemas_v2 import (
    ValueStreamMapSpec,
    WorkflowDefinitionV2,
    WorkflowLifecycleStatus,
)
from orcia_kernel.errors import OrciaDomainError

_OBSERVER_PERSONAS: frozenset[str] = frozenset({"claire", "observer"})
logger = get_logger("orcia.api.workflows")


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
    _request: Request,
    sql_store: SqlWorkflowDefinitionsV2Store,
) -> dict[str, WorkflowDefinitionV2]:
    """Load `WorkflowDefinitionV2` baselines and overrides strictly from PostgreSQL 18."""
    store: dict[str, WorkflowDefinitionV2] = {}
    persisted = await sql_store.list_persisted_workflows()
    for saved in persisted:
        store[saved.id] = saved
        store[saved.slug] = saved
        if saved.status == WorkflowLifecycleStatus.DRAFT:
            store[f"{saved.id}:draft"] = saved
    return store


async def load_vsm_definitions_from_pg18(
    _request: Request,
    vsm_store: SqlVsmDefinitionsV2Store,
) -> list[ValueStreamMapSpec]:
    """Read `ValueStreamMapSpec` rows strictly from PostgreSQL 18 `vsm_definitions_v2`."""
    return await vsm_store.list_vsm()


async def get_vsm_definition_from_pg18(
    request: Request,
    vsm_store: SqlVsmDefinitionsV2Store,
    vsm_id: str,
) -> ValueStreamMapSpec | None:
    """Fetch a single `ValueStreamMapSpec` from PG18 `vsm_definitions_v2` by ID or slug."""
    found = await vsm_store.get_vsm(vsm_id)
    if found is not None:
        return found
    all_vsm = await load_vsm_definitions_from_pg18(request, vsm_store)
    for item in all_vsm:
        if item.id == vsm_id or item.slug == vsm_id:
            return item
    if vsm_id in ("vsm-sdlc-idea-to-prod", "sdlc-idea-to-prod") and all_vsm:
        return all_vsm[0]
    return None


async def publish_workflow_outbox_event(request: Request, saved: WorkflowDefinitionV2) -> None:
    """Emit `WorkflowPublished` to Outbox and dispatch trigger/help hooks."""
    raw_ws = request.headers.get("X-Orcia-Workspace-Id", "").strip()
    ws_id = (
        validate_uuid(raw_ws, "workspace_id") if raw_ws else "0192c4e0-0000-7000-8000-000000000201"
    )
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    pub_event = WorkflowPublished.create(
        workflow_id=saved.id,
        workspace_id=ws_id,
        version=saved.version,
        pack_slug=saved.pack_id or "orcia-docs",
        title=saved.title,
        trace_id=trace_id,
    )
    try:
        dispatcher = get_trigger_dispatcher_service(request)
        if dispatcher._repo is not None:
            await dispatcher._repo.publish_outbox_event(pub_event)
        else:
            dispatcher._outbox_events.append(pub_event)
        help_svc = get_help_generation_and_attachment_service(request)
        await dispatcher.handle_workflow_published(pub_event, help_service=help_svc)
    except OrciaDomainError:
        raise
    except Exception as exc:
        logger.warning(
            "workflow_published_trigger_hook_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
