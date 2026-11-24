"""Schemas & escalation builder for `autonomous_runner.py` (`Story 7.1`, `AD-18`)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from orcia_connectors.protocol import SignedApprovalToken
from orcia_core.kernel.events import AutonomousEscalated, DomainEvent
from orcia_core.orchestration.help_generator_and_validator import HelpArticleDeterministicValidator
from orcia_core.permissions.autonomy_contracts import AutonomyContract
from orcia_core.workflows.gates.pipeline import GatePipelineExecutor
from orcia_core.workflows.schemas_v2 import StepControlsPipeline

AutonomousRunStatus = Literal[
    "COMMITTED_AUTONOMOUS",
    "PAUSED_AUTONOMOUS_ESCALATION",
    "KILL_SWITCH_STOPPED",
]


class AutonomousActionRequest(BaseModel):
    """External action requested during an `AUTONOMOUS_CONTRACT` workflow run."""

    action_key: str
    scheme: str = "catalog"
    payload: dict[str, Any] = Field(default_factory=dict)
    secret_ref_uri: str | None = None


class AutonomousGateInput(BaseModel):
    """Gate evaluation metrics fed into the autonomous contract decision boundary."""

    deterministic_passed: bool = True
    agentic_score: float = Field(default=0.92, ge=0.0, le=1.0)
    fact_verification_score: float = Field(default=0.95, ge=0.0, le=1.0)
    ontology_conflicts: int = Field(default=0, ge=0)
    stale_warnings: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.05, ge=0.0)
    help_article_markdown: str | None = None
    help_article_lang: Literal["fr", "en"] = "fr"


class AutonomousRunOutcome(BaseModel):
    """Execution outcome for a workflow run under `AUTONOMOUS_CONTRACT`."""

    run_id: str
    workspace_id: str
    workflow_id: str
    contract_id: str
    status: AutonomousRunStatus
    escalation_reason: str | None = None
    issued_tokens: list[SignedApprovalToken] = Field(default_factory=list)
    executed_actions: list[dict[str, Any]] = Field(default_factory=list)
    outbox_events: list[dict[str, Any]] = Field(default_factory=list)


def escalate_outcome(
    *,
    run_id: str,
    contract: AutonomyContract,
    reason: str,
    trace_id: str,
    scope_path: str,
) -> tuple[AutonomousRunOutcome, DomainEvent]:
    """Create escalation outcome and `AutonomousEscalated` outbox event."""
    event = AutonomousEscalated.create(
        run_id=run_id,
        workspace_id=contract.workspace_id,
        workflow_id=contract.workflow_id,
        reason=reason,
        contract_id=contract.id,
        service_principal_id=contract.service_principal_id,
        scope_path=scope_path,
        trace_id=trace_id,
    )
    outcome = AutonomousRunOutcome(
        run_id=run_id,
        workspace_id=contract.workspace_id,
        workflow_id=contract.workflow_id,
        contract_id=contract.id,
        status="PAUSED_AUTONOMOUS_ESCALATION",
        escalation_reason=reason,
        outbox_events=[{"event_id": event.event_id, "event_type": event.event_type}],
    )
    return outcome, event


def evaluate_gate_thresholds(
    *,
    workflow_id: str,
    contract: AutonomyContract,
    gates: AutonomousGateInput,
    controls_pipeline: StepControlsPipeline | None,
    artifact_text: str,
) -> str | None:
    """Evaluate deterministic, HelpArticle, agentic, and FinOps thresholds."""
    if not gates.deterministic_passed:
        return "DETERMINISTIC_GATE_FAILED"
    if controls_pipeline is not None and controls_pipeline.deterministic:
        report = GatePipelineExecutor().execute_pipeline(
            pipeline=controls_pipeline,
            artifact_text=artifact_text,
        )
        if not report.deterministic_passed:
            return "DETERMINISTIC_PIPELINE_FAILED"
    if (
        "generate-and-attach-help" in workflow_id or gates.help_article_markdown is not None
    ) and gates.help_article_markdown is not None:
        val = HelpArticleDeterministicValidator().validate_help_article(
            markdown_text=gates.help_article_markdown,
            lang=gates.help_article_lang,
        )
        if not val.passed:
            return f"HELP_ARTICLE_VALIDATION_FAILED:{';'.join(val.violations)}"
    if gates.agentic_score < 0.85:
        return f"AGENTIC_SCORE_BELOW_THRESHOLD:{gates.agentic_score:.2f}"
    if gates.fact_verification_score < 0.90:
        return f"FACT_VERIFICATION_BELOW_THRESHOLD:{gates.fact_verification_score:.2f}"
    if gates.ontology_conflicts > 0:
        return f"ONTOLOGY_CONFLICTS_PRESENT:{gates.ontology_conflicts}"
    if gates.stale_warnings > 0:
        return f"STALE_WARNINGS_PRESENT:{gates.stale_warnings}"
    if gates.estimated_cost_usd > contract.max_cost_per_run_usd:
        return f"CONTRACT_COST_CEILING_EXCEEDED:{gates.estimated_cost_usd:.4f}"
    return None
