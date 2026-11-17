"""OpenAPI 3.1 HTTP Transport Schemas for Autonomy Contracts (`Story 7.1`, `AD-18`, `AD-19`).

All `*Request` and `*Response` schemas live exclusively in `apps/api/src/orcia_api/schemas/`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ContractCriticalityLiteral = Literal["LOW_NON_CRITICAL", "STANDARD", "HIGH_CRITICAL"]
TieBreakPolicyLiteral = Literal[
    "ONTOLOGY_AXIOM_FIRST",
    "DEFER_AND_CONTINUE_WITH_ASSUMPTION",
    "PAUSE_AND_ESCALATE",
]


class EligibleServicePrincipalItem(BaseModel):
    """Active `SERVICE_PRINCIPAL` account eligible for an autonomy contract in this workspace."""

    id: str
    principal_id: str
    display_name: str
    roles: list[str] = Field(default_factory=list)
    team_ids: list[str] = Field(default_factory=list)
    status: str


class AutonomyContractResponse(BaseModel):
    """Serialized signed `AutonomyContract` (`autonomy_contracts`)."""

    id: str
    workspace_id: str
    workflow_id: str
    workflow_version: str
    workflow_sha256: str
    criticality: Literal["LOW_NON_CRITICAL", "STANDARD"]
    service_principal_id: str
    allowed_read_sources: list[str] = Field(default_factory=list)
    allowed_write_actions: list[str] = Field(default_factory=list)
    max_cost_per_run_usd: float
    tie_break_policy: TieBreakPolicyLiteral
    post_hoc_sampling_rate: float
    status: Literal["ACTIVE", "REVOKED", "SUPERSEDED"]
    signed_by_user_id: str
    signed_by_role: Literal["TEAM_LEAD", "BU_LEAD", "PLATFORM_ADMIN"]
    signature_sha256: str
    signed_at_iso: str
    revoked_at_iso: str | None = None
    revoked_by_user_id: str | None = None


class AutonomyContractStateResponse(BaseModel):
    """Current active contract, signature history & eligible service accounts for a workflow."""

    workspace_id: str
    workflow_id: str
    active_contract: AutonomyContractResponse | None = None
    history: list[AutonomyContractResponse] = Field(default_factory=list)
    eligible_service_principals: list[EligibleServicePrincipalItem] = Field(default_factory=list)
    trace_id: str


class SignAutonomyContractRequest(BaseModel):
    """Request payload to sign an `AutonomyContract` (single signature `TEAM_LEAD`/`BU_LEAD`)."""

    workflow_version: str = Field(default="1.0.0", min_length=1, max_length=64)
    workflow_sha256: str = Field(default="", max_length=80)
    criticality: ContractCriticalityLiteral = "STANDARD"
    service_principal_id: str = Field(..., min_length=1)
    allowed_read_sources: list[str] = Field(default_factory=list)
    allowed_write_actions: list[str] = Field(default_factory=list)
    max_cost_per_run_usd: float = Field(default=5.0, gt=0.0)
    tie_break_policy: TieBreakPolicyLiteral = "ONTOLOGY_AXIOM_FIRST"
    post_hoc_sampling_rate: float = Field(default=0.15, ge=0.10, le=0.20)
    scope_path: str = Field(default="GLOBAL", min_length=1)


class RevokeAutonomyContractRequest(BaseModel):
    """Request payload to revoke an active autonomy contract."""

    scope_path: str = Field(default="GLOBAL", min_length=1)


class AutonomousActionInput(BaseModel):
    """External action requested during an `AUTONOMOUS_CONTRACT` execution."""

    action_key: str = Field(..., min_length=1)
    scheme: str = "catalog"
    payload: dict[str, Any] = Field(default_factory=dict)
    secret_ref_uri: str | None = None


class StartAutonomousRunRequest(BaseModel):
    """Request payload to trigger a workflow run under `AUTONOMOUS_CONTRACT`."""

    criticality: ContractCriticalityLiteral = "STANDARD"
    actions: list[AutonomousActionInput] = Field(default_factory=list)
    deterministic_passed: bool = True
    agentic_score: float = Field(default=0.92, ge=0.0, le=1.0)
    fact_verification_score: float = Field(default=0.95, ge=0.0, le=1.0)
    ontology_conflicts: int = Field(default=0, ge=0)
    stale_warnings: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.05, ge=0.0)
    help_article_markdown: str | None = None
    help_article_lang: Literal["fr", "en"] = "fr"
    scope_path: str = Field(default="GLOBAL", min_length=1)


class AutonomousRunExecutionResponse(BaseModel):
    """Result of an autonomous workflow execution under contract."""

    run_id: str
    workspace_id: str
    workflow_id: str
    contract_id: str
    status: Literal[
        "COMMITTED_AUTONOMOUS",
        "PAUSED_AUTONOMOUS_ESCALATION",
        "KILL_SWITCH_STOPPED",
    ]
    escalation_reason: str | None = None
    issued_token_preview_ids: list[str] = Field(default_factory=list)
    executed_actions: list[dict[str, Any]] = Field(default_factory=list)
    trace_id: str


__all__ = [
    "AutonomousActionInput",
    "AutonomousRunExecutionResponse",
    "AutonomyContractResponse",
    "AutonomyContractStateResponse",
    "ContractCriticalityLiteral",
    "EligibleServicePrincipalItem",
    "RevokeAutonomyContractRequest",
    "SignAutonomyContractRequest",
    "StartAutonomousRunRequest",
    "TieBreakPolicyLiteral",
]
