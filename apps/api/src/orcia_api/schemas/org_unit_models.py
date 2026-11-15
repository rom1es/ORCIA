"""Pydantic v2 schemas for organizational units & known users (`Story 17.2` / `CAP-067`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.permissions.models import OrgUnitType


class OrgUnitTreeItem(BaseModel):
    """Organizational Unit node in the hierarchical team tree (`org_units`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    slug: str
    name: str
    unit_type: OrgUnitType
    parent_id: str | None = None


class AttachedWorkspaceRefResponse(BaseModel):
    """Reference to an attached solution workspace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    slug: str
    name: str


class KnownOrgUserResponse(BaseModel):
    """Active known platform user (human) suitable for org unit lead / member assignment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    principal_id: str
    display_name: str
    email: str | None = None


class KnownOrgUsersSearchResponse(BaseModel):
    """Search response payload for `GET /api/v1/org-units/known-users` (`Story 17.2`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    items: list[KnownOrgUserResponse] = Field(default_factory=list)
    has_more: bool = False


class OrgUnitResponse(BaseModel):
    """Enriched organizational unit (`BU` / `Pôle` / `TEAM`) DTO."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    slug: str
    name: str
    kind: Literal["BU", "TEAM"]
    parent_id: str | None = None
    billing_enabled: bool = True
    lead_user_id: str | None = None
    member_user_ids: list[str] = Field(default_factory=list)
    attached_workspaces_count: int = Field(default=0, ge=0)
    attached_workspaces: list[AttachedWorkspaceRefResponse] = Field(default_factory=list)
    lead_user_ids: list[str] = Field(default_factory=list)


class OrgUnitsListResponse(BaseModel):
    """Hierarchical DFS list of org units with known platform users (`GET /api/v1/org-units`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_units: list[OrgUnitResponse]
    known_users: list[KnownOrgUserResponse] = Field(default_factory=list)
    trace_id: str = Field(..., min_length=32, max_length=32)


class OrgUnitCreateRequest(BaseModel):
    """Request payload for `POST /api/v1/org-units`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., min_length=1, max_length=255)
    kind: Literal["BU", "TEAM"]
    slug: str | None = Field(default=None, max_length=128)
    parent_id: str | None = Field(default=None, max_length=128)
    billing_enabled: bool = True
    lead_user_id: str | None = Field(default=None, max_length=128)
    lead_user_ids: list[str] | None = Field(default=None, max_length=20)
    member_user_ids: list[str] = Field(default_factory=list, max_length=200)


class OrgUnitPatchRequest(BaseModel):
    """Request payload for `PATCH /api/v1/org-units/{org_unit_id}`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: str | None = Field(default=None, max_length=128)
    billing_enabled: bool | None = None
    lead_user_id: str | None = Field(default=None, max_length=128)
    lead_user_ids: list[str] | None = Field(default=None, max_length=20)
    member_user_ids: list[str] | None = Field(default=None, max_length=200)


class OrgUnitDeleteResponse(BaseModel):
    """Deletion confirmation payload for `DELETE /api/v1/org-units/{org_unit_id}`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    deleted_id: str
    deleted: bool = True
    trace_id: str = Field(..., min_length=32, max_length=32)


__all__ = [
    "AttachedWorkspaceRefResponse",
    "KnownOrgUserResponse",
    "KnownOrgUsersSearchResponse",
    "OrgUnitCreateRequest",
    "OrgUnitDeleteResponse",
    "OrgUnitPatchRequest",
    "OrgUnitResponse",
    "OrgUnitsListResponse",
    "OrgUnitTreeItem",
]
