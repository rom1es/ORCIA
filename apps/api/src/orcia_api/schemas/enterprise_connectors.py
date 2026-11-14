"""OpenAPI 3.1 / Pydantic v2 transport schemas for Story 17.4 Enterprise Connectors & RAG Referent.

Kept exclusively in `apps/api/src/orcia_api/schemas/` — never inside `orcia-core` (`AD-19`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EnterpriseConnectorKindLiteral = Literal[
    "GITLAB", "JIRA", "CONFLUENCE", "OIDC_SSO", "S3_OBJECT_STORE"
]
EnterpriseConnectorAuthModeLiteral = Literal[
    "OAUTH2_PASSTHROUGH", "PERSONAL_ACCESS_TOKEN", "OIDC_FEDERATION", "SERVICE_SECRET"
]
SyncIdentityModeLiteral = Literal["SERVICE_ACCOUNT", "TEAM_REFERENT_USER"]
DatasourceSyncStatusLiteral = Literal["ACTIVE", "PAUSED_REFERENT_RENEWAL_REQUIRED"]
DatasourceSyncReasonLiteral = Literal[
    "REFERENT_LEFT_TEAM", "REFERENT_ACCOUNT_DISABLED", "REFERENT_TOKEN_MISSING"
]

SourceNatureLiteral = Literal["DOCUMENT_KB", "WORK_TRACKER", "SOURCE_CODE", "RELATIONAL_SCHEMA"]
SourceSyncModeLiteral = Literal["WEBHOOK_PUSH", "POLLING_24H"]
SourceFreshnessStatusLiteral = Literal["SYNCED", "STALE", "SYNC_ERROR", "PENDING_INITIAL_SYNC"]
CodegraphAuthModeLiteral = Literal["SERVICE_ACCOUNT", "WORKSPACE_LEAD_TOKEN"]
CodegraphStatusLiteral = Literal[
    "DISABLED", "INDEXING", "READY", "PAUSED_REFERENT_RENEWAL_REQUIRED", "ERROR"
]


class ConnectorSecretStatusResponse(BaseModel):
    """Write-Only secret metadata (`AD-21` — never exposes raw secret)."""

    model_config = ConfigDict(extra="forbid")

    configured: bool
    fingerprint: str | None = None
    updated_at_iso: str | None = None


class EnterpriseConnectorItemResponse(BaseModel):
    """Platform-level Enterprise Connector definition (`Connecteurs & SSO`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    connector_kind: EnterpriseConnectorKindLiteral
    name: str
    base_url: str
    auth_mode: EnterpriseConnectorAuthModeLiteral
    enabled: bool
    admin_secret_status: ConnectorSecretStatusResponse
    created_at_iso: str
    updated_at_iso: str


class EnterpriseConnectorsListResponse(BaseModel):
    """List response for `GET /api/v1/settings/connectors`."""

    model_config = ConfigDict(extra="forbid")

    items: list[EnterpriseConnectorItemResponse]
    trace_id: str


class EnterpriseConnectorCreateRequest(BaseModel):
    """Payload for `POST /api/v1/settings/connectors`."""

    model_config = ConfigDict(extra="forbid")

    connector_kind: EnterpriseConnectorKindLiteral
    name: str = Field(min_length=1, max_length=160)
    base_url: str = Field(min_length=1, max_length=512)
    auth_mode: EnterpriseConnectorAuthModeLiteral
    admin_secret_value: str | None = None
    enabled: bool = True


class EnterpriseConnectorUpdateRequest(BaseModel):
    """Payload for `PATCH /api/v1/settings/connectors/{connector_id}`."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=160)
    base_url: str | None = Field(default=None, max_length=512)
    auth_mode: EnterpriseConnectorAuthModeLiteral | None = None
    enabled: bool | None = None
    admin_secret_value: str | None = None
    clear_admin_secret: bool = False


class EnterpriseConnectorDeleteResponse(BaseModel):
    """Response for `DELETE /api/v1/settings/connectors/{connector_id}`."""

    model_config = ConfigDict(extra="forbid")

    deleted: bool = True
    connector_id: str
    trace_id: str


class UserAccountOrgUnitItemResponse(BaseModel):
    """Read-only summary of an org unit attached to the user for FinOps transparency."""

    model_config = ConfigDict(extra="forbid")

    id: str
    slug: str
    name: str
    unit_type: str
    billing_enabled: bool
    is_lead: bool = False


class UserAccountProfileResponse(BaseModel):
    """User profile identity, active roles, and FinOps attachments for `👤 Mon Compte`."""

    model_config = ConfigDict(extra="forbid")

    principal_id: str
    display_name: str
    email: str
    roles: list[str]
    teams: list[UserAccountOrgUnitItemResponse]
    billing_org_units: list[UserAccountOrgUnitItemResponse]
    trace_id: str


class UserPassthroughConnectorItemResponse(BaseModel):
    """Per-user connection status for one Enterprise Connector (`Mon Compte`)."""

    model_config = ConfigDict(extra="forbid")

    connector_id: str
    connector_name: str
    connector_kind: EnterpriseConnectorKindLiteral
    base_url: str
    auth_mode: EnterpriseConnectorAuthModeLiteral
    connected: bool
    external_author_login: str | None = None
    secret_status: ConnectorSecretStatusResponse


class UserPassthroughTokensListResponse(BaseModel):
    """List response for `GET /api/v1/users/me/passthrough-tokens`."""

    model_config = ConfigDict(extra="forbid")

    items: list[UserPassthroughConnectorItemResponse]
    trace_id: str


class UpsertPassthroughTokenRequest(BaseModel):
    """Payload for `PUT /api/v1/users/me/passthrough-tokens/{connector_id}`."""

    model_config = ConfigDict(extra="forbid")

    external_author_login: str | None = Field(default=None, max_length=160)
    secret_value: str = Field(min_length=1)


class RevokePassthroughTokenResponse(BaseModel):
    """Response for `DELETE /api/v1/users/me/passthrough-tokens/{connector_id}`."""

    model_config = ConfigDict(extra="forbid")

    revoked: bool = True
    connector_id: str
    trace_id: str


class WorkspaceDatasourceItemResponse(BaseModel):
    """Workspace datasource with deterministic RAG health (`CA-17.4.3`) & Codegraph."""

    model_config = ConfigDict(extra="forbid")

    id: str
    workspace_id: str
    alias: str
    scheme: str
    uri: str
    connector_id: str | None = None
    sync_identity_mode: SyncIdentityModeLiteral = "SERVICE_ACCOUNT"
    service_account_id: str | None = None
    referent_user_id: str | None = None
    sync_status: DatasourceSyncStatusLiteral = "ACTIVE"
    sync_status_reason: DatasourceSyncReasonLiteral | None = None
    created_at_iso: str
    # Story 18.1 Multi-Nature & Codegraph
    source_nature: SourceNatureLiteral = "DOCUMENT_KB"
    sync_mode: SourceSyncModeLiteral = "POLLING_24H"
    target_scope: str | None = None
    target_ref: str | None = None
    last_sync_at_iso: str | None = None
    last_probe_at_iso: str | None = None
    fingerprint_hash: str | None = None
    freshness_status: SourceFreshnessStatusLiteral = "PENDING_INITIAL_SYNC"
    codegraph_enabled: bool = False
    codegraph_auth_mode: CodegraphAuthModeLiteral = "SERVICE_ACCOUNT"
    codegraph_owner_user_id: str | None = None
    codegraph_status: CodegraphStatusLiteral = "DISABLED"
    codegraph_status_reason: str | None = None
    codegraph_last_indexed_at_iso: str | None = None
    codegraph_head_sha: str | None = None


class WorkspaceDatasourcesListResponse(BaseModel):
    """List response for `GET /api/v1/workspaces/{workspace_id}/datasources`."""

    model_config = ConfigDict(extra="forbid")

    items: list[WorkspaceDatasourceItemResponse]
    trace_id: str


class CreateWorkspaceDatasourceRequest(BaseModel):
    """Payload for `POST /api/v1/workspaces/{workspace_id}/datasources`."""

    model_config = ConfigDict(extra="forbid")

    alias: str = Field(min_length=1, max_length=128)
    scheme: str = Field(min_length=1, max_length=32)
    uri: str = Field(min_length=1)
    connector_id: str | None = None
    sync_identity_mode: SyncIdentityModeLiteral = "SERVICE_ACCOUNT"
    service_account_id: str | None = Field(default=None, max_length=128)
    referent_user_id: str | None = Field(default=None, max_length=128)
    # Story 18.1 Multi-Nature & Codegraph
    source_nature: SourceNatureLiteral | None = None
    sync_mode: SourceSyncModeLiteral = "POLLING_24H"
    target_scope: str | None = Field(default=None, max_length=255)
    target_ref: str | None = Field(default=None, max_length=128)
    codegraph_enabled: bool = False
    codegraph_auth_mode: CodegraphAuthModeLiteral = "SERVICE_ACCOUNT"
    codegraph_owner_user_id: str | None = Field(default=None, max_length=128)


class UpdateWorkspaceDatasourceRequest(BaseModel):
    """Payload for `PATCH /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}`."""

    model_config = ConfigDict(extra="forbid")

    alias: str | None = Field(default=None, max_length=128)
    uri: str | None = None
    connector_id: str | None = None
    sync_identity_mode: SyncIdentityModeLiteral | None = None
    service_account_id: str | None = Field(default=None, max_length=128)
    referent_user_id: str | None = Field(default=None, max_length=128)
    # Story 18.1 Multi-Nature & Codegraph
    source_nature: SourceNatureLiteral | None = None
    sync_mode: SourceSyncModeLiteral | None = None
    target_scope: str | None = Field(default=None, max_length=255)
    target_ref: str | None = Field(default=None, max_length=128)
    codegraph_enabled: bool | None = None
    codegraph_auth_mode: CodegraphAuthModeLiteral | None = None
    codegraph_owner_user_id: str | None = Field(default=None, max_length=128)


class WorkspaceDatasourceDeleteResponse(BaseModel):
    """Response for `DELETE /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}`."""

    model_config = ConfigDict(extra="forbid")

    deleted: bool = True
    workspace_id: str
    datasource_id: str
    trace_id: str


class TriggerWorkspaceDatasourceSyncResponse(BaseModel):
    """Response for `POST /api/v1/workspaces/{workspace_id}/datasources/{datasource_id}/sync`."""

    model_config = ConfigDict(extra="forbid")

    datasource: WorkspaceDatasourceItemResponse
    trace_id: str
