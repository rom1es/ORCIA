"""Story 18.3 — Normalized Read-Only Code Graph MCP Router.

Exposes:
- `GET  /api/v1/workspaces/{workspace_id}/codegraph/tools`
- `POST /api/v1/workspaces/{workspace_id}/codegraph/invoke`
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Path, Query, Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.codegraph_mcp import (
    CodegraphActiveRepoResponse,
    CodegraphToolItemResponse,
    CodegraphToolsListResponse,
    InvokeCodegraphToolRequest,
    InvokeCodegraphToolResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_connectors.adapters.codegraph_mcp import (
    TOOL_DEFINITIONS,
    CodegraphMcpConnector,
)
from orcia_connectors.codegraph.providers import build_codegraph_provider
from orcia_core.bootstrap import list_workspace_datasources_from_postgres18
from orcia_core.kernel.errors import ValidationDomainError
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError

logger = get_logger("orcia.api.codegraph_mcp")

CODEGRAPH_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["codegraph-mcp"],
    responses=CODEGRAPH_PROBLEM_RESPONSES,
)


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _pg_enabled() -> bool:
    from orcia_api.dependencies._core_providers import is_pg_runtime_active

    return is_pg_runtime_active()


async def _get_workspace_datasources(request: Request, workspace_id: str) -> list[Any]:
    if not _pg_enabled():
        return []
    try:
        engine = get_or_create_shared_db_engine(request)
        return list(
            await list_workspace_datasources_from_postgres18(engine, workspace_id=workspace_id)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to load workspace datasources from Postgres",
            extra={"workspace_id": workspace_id, "error": str(exc)},
        )
        return []


async def _enforce_codegraph_workspace_access(
    request: Request,
    workspace_id: str,
    *,
    persona_key: str | None = None,
    require_execute: bool = False,
) -> None:
    effective_persona = (
        None
        if request.headers.get("Authorization")
        else (persona_key or request.headers.get("x-orcia-persona", "").strip() or None)
    )
    user = resolve_request_user(request, persona_key=effective_persona)
    if require_execute:
        enforce_observer_headers_guard(request, user)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    ws = auth_svc.evaluator.get_workspace(workspace_id)
    if ws is None:
        await sync_evaluator_topology_from_pg(request, auth_svc, force=True)
        ws = auth_svc.evaluator.get_workspace(workspace_id)
    if ws is None:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    access = auth_svc.evaluator.resolve_workspace_access(user, ws.id)
    if access is None:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    if require_execute and access.access_mode == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(instance=str(request.url.path))


@router.get(
    "/{workspace_id}/codegraph/tools",
    response_model=CodegraphToolsListResponse,
    summary="List normalized read-only Code Graph MCP tools and active repositories",
)
async def list_codegraph_tools(
    request: Request,
    workspace_id: Annotated[str, Path()],
    persona_key: Annotated[str | None, Query()] = None,
) -> CodegraphToolsListResponse:
    await _enforce_codegraph_workspace_access(
        request, workspace_id, persona_key=persona_key, require_execute=False
    )
    http_client = getattr(request.app.state, "http_client", None)
    provider = build_codegraph_provider(http_client=http_client)
    datasources = await _get_workspace_datasources(request, workspace_id)

    active_repos: list[CodegraphActiveRepoResponse] = []
    for ds in datasources:
        nature = getattr(ds, "source_nature", None) or (
            ds.get("source_nature") if isinstance(ds, dict) else None
        )
        enabled = getattr(ds, "codegraph_enabled", None)
        if enabled is None and isinstance(ds, dict):
            enabled = ds.get("codegraph_enabled")
        if nature == "SOURCE_CODE" and enabled:
            active_repos.append(
                CodegraphActiveRepoResponse(
                    datasource_id=str(getattr(ds, "id", "") or ds.get("id", "")),
                    alias=str(getattr(ds, "alias", "") or ds.get("alias", "")),
                    uri=str(getattr(ds, "uri", "") or ds.get("uri", "")),
                    source_nature=nature,
                    codegraph_enabled=True,
                    codegraph_status=str(
                        getattr(ds, "codegraph_status", "READY")
                        or ds.get("codegraph_status", "READY")
                    ),
                    codegraph_head_sha=getattr(ds, "codegraph_head_sha", None)
                    or (ds.get("codegraph_head_sha") if isinstance(ds, dict) else None),
                )
            )

    tools = [CodegraphToolItemResponse(**t) for t in TOOL_DEFINITIONS]

    return CodegraphToolsListResponse(
        workspace_id=workspace_id,
        provider=provider.provider_name,
        tools=tools,
        active_repositories=active_repos,
        trace_id=_trace(request),
    )


@router.post(
    "/{workspace_id}/codegraph/invoke",
    response_model=InvokeCodegraphToolResponse,
    summary="Invoke a normalized read-only Code Graph MCP tool",
)
async def invoke_codegraph_tool(
    request: Request,
    workspace_id: Annotated[str, Path()],
    body: InvokeCodegraphToolRequest,
    persona_key: Annotated[str | None, Query()] = None,
) -> InvokeCodegraphToolResponse:
    await _enforce_codegraph_workspace_access(
        request, workspace_id, persona_key=persona_key, require_execute=True
    )
    http_client = getattr(request.app.state, "http_client", None)
    provider = build_codegraph_provider(http_client=http_client)

    async def _resolve_ds(ws_id: str) -> list[Any]:
        return await _get_workspace_datasources(request, ws_id)

    connector = CodegraphMcpConnector(
        provider=provider,
        workspace_id=workspace_id,
        datasources_resolver=_resolve_ds,
    )

    try:
        result = await connector.invoke_tool(
            body.tool_name,
            body.arguments,
            workspace_id=workspace_id,
        )
    except ValidationDomainError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.detail_override or str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        msg = str(exc)
        if "not attached" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=403, detail=msg) from exc

    return InvokeCodegraphToolResponse(
        workspace_id=workspace_id,
        tool_name=body.tool_name,
        provider=provider.provider_name,
        result=result,
        trace_id=_trace(request),
    )


__all__ = ["router"]
