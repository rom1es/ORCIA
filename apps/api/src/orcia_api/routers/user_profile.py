"""Story 20.4 — Personal User Profile Summary Router (`GET /api/v1/users/me/profile-summary`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.user_profile import (
    PopularUsageItemResponse,
    UserProfileSummaryResponse,
)
from orcia_core.audit_finops import fetch_user_profile_summary_sql
from orcia_core.observability.logging import get_current_trace_id

router = APIRouter(
    prefix="/api/v1",
    tags=["user-profile"],
    responses=PROBLEM_RESPONSES,
)


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _resolve_optional_engine(request: Request) -> AsyncEngine | None:
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    return get_configured_db_engine(request)


@router.get(
    "/users/me/profile-summary",
    response_model=UserProfileSummaryResponse,
    summary="Get authenticated user's profile summary, 4 token/streak KPIs & top 5 popular items",
)
async def get_my_profile_summary(
    request: Request,
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> UserProfileSummaryResponse:
    """Return personal identity, BU/team attachments, token KPIs, streaks & popular items.

    Anti-IDOR by construction: no `user_id` query/path parameter is accepted;
    identity is strictly resolved from the authenticated session.
    """
    user = resolve_request_user(request, persona_key=persona_key)
    engine = _resolve_optional_engine(request)
    roles = user.roles if user.roles else (user.platform_role,)
    summary = await fetch_user_profile_summary_sql(
        engine,
        user_id=user.id,
        user_email=user.email,
        display_name=user.display_name,
        roles=roles,
    )
    return UserProfileSummaryResponse(
        user_id=summary.user_id,
        display_name=summary.display_name,
        handle=summary.handle,
        email=summary.email,
        primary_role=summary.primary_role,
        roles=list(summary.roles),
        led_business_units=list(summary.led_business_units),
        ontology_business_units=list(summary.ontology_business_units),
        led_teams=list(summary.led_teams),
        member_teams=list(summary.member_teams),
        total_tokens=summary.total_tokens,
        peak_daily_tokens=summary.peak_daily_tokens,
        longest_streak_days=summary.longest_streak_days,
        current_streak_days=summary.current_streak_days,
        popular_items=[
            PopularUsageItemResponse(
                item_type=item.item_type,
                item_key=item.item_key,
                title=item.title,
                usage_count=item.usage_count,
                target_route=item.target_route,
            )
            for item in summary.popular_items
        ],
        trace_id=_trace(request),
    )
