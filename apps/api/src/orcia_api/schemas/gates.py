"""Pydantic v2 HTTP/OpenAPI 3.1 transport schemas for Story 4.1 (`AD-9`, `AD-16`, `FR-17`)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas.bootstrap import SystemBootstrapRunItem
from orcia_api.schemas.catalog import CatalogItemResponse
from orcia_core.gates.models import GateStatus, GateType, SandboxTierLiteral


class PatternDriftFindingSchemaItem(BaseModel):
    """Single Pattern Drift violation against `ARCHITECTURE-SPINE.md` (`FR-17`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    forbidden_symbol: str
    severity: str
    message: str


class OntologyAxiomRuleInputItem(BaseModel):
    """Formal ontology axiom rule checked inside the Tier 1 Sandbox (`AD-7`, `AD-9`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    axiom_key: str = Field(..., min_length=1, max_length=128)
    forbidden_term: str = Field(default="", max_length=256)
    required_term: str = Field(default="", max_length=256)


class DeterministicGateEvaluateRequest(BaseModel):
    """Request payload for `POST /api/v1/gates/deterministic/evaluate` (`AD-9`, `FR-17`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(..., min_length=1, max_length=128)
    run_id: str = Field(..., min_length=1, max_length=128)
    step_execution_id: str = Field(..., min_length=1, max_length=128)
    step_key: str = Field(..., min_length=1, max_length=128)
    artifact_payload: dict[str, Any] = Field(default_factory=dict)
    required_sections: list[str] = Field(default_factory=lambda: ["artifact"])
    ontology_axioms: list[OntologyAxiomRuleInputItem] = Field(default_factory=list)
    allowed_dependencies: list[str] | None = Field(default=None)
    timeout_ms: int = Field(default=5000, ge=50, le=5000)
    max_memory_mb: int = Field(default=256, ge=16, le=256)
    raise_on_failure: bool = Field(default=False)
    simulate_timeout_sleep_ms: int = Field(default=0, ge=0, le=10000)
    simulate_network_escape: bool = Field(default=False)
    simulate_fs_escape_path: str | None = Field(default=None, max_length=256)
    simulate_tmp_overflow_mb: int = Field(default=0, ge=0, le=128)
    simulate_memory_alloc_mb: int = Field(default=0, ge=0, le=1024)


class GateEvaluationSchemaItem(BaseModel):
    """Serialized `GateEvaluationEntity` (`gate_evaluations` table)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    step_key: str
    gate_type: GateType
    sandbox_tier: SandboxTierLiteral
    status: GateStatus
    score: float
    schema_validation_passed: bool
    ontology_axioms_passed: bool
    pattern_drift_passed: bool
    pattern_drift_findings: list[PatternDriftFindingSchemaItem]
    missing_sections: list[str]
    violated_axioms: list[dict[str, str]]
    duration_ms: int
    outbox_event_id: str | None = None
    evaluated_at: str
    sandbox_exit_code: int = 0
    sandbox_stderr: str = ""


class DeterministicGateEvaluateResponse(BaseModel):
    """Response for `POST /api/v1/gates/deterministic/evaluate`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation: GateEvaluationSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class GateEvaluationsListResponse(BaseModel):
    """Response for `GET /api/v1/gates/evaluations`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluations: list[GateEvaluationSchemaItem]
    trace_id: str = Field(..., min_length=32, max_length=32)


class WorkspaceSpineBaselineSchemaItem(BaseModel):
    """Serialized `WorkspaceSpineBaseline` (`[ADOPTED]`, `FR-28`, `AD-16`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str
    spine_version: str
    status: Literal["ADOPTED"]
    allowed_dependencies: list[str]
    spine_markdown: str
    content_sha256: str
    signed_by_user_id: str
    human_anchor_signature: str


class InitExistingProjectRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/init-existing-project` (`FR-28`, `AD-16`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(..., min_length=1, max_length=128)
    repository_uri: str = Field(..., min_length=6, max_length=512)
    detected_dependencies: list[str] = Field(..., min_length=1, max_length=100)
    architecture_paradigm: str = Field(..., min_length=3, max_length=256)
    human_anchor_justification: str = Field(..., min_length=1, max_length=4096)
    human_anchor_signature: str = Field(..., min_length=1, max_length=256)
    spine_version: str = Field(default="1.0.0", min_length=1, max_length=32)


class InitExistingProjectResponse(BaseModel):
    """Response for `POST /api/v1/bootstrap/init-existing-project`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run: SystemBootstrapRunItem
    spine_baseline: WorkspaceSpineBaselineSchemaItem
    catalog_item: CatalogItemResponse
    trace_id: str = Field(..., min_length=32, max_length=32)


class InitSkillRequest(BaseModel):
    """Request payload for `POST /api/v1/bootstrap/init-skill` (`FR-28`, `AD-9`, `AD-16`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(..., min_length=1, max_length=128)
    skill_key: str = Field(..., min_length=2, max_length=64)
    skill_uri: str = Field(..., min_length=8, max_length=256)
    title: str = Field(..., min_length=2, max_length=128)
    description: str = Field(..., min_length=3, max_length=1024)
    version: str = Field(default="v1.0.0", min_length=1, max_length=32)
    test_payload: dict[str, Any] = Field(default_factory=lambda: {"artifact": "skill-self-test"})
    required_sections: list[str] = Field(default_factory=lambda: ["artifact"])
    timeout_ms: int = Field(default=5000, ge=50, le=5000)
    max_memory_mb: int = Field(default=256, ge=16, le=256)
    visibility_scope: Literal["SHARED_WORKSPACE", "SHARED_TEAM"] = Field(default="SHARED_WORKSPACE")
    simulate_timeout_sleep_ms: int = Field(default=0, ge=0, le=10000)
    simulate_network_escape: bool = Field(default=False)
    simulate_fs_escape_path: str | None = Field(default=None, max_length=256)
    simulate_memory_alloc_mb: int = Field(default=0, ge=0, le=1024)


class InitSkillResponse(BaseModel):
    """Response for `POST /api/v1/bootstrap/init-skill`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run: SystemBootstrapRunItem
    catalog_item: CatalogItemResponse
    gate_evaluation: GateEvaluationSchemaItem
    trace_id: str = Field(..., min_length=32, max_length=32)


class Tier2TddVerifyRequest(BaseModel):
    """Request payload for `POST /api/v1/gates/sandbox/tier2/tdd-verify` (`Story 4.1a`, `UJ-12`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(..., min_length=1, max_length=128)
    run_id: str = Field(..., min_length=1, max_length=128)
    step_key: str = Field(..., min_length=1, max_length=128)
    buggy_files: dict[str, str] = Field(default_factory=dict)
    patched_files: dict[str, str] = Field(default_factory=dict)
    test_files: dict[str, str] = Field(default_factory=dict)
    tools: list[str] = Field(default_factory=lambda: ["pytest", "ruff"])
    cas_readonly_dir: str | None = Field(default=None, max_length=512)
    timeout_ms: int = Field(default=60000, ge=100, le=60000)
    max_memory_mb: int = Field(default=1024, ge=64, le=1024)
    raise_on_failure: bool = Field(default=False)


class Tier2TddVerifyResponse(BaseModel):
    """Response for `POST /api/v1/gates/sandbox/tier2/tdd-verify` (`Story 4.1a`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    red_reproduced: bool
    red_exit_code: int
    red_stdout: str
    green_verified: bool
    green_tool_runs: list[dict[str, Any]]
    container_cli_args: list[str]
    duration_ms: int
    trace_id: str = Field(..., min_length=32, max_length=32)


class DeploymentRoleSchemaItem(BaseModel):
    """Serialized `DeploymentRoleSpec` (`Story 4.1a`, `M9`, `AD-19`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: str
    description: str
    entrypoint_command: list[str]
    required_extras: list[str]
    loads_docling: bool
    forbidden_modules_in_process: list[str]
    supported_sandbox_tiers: list[str]


class DeploymentRolesListResponse(BaseModel):
    """Response for `GET /api/v1/gates/sandbox/deployment-roles` (`Story 4.1a`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    roles: list[DeploymentRoleSchemaItem]
    trace_id: str = Field(..., min_length=32, max_length=32)


class AgenticGateEvaluateRequest(BaseModel):
    """Request payload for `POST /api/v1/gates/agentic/evaluate` (`Story 4.2`, `AD-10`, `FR-18`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_id: str = Field(..., min_length=1, max_length=128)
    run_id: str = Field(..., min_length=1, max_length=128)
    step_execution_id: str = Field(..., min_length=1, max_length=128)
    step_key: str = Field(..., min_length=1, max_length=128)
    executor_model_family: str = Field(..., min_length=1, max_length=64)
    evaluator_model_family: str = Field(..., min_length=1, max_length=64)
    evaluator_model_id: str = Field(default="google/gemini-2.5-pro", min_length=1, max_length=128)
    data_classification: Literal["PUBLIC", "INTERNAL", "SENSITIVE", "RESTRICTED"] = Field(
        default="INTERNAL"
    )
    anonymize_pii_reversible: bool = Field(default=True)
    custom_pii_entities: list[str] = Field(default_factory=list)
    candidate_artifact: dict[str, Any] = Field(default_factory=dict)
    step1_prd_invariants: list[str] = Field(default_factory=list)
    step2_arch_invariants: list[str] = Field(default_factory=list)
    ontology_facts: dict[str, str] = Field(default_factory=dict)
    pinned_kb_facts: dict[str, str] = Field(default_factory=dict)
    step_memlog_markers: list[dict[str, str]] = Field(default_factory=list)
    fact_confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    pass_score_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class AgenticGateEvaluateResponse(BaseModel):
    """Response for `POST /api/v1/gates/agentic/evaluate` (`Story 4.2`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation: GateEvaluationSchemaItem
    routed_model_family: str
    routed_model_id: str
    routed_to_local_sovereign_model: bool
    cot_items_purged: int
    pii_tokens_redacted: int
    rehydrated_summary: str
    lens_results: list[dict[str, Any]]
    briefing_4blocks: dict[str, Any]
    trace_id: str = Field(..., min_length=32, max_length=32)
