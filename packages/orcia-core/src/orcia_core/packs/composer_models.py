"""Pure domain models for Pack Composer, closure diagnostics & export (`Story 31.5`).

Zero framework or database driver imports.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from orcia_core.packs.models import (
    PackDraftEntityType,
    PackQuickActionSpec,
    PackSlotSpec,
)


class PackDraftMemberInput(BaseModel):
    """Input entry selecting an existing workspace/visible entity for a draft pack."""

    entity_type: PackDraftEntityType
    entity_id: str = Field(..., min_length=1, max_length=128)
    entity_slug: str | None = Field(default=None, max_length=128)


class PackDraftMemberView(BaseModel):
    """Hydrated `pack_draft_memberships` record with all 8 typed FK columns."""

    id: str
    draft_bundle_id: str
    entity_type: PackDraftEntityType
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


class ClosureMissingDependency(BaseModel):
    """Transitive dependency gap or non-ACTIVE entity detected during closure analysis."""

    entity_type: str
    entity_id: str
    reason: str
    referenced_by: str


class ProseLintWarning(BaseModel):
    """Non-mutating warning for bare `@slug` or `/slug` references in authored markdown."""

    entity_type: str
    entity_slug: str
    token: str
    message: str


class PackClosureReport(BaseModel):
    """Result of transitive closure verification and prose handle linting."""

    complete: bool
    missing_dependencies: list[ClosureMissingDependency] = Field(default_factory=list)
    non_active_dependencies: list[ClosureMissingDependency] = Field(default_factory=list)
    prose_lint_warnings: list[ProseLintWarning] = Field(default_factory=list)
    auto_included_count: int = 0


class PackDraftDetail(BaseModel):
    """Full representation of a `CUSTOM` composer pack draft (or published custom bundle)."""

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
    declared_slots: list[PackSlotSpec] = Field(default_factory=list)
    quick_actions: list[PackQuickActionSpec] = Field(default_factory=list)
    members: list[PackDraftMemberView] = Field(default_factory=list)
    closure: PackClosureReport | None = None
    created_by_user_id: str | None = None
    published_at_iso: str | None = None
    updated_at_iso: str = ""


class PackExportResult(BaseModel):
    """Deterministic scrubbed APM `.zip` + `apm.lock.yaml` export outcome."""

    bundle_id: str
    slug: str
    version: str
    archive_sha256: str
    lockfile_bundle_sha256: str
    zip_bytes: bytes
    included_dependencies_count: int = 0
    prose_lint_warnings: list[ProseLintWarning] = Field(default_factory=list)
    declared_slots: list[PackSlotSpec] = Field(default_factory=list)


__all__ = [
    "ClosureMissingDependency",
    "PackClosureReport",
    "PackDraftDetail",
    "PackDraftMemberInput",
    "PackDraftMemberView",
    "PackExportResult",
    "ProseLintWarning",
]
