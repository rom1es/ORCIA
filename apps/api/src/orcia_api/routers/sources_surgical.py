"""Surgical Source Exploration Router (`Story 16.1`, `CAP-160`).

Exposes:
- `GET /api/v1/sources/inspect-lines`: 1-indexed `#Lstart-end` slice (`<= 250` lines) with
  `READ_SOURCE` governance (`redacted=True`) and RFC 9457 Problem Details on invalid URIs.
- `POST /api/v1/sources/surgical-explore`: Read-only execution of the 4 surgical primitives.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import get_surgical_explorer_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.reflexive_execution import (
    SurgicalExploreRequest,
    SurgicalExploreResponse,
    SurgicalInspectLinesResponse,
    SurgicalLineEntryItem,
    SurgicalOutlineNodeItem,
    SurgicalSnippetMatchItem,
)
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalObservation,
)

router = APIRouter(
    prefix="/api/v1/sources",
    tags=["sources-surgical"],
    responses=PROBLEM_RESPONSES,
)

SurgicalExplorerDep = Annotated[SurgicalExplorerPort, Depends(get_surgical_explorer_service)]

_DENIED_HEADER_VALUES: frozenset[str] = frozenset({"0", "false", "denied", "restricted", "no"})


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _resolve_header_read_source_restriction(request: Request) -> bool:
    """Allow context/header to restrict `READ_SOURCE` (`False`), never elevate privileges."""
    raw = (request.headers.get("x-orcia-read-source") or "").strip().lower()
    return raw not in _DENIED_HEADER_VALUES


def _serialize_observation(obs: SurgicalObservation, trace_id: str) -> SurgicalInspectLinesResponse:
    return SurgicalInspectLinesResponse(
        kind=obs.kind,
        resource_uri=obs.resource_uri,
        display_filename=obs.display_filename,
        file_badge_code=obs.file_badge_code,
        formatted_badge=obs.formatted_badge,
        exists=obs.exists,
        start_line=obs.start_line,
        end_line=obs.end_line,
        total_lines=obs.total_lines,
        lines=[
            SurgicalLineEntryItem(line_number=ln.line_number, content=ln.content)
            for ln in obs.lines
        ],
        outline=[
            SurgicalOutlineNodeItem(
                kind=node.kind,
                title=node.title,
                line_number=node.line_number,
                level=node.level,
            )
            for node in obs.outline
        ],
        snippets=[
            SurgicalSnippetMatchItem(
                resource_uri=sn.resource_uri,
                display_filename=sn.display_filename,
                file_badge_code=sn.file_badge_code,
                start_line=sn.start_line,
                end_line=sn.end_line,
                line_anchor=sn.line_anchor,
                excerpt=sn.excerpt,
            )
            for sn in obs.snippets
        ],
        check_label=obs.check_label,
        summary=obs.summary,
        sha256=obs.sha256,
        redacted=obs.redacted,
        redacted_reason=obs.redacted_reason,
        permission_request_hint=obs.permission_request_hint,
        trace_id=trace_id,
    )


@router.get(
    "/inspect-lines",
    response_model=SurgicalInspectLinesResponse,
    summary="Inspect a governed `#Lstart-end` source slice (`<= 250` lines, `READ_SOURCE` checked)",
)
async def inspect_source_lines_endpoint(
    request: Request,
    explorer: SurgicalExplorerDep,
    uri: str = Query(..., min_length=1, max_length=1024),
    start_line: int = Query(default=1, ge=1, le=1_000_000),
    end_line: int = Query(default=200, ge=1, le=1_000_000),
    workspace_id: str | None = Query(default=None, min_length=1, max_length=128),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> SurgicalInspectLinesResponse:
    """Return a 1-indexed source slice or a governed `redacted=True` observation."""
    user = resolve_request_user(request, persona_key=persona_key)
    has_read_source = _resolve_header_read_source_restriction(request)
    observation = await explorer.inspect_lines(
        uri,
        start_line=start_line,
        end_line=end_line,
        workspace_id=workspace_id,
        actor_id=user.id,
        has_read_source=has_read_source,
    )
    return _serialize_observation(observation, _trace(request))


@router.post(
    "/surgical-explore",
    response_model=SurgicalExploreResponse,
    summary="Execute one of the 4 read-only surgical context exploration primitives",
)
async def execute_surgical_explore_endpoint(
    payload: SurgicalExploreRequest,
    request: Request,
    explorer: SurgicalExplorerDep,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> SurgicalExploreResponse:
    """Execute `check_resource_state`, `outline_resource_structure`, `search_workspace_snippets`,
    or `inspect_resource_lines` under RBAC `READ_SOURCE` governance.
    """
    user = resolve_request_user(request, persona_key=persona_key)
    has_read_source = _resolve_header_read_source_restriction(request)
    observation = await explorer.execute_primitive(
        payload.primitive,
        resource_uri=payload.resource_uri,
        query=payload.query,
        start_line=payload.start_line,
        end_line=payload.end_line,
        max_results=payload.max_results,
        workspace_id=payload.workspace_id,
        actor_id=user.id,
        has_read_source=has_read_source,
    )
    base = _serialize_observation(observation, _trace(request))
    return SurgicalExploreResponse(**base.model_dump())
