"""Pure domain models for APM-Superset declarative packs v2 (`AD-19`, `Story 31.1`).

Zero framework or database driver imports (`fastapi`, `sqlalchemy`, `dbos`, `redis`, `wasmtime`).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from orcia_core.workflows.schemas_v2 import ValueStreamMapSpec, WorkflowDefinitionV2


class PackBundleKind(StrEnum):
    SYSTEM = "SYSTEM"
    ORG = "ORG"
    IMPORTED = "IMPORTED"
    CUSTOM = "CUSTOM"


class PackScopeType(StrEnum):
    GLOBAL = "GLOBAL"
    BU = "BU"
    TEAM = "TEAM"
    WORKSPACE = "WORKSPACE"


class PackSourceOrigin(StrEnum):
    LOCAL_SYSTEM = "LOCAL_SYSTEM"
    APM_ZIP = "APM_ZIP"
    APM_GIT = "APM_GIT"
    ORCIA_COMPOSER = "ORCIA_COMPOSER"


class PackBundleStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"


class PackDraftEntityType(StrEnum):
    AGENT = "AGENT"
    SKILL = "SKILL"
    INSTRUCTION = "INSTRUCTION"
    WORKFLOW_V2 = "WORKFLOW_V2"
    VSM_V2 = "VSM_V2"
    ONTOLOGY_CONCEPT = "ONTOLOGY_CONCEPT"
    ONTOLOGY_RELATION = "ONTOLOGY_RELATION"
    ONTOLOGY_AXIOM = "ONTOLOGY_AXIOM"
    DNA_MECHANISM = "DNA_MECHANISM"
    POLICY = "POLICY"
    HELP_ARTICLE = "HELP_ARTICLE"


class PackSlotTargetKind(StrEnum):
    UNBOUND = "UNBOUND"
    WORKSPACE_DATASOURCE = "WORKSPACE_DATASOURCE"
    ENTERPRISE_CONNECTOR = "ENTERPRISE_CONNECTOR"
    INTERNAL = "INTERNAL"


class PackReadinessStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"


class PackSlotSpec(BaseModel):
    """Logical connector slot declared in `apm.yml` (`x-orcia.connector_slots`)."""

    slot_key: str = Field(..., min_length=1, max_length=128)
    scheme: str = Field(..., min_length=1, max_length=32)
    connector_kind: str = ""
    source_nature: str = ""
    required_access: list[str] = Field(default_factory=lambda: ["read"])
    required: bool = True
    description_fr: str = ""
    description_en: str = ""


class PackQuickActionSpec(BaseModel):
    id: str
    label: str
    target_workflow_slug: str
    icon: str = "play"


class PackAgentSpec(BaseModel):
    slug: str
    name: str
    description: str = ""
    instructions_markdown: str = ""
    model_tier: str = "medium"
    skill_refs: list[str] = Field(default_factory=list)
    connector_slots: list[str] = Field(default_factory=list)
    lifecycle_status: PackReadinessStatus = PackReadinessStatus.DRAFT
    has_orcia_governance: bool = False
    frontmatter: dict[str, Any] = Field(default_factory=dict)


class PackSkillSpec(BaseModel):
    slug: str
    name: str
    description: str = ""
    instructions_markdown: str = ""
    command_handle: str = ""
    input_parameters: list[dict[str, Any]] = Field(default_factory=list)
    is_si_write: bool = False
    human_authored_required: bool = False
    lifecycle_status: PackReadinessStatus = PackReadinessStatus.DRAFT
    has_orcia_governance: bool = False
    frontmatter: dict[str, Any] = Field(default_factory=dict)


class PackInstructionSpec(BaseModel):
    slug: str
    apply_to: str = "**/*"
    description: str = ""
    body_markdown: str = ""
    frontmatter: dict[str, Any] = Field(default_factory=dict)


class PackDnaMechanismSpec(BaseModel):
    mechanism_slug: str
    name: str
    starlark_source: str
    source_sha256: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    passing_test_payload: dict[str, Any] | None = None
    failing_test_payload: dict[str, Any] | None = None


class PackPolicySpec(BaseModel):
    policy_key: str
    uri_pattern: str
    connector_scheme: str
    required_role: str
    approver_team: str = ""
    sla_hours: int = Field(default=24, gt=0)
    procedure_markdown: str = ""
    frontmatter: dict[str, Any] = Field(default_factory=dict)


class PackHelpArticleSpec(BaseModel):
    slug: str
    lang: Literal["fr", "en"]
    title: str = ""
    bound_routes: list[str] = Field(default_factory=list)
    body_markdown: str = ""
    frontmatter: dict[str, Any] = Field(default_factory=dict)


class PackLockFileEntry(BaseModel):
    path: str
    sha256: str = Field(..., min_length=64, max_length=64)
    byte_size: int = Field(default=0, ge=0)


class PackLockSpec(BaseModel):
    lockfile_version: str = "1"
    bundle_sha256: str = ""
    files: dict[str, PackLockFileEntry] = Field(default_factory=dict)


class PackManifestV2(BaseModel):
    """Canonical APM-Superset manifest unifying `apm.yml` (`x-orcia:`) and legacy `pack.yaml`."""

    id: str = ""
    slug: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    author: str = ""
    maintainers: list[str] = Field(default_factory=list)
    license: str = ""
    rbac_namespace: str = "default"
    bundle_kind: PackBundleKind = PackBundleKind.IMPORTED
    scope_type: PackScopeType = PackScopeType.WORKSPACE
    scope_id: str = "global"
    status: PackBundleStatus = PackBundleStatus.PUBLISHED
    source_origin: PackSourceOrigin = PackSourceOrigin.APM_ZIP
    published_at_iso: str | None = None
    created_by_user_id: str | None = None
    declared_slots: list[PackSlotSpec] = Field(default_factory=list)
    mcp_declarations: dict[str, Any] = Field(default_factory=dict)
    quick_actions: list[PackQuickActionSpec] = Field(default_factory=list)
    x_orcia: dict[str, Any] = Field(default_factory=dict)


class LoadedPackBundleV2(BaseModel):
    """In-memory canonical representation of a decoded APM-Superset or legacy Pack bundle."""

    manifest: PackManifestV2
    archive_sha256: str = Field(..., min_length=64, max_length=64)
    manifest_yaml: str = ""
    lockfile: PackLockSpec | None = None
    agents: list[PackAgentSpec] = Field(default_factory=list)
    skills: list[PackSkillSpec] = Field(default_factory=list)
    instructions: list[PackInstructionSpec] = Field(default_factory=list)
    vsm_specs: list[ValueStreamMapSpec] = Field(default_factory=list)
    workflows: list[WorkflowDefinitionV2] = Field(default_factory=list)
    glossary: dict[str, Any] = Field(default_factory=dict)
    dna_mechanisms: list[PackDnaMechanismSpec] = Field(default_factory=list)
    gates_specs: dict[str, Any] = Field(default_factory=dict)
    policies: list[PackPolicySpec] = Field(default_factory=list)
    help_articles: list[PackHelpArticleSpec] = Field(default_factory=list)
    raw_files: dict[str, bytes] = Field(default_factory=dict)


class WorkspacePackActivation(BaseModel):
    id: str
    workspace_id: str
    pack_bundle_id: str
    pack_slug: str
    priority_order: int | None = Field(default=None, ge=1)
    is_active: bool = True
    activated_by: str
    activated_at_iso: str = ""


class WorkspacePackSlotBinding(BaseModel):
    id: str
    workspace_id: str
    pack_bundle_id: str = ""
    pack_slug: str
    slot_key: str
    target_kind: PackSlotTargetKind = PackSlotTargetKind.UNBOUND
    target_id: str | None = None
    bound_datasource_id: str | None = None
    bound_connector_id: str | None = None
    connector_scheme: str | None = None
    bound_by: str
    bound_at_iso: str = ""


class PackDraftMembership(BaseModel):
    id: str
    draft_bundle_id: str
    entity_type: PackDraftEntityType
    entity_id: str
    entity_slug: str
    catalog_item_id: str | None = None
    workflow_v2_id: str | None = None
    vsm_v2_id: str | None = None
    ontology_concept_id: str | None = None
    ontology_relation_id: str | None = None
    ontology_axiom_id: str | None = None
    dna_mechanism_id: str | None = None
    policy_id: str | None = None
    created_at_iso: str = ""


__all__ = [
    "LoadedPackBundleV2",
    "PackAgentSpec",
    "PackBundleKind",
    "PackBundleStatus",
    "PackDnaMechanismSpec",
    "PackDraftEntityType",
    "PackDraftMembership",
    "PackHelpArticleSpec",
    "PackInstructionSpec",
    "PackLockFileEntry",
    "PackLockSpec",
    "PackManifestV2",
    "PackPolicySpec",
    "PackQuickActionSpec",
    "PackReadinessStatus",
    "PackScopeType",
    "PackSkillSpec",
    "PackSlotSpec",
    "PackSlotTargetKind",
    "PackSourceOrigin",
    "WorkspacePackActivation",
    "WorkspacePackSlotBinding",
]
