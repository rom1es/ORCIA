"""Helper Guards & Snapshot Serializer for `executions_trace.py` (`<= 300 L`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.reflexive_execution import ReflexiveExecutionSnapshotResponse
from orcia_core.agents import ReflexiveSessionSnapshot
from orcia_core.agents.errors import ObserverModeReadOnlyError
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.permissions import UserIdentity

_DENIED_HEADER_VALUES: frozenset[str] = frozenset({"0", "false", "denied", "restricted", "no"})
_OBSERVER_PERSONAS: frozenset[str] = frozenset({"claire", "observer"})


def trace_id_or_current(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def resolve_has_read_source(request: Request) -> bool:
    raw = (request.headers.get("x-orcia-read-source") or "").strip().lower()
    return raw not in _DENIED_HEADER_VALUES


async def enforce_not_observer(
    request: Request,
    *,
    persona_key: str | None,
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
        auth_svc = get_auth_service(request)
        await sync_evaluator_topology_from_pg(request, auth_svc)
        ws_access = auth_svc.evaluator.resolve_workspace_access(user, workspace_id)
        if ws_access is not None and ws_access.access_mode == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(instance=str(request.url.path))
    return user


def serialize_snapshot(
    snap: ReflexiveSessionSnapshot,
    trace_id: str,
) -> ReflexiveExecutionSnapshotResponse:
    data = snap.model_dump(
        mode="json",
        exclude={
            "execution_profile",
            "has_read_source",
            "locale",
            "initial_resources",
            "requested_write_preview",
        },
    )
    return ReflexiveExecutionSnapshotResponse.model_validate({**data, "trace_id": trace_id})
