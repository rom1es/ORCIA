"""OpenAPI 3.1 / Pydantic v2 transport schemas for Epic 8 (`Stories 8.1..8.6`, `AD-19`, `AD-21`).

Kept exclusively in `apps/api/src/orcia_api/schemas/` — never inside `packages/orcia-core`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas._settings_wizard_and_rag import (
    CognitiveRoutingOutcomeResponse,
    ConnectorTestConnectionResponse,
    DataSecurityClassificationLiteral,
    DemoWorkspaceProvisionResponse,
    DocumentIngestionRequest,
    DocumentIngestionResponse,
    ExecuteTierRoutingRequest,
    InferenceAttemptResponse,
    InferenceEffortLiteral,
    InferenceTierLiteral,
    PiiArbitrationDecisionLiteral,
    RagReciprocityResponse,
    ResolvedInferenceTierLiteral,
    SecretInputPayload,
    StudioDryRunRequest,
    StudioDryRunResponse,
    WizardAdvanceStepRequest,
    WizardSessionRequest,
    WizardSessionResponse,
    WizardSessionsListResponse,
    WizardStepBackRequest,
    WizardTypeLiteral,
)

PermissionVerbLiteral = Literal["create", "read", "update", "delete", "execute", "grant"]
PermissionEffectLiteral = Literal["ALLOW", "DENY", "INHERITANCE_BLOCK"]
GrantResourceKindLiteral = Literal["ALL", "WORKFLOW", "AGENT", "DATASOURCE", "CONNECTOR"]
SubjectTypeLiteral = Literal["USER", "ROLE", "SERVICE_PRINCIPAL"]
SettingScopeLevelLiteral = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
SettingCategoryLiteral = Literal["iam", "connectors", "ai-models", "packs", "workflows", "audit"]
SecretActionLiteral = Literal["keep", "set", "clear"]
StudioLifecycleTabLiteral = Literal[
    "PUBLISHED", "DRAFT", "TRASH", "ACTIVE_RUNS", "PAUSED_ARBITRATION"
]


class SecretStatusResponse(BaseModel):
    """Read-only secret status metadata (`Story 8.3`, `Story 17.5`, `AD-21.3`)."""

    model_config = ConfigDict(extra="forbid")

    configured: bool
    fingerprint: str | None = None
    masked_hint: str | None = None
    updated_at: str
    updated_by: str


class RolePermissionGrantResponse(BaseModel):
    """6-verb RBAC/ABAC grant representation (`Story 8.1`, `Story 17.3`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    subject_type: SubjectTypeLiteral
    subject_id: str
    scope_path: str
    verb: PermissionVerbLiteral
    effect: PermissionEffectLiteral
    inheritance_block: bool
    resource_kind: GrantResourceKindLiteral = "ALL"
    conditions: dict[str, Any]
    hidden_when_unauthorized: bool
    granted_by_user_id: str | None = None
    created_at_iso: str


class GrantDeleteResponse(BaseModel):
    """Envelope returned by `DELETE /api/v1/settings/iam/grants/{grant_id}` (`Story 17.3`)."""

    model_config = ConfigDict(extra="forbid")

    deleted_id: str
    trace_id: str


def _default_delegate_verbs() -> list[PermissionVerbLiteral]:
    return ["read", "execute"]


class DelegateGrantRequest(BaseModel):
    """Request to delegate held permissions (`grant` confinement, `Story 8.1` / `17.3`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "marc"
    subject_type: SubjectTypeLiteral = "USER"
    subject_id: str = Field(default="0195f000-0000-7000-8000-000000000204", min_length=1)
    scope_path: str = Field(default="org/orcia/bu/claims/team/alpha", min_length=2)
    verbs: list[PermissionVerbLiteral] = Field(default_factory=_default_delegate_verbs)
    effect: PermissionEffectLiteral = "ALLOW"
    inheritance_block: bool = False
    resource_kind: GrantResourceKindLiteral = "ALL"
    conditions: dict[str, Any] = Field(default_factory=dict)
    hidden_when_unauthorized: bool = False
    workspace_id: str | None = None


class EvaluateResourceAccessRequest(BaseModel):
    """Evaluate 6-verb RBAC/ABAC access on a resource (`Story 8.1`)."""

    model_config = ConfigDict(extra="forbid")

    subject_id: str = "0195f000-0000-7000-8000-000000000204"
    subject_type: SubjectTypeLiteral = "USER"
    roles: list[str] = Field(default_factory=lambda: ["CONTRIBUTOR"])
    scope_path: str = "org/orcia/bu/claims/team/alpha/workspace/ws-1/resource/res-1"
    title: str = "Connecteur Cible"
    context: dict[str, Any] = Field(default_factory=dict)
    require_secret_read: bool = False
    require_execute: bool = False


class ResourceDiscoveryResponse(BaseModel):
    """Evaluated resource access & passive-discovery lock state (`Story 8.1`)."""

    model_config = ConfigDict(extra="forbid")

    scope_path: str
    title: str
    allowed_verbs: list[PermissionVerbLiteral]
    locked: bool
    reason: str | None = None
    can_request_access: bool
    secret_config_visible: bool


class PlatformSettingResponse(BaseModel):
    """Versioned platform setting response with `ETag` and `SecretStatus` (`Story 8.3`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    scope_level: SettingScopeLevelLiteral
    scope_id: str
    category: SettingCategoryLiteral
    key: str
    value_jsonb: dict[str, Any]
    secret_status: SecretStatusResponse
    version: int
    etag: str
    updated_at: str
    updated_by: str


class PatchPlatformSettingRequest(BaseModel):
    """Mutate a versioned platform setting with write-only `SecretInput` (`Story 8.3`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "karim"
    scope_level: SettingScopeLevelLiteral = "WORKSPACE"
    scope_id: str = "0195f000-0000-7000-8000-000000000301"
    category: SettingCategoryLiteral = "ai-models"
    key: str = "default_routing_policy"
    value_jsonb: dict[str, Any] = Field(default_factory=lambda: {"default_tier": "medium"})
    secret_input: SecretInputPayload | None = None


class OutboxReplayRequest(BaseModel):
    """Bounded Outbox replay request (`<= 500` events, `dry_run: true` default, `Story 8.3`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "karim"
    consumer_name: str = "audit_finops"
    event_ids: list[str] = Field(default_factory=list)
    max_events: int = Field(default=100, ge=1, le=500)
    dry_run: bool = True


class OutboxReplayResponse(BaseModel):
    """Bounded Outbox replay result (`Story 8.3`)."""

    model_config = ConfigDict(extra="forbid")

    consumer_name: str
    dry_run: bool
    scanned_count: int
    replayed_count: int
    event_ids: list[str]


class LlmTierMappingResponse(BaseModel):
    """Workspace cognitive tier mapping response (`Story 8.2`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    scope_level: SettingScopeLevelLiteral
    scope_id: str
    inference_tier: ResolvedInferenceTierLiteral
    effort: InferenceEffortLiteral
    provider_slug: str
    model_family: str
    model_name: str
    max_tokens_budget: int
    max_cost_usd: float
    fallback_order: int
    is_active: bool
    draining: bool


__all__ = [
    "CognitiveRoutingOutcomeResponse",
    "ConnectorTestConnectionResponse",
    "DataSecurityClassificationLiteral",
    "DelegateGrantRequest",
    "DemoWorkspaceProvisionResponse",
    "DocumentIngestionRequest",
    "DocumentIngestionResponse",
    "EvaluateResourceAccessRequest",
    "ExecuteTierRoutingRequest",
    "GrantDeleteResponse",
    "GrantResourceKindLiteral",
    "InferenceAttemptResponse",
    "InferenceEffortLiteral",
    "InferenceTierLiteral",
    "LlmTierMappingResponse",
    "OutboxReplayRequest",
    "OutboxReplayResponse",
    "PatchPlatformSettingRequest",
    "PermissionEffectLiteral",
    "PermissionVerbLiteral",
    "PiiArbitrationDecisionLiteral",
    "PlatformSettingResponse",
    "RagReciprocityResponse",
    "ResolvedInferenceTierLiteral",
    "ResourceDiscoveryResponse",
    "RolePermissionGrantResponse",
    "SecretActionLiteral",
    "SecretInputPayload",
    "SecretStatusResponse",
    "SettingCategoryLiteral",
    "SettingScopeLevelLiteral",
    "StudioDryRunRequest",
    "StudioDryRunResponse",
    "StudioLifecycleTabLiteral",
    "SubjectTypeLiteral",
    "WizardAdvanceStepRequest",
    "WizardSessionRequest",
    "WizardSessionResponse",
    "WizardSessionsListResponse",
    "WizardStepBackRequest",
    "WizardTypeLiteral",
]
