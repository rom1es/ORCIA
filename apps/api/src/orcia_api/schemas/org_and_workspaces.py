"""Pydantic v2 schemas for scoped Workspace `PATCH /api/v1/workspaces/{workspace_id}`."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.permissions.models import AccessMode, PlatformRole


class WorkspacePatchRequest(BaseModel):
    """Request payload for scoped `PATCH /api/v1/workspaces/{workspace_id}` (`Story 29.2`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    visibility_mode: Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"] | None = None
    lifecycle_phase: Literal["BUILD", "RUN", "MIGRATION"] | None = None


class WorkspacePatchResponse(BaseModel):
    """Response payload for scoped `PATCH /api/v1/workspaces/{workspace_id}`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    slug: str
    name: str
    owner_org_unit_id: str
    owner_org_unit_name: str
    visibility_mode: Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"]
    lifecycle_phase: Literal["BUILD", "RUN", "MIGRATION"]
    effective_role: PlatformRole
    access_mode: AccessMode
    access_origin: Literal["DIRECT_TEAM", "ROLLUP_PARENT", "PARTNER_INVITE", "GLOBAL_ADMIN"]
    finops_cost_usd: float = 0.0
    trace_id: str = Field(..., min_length=32, max_length=32)


__all__ = ["WorkspacePatchRequest", "WorkspacePatchResponse"]
