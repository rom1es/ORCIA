"""Pure domain models for Organizational Units, Multi-Source Workspaces, Identity & 5 Permissions.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

OrgUnitType = Literal["ENTERPRISE", "BU", "TRIBE", "TEAM", "SUB_TEAM"]
AuthMode = Literal["OIDC", "LOCAL", "HYBRID"]
PlatformRole = Literal[
    "PLATFORM_ADMIN",
    "BU_DIRECTOR",
    "TEAM_LEAD",
    "CONTRIBUTOR",
    "GATE_REVIEWER",
    "ONTOLOGY_STEWARD_L3",
    "OBSERVER",
]
WorkspaceVisibilityMode = Literal["STANDARD", "CONFIDENTIAL_RESTRICTED"]
# Dynamic connector scheme backed by `list_registered_connector_schemes()` (`AD-20`, `AC-E3`)
DatasourceScheme = str
ExecutionIdentityMode = Literal["passthrough", "service_principal"]
AccessMode = Literal["CONTRIBUTOR_ACTION_REQUIRED", "READ_ONLY_OBSERVER"]
CatalogVisibilityScope = Literal[
    "DRAFT",
    "SHARED_WORKSPACE",
    "SHARED_TEAM",
    "SHARED_BU",
    "PUBLISHED_ORG",
    "PENDING_APPROVAL",
]
CatalogPermission = Literal["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"]


@dataclass(frozen=True, slots=True)
class OrgUnitNode:
    """Node in the hierarchical organizational tree (`org_units`, AD-6, AD-14)."""

    id: str
    slug: str
    name: str
    unit_type: OrgUnitType
    parent_id: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceDatasourceEntity:
    """Federated datasource attached to a Solution Workspace (`1..N` per scheme, AD-14)."""

    id: str
    workspace_id: str
    alias: str
    scheme: DatasourceScheme
    uri: str
    role: str
    execution_identity: ExecutionIdentityMode = "passthrough"
    freshness_ttl_days: int = 90


@dataclass(frozen=True, slots=True)
class WorkspaceEntity:
    """Solution Workspace aggregating multiple datasources decoupled from OrgUnits (AD-6, AD-14)."""

    id: str
    slug: str
    name: str
    owner_org_unit_id: str
    visibility_mode: WorkspaceVisibilityMode = "STANDARD"
    finops_cost_usd: float = 0.0
    datasources: tuple[WorkspaceDatasourceEntity, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class WorkspaceMembershipEntity:
    """Direct user or invited partner team membership on a specific Workspace."""

    id: str
    workspace_id: str
    role: PlatformRole
    access_mode: AccessMode
    user_id: str | None = None
    invited_org_unit_id: str | None = None


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """Authenticated user identity supporting Hybrid Bi-Mode (OIDC + Local Argon2id/TOTP)."""

    id: str
    email: str
    display_name: str
    auth_mode: AuthMode
    human_profile_archetype: str
    platform_role: PlatformRole
    primary_org_unit_id: str
    oidc_subject: str | None = None
    password_hash_argon2id: str | None = None
    totp_secret: str | None = None
    totp_enabled: bool = False
    transverse_groups: tuple[str, ...] = field(default_factory=tuple)
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class CatalogAclEntry:
    """Catalog resource ACL entry carrying the 5 dissociated permissions (AD-6)."""

    id: str
    resource_id: str
    resource_uri: str
    title: str
    visibility_scope: CatalogVisibilityScope
    owner_org_unit_id: str
    owner_workspace_id: str | None = None
    grantee_org_unit_id: str | None = None
    grantee_workspace_id: str | None = None
    grantee_transverse_group: str | None = None
    can_discover: bool = True
    can_execute: bool = False
    can_read_source: bool = False
    can_edit: bool = False
    can_admin: bool = False
    system_prompt_secret: str = ""


@dataclass(frozen=True, slots=True)
class EffectiveResourcePermissions:
    """Evaluated 5 dissociated permissions for a caller on a catalog resource."""

    resource_id: str
    resource_uri: str
    title: str
    visibility_scope: CatalogVisibilityScope
    can_discover: bool
    can_execute: bool
    can_read_source: bool
    can_edit: bool
    can_admin: bool

    @property
    def source_masked(self) -> bool:
        """True when internal prompt/code is protected in black-box mode (`READ_SOURCE=False`)."""
        return not self.can_read_source

    @property
    def granted_permissions(self) -> tuple[CatalogPermission, ...]:
        """Return the tuple of granted permission keys."""
        granted: list[CatalogPermission] = []
        if self.can_discover:
            granted.append("DISCOVER")
        if self.can_execute:
            granted.append("EXECUTE")
        if self.can_read_source:
            granted.append("READ_SOURCE")
        if self.can_edit:
            granted.append("EDIT")
        if self.can_admin:
            granted.append("ADMIN")
        return tuple(granted)


@dataclass(frozen=True, slots=True)
class WorkspaceAccessSummary:
    """Evaluated access rights and FinOps roll-up state for a caller on a Workspace."""

    workspace: WorkspaceEntity
    effective_role: PlatformRole
    access_mode: AccessMode
    access_origin: Literal["DIRECT_TEAM", "ROLLUP_PARENT", "PARTNER_INVITE", "GLOBAL_ADMIN"]
    finops_visible: bool


@dataclass(frozen=True, slots=True)
class PassthroughCredentialRecord:
    """Encrypted Passthrough credential stored in `AES-256-GCM` (`NFR-SEC-4`)."""

    id: str
    user_id: str
    connector_scheme: DatasourceScheme
    target_host: str
    ciphertext_b64: str
    nonce_b64: str
    key_version: int = 1
