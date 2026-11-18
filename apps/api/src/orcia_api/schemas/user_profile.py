"""OpenAPI 3.1 schemas for Personal User Profile Summary (`Story 20.4`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PopularUsageItemResponse(BaseModel):
    """Single popular agent, process, skill, or tool card on `/profile`."""

    item_type: Literal["AGENT", "PROCESS", "SKILL", "TOOL"]
    item_key: str
    title: str
    usage_count: int = Field(ge=0)
    target_route: str


class UserProfileSummaryResponse(BaseModel):
    """Personal user profile overview (identity, org attachments, 4 KPIs, top 5 popular)."""

    user_id: str
    display_name: str
    handle: str
    email: str
    primary_role: str
    roles: list[str] = Field(default_factory=list)
    led_business_units: list[str] = Field(default_factory=list)
    ontology_business_units: list[str] = Field(default_factory=list)
    led_teams: list[str] = Field(default_factory=list)
    member_teams: list[str] = Field(default_factory=list)
    total_tokens: int = Field(ge=0)
    peak_daily_tokens: int = Field(ge=0)
    longest_streak_days: int = Field(ge=0)
    current_streak_days: int = Field(ge=0)
    popular_items: list[PopularUsageItemResponse] = Field(default_factory=list)
    trace_id: str


__all__ = ["PopularUsageItemResponse", "UserProfileSummaryResponse"]
