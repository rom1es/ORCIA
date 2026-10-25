"""Pydantic v2 schemas for Story 1.3: Federated Catalog, CAS, 4-Layer Overrides & BMAD."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.catalog.models import (
    AdaptiveGatePolicy,
    CatalogResourceType,
    CatalogSourceFormat,
    FederatedScheme,
    ScalarValue,
)
from orcia_core.permissions.models import CatalogPermission, CatalogVisibilityScope


class CatalogItemResponse(BaseModel):
    """Serialized Federated Catalog item with URI scheme, short SHA-256, and 5 RBAC permissions."""

    model_config = ConfigDict(extra="forbid")

    id: str
    resource_id: str
    uri: str
    scheme: FederatedScheme
    title: str
    description: str
    resource_type: CatalogResourceType
    source_format: CatalogSourceFormat
    version: str
    sha256: str = Field(..., min_length=64, max_length=64)
    sha256_short: str = Field(..., min_length=6, max_length=16)
    cas_key: str
    visibility_scope: CatalogVisibilityScope
    granted_permissions: list[CatalogPermission]
    source_masked: bool


class CatalogItemsListResponse(BaseModel):
    """Response envelope for `GET /api/v1/catalog/items`."""

    model_config = ConfigDict(extra="forbid")

    items: list[CatalogItemResponse]
    trace_id: str = Field(..., min_length=32, max_length=32)


class CatalogPromoteRequest(BaseModel):
    """Request payload for `POST /api/v1/catalog/items/{resource_id}/promote` (`FR-21`)."""

    model_config = ConfigDict(extra="forbid")

    target_scope: CatalogVisibilityScope
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)


class CatalogPromoteResponse(BaseModel):
    """Response payload after promoting a catalog item along the publication lifecycle."""

    model_config = ConfigDict(extra="forbid")

    item: CatalogItemResponse
    previous_scope: CatalogVisibilityScope
    trace_id: str = Field(..., min_length=32, max_length=32)


class CatalogUriResolveRequest(BaseModel):
    """Request payload for `POST /api/v1/catalog/resolve` (`AD-5`, `NFR-PERF-3`)."""

    model_config = ConfigDict(extra="forbid")

    uri: str = Field(
        ...,
        min_length=8,
        max_length=512,
        pattern=(
            r"^(git|nexus|db|confluence|jira|orcia)://"
            r"[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+(@[A-Za-z0-9.:_-]+)?$"
        ),
    )
    expected_sha256: str | None = Field(
        default=None,
        min_length=6,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{6,64}$",
    )


class CatalogUriResolveResponse(BaseModel):
    """Response payload for `POST /api/v1/catalog/resolve` (`< 50 ms` on hot cache)."""

    model_config = ConfigDict(extra="forbid")

    uri: str
    scheme: FederatedScheme
    resolved_version: str
    sha256: str = Field(..., min_length=64, max_length=64)
    cas_key: str
    cache_hit: bool
    resolution_ms: float = Field(..., ge=0.0)
    content_text: str
    trace_id: str = Field(..., min_length=32, max_length=32)


class CasObjectResponse(BaseModel):
    """Response payload for `GET /api/v1/cas/{sha256}`."""

    model_config = ConfigDict(extra="forbid")

    sha256: str = Field(..., min_length=64, max_length=64)
    cas_key: str
    content_type: str
    content_text: str
    trace_id: str = Field(..., min_length=32, max_length=32)


class EvaluationLensItem(BaseModel):
    """Evaluation lens item in a workflow definition."""

    model_config = ConfigDict(extra="forbid")

    code: str
    weight: float
    threshold: float


class WorkflowStepItem(BaseModel):
    """Workflow step item in a workflow definition."""

    model_config = ConfigDict(extra="forbid")

    step_key: str
    title: str
    instructions: str
    human_authored_required: bool


class WorkflowDefinitionResponseItem(BaseModel):
    """Serialized workflow definition (`ORCIA` native or `BMAD_PACK`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str | None = None
    uri: str
    title: str
    description: str
    version: str
    source_format: CatalogSourceFormat
    adaptive_gate_policy: AdaptiveGatePolicy
    scalars: dict[str, ScalarValue]
    datasources: list[str]
    rules: list[str]
    facts: list[str]
    lenses: list[EvaluationLensItem]
    steps: list[WorkflowStepItem]
    sha256: str = Field(..., min_length=64, max_length=64)


class RunLockSourceTripletItem(BaseModel):
    """Pinned `(alias, uri, resolved_version, sha256)` source entry in `run-lock.json`."""

    model_config = ConfigDict(extra="forbid")

    alias: str
    scheme: FederatedScheme
    uri: str
    resolved_version: str
    sha256: str = Field(..., min_length=64, max_length=64)
    cas_key: str


class RunLockManifestItem(BaseModel):
    """Serialized `run-lock.json` provenance manifest (`AD-5`, `AD-14`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    workflow_uri: str
    workflow_version: str
    workflow_sha256: str = Field(..., min_length=64, max_length=64)
    effective_workflow_sha256: str = Field(..., min_length=64, max_length=64)
    applied_override_keys: list[str]
    sources: list[RunLockSourceTripletItem]
    manifest_sha256: str = Field(..., min_length=64, max_length=64)


class EffectiveWorkflowResolveRequest(BaseModel):
    """Request payload for `POST /api/v1/catalog/workflows/resolve-effective`."""

    model_config = ConfigDict(extra="forbid")

    workflow_uri: str = Field(..., min_length=5, max_length=512)
    workspace_id: str = Field(..., min_length=1, max_length=128)


class EffectiveWorkflowResolveResponse(BaseModel):
    """Response payload for 4-layer merged workflow and `run-lock.json`."""

    model_config = ConfigDict(extra="forbid")

    base_workflow: WorkflowDefinitionResponseItem
    effective_workflow: WorkflowDefinitionResponseItem
    applied_override_keys: list[str]
    run_lock: RunLockManifestItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class BmadSkillStepInputItem(BaseModel):
    """Single Markdown step file input for BMAD skill pack import (`AR-5`)."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(
        ...,
        min_length=4,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+\.md$",
    )
    content_markdown: str = Field(
        ...,
        min_length=4,
        max_length=16384,
        pattern=r"^# [^\n\r]+(\n[\s\S]+)?$",
    )


class BmadSkillPackImportRequest(BaseModel):
    """Request payload for `POST /api/v1/catalog/bmad-packs/import` (`AR-5`, `AD-14`)."""

    model_config = ConfigDict(extra="forbid")

    uri: str = Field(
        ...,
        min_length=8,
        max_length=512,
        pattern=(
            r"^(git|nexus|db|confluence|jira|orcia)://"
            r"[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+(@[A-Za-z0-9.:_-]+)?$"
        ),
    )
    skill_markdown: str = Field(
        ...,
        min_length=25,
        max_length=32768,
        pattern=(
            r"^---\nname: [A-Za-z0-9._-]+\n"
            r"description: [^\n\r]+(\n[a-z_]+: [^\n\r]+)*\n---\n[\s\S]+$"
        ),
    )
    customize_toml: str = Field(
        default="",
        max_length=16384,
        pattern=r"^(\[scalars\](\n[a-z0-9_]+ = (\"[^\n\r\"]*\"|[0-9]+|true|false))*\n?)?$",
    )
    steps: list[BmadSkillStepInputItem] = Field(..., min_length=1, max_length=8)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)


class BmadSkillPackImportResponse(BaseModel):
    """Response payload for `POST /api/v1/catalog/bmad-packs/import`."""

    model_config = ConfigDict(extra="forbid")

    catalog_item: CatalogItemResponse
    workflow_definition: WorkflowDefinitionResponseItem
    trace_id: str = Field(..., min_length=32, max_length=32)
