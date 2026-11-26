"""OpenAPI 3.1 HTTP Transport Schemas for Declarative Packs v2 Import/Delete (`Story 31.2`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from orcia_api.schemas._workspace_packs import (
    ActivateWorkspacePackRequest,
    ActivateWorkspacePackResponse,
    BindWorkspacePackSlotsRequest,
    BindWorkspacePackSlotsResponse,
    DeactivateWorkspacePackResponse,
    PinnedPackManifestSchema,
    ReorderedWorkspacePackItemResponse,
    ReorderWorkspacePacksRequest,
    ReorderWorkspacePacksResponse,
    ResolvedPackSlotSchema,
    RunLockManifestReadResponse,
    WorkspacePackItemResponse,
    WorkspacePacksListResponse,
    WorkspacePackSlotBindingInputSchema,
    WorkspacePackSlotBindingItemResponse,
)


class PackImportRequest(BaseModel):
    """JSON payload for `POST /api/v1/packs/import` (base64-encoded `.zip` archive)."""

    zip_base64: str = Field(..., min_length=4)
    scope_type: Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"] | None = None
    scope_id: str | None = Field(default=None, max_length=128)
    replace_draft: bool = False


class PackImportEntityCountsResponse(BaseModel):
    """Materialized entity counts persisted for an imported pack bundle."""

    agents: int = 0
    skills: int = 0
    instructions: int = 0
    workflows: int = 0
    vsm: int = 0
    ontology_terms: int = 0
    dna_mechanisms: int = 0
    policies: int = 0
    help_articles: int = 0


class PackImportResponse(BaseModel):
    """Response envelope returned after transactional pack `.zip` import."""

    bundle_id: str
    pack_id: str
    slug: str
    name: str
    version: str
    bundle_kind: str
    scope_type: str
    scope_id: str
    status: str
    archive_sha256: str
    cas_object_key: str | None = None
    idempotent_noop: bool = False
    counts: PackImportEntityCountsResponse
    trace_id: str


class PackDeleteResponse(BaseModel):
    """Response envelope returned after guarded pack bundle deletion."""

    bundle_id: str
    slug: str
    version: str
    deleted: bool = True
    trace_id: str


__all__ = [
    "ActivateWorkspacePackRequest",
    "ActivateWorkspacePackResponse",
    "BindWorkspacePackSlotsRequest",
    "BindWorkspacePackSlotsResponse",
    "DeactivateWorkspacePackResponse",
    "PackDeleteResponse",
    "PackImportEntityCountsResponse",
    "PackImportRequest",
    "PackImportResponse",
    "PinnedPackManifestSchema",
    "ReorderWorkspacePacksRequest",
    "ReorderWorkspacePacksResponse",
    "ReorderedWorkspacePackItemResponse",
    "ResolvedPackSlotSchema",
    "RunLockManifestReadResponse",
    "WorkspacePackItemResponse",
    "WorkspacePackSlotBindingInputSchema",
    "WorkspacePackSlotBindingItemResponse",
    "WorkspacePacksListResponse",
]
