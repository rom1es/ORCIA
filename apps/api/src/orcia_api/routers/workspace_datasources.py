"""Story 17.4, 18.1 & 25.5 — Workspace RAG & Multi-Nature Datasources Router."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import get_or_create_shared_db_engine
from orcia_api.routers._workspace_datasources_helpers import (
    enforce_codegraph_access,
    enforce_datasource_mutation_access,
    enforce_personal_workspace_isolation,
    pg_enabled,
    resolve_datasources_user,
    serialize_datasource,
    trace_id_for_request,
)
from orcia_api.routers.ontology_rag_helpers import persist_ingested_document_pg
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
from orcia_core.permissions.errors import ResourceNotFoundError

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


@router.get(
    "/{workspace_id}/datasources",
    response_model=WorkspaceDatasourcesListResponse,
    summary="List datasources attached to a workspace with evaluated sync health",
)
async def list_workspace_datasources(
    request: Request,
    workspace_id: Annotated[str, Path()],
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> WorkspaceDatasourcesListResponse:
    user = resolve_datasources_user(request, persona_key=persona)
    await enforce_personal_workspace_isolation(request, user, workspace_id)

    if pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        datasources = await list_workspace_datasources_from_postgres18(
            engine, workspace_id=workspace_id
        )
    else:
        datasources = []

    return WorkspaceDatasourcesListResponse(
        items=[serialize_datasource(d) for d in datasources],
        trace_id=trace_id_for_request(request),
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
    user = enforce_datasource_mutation_access(request, persona_key=persona)
    await enforce_personal_workspace_isolation(request, user, workspace_id, require_write=True)

    if payload.codegraph_enabled:
        enforce_codegraph_access(request, user)

    if not pg_enabled():
        raise ResourceNotFoundError(
            detail_override="In-memory mode does not support standalone datasource creation.",
            instance=str(request.url.path),
        )
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
    return serialize_datasource(rec)


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
    user = enforce_datasource_mutation_access(request, persona_key=persona)
    await enforce_personal_workspace_isolation(request, user, workspace_id, require_write=True)

    if (
        payload.codegraph_enabled is not None
        or payload.codegraph_auth_mode is not None
        or payload.codegraph_owner_user_id is not None
    ):
        enforce_codegraph_access(request, user)

    if not pg_enabled():
        raise ResourceNotFoundError(instance=str(request.url.path))
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
    return serialize_datasource(rec)


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
    user = enforce_datasource_mutation_access(request, persona_key=persona)
    await enforce_personal_workspace_isolation(request, user, workspace_id, require_write=True)

    if not pg_enabled():
        raise ResourceNotFoundError(instance=str(request.url.path))
    engine = get_or_create_shared_db_engine(request)
    await delete_workspace_datasource_on_postgres18(
        engine,
        workspace_id=workspace_id,
        datasource_id=datasource_id,
        instance=str(request.url.path),
    )
    return WorkspaceDatasourceDeleteResponse(
        deleted=True,
        workspace_id=workspace_id,
        datasource_id=datasource_id,
        trace_id=trace_id_for_request(request),
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
    user = enforce_datasource_mutation_access(request, persona_key=persona)
    await enforce_personal_workspace_isolation(request, user, workspace_id, require_write=True)

    if not pg_enabled():
        raise ResourceNotFoundError(instance=str(request.url.path))
    engine = get_or_create_shared_db_engine(request)
    rec = await trigger_workspace_datasource_sync_on_postgres18(
        engine,
        workspace_id=workspace_id,
        datasource_id=datasource_id,
        instance=str(request.url.path),
    )
    if rec.freshness_status != "SYNC_ERROR":
        regime = (
            "CODE_AST_GRAPH"
            if rec.source_nature == "SOURCE_CODE"
            else "DB_DDL_ONLY"
            if rec.scheme == "db"
            else "DOC_PARENT_CHILD"
        )
        chunk_role = (
            "AST_SYMBOL"
            if regime == "CODE_AST_GRAPH"
            else "DDL_SCHEMA"
            if regime == "DB_DDL_ONLY"
            else "PARENT"
        )
        await persist_ingested_document_pg(
            request,
            document_id=rec.id,
            workspace_id=rec.workspace_id,
            datasource_id=rec.id,
            datasource_alias=rec.alias,
            uri=rec.uri,
            title=rec.alias,
            content_text=f"{rec.alias} ({rec.uri})",
            indexing_regime=regime,
            chunk_role=chunk_role,
            is_stale=rec.freshness_status == "STALE",
        )
    return TriggerWorkspaceDatasourceSyncResponse(
        datasource=serialize_datasource(rec),
        trace_id=trace_id_for_request(request),
    )
