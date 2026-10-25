"""Pure domain models for Bounded Context 3: Federated Multi-Source Catalog & 4-Layer Overrides.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

from orcia_core.permissions.models import CatalogVisibilityScope

FederatedScheme = Literal["git", "nexus", "db", "confluence", "jira", "orcia"]
CatalogResourceType = Literal["workflow", "agent", "skill", "template", "datasource"]
CatalogSourceFormat = Literal["ORCIA", "BMAD_PACK"]
AdaptiveGatePolicy = Literal["STRICT", "STANDARD", "FAST_TRACK"]
OverrideLayer = Literal["TEAM", "WORKSPACE", "USER"]
ArchiveFormat = Literal["tar.gz", "zip", "none"]

CATALOG_PROMOTION_ORDER: tuple[CatalogVisibilityScope, ...] = (
    "DRAFT",
    "SHARED_WORKSPACE",
    "SHARED_TEAM",
    "SHARED_BU",
    "PENDING_APPROVAL",
    "PUBLISHED_ORG",
)


@dataclass(frozen=True, slots=True)
class ParsedFederatedUri:
    """Structured representation of a canonical federated URI (`AD-5`, `FR-20`)."""

    raw_uri: str
    scheme: FederatedScheme
    authority: str
    path: str
    version_or_ref: str
    expected_sha256: str | None = None
    archive_format: ArchiveFormat = "none"


@dataclass(frozen=True, slots=True)
class CasObjectEntry:
    """Immutable Content-Addressable Storage object stored under `cas/<sha256>` (`AD-5`)."""

    sha256: str
    cas_key: str
    content_bytes: bytes
    content_type: str = "application/json"
    source_uri: str = ""

    @property
    def content_text(self) -> str:
        """Decode UTF-8 text payload."""
        return self.content_bytes.decode("utf-8", errors="replace")


@dataclass(frozen=True, slots=True)
class CasResolutionResult:
    """Result of resolving a federated URI against the `cas/<sha256>` cache (`NFR-PERF-3`)."""

    uri: str
    scheme: FederatedScheme
    resolved_version: str
    sha256: str
    cas_key: str
    cache_hit: bool
    resolution_ms: float
    content_text: str


@dataclass(frozen=True, slots=True)
class CatalogItemEntity:
    """Federated catalog item with hierarchical publication scope (`FR-20`, `FR-21`)."""

    id: str
    resource_id: str
    uri: str
    scheme: FederatedScheme
    title: str
    description: str
    resource_type: CatalogResourceType
    source_format: CatalogSourceFormat
    version: str
    sha256: str
    cas_key: str
    visibility_scope: CatalogVisibilityScope
    owner_org_unit_id: str
    owner_workspace_id: str | None = None
    content_payload: str = ""

    @property
    def sha256_short(self) -> str:
        """Return the first 12 hex characters of `sha256` for `uri-badge` display (`UX-DR8`)."""
        return self.sha256[:12]


@dataclass(frozen=True, slots=True)
class EvaluationLensDefinition:
    """Orthogonal evaluation lens configuration in a workflow definition (`AD-10`, `AD-14`)."""

    code: str
    weight: float
    threshold: float


@dataclass(frozen=True, slots=True)
class WorkflowStepDefinition:
    """Ordered workflow step definition (`ORCIA` native or imported from `BMAD_PACK`)."""

    step_key: str
    title: str
    instructions: str
    human_authored_required: bool = False


ScalarValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class WorkflowDefinitionEntity:
    """Immutable workflow definition supporting 4-layer overrides and BMAD packs (`AD-14`)."""

    id: str
    workspace_id: str | None
    uri: str
    title: str
    description: str
    version: str
    source_format: CatalogSourceFormat
    adaptive_gate_policy: AdaptiveGatePolicy
    scalars: dict[str, ScalarValue]
    datasources: tuple[str, ...]
    rules: tuple[str, ...]
    facts: tuple[str, ...]
    lenses: tuple[EvaluationLensDefinition, ...]
    steps: tuple[WorkflowStepDefinition, ...]
    sha256: str
    customize_metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CustomizationOverrideEntity:
    """Declarative override layer (`TEAM`, `WORKSPACE`, `USER`) applied over a base workflow."""

    id: str
    override_key: str
    target_uri: str
    override_layer: OverrideLayer
    org_unit_id: str | None = None
    workspace_id: str | None = None
    user_id: str | None = None
    scalars: dict[str, ScalarValue] = field(default_factory=dict)
    datasources: tuple[str, ...] = field(default_factory=tuple)
    rules: tuple[str, ...] = field(default_factory=tuple)
    facts: tuple[str, ...] = field(default_factory=tuple)
    lenses: tuple[EvaluationLensDefinition, ...] = field(default_factory=tuple)
    sha256: str = ""


@dataclass(frozen=True, slots=True)
class RunLockSourceTriplet:
    """Pinned `(alias, uri, resolved_version, sha256)` entry inside `run-lock.json` (`AD-5`)."""

    alias: str
    scheme: FederatedScheme
    uri: str
    resolved_version: str
    sha256: str
    cas_key: str


@dataclass(frozen=True, slots=True)
class RunLockManifest:
    """Cryptographic `run-lock.json` manifest pinning all sources and 4-layer overrides (`AD-5`)."""

    workspace_id: str
    workflow_uri: str
    workflow_version: str
    workflow_sha256: str
    effective_workflow_sha256: str
    applied_override_keys: tuple[str, ...]
    sources: tuple[RunLockSourceTriplet, ...]
    manifest_sha256: str

    def to_dict(self) -> dict[str, object]:
        """Return canonical dictionary representation of `run-lock.json`."""
        return {
            "workspace_id": self.workspace_id,
            "workflow_uri": self.workflow_uri,
            "workflow_version": self.workflow_version,
            "workflow_sha256": self.workflow_sha256,
            "effective_workflow_sha256": self.effective_workflow_sha256,
            "applied_override_keys": list(self.applied_override_keys),
            "sources": [
                {
                    "alias": s.alias,
                    "scheme": s.scheme,
                    "uri": s.uri,
                    "resolved_version": s.resolved_version,
                    "sha256": s.sha256,
                    "cas_key": s.cas_key,
                }
                for s in self.sources
            ],
            "manifest_sha256": self.manifest_sha256,
        }

    def to_json(self) -> str:
        """Serialize `run-lock.json` deterministically."""
        return json.dumps(self.to_dict(), sort_keys=True, indent=2)


@dataclass(frozen=True, slots=True)
class BmadSkillStepFile:
    """Single Markdown step file (`steps/step-XX-*.md`) in a BMAD skill pack (`AR-5`)."""

    filename: str
    content_markdown: str


@dataclass(frozen=True, slots=True)
class BmadSkillPackInput:
    """Input payload for lossless BMAD skill pack import (`SKILL.md` + `customize.toml`)."""

    uri: str
    skill_markdown: str
    customize_toml: str = ""
    steps: tuple[BmadSkillStepFile, ...] = field(default_factory=tuple)
    workspace_id: str | None = None
    owner_org_unit_id: str = "0192c4e0-0000-7000-8000-000000000104"
