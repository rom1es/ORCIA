"""HTTP OpenAPI 3.1 transport schemas for Epic 16 Reflexive Execution & Surgical Exploration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.ports.surgical_explorer_port import (
    SurgicalFileBadgeCode,
    SurgicalPrimitiveName,
)


class SurgicalLineEntryItem(BaseModel):
    """HTTP transport item representing a single 1-indexed line slice entry."""

    model_config = ConfigDict(extra="forbid")

    line_number: int = Field(ge=1)
    content: str


class SurgicalOutlineNodeItem(BaseModel):
    """HTTP transport item representing a structural heading, key, or symbol."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    line_number: int = Field(ge=1)
    level: int = Field(default=1, ge=1, le=6)


class SurgicalSnippetMatchItem(BaseModel):
    """HTTP transport item representing a bounded `#Lstart-end` workspace match."""

    model_config = ConfigDict(extra="forbid")

    resource_uri: str
    display_filename: str
    file_badge_code: SurgicalFileBadgeCode = "DOC"
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    line_anchor: str = ""
    excerpt: str


class SurgicalInspectLinesResponse(BaseModel):
    """HTTP response envelope for `GET /api/v1/sources/inspect-lines`."""

    model_config = ConfigDict(extra="forbid")

    kind: SurgicalPrimitiveName = SurgicalPrimitiveName.INSPECT_RESOURCE_LINES
    resource_uri: str
    display_filename: str
    file_badge_code: SurgicalFileBadgeCode = "DOC"
    formatted_badge: str = ""
    exists: bool = True
    start_line: int | None = None
    end_line: int | None = None
    total_lines: int = 0
    lines: list[SurgicalLineEntryItem] = Field(default_factory=list)
    outline: list[SurgicalOutlineNodeItem] = Field(default_factory=list)
    snippets: list[SurgicalSnippetMatchItem] = Field(default_factory=list)
    check_label: str | None = None
    summary: str = ""
    sha256: str | None = None
    redacted: bool = False
    redacted_reason: str | None = None
    permission_request_hint: str | None = None
    trace_id: str


class SurgicalExploreRequest(BaseModel):
    """HTTP request payload for `POST /api/v1/sources/surgical-explore`."""

    model_config = ConfigDict(extra="forbid")

    primitive: SurgicalPrimitiveName
    resource_uri: str = Field(default="", max_length=1024)
    query: str = Field(default="", max_length=256)
    start_line: int = Field(default=1, ge=1, le=1_000_000)
    end_line: int = Field(default=200, ge=1, le=1_000_000)
    max_results: int = Field(default=20, ge=1, le=50)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)


class SurgicalExploreResponse(SurgicalInspectLinesResponse):
    """HTTP response envelope for `POST /api/v1/sources/surgical-explore`."""
