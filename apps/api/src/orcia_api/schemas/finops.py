"""FastAPI transport Pydantic v2 schemas for FinOps accounting and budgets (`Story 6.2`).

Strict RFC 9457 Problem Details envelopes — zero domain model leakages (`AD-19`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ScopeType = Literal["GLOBAL", "BU", "TEAM", "WORKSPACE"]


class FinopsOverviewResponse(BaseModel):
    """Top-level FinOps dashboard summary response."""

    total_cost_usd: float = Field(..., description="Consolidated total cost in USD")
    total_cost_eur: float = Field(..., description="Consolidated total cost in EUR")
    verified_internal_cost_usd: float = Field(..., description="Verified internal LLM cost in USD")
    verified_internal_cost_eur: float = Field(..., description="Verified internal LLM cost in EUR")
    reported_external_cost_usd: float = Field(
        ..., description="Reported external tool/MCP cost in USD"
    )
    reported_external_cost_eur: float = Field(
        ..., description="Reported external tool/MCP cost in EUR"
    )
    total_llm_tokens: int = Field(..., description="Sum of all processed tokens")
    internal_tokens: int = Field(..., description="Tokens from internal models")
    remote_tokens: int = Field(..., description="Tokens reported by remote tools/agents")
    total_external_calls: int = Field(..., description="Total invocations of external services")
    external_units_breakdown: dict[str, float] = Field(
        default_factory=dict, description="Custom metric units"
    )
    cache_savings_usd: float = Field(default=0.0, description="Estimated cache savings in USD")
    cache_savings_eur: float = Field(default=0.0, description="Estimated cache savings in EUR")
    active_circuit_breakers_count: int = Field(
        default=0, description="Number of currently tripped circuit breakers"
    )
    paused_runs_count: int = Field(default=0, description="Number of paused workflow runs")
    accounted_runs_count: int = Field(default=0, description="Total runs accounted for")


class FinopsProcessItemResponse(BaseModel):
    """Accounting item per workflow process."""

    workflow_id: str = Field(..., description="Workflow definition UUID")
    workflow_title: str = Field(..., description="Human-readable title of the workflow")
    runs_count: int = Field(..., description="Total executions of this workflow")
    amortized_setup_cost_usd: float = Field(
        ..., description="Amortized initial setup engineering cost (USD)"
    )
    amortized_setup_cost_eur: float = Field(
        ..., description="Amortized initial setup engineering cost (EUR)"
    )
    run_cost_usd: float = Field(..., description="Consolidated execution run cost (USD)")
    run_cost_eur: float = Field(..., description="Consolidated execution run cost (EUR)")
    human_time_cost_usd: float = Field(
        ..., description="Valorized human review and arbitration time (USD)"
    )
    human_time_cost_eur: float = Field(
        ..., description="Valorized human review and arbitration time (EUR)"
    )
    total_cost_usd: float = Field(..., description="Complete 3-component economic cost (USD)")
    total_cost_eur: float = Field(..., description="Complete 3-component economic cost (EUR)")
    baseline_manual_cost_usd: float = Field(..., description="Declared manual baseline cost (USD)")
    baseline_manual_cost_eur: float = Field(..., description="Declared manual baseline cost (EUR)")
    ttm_reduction_pct: float = Field(
        ..., description="Observed Time-to-Market reduction % vs baseline"
    )
    active_budget_override: bool = Field(
        default=False, description="Whether an active budget extension exists"
    )
    paused_runs_count: int = Field(
        default=0, description="Number of currently paused runs for this process"
    )


class FinopsTierEffortItemResponse(BaseModel):
    """Breakdown item by cognitive inference tier and effort level."""

    inference_tier: str = Field(..., description="Cognitive tier (simple, medium, complex, auto)")
    effort: str = Field(..., description="Inference effort (default, fast, balanced, deep)")
    invocations_count: int = Field(..., description="Total invocations")
    input_tokens: int = Field(..., description="Prompt input tokens")
    output_tokens: int = Field(..., description="Generated completion tokens")
    total_tokens: int = Field(..., description="Sum of input and output tokens")
    cost_usd: float = Field(..., description="Attributed cost in USD")
    cost_eur: float = Field(..., description="Attributed cost in EUR")
    escalated_from_auto_count: int = Field(
        default=0, description="Number of escalations originating from auto tier"
    )


class ScopeBudgetResponse(BaseModel):
    """Configured budget ceiling for a specific organizational scope."""

    id: str = Field(..., description="Budget record UUID")
    scope_type: ScopeType = Field(..., description="Scope level: GLOBAL, BU, TEAM, WORKSPACE")
    scope_id: str | None = Field(
        default=None, description="Scope target identifier or None for GLOBAL"
    )
    monthly_budget_usd: float = Field(..., description="Monthly spending limit in USD")
    warning_threshold_pct: int = Field(
        default=80, description="Warning threshold percentage (e.g. 80)"
    )
    hard_stop_pct: int = Field(default=100, description="Hard stop ceiling percentage (e.g. 100)")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")


class WorkflowBaselineResponse(BaseModel):
    """Declared manual baseline for a workflow definition."""

    id: str = Field(..., description="Baseline record UUID")
    workflow_definition_id: str = Field(..., description="Associated workflow definition UUID")
    scope_id: str | None = Field(default=None, description="Workspace scope UUID or None")
    manual_time_minutes: int = Field(
        ..., description="Pre-automation manual execution duration in minutes"
    )
    manual_cost_usd: float = Field(..., description="Pre-automation manual execution cost in USD")
    target_ttm_reduction_pct: int = Field(default=25, description="Target TTM reduction percentage")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")


class FinopsBreakdownResponse(BaseModel):
    """Complete FinOps governance breakdown payload."""

    overview: FinopsOverviewResponse = Field(..., description="Aggregated KPI overview")
    processes: list[FinopsProcessItemResponse] = Field(
        default_factory=list, description="Process breakdown"
    )
    tiers: list[FinopsTierEffortItemResponse] = Field(
        default_factory=list, description="Tier/effort breakdown"
    )
    scope_budgets: list[ScopeBudgetResponse] = Field(
        default_factory=list, description="Configured scope ceilings"
    )
    baselines: list[WorkflowBaselineResponse] = Field(
        default_factory=list, description="Declared baselines"
    )


class UpdateScopeBudgetRequest(BaseModel):
    """Request payload to configure or update a scope budget."""

    scope_type: ScopeType = Field(..., description="Scope type: GLOBAL, BU, TEAM, or WORKSPACE")
    scope_id: str | None = Field(default=None, description="Target scope ID or None for GLOBAL")
    monthly_budget_usd: float = Field(
        ..., ge=0, le=999_999.999999, description="Monthly spending limit in USD"
    )
    warning_threshold_pct: int = Field(
        default=80, ge=1, le=100, description="Warning threshold percentage"
    )
    hard_stop_pct: int = Field(
        default=100, ge=1, le=200, description="Hard stop ceiling percentage"
    )


class SetWorkflowBaselineRequest(BaseModel):
    """Request payload to set a pre-automation manual reference baseline."""

    workflow_definition_id: str = Field(..., min_length=1, description="Workflow definition UUID")
    scope_id: str | None = Field(default=None, description="Target workspace scope UUID or None")
    manual_time_minutes: int = Field(
        ..., ge=0, le=525600, description="Estimated manual time in minutes"
    )
    manual_cost_usd: float = Field(
        ..., ge=0, le=999_999.999999, description="Estimated manual cost in USD"
    )
    target_ttm_reduction_pct: int = Field(
        default=25, ge=0, le=100, description="Target reduction percentage"
    )


class BudgetOverrideRequest(BaseModel):
    """Request payload to extend budget and awaken a paused run."""

    override_amount_usd: float = Field(
        ..., gt=0, le=999_999.999999, description="Additional budget amount to allocate in USD"
    )
    reason: str = Field(
        ..., min_length=3, max_length=1000, description="Business justification for the extension"
    )
    workspace_id: str | None = Field(
        default=None, description="Target workspace ID for scope guard validation"
    )


class BudgetOverrideResponse(BaseModel):
    """Response returned upon approving a budget override."""

    id: str = Field(..., description="Override record UUID")
    run_id: str = Field(..., description="Target workflow run UUID")
    requested_by: str = Field(..., description="Requesting user UUID")
    approved_by: str = Field(..., description="Approving manager UUID")
    override_amount_usd: float = Field(..., description="Allocated extension amount in USD")
    reason: str = Field(..., description="Business justification")
    created_at: datetime | None = Field(default=None, description="Approval timestamp")
    new_run_status: str = Field(default="RUNNING", description="Updated run status")


class GatePolicyRecommendationSchema(BaseModel):
    """Actionable recommendation for human validation gate policy adjustment (`Story 6.3`)."""

    id: str = Field(..., description="Recommendation UUID or identifier")
    workflow_id: str = Field(..., description="Target workflow definition UUID")
    workflow_title: str = Field(..., description="Human-readable workflow title")
    recommendation_type: str = Field(
        ...,
        description="Type of recommendation (SWITCH_TO_RISK_OR_SAMPLING, STRENGTHEN_HUMAN_ANCHORS)",
    )
    title: str = Field(..., description="Clear business title")
    description: str = Field(..., description="Detailed rationale")
    action_label: str = Field(..., description="Action button label")
    suggested_policy: str = Field(..., description="Target policy setting (e.g. SAMPLING_20_PCT)")
    status: str = Field(default="PROPOSED", description="PROPOSED, APPLIED, or DISMISSED")
    applied_at: datetime | None = Field(default=None, description="Application timestamp")
    applied_by: str | None = Field(default=None, description="Applying user identifier")


class WorkflowCognitiveMetricsSchema(BaseModel):
    """Workflow-level cognitive mastery metrics (`Story 6.3`)."""

    workflow_id: str = Field(..., description="Workflow UUID")
    workflow_title: str = Field(..., description="Workflow title")
    criticality: str = Field(..., description="Workflow criticality level")
    human_gates_count: int = Field(..., description="Total human gates evaluated")
    human_passes_count: int = Field(..., description="Total approved gates")
    quick_passes_count: int = Field(..., description="Approvals flagged as quick-pass")
    quick_pass_rate: float = Field(..., description="Quick pass rate")
    median_review_duration_ms: int = Field(..., description="Median human review duration in ms")
    uncovered_drift_count: int = Field(
        ..., description="Number of architecture deviations not covered by a waiver"
    )
    has_alert: bool = Field(..., description="Whether workflow triggers a warning")


class CognitiveImpactDashboardResponse(BaseModel):
    """Executive Cognitive Impact, Human Mastery & Reversibility response (`Story 6.3`, `FR-27`)."""

    active_framing_ratio: float = Field(
        ..., description="Ratio of active framing time over total human time (target >= 40%)"
    )
    active_framing_target: float = Field(
        default=0.40, description="Target minimum ratio for active framing"
    )
    active_framing_alert: bool = Field(
        ..., description="True if active framing ratio is below target threshold"
    )
    quick_pass_rate: float = Field(
        ..., description="Rate of approvals with fast warning or unopened brief (threshold < 5%)"
    )
    quick_pass_threshold: float = Field(
        default=0.05, description="Warning threshold for quick-pass approvals"
    )
    quick_pass_alert: bool = Field(..., description="True if quick-pass rate exceeds threshold")
    rubber_stamping_rate: float = Field(
        ..., description="Compatibility alias for quick-pass approvals rate"
    )
    rubber_stamping_alert: bool = Field(
        ..., description="Compatibility alias for quick-pass approvals alert"
    )
    architecture_deviation_index: float = Field(
        ..., description="Index of architecture deviations not covered by waiver (target 0%)"
    )
    architecture_deviation_target: float = Field(
        default=0.00, description="Target for architecture deviation index"
    )
    architecture_deviation_alert: bool = Field(
        ..., description="True if any uncovered deviations exist"
    )
    pattern_drift_index: float = Field(
        ..., description="Compatibility alias for architecture deviation index"
    )
    pattern_drift_alert: bool = Field(
        ..., description="Compatibility alias for architecture deviation alert"
    )
    total_human_hours: float = Field(..., description="Total valorized human time in hours")
    active_framing_hours: float = Field(..., description="Time spent actively framing in hours")
    review_hours: float = Field(..., description="Time spent reviewing in hours")
    uncovered_deviations_count: int = Field(
        ..., description="Count of active deviations without waiver"
    )
    workflow_breakdowns: list[WorkflowCognitiveMetricsSchema] = Field(
        default_factory=list, description="Per-workflow metrics"
    )
    recommendations: list[GatePolicyRecommendationSchema] = Field(
        default_factory=list, description="Actionable gate policy recommendations"
    )


class ApplyRecommendationResponse(BaseModel):
    """Response returned upon applying a gate policy recommendation (`Story 6.3`)."""

    recommendation_id: str = Field(..., description="Applied recommendation ID")
    status: str = Field(default="APPLIED", description="New status")
    applied_at: datetime = Field(..., description="Application timestamp")
    applied_by: str = Field(..., description="Applying user UUID")
    workflow_id: str = Field(..., description="Target workflow UUID")
    suggested_policy: str = Field(..., description="Applied policy configuration")


__all__ = [
    "ApplyRecommendationResponse",
    "BudgetOverrideRequest",
    "BudgetOverrideResponse",
    "CognitiveImpactDashboardResponse",
    "FinopsBreakdownResponse",
    "FinopsOverviewResponse",
    "FinopsProcessItemResponse",
    "FinopsTierEffortItemResponse",
    "GatePolicyRecommendationSchema",
    "ScopeBudgetResponse",
    "SetWorkflowBaselineRequest",
    "UpdateScopeBudgetRequest",
    "WorkflowBaselineResponse",
    "WorkflowCognitiveMetricsSchema",
]
