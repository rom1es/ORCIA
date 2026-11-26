"""Two-speed search Pydantic contracts extracted from `schemas/ontology_and_rag.py`."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class TwoSpeedSearchHitSchemaItem(BaseModel):
    """Single hit item returned by `GET /api/v1/search` (`Story 9.3`)."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    family: Literal[
        "FOLDERS_DISCUSSIONS",
        "PROCESSES_EXECUTIONS",
        "DELIVERABLES_ARTIFACTS",
        "SOURCES_SNIPPETS",
        "GLOSSARY_RULES",
        "AGENTS_SKILLS",
        "HELP_ACTIONS",
    ]
    title: str
    snippet: str
    workspace_id: str
    screen_route: str
    deep_link_uri: str
    speed_tier: Literal[1, 2]
    locked_top: bool
    score: float
    badge: str | None = None
    highlight_duration_ms: int = 2000
    opens_contextual_help_column: bool = False


class TwoSpeedSearchResponse(BaseModel):
    """Response for `GET /api/v1/search` (`Story 9.3`)."""

    model_config = ConfigDict(extra="forbid")

    query: str
    scope: Literal["SCREEN", "WORKSPACE", "ALL_WORKSPACES"]
    hits: list[TwoSpeedSearchHitSchemaItem]
    speed1_llm_cost_usd: float
    speed2_executed: bool
    speed2_cache_hit: bool
    speed2_redis_key: str | None = None
    speed2_cache_ttl_seconds: int = 300
    trace_id: str | None = None
