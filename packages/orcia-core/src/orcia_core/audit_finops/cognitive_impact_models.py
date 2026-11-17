"""Domain models for Cognitive Impact, Human Mastery & Reversibility (`Story 6.3`, `FR-27`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from orcia_core.audit_finops.post_hoc_audit import AutonomousGovernanceMetrics

PolicyRecommendationType = Literal["SWITCH_TO_RISK_OR_SAMPLING", "STRENGTHEN_HUMAN_ANCHORS"]
RecommendationStatus = Literal["PROPOSED", "APPLIED", "DISMISSED"]


@dataclass(frozen=True, slots=True)
class GatePolicyRecommendation:
    """Actionable recommendation to adjust a workflow's human validation gate policy."""

    id: str
    workflow_id: str
    workflow_title: str
    recommendation_type: PolicyRecommendationType
    title: str
    description: str
    action_label: str
    suggested_policy: str
    status: RecommendationStatus = "PROPOSED"
    applied_at: datetime | None = None
    applied_by: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowCognitiveMetrics:
    """Breakdown of human mastery metrics for a single workflow process."""

    workflow_id: str
    workflow_title: str
    criticality: str
    human_gates_count: int
    human_passes_count: int
    quick_passes_count: int
    quick_pass_rate: float
    median_review_duration_ms: int
    uncovered_drift_count: int
    has_alert: bool


@dataclass(frozen=True, slots=True)
class CognitiveMasteryDashboard:
    """Consolidated dashboard payload for Executive Cognitive Impact and Human Reversibility."""

    active_framing_ratio: float
    active_framing_target: float
    active_framing_alert: bool
    quick_pass_rate: float
    quick_pass_threshold: float
    quick_pass_alert: bool
    architecture_deviation_index: float
    architecture_deviation_target: float
    architecture_deviation_alert: bool
    total_human_hours: float
    active_framing_hours: float
    review_hours: float
    uncovered_deviations_count: int
    workflow_breakdowns: list[WorkflowCognitiveMetrics]
    recommendations: list[GatePolicyRecommendation] = field(default_factory=list)
    autonomous_governance: AutonomousGovernanceMetrics | None = None

    @property
    def rubber_stamping_rate(self) -> float:
        return self.quick_pass_rate

    @property
    def rubber_stamping_alert(self) -> bool:
        return self.quick_pass_alert

    @property
    def pattern_drift_index(self) -> float:
        return self.architecture_deviation_index

    @property
    def pattern_drift_alert(self) -> bool:
        return self.architecture_deviation_alert
