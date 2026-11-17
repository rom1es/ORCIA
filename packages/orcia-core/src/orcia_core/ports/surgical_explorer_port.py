"""Pure hexagonal Surgical Context Explorer Port (`AD-19`, `AD-20`, `Story 16.1`).

Defines the domain-agnostic protocol and Pydantic v2 models for the 4 read-only
surgical exploration primitives (`<= 250` lines per slice).
Zero external connector or framework dependencies may be imported in this module.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

MAX_SURGICAL_LINES: Final[int] = 250

SurgicalFileBadgeCode = Literal["M↓", "Y", "TS", "PY", "DOC", "JSON", "SQL"]


class SurgicalPrimitiveName(StrEnum):
    """Canonical names of the 4 read-only surgical exploration primitives."""

    CHECK_RESOURCE_STATE = "check_resource_state"
    OUTLINE_RESOURCE_STRUCTURE = "outline_resource_structure"
    SEARCH_WORKSPACE_SNIPPETS = "search_workspace_snippets"
    INSPECT_RESOURCE_LINES = "inspect_resource_lines"


class SurgicalLineEntry(BaseModel):
    """Single 1-indexed source line returned by `inspect_resource_lines`."""

    model_config = ConfigDict(extra="forbid")

    line_number: int = Field(ge=1)
    content: str


class SurgicalOutlineNode(BaseModel):
    """Structural symbol or section heading extracted by `outline_resource_structure`."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=512)
    line_number: int = Field(ge=1)
    level: int = Field(default=1, ge=1, le=6)


class SurgicalSnippetMatch(BaseModel):
    """Bounded numbered excerpt returned by `search_workspace_snippets`."""

    model_config = ConfigDict(extra="forbid")

    resource_uri: str = Field(min_length=1, max_length=1024)
    display_filename: str = Field(min_length=1, max_length=256)
    file_badge_code: SurgicalFileBadgeCode = "DOC"
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    line_anchor: str = ""
    excerpt: str


class SurgicalObservation(BaseModel):
    """Unified governed observation returned by any `SurgicalExplorerPort` primitive."""

    model_config = ConfigDict(extra="forbid")

    kind: SurgicalPrimitiveName
    resource_uri: str
    display_filename: str
    file_badge_code: SurgicalFileBadgeCode = "DOC"
    formatted_badge: str = ""
    exists: bool = True
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    total_lines: int = Field(default=0, ge=0)
    lines: list[SurgicalLineEntry] = Field(default_factory=list)
    outline: list[SurgicalOutlineNode] = Field(default_factory=list)
    snippets: list[SurgicalSnippetMatch] = Field(default_factory=list)
    check_label: str | None = None
    summary: str = ""
    sha256: str | None = None
    redacted: bool = False
    redacted_reason: str | None = None
    permission_request_hint: str | None = None


SurgicalLineSlice = SurgicalObservation


@runtime_checkable
class SurgicalExplorerPort(Protocol):
    """Hexagonal port for read-only, RBAC-governed `#Lstart-end` resource exploration."""

    async def execute_primitive(
        self,
        primitive: SurgicalPrimitiveName,
        *,
        resource_uri: str = "",
        query: str = "",
        start_line: int = 1,
        end_line: int = 200,
        max_results: int = 20,
        workspace_id: str | None = None,
        actor_id: str | None = None,
        has_read_source: bool = True,
    ) -> SurgicalObservation:
        """Execute one of the 4 read-only surgical exploration primitives."""
        ...

    async def inspect_lines(
        self,
        resource_uri: str,
        *,
        start_line: int = 1,
        end_line: int = 200,
        workspace_id: str | None = None,
        actor_id: str | None = None,
        has_read_source: bool = True,
    ) -> SurgicalObservation:
        """Read a 1-indexed inclusive slice capped at `MAX_SURGICAL_LINES` (`250`)."""
        ...


__all__ = [
    "MAX_SURGICAL_LINES",
    "SurgicalExplorerPort",
    "SurgicalFileBadgeCode",
    "SurgicalLineEntry",
    "SurgicalLineSlice",
    "SurgicalObservation",
    "SurgicalOutlineNode",
    "SurgicalPrimitiveName",
    "SurgicalSnippetMatch",
]
