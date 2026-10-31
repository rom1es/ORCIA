"""Epic 9 Portal Router: Two-Speed Federated Search (`GET /api/v1/search`),
User Preferences / Personal MCP Tokens & Hybrid Contextual Help (`AD-8`, `AD-14`, `AD-19`).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_two_speed_search_service
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.ontology_and_rag import (
    TwoSpeedSearchHitSchemaItem,
    TwoSpeedSearchResponse,
)
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(prefix="/api/v1", tags=["portal-epic9"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


@router.get(
    "/search",
    response_model=TwoSpeedSearchResponse,
    summary="Execute 2-Speed Federated & Contextual Search (`⌘K`, Zero Layout Shift, `Story 9.3`)",
    responses=PROBLEM_RESPONSES,
)
async def execute_two_speed_federated_search(
    request: Request,
    q: str = Query(default="", max_length=256),
    scope: Literal["SCREEN", "WORKSPACE", "ALL_WORKSPACES"] = Query(default="WORKSPACE"),
    workspace_id: str = Query(default="ws-claims-alpha", min_length=1, max_length=128),
    screen_route: str = Query(default="/cockpit", min_length=1, max_length=128),
    include_speed2: bool = Query(default=True),
    force_semantic: bool = Query(default=False),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> TwoSpeedSearchResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_two_speed_search_service(request)
    report = svc.execute_search(
        query=q,
        scope=scope,
        active_workspace_id=workspace_id,
        active_screen_route=screen_route,
        user_role=user.platform_role,
        include_speed2=include_speed2,
        force_semantic=force_semantic,
    )
    return TwoSpeedSearchResponse(
        query=report.query,
        scope=report.scope,
        hits=[TwoSpeedSearchHitSchemaItem(**asdict(h)) for h in report.hits],
        speed1_llm_cost_usd=report.speed1_llm_cost_usd,
        speed2_executed=report.speed2_executed,
        speed2_cache_hit=report.speed2_cache_hit,
        speed2_redis_key=report.speed2_redis_key,
        speed2_cache_ttl_seconds=report.speed2_cache_ttl_seconds,
        trace_id=_trace(request),
    )
