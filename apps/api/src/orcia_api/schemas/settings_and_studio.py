"""OpenAPI 3.1 / Pydantic v2 transport schemas for Epic 8 (`Stories 8.1..8.6`, `AD-19`, `AD-21`).

Kept exclusively in `apps/api/src/orcia_api/schemas/` — never inside `packages/orcia-core`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PermissionVerbLiteral = Literal["create", "read", "update", "delete", "execute", "grant"]
PermissionEffectLiteral = Literal["ALLOW", "DENY"]
SubjectTypeLiteral = Literal["USER", "ROLE", "SERVICE_PRINCIPAL"]
InferenceTierLiteral = Literal["simple", "medium", "complex", "auto"]
ResolvedInferenceTierLiteral = Literal["simple", "medium", "complex"]
InferenceEffortLiteral = Literal["default", "fast", "balanced", "deep"]
SettingScopeLevelLiteral = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]
SettingCategoryLiteral = Literal["iam", "connectors", "ai-models", "packs", "workflows", "audit"]
SecretActionLiteral = Literal["keep", "set", "clear"]
DataSecurityClassificationLiteral = Literal["C0_C2_STANDARD", "C3_CONFIDENTIAL_RESTRICTED"]
PiiArbitrationDecisionLiteral = Literal["PSEUDONYMIZE", "INDEX_AS_IS_AUDITED", "CANCEL_IMPORT"]
StudioLifecycleTabLiteral = Literal[
    "PUBLISHED", "DRAFT", "TRASH", "ACTIVE_RUNS", "PAUSED_ARBITRATION"
]
WizardTypeLiteral = Literal["sdlc_tech_lead", "ops_manager", "secops_admin"]


class SecretInputPayload(BaseModel):
    """Discriminated write-only secret mutation input (`keep | set | clear`, `Story 8.3`)."""

    model_config = ConfigDict(extra="forbid")

    action: SecretActionLiteral = "keep"
    plaintext_value: str | None = Field(default=None, max_length=4096)


class SecretStatusResponse(BaseModel):
    """Read-only secret status metadata (`configured` + salted `sha256:<8-hex>`, `Story 8.3`)."""

    model_config = ConfigDict(extra="forbid")

    configured: bool
    fingerprint: str | None = None
    updated_at: str
    updated_by: str


class RolePermissionGrantResponse(BaseModel):
    """6-verb RBAC/ABAC grant representation (`Story 8.1`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    subject_type: SubjectTypeLiteral
    subject_id: str
    scope_path: str
    verb: PermissionVerbLiteral
    effect: PermissionEffectLiteral
    inheritance_block: bool
    conditions: dict[str, Any]
    hidden_when_unauthorized: bool
    granted_by_user_id: str | None = None
    created_at_iso: str


def _default_delegate_verbs() -> list[PermissionVerbLiteral]:
    return ["read", "execute"]


class DelegateGrantRequest(BaseModel):
    """Request to delegate a subset of held permissions (`grant` confinement, `Story 8.1`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "marc"
    subject_type: SubjectTypeLiteral = "USER"
    subject_id: str = Field(default="0195f000-0000-7000-8000-000000000204", min_length=1)
    scope_path: str = Field(default="org/orcia/bu/claims/team/alpha", min_length=3)
    verbs: list[PermissionVerbLiteral] = Field(default_factory=_default_delegate_verbs)
    effect: PermissionEffectLiteral = "ALLOW"
    inheritance_block: bool = False
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


class ExecuteTierRoutingRequest(BaseModel):
    """Execute an LLM call or `auto` tier escalation (`Story 8.2`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = "0195f000-0000-7000-8000-000000000701"
    step_execution_id: str = "0195f000-0000-7000-8000-000000000801"
    scope_id: str = "0195f000-0000-7000-8000-000000000301"
    system_prompt: str = "You are ORCIA."
    user_prompt: str = "Analyze architecture."
    inference_tier: InferenceTierLiteral = "auto"
    effort: InferenceEffortLiteral = "balanced"
    evaluator_model_family: str | None = None
    fail_simple_tier_gate: bool = False


class InferenceAttemptResponse(BaseModel):
    """Recorded DBOS inference attempt (`Story 8.2`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    attempt_index: int
    requested_tier: InferenceTierLiteral
    resolved_tier: ResolvedInferenceTierLiteral
    effort: InferenceEffortLiteral
    model_family: str
    model_name: str
    deterministic_gate_passed: bool
    failure_reason: str
    cost_usd: float
    idempotency_key: str


class CognitiveRoutingOutcomeResponse(BaseModel):
    """Cognitive routing outcome response (`Story 8.2`)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    step_execution_id: str
    requested_tier: InferenceTierLiteral
    final_resolved_tier: ResolvedInferenceTierLiteral
    effort: InferenceEffortLiteral
    response_content: str
    model_family: str
    model_name: str
    attempts: list[InferenceAttemptResponse]
    total_cost_usd: float
    paused_budget_exceeded: bool


class ConnectorTestConnectionResponse(BaseModel):
    """Fail-fast DBOS connector healthcheck response (`< 5 s`, `Story 8.4`)."""

    model_config = ConfigDict(extra="forbid")

    connector_id: str
    scheme: str
    uri: str
    status: Literal["HEALTHY", "DEGRADED", "UNREACHABLE"]
    latency_ms: int
    timeout_budget_ms: int
    diagnostic_message: str
    tested_at_iso: str


class DocumentIngestionRequest(BaseModel):
    """Guarded document ingestion request (`C0-C3`, `0 char` OCR, PII arbitration, `Story 8.4`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "marc"
    workspace_id: str = "0195f000-0000-7000-8000-000000000301"
    uri: str = "confluence://ORCIA/pages/architecture-spec"
    title: str = "Architecture Spec"
    raw_extracted_text: str = "Spécification complète d'architecture modulaire."
    classification: DataSecurityClassificationLiteral = "C0_C2_STANDARD"
    pii_decision: PiiArbitrationDecisionLiteral | None = None


class DocumentIngestionResponse(BaseModel):
    """Guarded document ingestion report (`Story 8.4`)."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    workspace_id: str
    uri: str
    title: str
    classification: DataSecurityClassificationLiteral
    status: Literal["INDEXED", "WAITING_FOR_PII_ARBITRATION", "CANCELLED"]
    extracted_char_count: int
    pii_detected: bool
    pii_categories: list[str]
    arbitration_options: list[PiiArbitrationDecisionLiteral]
    pseudonymized: bool
    audit_derogation_recorded: bool
    indexed_chunk_id: str | None = None


class RagReciprocityResponse(BaseModel):
    """1-click RAG reciprocity check response (`Story 8.4`)."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    uri: str
    passed: bool
    control_query: str
    response_markdown: str
    cited_uri: str
    cited_chunk_id: str


class StudioDryRunRequest(BaseModel):
    """Isolated Studio *What-If* dry-run request (`▷ Tester`, `Story 8.5`)."""

    model_config = ConfigDict(extra="forbid")

    input_values: dict[str, Any] = Field(
        default_factory=lambda: {"p_1": "Ledger Core", "p_2": "STANDARD"}
    )
    preview_markdown_output: str | None = None


class StudioDryRunResponse(BaseModel):
    """Isolated Studio *What-If* dry-run outcome (`Story 8.5`)."""

    model_config = ConfigDict(extra="forbid")

    revision_id: str
    workflow_uri: str
    version: str
    executed_steps: list[str]
    skipped_layers: list[str]
    deterministic_structure_gate_passed: bool
    missing_markdown_sections: list[str]
    external_writes_count: int


class WizardSessionRequest(BaseModel):
    """Start or resume a 5-step durable DBOS wizard (`Story 8.6`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "marc"
    wizard_type: WizardTypeLiteral = "sdlc_tech_lead"
    scope_id: str = "0195f000-0000-7000-8000-000000000301"


class WizardAdvanceStepRequest(BaseModel):
    """Save and advance a step in a durable DBOS wizard (`Story 8.6`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "marc"
    step_index: int = Field(default=1, ge=1, le=5)
    step_payload: dict[str, Any] = Field(default_factory=lambda: {"configured": True})
    secret_input: SecretInputPayload | None = None


class WizardSessionResponse(BaseModel):
    """Durable DBOS onboarding wizard session state (`Story 8.6`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    wizard_type: WizardTypeLiteral
    user_id: str
    scope_id: str
    current_step_index: int
    total_steps: int
    dbos_workflow_id: str
    status: Literal["IN_PROGRESS", "COMPLETED", "ABANDONED"]
    completed_steps: list[int]
    rag_reciprocity_verified: bool
    state_jsonb: dict[str, Any]


class DemoWorkspaceProvisionResponse(BaseModel):
    """Zero Empty-State Demo Workspace provision response (`Story 8.6`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    workspace_slug: str
    workspace_name: str
    ontology_concepts_seeded: int
    kb_documents_indexed: int
    published_workflow_uri: str
    rag_reciprocity_verified: bool
    plaintext_secrets_count: int
