"""Pydantic v2 contracts for Day-0 System Bootstrap Workflows & Autonomous Team Onboarding.

Single source of truth for OpenAPI 3.1 schema generation (`AD-1`, `AD-10`, `FR-28`, `UX-DR3`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas.auth_and_org import (
    PassthroughSecretMetadataResponse,
    WorkspaceDatasourceItem,
    WorkspaceSummaryItem,
)
from orcia_api.schemas.catalog import CatalogItemResponse
from orcia_api.schemas.permission_broker import PermissionBrokerPolicyItem
from orcia_core.bootstrap.models import (
    BootstrapRunStatus,
    BootstrapScopeLevel,
    OntologyLayerLevel,
)
from orcia_core.catalog.models import ScalarValue
from orcia_core.permissions.models import (
    DatasourceScheme,
    ExecutionIdentityMode,
    PlatformRole,
    WorkspaceVisibilityMode,
)


class LlmModelEndpointItem(BaseModel):
    """Registered LLM model endpoint item (`AD-10`, `FR-28`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, max_length=64)
    endpoint_key: str = Field(..., min_length=1, max_length=128)
    provider_slug: str = Field(..., min_length=1, max_length=64)
    model_family: str = Field(..., min_length=1, max_length=64)
    model_name: str = Field(..., min_length=1, max_length=128)
    endpoint_uri: str = Field(..., min_length=8, max_length=512)
    connectivity_verified: bool = Field(default=True)
    is_active: bool = Field(default=True)


class SystemBootstrapWorkflowItem(BaseModel):
    """Pre-embedded `orcia://system/bootstrap/*` workflow definition summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, max_length=64)
    uri: str = Field(..., min_length=16, max_length=128)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1024)
    required_role: str = Field(..., min_length=1, max_length=64)
    scope_level: BootstrapScopeLevel
    deterministic_gate_rules: list[str]
    sha256: str = Field(..., min_length=64, max_length=64)


class SystemBootstrapRunItem(BaseModel):
    """Execution record of a system bootstrap workflow run (`FR-28`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, max_length=64)
    run_key: str = Field(..., min_length=1, max_length=128)
    workflow_uri: str = Field(..., min_length=16, max_length=128)
    scope_level: BootstrapScopeLevel
    target_org_unit_id: str | None = Field(default=None, max_length=64)
    target_workspace_id: str | None = Field(default=None, max_length=64)
    triggered_by_user_id: str = Field(..., min_length=1, max_length=64)
    status: BootstrapRunStatus
    gate_passed: bool
    gate_report: dict[str, object]
    execution_payload: dict[str, object]


class UserOnboardingStateItem(BaseModel):
    """Member onboarding and `init-user` first-login state (`FR-28`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, max_length=64)
    user_email: str = Field(..., min_length=3, max_length=255)
    user_id: str | None = Field(default=None, max_length=64)
    invited_by_user_id: str | None = Field(default=None, max_length=64)
    org_unit_id: str = Field(..., min_length=1, max_length=64)
    human_profile_archetype: str = Field(..., min_length=1, max_length=64)
    assigned_role: PlatformRole
    workspace_ids: list[str]
    init_user_completed: bool
    linked_connectors: list[DatasourceScheme]


class SystemBootstrapStateResponse(BaseModel):
    """Response for `GET /api/v1/bootstrap/state`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workflows: list[SystemBootstrapWorkflowItem]
    llm_endpoints: list[LlmModelEndpointItem]
    orthogonal_families: list[str]
    is_model_orthogonal: bool
    runs: list[SystemBootstrapRunItem]
    onboarding_states: list[UserOnboardingStateItem]
    trace_id: str = Field(..., min_length=32, max_length=32)


class InitOrganizationRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/init-organization` (`AD-10`, `FR-28`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    organization_name: str = Field(..., min_length=2, max_length=128)
    oidc_enabled: bool = Field(default=True)
    local_argon2id_enabled: bool = Field(default=True)
    rbac_role_mappings: dict[str, str] = Field(default_factory=dict)
    llm_endpoints: list[LlmModelEndpointItem] = Field(..., min_length=1, max_length=16)


class InitOrganizationResponse(BaseModel):
    """Response for `POST /api/v1/bootstrap/init-organization`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run: SystemBootstrapRunItem
    orthogonal_families: list[str]
    trace_id: str = Field(..., min_length=32, max_length=32)


class OntologyTermInputItem(BaseModel):
    """Ontology concept proposed during `init-workspace` (`3_TEAM` / `3_WORKSPACE`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    term_key: str = Field(..., min_length=1, max_length=64)
    definition: str = Field(..., min_length=3, max_length=512)
    level: OntologyLayerLevel = Field(default="3_WORKSPACE")


class WorkspaceBootstrapInputItem(BaseModel):
    """Solution Workspace creation item inside `InitWorkspaceRequest`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=128)
    visibility_mode: WorkspaceVisibilityMode = Field(default="STANDARD")
    notification_channel: str = Field(default="#workspace-alerts", min_length=1, max_length=64)
    workspace_override_scalars: dict[str, ScalarValue] = Field(default_factory=dict)
    workspace_ontology_terms: list[OntologyTermInputItem] = Field(
        default_factory=list, max_length=20
    )


class MemberInvitationInputItem(BaseModel):
    """Invited team member item inside `InitWorkspaceRequest`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: str = Field(..., min_length=3, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=128)
    human_profile_archetype: str = Field(..., min_length=1, max_length=64)
    role: PlatformRole = Field(default="CONTRIBUTOR")


class InitWorkspaceRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/init-workspace` (`AD-14`, `FR-28`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    team_slug: str = Field(..., min_length=2, max_length=64)
    team_name: str = Field(..., min_length=2, max_length=128)
    parent_org_unit_id: str = Field(..., min_length=1, max_length=64)
    subteam_slug: str | None = Field(default=None, min_length=2, max_length=64)
    subteam_name: str | None = Field(default=None, min_length=2, max_length=128)
    team_override_scalars: dict[str, ScalarValue] = Field(default_factory=dict)
    team_ontology_terms: list[OntologyTermInputItem] = Field(default_factory=list, max_length=20)
    workspaces: list[WorkspaceBootstrapInputItem] = Field(..., min_length=1, max_length=10)
    invited_members: list[MemberInvitationInputItem] = Field(default_factory=list, max_length=50)


class InitWorkspaceResponse(BaseModel):
    """Response for `POST /api/v1/bootstrap/init-workspace`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run: SystemBootstrapRunItem
    workspaces: list[WorkspaceSummaryItem]
    onboarding_states: list[UserOnboardingStateItem]
    trace_id: str = Field(..., min_length=32, max_length=32)


class InitDatasourceRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/init-datasource` (`UX-DR3`, `FR-28`, `AD-16`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(..., min_length=1, max_length=128)
    alias: str = Field(..., min_length=1, max_length=64)
    scheme: DatasourceScheme
    uri: str = Field(..., min_length=6, max_length=512)
    role: str = Field(..., min_length=1, max_length=64)
    execution_identity: ExecutionIdentityMode = Field(default="passthrough")
    freshness_ttl_days: int = Field(..., ge=-3650, le=10000)
    cql_filter: str | None = Field(default=None, max_length=512)
    jql_filter: str | None = Field(default=None, max_length=512)
    permission_broker_markdown: str = Field(..., min_length=10, max_length=16384)
    human_anchor_justification: str = Field(..., min_length=1, max_length=4096)
    human_anchor_signature: str = Field(..., min_length=1, max_length=256)
    human_anchor_author_id: str | None = Field(default=None, max_length=64)
    visibility_scope: Literal["SHARED_WORKSPACE", "SHARED_TEAM"] = Field(default="SHARED_WORKSPACE")


class InitDatasourceResponse(BaseModel):
    """Response for `POST /api/v1/bootstrap/init-datasource`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run: SystemBootstrapRunItem
    datasource: WorkspaceDatasourceItem
    policy: PermissionBrokerPolicyItem
    catalog_item: CatalogItemResponse
    trace_id: str = Field(..., min_length=32, max_length=32)


class InitUserPassthroughSecretItem(BaseModel):
    """Passthrough secret item inside `InitUserRequest` (`AES-256-GCM`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    connector_scheme: DatasourceScheme
    target_host: str = Field(..., min_length=1, max_length=255)
    plaintext_secret: str = Field(..., min_length=1, max_length=2048)


class InitUserRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/init-user` (`NFR-SEC-4`, `FR-28`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_email: str | None = Field(default=None, min_length=3, max_length=255)
    confirmed_human_profile_archetype: str = Field(..., min_length=1, max_length=64)
    passthrough_secrets: list[InitUserPassthroughSecretItem] = Field(
        ..., min_length=1, max_length=10
    )


class InitUserResponse(BaseModel):
    """Response for `POST /api/v1/bootstrap/init-user`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run: SystemBootstrapRunItem
    onboarding_state: UserOnboardingStateItem
    credentials: list[PassthroughSecretMetadataResponse]
    trace_id: str = Field(..., min_length=32, max_length=32)


class WelcomeSetupFirstAdminRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/welcome-setup/first-admin` (`Story 9.2`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    email: str = Field(..., min_length=3, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=8, max_length=256)
    orcia_env: str = Field(default="local", min_length=1, max_length=32)
    bootstrap_token: str | None = Field(default=None, max_length=256)


class WelcomeSetupFirstAdminResponse(BaseModel):
    """Response for `POST /api/v1/bootstrap/welcome-setup/first-admin` (`Story 9.2`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str = Field(..., min_length=1, max_length=64)
    email: str = Field(..., min_length=3, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=128)
    platform_role: Literal["PLATFORM_ADMIN"]
    orcia_env: str = Field(..., min_length=1, max_length=32)
    sql_lock_statement: str = Field(..., min_length=1, max_length=128)
    trace_id: str = Field(..., min_length=32, max_length=32)


class ProgressiveLlmEndpointRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/welcome-setup/progressive-llm` (`Story 9.2`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    endpoint_key: str = Field(..., min_length=1, max_length=128)
    provider_slug: str = Field(..., min_length=1, max_length=64)
    model_family: str = Field(..., min_length=1, max_length=64)
    model_name: str = Field(..., min_length=1, max_length=128)
    endpoint_uri: str = Field(..., min_length=8, max_length=512)


class LlmConnectionTestRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/welcome-setup/llm-test`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_slug: str = Field(default="", max_length=128)
    model_name: str = Field(default="", max_length=128)
    endpoint_uri: str = Field(default="", max_length=512)
    auth_mode: Literal["api_key", "env_var", "none_local"] = Field(default="api_key")
    api_key: str | None = Field(default=None, max_length=512)
    api_key_configured: bool = Field(default=False)


class LlmConnectionTestResponse(BaseModel):
    """Response for `POST /api/v1/bootstrap/welcome-setup/llm-test`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool
    status: Literal["CONNECTED", "INVALID_PARAMETERS", "AUTH_REQUIRED"]
    latency_ms: int = Field(..., ge=0, le=60000)
    provider_slug: str
    model_name: str
    endpoint_uri: str
    auth_mode: Literal["api_key", "env_var", "none_local"]
    message_fr: str
    message_en: str
    trace_id: str = Field(..., min_length=32, max_length=32)


class AccostageStatusResponse(BaseModel):
    """Response for `GET /api/v1/bootstrap/accostage-status` & progressive LLM registration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    completed_count: int = Field(..., ge=1, le=6)
    total_count: int = Field(..., ge=6, le=6)
    badge_label: str = Field(..., min_length=1, max_length=64)
    llm_tier_mode: Literal[
        "UNCONFIGURED",
        "QUICK_TRIAL_SINGLE_FAMILY",
        "FULL_ORTHOGONAL_AD10",
    ]
    distinct_families: list[str]
    assistant_trial_enabled: bool
    agentic_gates_ad10_enabled: bool
    amber_warning_badge: str | None = Field(default=None, max_length=512)
    completed_milestone_keys: list[str]
    first_admin_initialized: bool = Field(default=False)
    first_admin_email: str | None = Field(default=None, max_length=255)
    first_admin_display_name: str | None = Field(default=None, max_length=128)
    trace_id: str = Field(..., min_length=32, max_length=32)


class PlatformSetupStatePutRequest(BaseModel):
    """Request payload for `PUT /api/v1/bootstrap/platform-setup-state` (`Epics 8..12`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    org_units: list[dict[str, object]] = Field(default_factory=list)
    rbac_grants: list[dict[str, object]] = Field(default_factory=list)
    llm_tiers: list[dict[str, object]] = Field(default_factory=list)
    workspaces: list[dict[str, object]] = Field(default_factory=list)
    datasources: list[dict[str, object]] = Field(default_factory=list)
    packs: list[dict[str, object]] = Field(default_factory=list)
    workflows: list[dict[str, object]] = Field(default_factory=list)
    runs: list[dict[str, object]] = Field(default_factory=list)
    catalog_items: list[dict[str, object]] = Field(default_factory=list)
    ontology_concepts: list[dict[str, object]] = Field(default_factory=list)
    audit_events: list[dict[str, object]] = Field(default_factory=list)


class PlatformSetupStateResponse(BaseModel):
    """Response for `GET` / `PUT /api/v1/bootstrap/platform-setup-state` (`Epics 8..12`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    first_admin_initialized: bool = Field(default=False)
    first_admin_email: str | None = Field(default=None, max_length=255)
    first_admin_display_name: str | None = Field(default=None, max_length=128)
    org_units: list[dict[str, object]] = Field(default_factory=list)
    rbac_grants: list[dict[str, object]] = Field(default_factory=list)
    llm_tiers: list[dict[str, object]] = Field(default_factory=list)
    workspaces: list[dict[str, object]] = Field(default_factory=list)
    datasources: list[dict[str, object]] = Field(default_factory=list)
    packs: list[dict[str, object]] = Field(default_factory=list)
    workflows: list[dict[str, object]] = Field(default_factory=list)
    runs: list[dict[str, object]] = Field(default_factory=list)
    catalog_items: list[dict[str, object]] = Field(default_factory=list)
    ontology_concepts: list[dict[str, object]] = Field(default_factory=list)
    audit_events: list[dict[str, object]] = Field(default_factory=list)
    trace_id: str = Field(..., min_length=32, max_length=32)
