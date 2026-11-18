"""Story 17.4 & 18.1 — Workspace RAG & Multi-Nature Datasources Router.

Exposes:
- `GET    /api/v1/workspaces/{workspace_id}/datasources`
- `POST   /api/v1/workspaces/{workspace_id}/datasources`
- `PATCH  /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}`
- `DELETE /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}`
- `POST   /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}/sync`
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_or_create_shared_db_engine
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.enterprise_connectors import (
    CreateWorkspaceDatasourceRequest,
    TriggerWorkspaceDatasourceSyncResponse,
    UpdateWorkspaceDatasourceRequest,
    WorkspaceDatasourceDeleteResponse,
    WorkspaceDatasourceItemResponse,
    WorkspaceDatasourcesListResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.bootstrap import (
    create_workspace_datasource_on_postgres18,
    delete_workspace_datasource_on_postgres18,
    list_workspace_datasources_from_postgres18,
    trigger_workspace_datasource_sync_on_postgres18,
    update_workspace_datasource_on_postgres18,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions.errors import (
    CodegraphWorkspaceLeadRequiredError,
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
)
from orcia_core.permissions.workspace_sources_governance import (
    WorkspaceDatasourceRecord,
    can_manage_workspace_codegraph,
)

logger = get_logger("orcia.api.workspace_datasources")

WORKSPACE_DATASOURCES_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["workspace-datasources"],
    responses=WORKSPACE_DATASOURCES_PROBLEM_RESPONSES,
)


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _pg_enabled() -> bool:
    from orcia_api.dependencies._core_providers import is_pg_runtime_active

    return is_pg_runtime_active()


def _enforce_mutation_access(request: Request, persona_key: str | None = None) -> Any:
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or observer_hdr in ("1", "true", "yes")
        or active_hat == "OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))

    effective_persona = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    user = resolve_request_user(request, persona_key=effective_persona)
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    return user


def _enforce_codegraph_access(request: Request, user: Any) -> None:
    candidate_roles: set[str] = set()
    if getattr(user, "platform_role", None):
        candidate_roles.add(str(user.platform_role).upper())
    if hat := request.headers.get("x-orcia-active-hat"):
        candidate_roles.add(hat.strip().upper())
    if role_hdr := request.headers.get("x-orcia-role"):
        candidate_roles.add(role_hdr.strip().upper())

    if not can_manage_workspace_codegraph(candidate_roles):
        raise CodegraphWorkspaceLeadRequiredError(instance=str(request.url.path))


def _serialize_datasource(rec: WorkspaceDatasourceRecord) -> WorkspaceDatasourceItemResponse:
    return WorkspaceDatasourceItemResponse(
        id=rec.id,
        workspace_id=rec.workspace_id,
        alias=rec.alias,
        scheme=rec.scheme,
        uri=rec.uri,
        connector_id=rec.connector_id,
        sync_identity_mode=rec.sync_identity_mode,
        service_account_id=rec.service_account_id,
        referent_user_id=rec.referent_user_id,
        sync_status=rec.sync_status,
        sync_status_reason=rec.sync_status_reason,
        created_at_iso=rec.created_at_iso,
        source_nature=rec.source_nature,
        sync_mode=rec.sync_mode,
        target_scope=rec.target_scope,
        target_ref=rec.target_ref,
        last_sync_at_iso=rec.last_sync_at_iso,
        last_probe_at_iso=rec.last_probe_at_iso,
        fingerprint_hash=rec.fingerprint_hash,
        freshness_status=rec.freshness_status,
        codegraph_enabled=rec.codegraph_enabled,
        codegraph_auth_mode=rec.codegraph_auth_mode,
        codegraph_owner_user_id=rec.codegraph_owner_user_id,
        codegraph_status=rec.codegraph_status,
        codegraph_status_reason=rec.codegraph_status_reason,
        codegraph_last_indexed_at_iso=rec.codegraph_last_indexed_at_iso,
        codegraph_head_sha=rec.codegraph_head_sha,
    )


@router.get(
    "/{workspace_id}/datasources",
    response_model=WorkspaceDatasourcesListResponse,
    summary="List datasources attached to a workspace with evaluated sync health",
)
async def list_workspace_datasources(
    request: Request,
    workspace_id: Annotated[str, Path()],
) -> WorkspaceDatasourcesListResponse:
    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        datasources = await list_workspace_datasources_from_postgres18(
            engine, workspace_id=workspace_id
        )
    else:
        datasources = []

    return WorkspaceDatasourcesListResponse(
        items=[_serialize_datasource(d) for d in datasources],
        trace_id=_trace(request),
    )


@router.post(
    "/{workspace_id}/datasources",
    response_model=WorkspaceDatasourceItemResponse,
    status_code=201,
    summary="Attach a new datasource to a workspace with multi-nature and codegraph options",
)
async def create_workspace_datasource(
    request: Request,
    workspace_id: Annotated[str, Path()],
    payload: CreateWorkspaceDatasourceRequest,
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> WorkspaceDatasourceItemResponse:
    user = _enforce_mutation_access(request, persona_key=persona)

    if payload.codegraph_enabled:
        _enforce_codegraph_access(request, user)

    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        rec = await create_workspace_datasource_on_postgres18(
            engine,
            workspace_id=workspace_id,
            alias=payload.alias,
            scheme=payload.scheme,
            uri=payload.uri,
            connector_id=payload.connector_id,
            sync_identity_mode=payload.sync_identity_mode,
            service_account_id=payload.service_account_id,
            referent_user_id=payload.referent_user_id,
            source_nature=payload.source_nature,
            sync_mode=payload.sync_mode,
            target_scope=payload.target_scope,
            target_ref=payload.target_ref,
            codegraph_enabled=payload.codegraph_enabled,
            codegraph_auth_mode=payload.codegraph_auth_mode,
            codegraph_owner_user_id=payload.codegraph_owner_user_id,
            instance=str(request.url.path),
        )
    else:
        raise ResourceNotFoundError(
            detail_override="In-memory mode does not support standalone datasource creation.",
            instance=str(request.url.path),
        )

    return _serialize_datasource(rec)


@router.patch(
    "/{workspace_id}/datasources/{datasource_id}",
    response_model=WorkspaceDatasourceItemResponse,
    summary="Update datasource settings, sync mode or codegraph options",
)
async def update_workspace_datasource(
    request: Request,
    workspace_id: Annotated[str, Path()],
    datasource_id: Annotated[str, Path()],
    payload: UpdateWorkspaceDatasourceRequest,
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> WorkspaceDatasourceItemResponse:
    user = _enforce_mutation_access(request, persona_key=persona)

    if (
        payload.codegraph_enabled is not None
        or payload.codegraph_auth_mode is not None
        or payload.codegraph_owner_user_id is not None
    ):
        _enforce_codegraph_access(request, user)

    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        rec = await update_workspace_datasource_on_postgres18(
            engine,
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            alias=payload.alias,
            uri=payload.uri,
            connector_id=payload.connector_id,
            sync_identity_mode=payload.sync_identity_mode,
            service_account_id=payload.service_account_id,
            referent_user_id=payload.referent_user_id,
            source_nature=payload.source_nature,
            sync_mode=payload.sync_mode,
            target_scope=payload.target_scope,
            target_ref=payload.target_ref,
            codegraph_enabled=payload.codegraph_enabled,
            codegraph_auth_mode=payload.codegraph_auth_mode,
            codegraph_owner_user_id=payload.codegraph_owner_user_id,
            instance=str(request.url.path),
        )
    else:
        raise ResourceNotFoundError(instance=str(request.url.path))

    return _serialize_datasource(rec)


@router.delete(
    "/{workspace_id}/datasources/{datasource_id}",
    response_model=WorkspaceDatasourceDeleteResponse,
    summary="Delete a datasource from a workspace",
)
async def delete_workspace_datasource(
    request: Request,
    workspace_id: Annotated[str, Path()],
    datasource_id: Annotated[str, Path()],
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> WorkspaceDatasourceDeleteResponse:
    _enforce_mutation_access(request, persona_key=persona)

    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        await delete_workspace_datasource_on_postgres18(
            engine,
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            instance=str(request.url.path),
        )
    else:
        raise ResourceNotFoundError(instance=str(request.url.path))

    return WorkspaceDatasourceDeleteResponse(
        deleted=True,
        workspace_id=workspace_id,
        datasource_id=datasource_id,
        trace_id=_trace(request),
    )


@router.post(
    "/{workspace_id}/datasources/{datasource_id}/sync",
    response_model=TriggerWorkspaceDatasourceSyncResponse,
    summary="Trigger manual synchronization of a datasource",
)
async def trigger_workspace_datasource_sync(
    request: Request,
    workspace_id: Annotated[str, Path()],
    datasource_id: Annotated[str, Path()],
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> TriggerWorkspaceDatasourceSyncResponse:
    _enforce_mutation_access(request, persona_key=persona)

    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        rec = await trigger_workspace_datasource_sync_on_postgres18(
            engine,
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            instance=str(request.url.path),
        )
    else:
        raise ResourceNotFoundError(instance=str(request.url.path))

    return TriggerWorkspaceDatasourceSyncResponse(
        datasource=_serialize_datasource(rec),
        trace_id=_trace(request),
    )
