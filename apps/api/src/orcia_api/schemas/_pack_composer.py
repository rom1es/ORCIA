"""OpenAPI 3.1 HTTP Transport Schemas for Pack Composer, Export & Guarded Delete (`Story 31.5`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ComposerEntityTypeLiteral = Literal[
    "AGENT",
    "SKILL",
    "INSTRUCTION",
    "WORKFLOW_V2",
    "VSM_V2",
    "ONTOLOGY_CONCEPT",
    "ONTOLOGY_RELATION",
    "ONTOLOGY_AXIOM",
    "DNA_MECHANISM",
    "POLICY",
    "HELP_ARTICLE",
]


class PackComposerSlotSchema(BaseModel):
    """Logical connector slot declaration inside a composed pack."""

    slot_key: str = Field(..., min_length=1, max_length=128)
    scheme: str = Field(..., min_length=1, max_length=32)
    connector_kind: str = ""
    source_nature: str = ""
    required_access: list[str] = Field(default_factory=lambda: ["read"])
    required: bool = True
    description_fr: str = ""
    description_en: str = ""


class PackComposerQuickActionSchema(BaseModel):
    """Quick action shortcut declared inside a composed pack."""

    id: str = Field(..., min_length=1, max_length=128)
    label: str = Field(..., min_length=1, max_length=255)
    target_workflow_slug: str = Field(..., min_length=1, max_length=128)
    icon: str = "play"


class CreatePackDraftRequest(BaseModel):
    """Create a `CUSTOM` `DRAFT` pack bundle (`POST /api/v1/packs/composer`)."""

    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(default="0.1.0", min_length=1, max_length=64)
    description: str = ""
    author: str = ""
    maintainers: list[str] = Field(default_factory=list)
    license: str = ""
    scope_type: Literal["BU", "TEAM", "WORKSPACE"] = "WORKSPACE"
    scope_id: str = Field(..., min_length=1, max_length=128)
    declared_slots: list[PackComposerSlotSchema] = Field(default_factory=list)
    quick_actions: list[PackComposerQuickActionSchema] = Field(default_factory=list)


class UpdatePackDraftRequest(BaseModel):
    """Patch metadata on an existing `CUSTOM` `DRAFT` pack bundle."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    version: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = None
    author: str | None = None
    maintainers: list[str] | None = None
    license: str | None = None
    declared_slots: list[PackComposerSlotSchema] | None = None
    quick_actions: list[PackComposerQuickActionSchema] | None = None


class PackDraftMemberInputSchema(BaseModel):
    """Single entity selection entry for `PUT /api/v1/packs/composer/{draft_id}/members`."""

    entity_type: ComposerEntityTypeLiteral
    entity_id: str = Field(..., min_length=1, max_length=128)
    entity_slug: str | None = Field(default=None, max_length=128)


class SetPackDraftMembersRequest(BaseModel):
    """Atomic replacement payload for a draft pack's typed memberships."""

    members: list[PackDraftMemberInputSchema] = Field(default_factory=list)


class PackDraftMemberResponse(BaseModel):
    """Serialized `pack_draft_memberships` entry with resolved typed surrogate FKs."""

    id: str
    draft_bundle_id: str
    entity_type: ComposerEntityTypeLiteral
    entity_id: str
    entity_slug: str
    title: str = ""
    lifecycle_status: str = "ACTIVE"
    catalog_item_id: str | None = None
    workflow_v2_id: str | None = None
    vsm_v2_id: str | None = None
    ontology_concept_id: str | None = None
    ontology_relation_id: str | None = None
    ontology_axiom_id: str | None = None
    dna_mechanism_id: str | None = None
    policy_id: str | None = None
    created_at_iso: str = ""


class ClosureMissingDependencyResponse(BaseModel):
    """Missing or non-ACTIVE transitive dependency surfaced during closure validation."""

    entity_type: str
    entity_id: str
    reason: str
    referenced_by: str


class ProseLintWarningResponse(BaseModel):
    """Non-mutating bare-handle warning emitted for pack markdown prose."""

    entity_type: str
    entity_slug: str
    token: str
    message: str


class PackClosureReportResponse(BaseModel):
    """Transitive dependency closure & bare-handle lint preview."""

    complete: bool
    missing_dependencies: list[ClosureMissingDependencyResponse] = Field(default_factory=list)
    non_active_dependencies: list[ClosureMissingDependencyResponse] = Field(default_factory=list)
    prose_lint_warnings: list[ProseLintWarningResponse] = Field(default_factory=list)
    auto_included_count: int = 0


class PackDraftDetailResponse(BaseModel):
    """Full `CUSTOM` composer pack bundle representation."""

    bundle_id: str
    pack_id: str
    slug: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    maintainers: list[str] = Field(default_factory=list)
    license: str = ""
    bundle_kind: str = "CUSTOM"
    scope_type: str = "WORKSPACE"
    scope_id: str = ""
    status: str = "DRAFT"
    source_origin: str = "ORCIA_COMPOSER"
    archive_sha256: str = ""
    cas_object_key: str | None = None
    declared_slots: list[PackComposerSlotSchema] = Field(default_factory=list)
    quick_actions: list[PackComposerQuickActionSchema] = Field(default_factory=list)
    members: list[PackDraftMemberResponse] = Field(default_factory=list)
    closure: PackClosureReportResponse | None = None
    created_by_user_id: str | None = None
    published_at_iso: str | None = None
    updated_at_iso: str = ""
    trace_id: str = ""


class PackDraftListResponse(BaseModel):
    """List envelope for `GET /api/v1/packs/composer`."""

    drafts: list[PackDraftDetailResponse] = Field(default_factory=list)
    trace_id: str = ""


class PackDraftDeleteResponse(BaseModel):
    """Deletion confirmation for `DELETE /api/v1/packs/composer/{draft_id}`."""

    bundle_id: str
    slug: str
    version: str
    deleted: bool = True
    trace_id: str


class PackPublishRequest(BaseModel):
    """Optional options for `POST /api/v1/packs/composer/{draft_id}/publish`."""

    auto_include_dependencies: bool = False


class PackExportRequest(BaseModel):
    """Optional options for `POST /api/v1/packs/.../export`."""

    auto_include_dependencies: bool = False


class GuardedEntityDeleteResponse(BaseModel):
    """Response payload for guarded PG18 entity `DELETE` endpoints (`Story 31.5`)."""

    entity_type: str
    deleted_id: str
    deleted_uuid: str
    unlinked_draft_packs: list[dict[str, str]] = Field(default_factory=list)
    trace_id: str


__all__ = [
    "ClosureMissingDependencyResponse",
    "CreatePackDraftRequest",
    "GuardedEntityDeleteResponse",
    "PackClosureReportResponse",
    "PackComposerQuickActionSchema",
    "PackComposerSlotSchema",
    "PackDraftDeleteResponse",
    "PackDraftDetailResponse",
    "PackDraftListResponse",
    "PackDraftMemberInputSchema",
    "PackDraftMemberResponse",
    "PackExportRequest",
    "PackPublishRequest",
    "ProseLintWarningResponse",
    "SetPackDraftMembersRequest",
    "UpdatePackDraftRequest",
]
