"""Pydantic v2 schemas for Story 1.2 Auth, OrgUnits, Multi-Source Workspaces & 5 Permissions."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.permissions.models import (
    AccessMode,
    AuthMode,
    CatalogPermission,
    CatalogVisibilityScope,
    DatasourceScheme,
    ExecutionIdentityMode,
    OrgUnitType,
    PlatformRole,
    WorkspaceVisibilityMode,
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

    access_token: str = Field(..., min_length=16)
    token_type: Literal["Bearer"] = "Bearer"
    expires_in_seconds: int = Field(default=900, ge=60)
    user_id: str
    email: str
    display_name: str
    platform_role: PlatformRole
    human_profile_archetype: str
    primary_org_unit_id: str
    trace_id: str = Field(..., min_length=32, max_length=32)


class LogoutResponse(BaseModel):
    """Response payload for `POST /api/v1/auth/logout`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    revoked: bool = True
    trace_id: str = Field(..., min_length=32, max_length=32)


class OrgUnitTreeItem(BaseModel):
    """Organizational Unit node in the hierarchical team tree (`org_units`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    slug: str
    name: str
    unit_type: OrgUnitType
    parent_id: str | None = None


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
    visibility_mode: WorkspaceVisibilityMode
    effective_role: PlatformRole
    access_mode: AccessMode
    access_origin: Literal["DIRECT_TEAM", "ROLLUP_PARENT", "PARTNER_INVITE", "GLOBAL_ADMIN"]
    finops_cost_usd: float | None = None
    datasources: list[WorkspaceDatasourceItem]


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


class UserPreferencesUpdateRequest(BaseModel):
    """Story 9.4 — Request payload for `PATCH /api/v1/users/me/preferences` (`0 ms` Anti-FOUC)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    theme: Literal["light", "dark", "system"] | None = None
    locale: Literal["fr", "en"] | None = None
    default_hat: str | None = Field(default=None, min_length=1, max_length=64)
    auto_open_contextual_help: bool | None = None
    notifications_enabled: bool | None = None


class UserPreferencesResponse(BaseModel):
    """Story 9.4 — Response payload for `/api/v1/users/me/preferences`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str
    theme: Literal["light", "dark", "system"]
    locale: Literal["fr", "en"]
    default_hat: str
    auto_open_contextual_help: bool
    notifications_enabled: bool
    assistant_behavior_redirect_uri: str
    trace_id: str | None = None


class McpPersonalTokenCreateRequest(BaseModel):
    """Story 9.4 — Request payload for `POST /api/v1/users/me/mcp-tokens` (`pat_mcp_*`, SHA-256)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(default="Clé IDE MCP", min_length=1, max_length=120)
    expires_in_days: int = Field(default=30)
    rpm_limit: int = Field(default=60, ge=1, le=600)
    allowed_workspace_slugs: list[str] = Field(default_factory=lambda: ["ws-claims-alpha"])
    exposed_capabilities: list[
        Literal["ASSISTANT", "PUBLISHED_AGENTS", "KB_GLOSSARY_SEARCH", "STAGED_DRAFTS"]
    ] = ["ASSISTANT", "KB_GLOSSARY_SEARCH"]
    target_kind: Literal["SPACE", "AGENT"] = "SPACE"
    target_slug: str = Field(default="ws-claims-alpha", min_length=1, max_length=120)


class McpPersonalTokenMetadataItem(BaseModel):
    """Story 9.4 — Metadata item for a personal IDE/MCP token (`SHA-256` at rest)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token_id: str
    user_id: str
    label: str
    token_prefix: str
    token_sha256: str
    expires_in_days: Literal[30, 90]
    rpm_limit: int
    allowed_workspace_slugs: list[str]
    exposed_capabilities: list[
        Literal["ASSISTANT", "PUBLISHED_AGENTS", "KB_GLOSSARY_SEARCH", "STAGED_DRAFTS"]
    ]
    target_kind: Literal["SPACE", "AGENT"]
    target_slug: str
    mcp_endpoint_uri: str
    ide_json_snippet: str
    revoked: bool


class McpPersonalTokenIssuedResponse(BaseModel):
    """Story 9.4 — One-time issuance response returning `plaintext_token` (`pat_mcp_*`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plaintext_token: str
    record: McpPersonalTokenMetadataItem
    trace_id: str | None = None


class McpPersonalTokenListResponse(BaseModel):
    """Story 9.4 — List of personal IDE/MCP token metadata items."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tokens: list[McpPersonalTokenMetadataItem]
    trace_id: str | None = None
