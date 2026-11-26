"""OpenAPI 3.1 HTTP Schemas for Workspace Pack Activation, Slots & Run Lock (`Story 31.4`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from orcia_core.packs.models import PackSlotSpec


class WorkspacePackSlotBindingInputSchema(BaseModel):
    """Input entry for `PUT /api/v1/workspaces/{workspace_id}/packs/{slug}/slots`."""

    slot_key: str = Field(..., min_length=1, max_length=128)
    target_kind: Literal["UNBOUND", "WORKSPACE_DATASOURCE", "ENTERPRISE_CONNECTOR", "INTERNAL"]
    target_id: str | None = Field(default=None, max_length=128)
    connector_scheme: str | None = Field(default=None, max_length=32)


class BindWorkspacePackSlotsRequest(BaseModel):
    """Request payload for binding declared connector slots on a workspace pack."""

    bundle_id: str | None = Field(default=None, max_length=128)
    bindings: list[WorkspacePackSlotBindingInputSchema] = Field(..., min_length=1)


class WorkspacePackSlotBindingItemResponse(BaseModel):
    """Hydrated connector slot binding status for a workspace pack."""

    id: str = ""
    workspace_id: str
    pack_bundle_id: str = ""
    pack_slug: str
    slot_key: str
    target_kind: Literal["UNBOUND", "WORKSPACE_DATASOURCE", "ENTERPRISE_CONNECTOR", "INTERNAL"]
    target_id: str | None = None
    bound_datasource_id: str | None = None
    bound_connector_id: str | None = None
    connector_scheme: str | None = None
    bound_by: str = ""
    bound_at_iso: str = ""
    is_effective_bound: bool = False
    target_uri: str | None = None
    target_display_name: str | None = None
    target_enabled: bool = True


class BindWorkspacePackSlotsResponse(BaseModel):
    """Response envelope after binding workspace pack connector slots."""

    workspace_id: str
    pack_slug: str
    slot_bindings: list[WorkspacePackSlotBindingItemResponse]
    trace_id: str


class WorkspacePackItemResponse(BaseModel):
    """Workspace-visible pack summary with activation state, slots & missing required slots."""

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
    description: str = ""
    author: str | None = None
    is_active: bool = False
    priority_order: int | None = None
    activated_at_iso: str | None = None
    activated_by: str | None = None
    declared_slots: list[PackSlotSpec] = Field(default_factory=list)
    slot_bindings: list[WorkspacePackSlotBindingItemResponse] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    readiness_ok: bool = True


class WorkspacePacksListResponse(BaseModel):
    """Response envelope for `GET /api/v1/workspaces/{workspace_id}/packs`."""

    workspace_id: str
    packs: list[WorkspacePackItemResponse]
    trace_id: str


class ActivateWorkspacePackRequest(BaseModel):
    """Optional JSON body for `POST /api/v1/workspaces/{workspace_id}/packs/{slug}/activate`."""

    bundle_id: str | None = Field(default=None, max_length=128)
    version: str | None = Field(default=None, max_length=64)
    priority_order: int | None = Field(default=None, ge=1)
    slot_bindings: list[WorkspacePackSlotBindingInputSchema] = Field(default_factory=list)


class ActivateWorkspacePackResponse(BaseModel):
    """Response envelope returned after activating a workspace pack."""

    activation_id: str
    workspace_id: str
    pack_bundle_id: str
    pack_slug: str
    version: str
    priority_order: int
    is_active: bool = True
    activated_at_iso: str
    trace_id: str


class DeactivateWorkspacePackResponse(BaseModel):
    """Response envelope returned after deactivating a workspace pack."""

    workspace_id: str
    pack_bundle_id: str
    pack_slug: str
    is_active: bool = False
    trace_id: str


class ReorderWorkspacePacksRequest(BaseModel):
    """Request payload for atomic priority reordering of active workspace packs."""

    ordered_pack_slugs: list[str] = Field(..., min_length=1)


class ReorderedWorkspacePackItemResponse(BaseModel):
    """Updated priority rank for an active workspace pack."""

    pack_slug: str
    pack_bundle_id: str
    priority_order: int


class ReorderWorkspacePacksResponse(BaseModel):
    """Response envelope returned after atomic workspace pack priority reorder."""

    workspace_id: str
    packs: list[ReorderedWorkspacePackItemResponse]
    trace_id: str


class ResolvedPackSlotSchema(BaseModel):
    """Pinned slot entry inside `run_lock_manifests`."""

    pack_slug: str
    slot_key: str
    scheme: str
    required: bool
    status: Literal["bound", "optional_unbound"]
    target_kind: Literal["UNBOUND", "WORKSPACE_DATASOURCE", "ENTERPRISE_CONNECTOR", "INTERNAL"]
    target_id: str | None = None
    target_uri: str | None = None
    connector_scheme: str | None = None


class PinnedPackManifestSchema(BaseModel):
    """Pinned pack entry inside `run_lock_manifests`."""

    pack_bundle_id: str
    pack_slug: str
    version: str
    archive_sha256: str
    priority_order: int
    resolved_pack_slots: list[ResolvedPackSlotSchema] = Field(default_factory=list)


class RunLockManifestReadResponse(BaseModel):
    """Immutable `run_lock_manifests` snapshot returned by `GET /api/v1/runs/{run_id}/lock`."""

    run_id: str
    workspace_id: str
    workflow_id: str = ""
    workflow_slug: str = ""
    workflow_version: str = ""
    pinned_packs: list[PinnedPackManifestSchema] = Field(default_factory=list)
    resolved_pack_slots: list[ResolvedPackSlotSchema] = Field(default_factory=list)
    manifest_sha256: str
    locked_at_iso: str = ""
    trace_id: str


__all__ = [
    "ActivateWorkspacePackRequest",
    "ActivateWorkspacePackResponse",
    "BindWorkspacePackSlotsRequest",
    "BindWorkspacePackSlotsResponse",
    "DeactivateWorkspacePackResponse",
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
