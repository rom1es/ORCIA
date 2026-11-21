"""Extracted Day-0 Welcome Setup, Accostage & Platform Setup State Schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.permissions.models import DatasourceScheme


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
    access_token: str | None = Field(default=None)
    must_change_password: bool = Field(default=False)
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


class AccostageMilestoneItem(BaseModel):
    """Role-filtered Day-0 Accostage milestone exposed by `/accostage-status` (`Story 24.5`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(..., ge=1, le=6)
    key: str = Field(..., min_length=1, max_length=64)
    title_fr: str = Field(..., min_length=1, max_length=128)
    title_en: str = Field(..., min_length=1, max_length=128)
    target_route: str = Field(..., min_length=1, max_length=128)
    completed: bool
    is_accessible: bool


class AccostageStatusResponse(BaseModel):
    """Response for `GET /api/v1/bootstrap/accostage-status` & progressive LLM registration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    completed_count: int = Field(..., ge=0, le=6)
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
    platform_admin_display_name: str | None = Field(default=None, max_length=128)
    visible_milestones: list[AccostageMilestoneItem] = Field(default_factory=list)
    admin_created: bool = Field(default=False)
    users_count: int = Field(default=0, ge=0)
    org_units_count: int = Field(default=0, ge=0)
    workspaces_count: int = Field(default=0, ge=0)
    models_count: int = Field(default=0, ge=0)
    sources_count: int = Field(default=0, ge=0)
    workflows_count: int = Field(default=0, ge=0)
    boot_epoch: str | None = Field(default=None, max_length=64)
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


class PlatformSetupStatePublicResponse(BaseModel):
    """Minimal unauthenticated Day-0 projection (`Story 26.1`, `AD-21`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_initialized: bool = Field(default=False)
    step: str = Field(..., min_length=1, max_length=64)


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


class InitUserPassthroughSecretItem(BaseModel):
    """Passthrough secret item inside `InitUserRequest` (`AES-256-GCM`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    connector_scheme: DatasourceScheme
    target_host: str = Field(..., min_length=1, max_length=255)
    plaintext_secret: str = Field(..., min_length=1, max_length=2048)
