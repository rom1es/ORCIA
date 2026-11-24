"""Pydantic v2 schemas for Story 1.2 Auth, OrgUnits, Multi-Source Workspaces & 5 Permissions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas._auth_mcp_tokens import (
    McpPersonalTokenCreateRequest,
    McpPersonalTokenIssuedResponse,
    McpPersonalTokenListResponse,
    McpPersonalTokenMetadataItem,
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
)
from orcia_api.schemas.org_unit_models import (
    AttachedWorkspaceRefResponse,
    KnownOrgUserResponse,
    KnownOrgUsersSearchResponse,
    OrgUnitCreateRequest,
    OrgUnitDeleteResponse,
    OrgUnitInviteUserRequest,
    OrgUnitInviteUserResponse,
    OrgUnitPatchRequest,
    OrgUnitResponse,
    OrgUnitsListResponse,
    OrgUnitTreeItem,
)
from orcia_core.permissions.models import (
    AccessMode,
    AuthMode,
    CatalogPermission,
    CatalogVisibilityScope,
    DatasourceScheme,
    ExecutionIdentityMode,
    PlatformRole,
)


class LocalLoginRequest(BaseModel):
    """Request payload for `POST /api/v1/auth/login/local` (Argon2id + optional TOTP MFA)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)
    totp_code: str | None = Field(default=None, min_length=6, max_length=6)


class OidcLoginRequest(BaseModel):
    """Request payload for `POST /api/v1/auth/login/oidc` (Enterprise SSO OIDC / OAuth 2.1)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    oidc_subject: str = Field(..., min_length=3, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=255)


class AuthTokenResponse(BaseModel):
    """Response payload for authentication and session refresh endpoints (AD-6)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    access_token: str = Field(default="", max_length=4096)
    token_type: Literal["Bearer"] = "Bearer"
    expires_in_seconds: int = Field(default=900, ge=0)
    user_id: str
    email: str
    display_name: str
    platform_role: PlatformRole
    human_profile_archetype: str
    primary_org_unit_id: str
    roles: list[str] = Field(default_factory=list)
    must_change_password: bool = Field(default=False)
    requires_two_factor: bool = Field(default=False)
    challenge_token: str | None = Field(default=None, max_length=255)
    challenge_kind: Literal["EMAIL_OTP", "TOTP", "TOTP_ENROLL"] | None = None
    masked_destination: str | None = Field(default=None, max_length=255)
    totp_provisioning_uri: str | None = Field(default=None, max_length=1024)
    totp_manual_key: str | None = Field(default=None, max_length=128)
    trace_id: str = Field(..., min_length=32, max_length=32)


class LogoutResponse(BaseModel):
    """Response payload for `POST /api/v1/auth/logout`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    revoked: bool = True
    trace_id: str = Field(..., min_length=32, max_length=32)


class WorkspaceDatasourceItem(BaseModel):
    """Federated datasource (`N × git://`, `N × jira://`, `N × confluence://`, `db://`, `nexus://`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: str
    alias: str
    scheme: DatasourceScheme
    uri: str
    role: str
    execution_identity: ExecutionIdentityMode
    freshness_ttl_days: int = Field(..., ge=1)


class WorkspaceSummaryItem(BaseModel):
    """Solution Workspace summary with effective RBAC access and multi-source topology."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    slug: str
    name: str
    owner_org_unit_id: str
    visibility_mode: Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"]
    is_personal: bool = False
    effective_role: PlatformRole
    access_mode: AccessMode
    access_origin: Literal["DIRECT_TEAM", "ROLLUP_PARENT", "PARTNER_INVITE", "GLOBAL_ADMIN"]
    finops_cost_usd: float | None = None
    datasources: list[WorkspaceDatasourceItem]


class WorkspaceCreateRequest(BaseModel):
    """Request payload for `POST /api/v1/workspaces` (`REM-01`, `UUIDv7` + exact `slug`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    visibility_mode: Literal["STANDARD", "CONFIDENTIAL_RESTRICTED", "PRIVATE_USER"] = "STANDARD"
    lifecycle_phase: Literal["BUILD", "RUN", "MIGRATION"] = "BUILD"
    owner_org_unit_id: str | None = Field(default=None, max_length=128)


class WorkspaceCreateResponse(BaseModel):
    """Response payload for `POST /api/v1/workspaces` returning persisted PG18 `UUIDv7` & `slug`."""

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


class WorkspacesListResponse(BaseModel):
    """Consolidated response for `GET /api/v1/workspaces`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspaces: list[WorkspaceSummaryItem]
    consolidated_finops_usd: float
    trace_id: str = Field(..., min_length=32, max_length=32)


class ScopeMutationCheckResponse(BaseModel):
    """Response for `POST /api/v1/workspaces/{workspace_id}/mutations/check`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str
    allowed: bool = True
    effective_role: PlatformRole
    access_mode: AccessMode
    trace_id: str = Field(..., min_length=32, max_length=32)


class UserMeResponse(BaseModel):
    """Complete Human Profile, OrgUnit tree, and accessible Workspaces for `GET /api/v1/auth/me`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    email: str
    display_name: str
    auth_mode: AuthMode
    human_profile_archetype: str
    platform_role: PlatformRole
    primary_org_unit_id: str
    totp_enabled: bool
    roles: list[str] = Field(default_factory=list)
    must_change_password: bool = Field(default=False)
    transverse_groups: list[str]
    org_units: list[OrgUnitTreeItem]
    workspaces: list[WorkspaceSummaryItem]
    consolidated_finops_usd: float
    modules: dict[str, bool]
    trace_id: str = Field(..., min_length=32, max_length=32)


class CatalogResourceInspectionResponse(BaseModel):
    """Evaluated 5 permissions for a catalog resource (`/inspect`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_id: str
    resource_uri: str
    title: str
    visibility_scope: CatalogVisibilityScope
    granted_permissions: list[CatalogPermission]
    source_masked: bool
    trace_id: str = Field(..., min_length=32, max_length=32)


class CatalogResourceSourceResponse(BaseModel):
    """Protected internal source payload requiring `READ_SOURCE` (`AD-6`, `FR-21`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    resource_id: str
    resource_uri: str
    system_prompt_secret: str
    trace_id: str = Field(..., min_length=32, max_length=32)


class PassthroughSecretStoreRequest(BaseModel):
    """Request payload to encrypt and store a user Passthrough secret in AES-256-GCM."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    connector_scheme: DatasourceScheme
    target_host: str = Field(..., min_length=1, max_length=255)
    plaintext_secret: str = Field(..., min_length=1, max_length=4096)


class PassthroughSecretMetadataResponse(BaseModel):
    """Metadata returned after storing an AES-256-GCM Passthrough credential."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    user_id: str
    connector_scheme: DatasourceScheme
    target_host: str
    key_version: int
    encrypted_at_rest: bool = True
    trace_id: str = Field(..., min_length=32, max_length=32)


__all__ = [
    "AttachedWorkspaceRefResponse",
    "AuthTokenResponse",
    "KnownOrgUserResponse",
    "KnownOrgUsersSearchResponse",
    "LocalLoginRequest",
    "LogoutResponse",
    "McpPersonalTokenCreateRequest",
    "McpPersonalTokenIssuedResponse",
    "McpPersonalTokenListResponse",
    "McpPersonalTokenMetadataItem",
    "OidcLoginRequest",
    "OrgUnitCreateRequest",
    "OrgUnitDeleteResponse",
    "OrgUnitInviteUserRequest",
    "OrgUnitInviteUserResponse",
    "OrgUnitPatchRequest",
    "OrgUnitResponse",
    "OrgUnitsListResponse",
    "OrgUnitTreeItem",
    "UserPreferencesResponse",
    "UserPreferencesUpdateRequest",
    "WorkspaceCreateRequest",
    "WorkspaceCreateResponse",
    "WorkspaceDatasourceItem",
    "WorkspaceSummaryItem",
]
