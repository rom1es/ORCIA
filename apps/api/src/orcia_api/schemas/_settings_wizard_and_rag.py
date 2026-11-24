"""Document ingestion, RAG reciprocity, Studio dry-run & wizard Pydantic v2 schemas (split)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

DataSecurityClassificationLiteral = Literal["C0_C2_STANDARD", "C3_CONFIDENTIAL_RESTRICTED"]
PiiArbitrationDecisionLiteral = Literal["PSEUDONYMIZE", "INDEX_AS_IS_AUDITED", "CANCEL_IMPORT"]
WizardTypeLiteral = Literal["sdlc_tech_lead", "ops_manager", "secops_admin"]
InferenceTierLiteral = Literal["simple", "medium", "complex", "auto"]
ResolvedInferenceTierLiteral = Literal["simple", "medium", "complex"]
InferenceEffortLiteral = Literal["default", "fast", "balanced", "deep"]


class SecretInputPayload(BaseModel):
    """Discriminated write-only secret mutation input (`keep | set | clear`, `Story 8.3`)."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["keep", "set", "clear"] = "keep"  # pragma: allowlist secret
    plaintext_value: str | None = Field(default=None, max_length=4096)


class DocumentIngestionRequest(BaseModel):
    """Guarded document ingestion request (`C0-C3`, `0 char` OCR, PII arbitration, `Story 8.4`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "marc"
    workspace_id: str = "0195f000-0000-7000-8000-000000000301"
    uri: str = "confluence://ORCIA/pages/architecture-spec"
    title: str = "Architecture Spec"
    raw_extracted_text: str = "Complete modular architecture specification."
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
    """Isolated Studio *What-If* dry-run request (`Story 8.5`)."""

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
    """Save and advance (or step back) in a durable DBOS wizard (`Story 8.6`, `22.5`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "marc"
    step_index: int = Field(default=1, ge=1, le=5)
    step_payload: dict[str, Any] = Field(default_factory=lambda: {"configured": True})
    secret_input: SecretInputPayload | None = None
    step_back: bool = False


class WizardStepBackRequest(BaseModel):
    """Non-destructive step-back in a durable DBOS wizard (`Story 22.5`, `REM-15`)."""

    model_config = ConfigDict(extra="forbid")

    actor_persona: str = "marc"
    step_index: int = Field(default=2, ge=1, le=5)
    step_payload: dict[str, Any] = Field(default_factory=dict)


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


class WizardSessionsListResponse(BaseModel):
    """List of durable wizard sessions for the authenticated user (`Story 22.5`)."""

    model_config = ConfigDict(extra="forbid")

    sessions: list[WizardSessionResponse]
    trace_id: str


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
