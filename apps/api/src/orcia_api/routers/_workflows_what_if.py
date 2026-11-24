"""What-If dry-run simulation helper for Process Studio v2 workflows (`Story 27.7`)."""

from __future__ import annotations

from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.schemas.process_studio_v2 import WhatIfSimulationRequest
from orcia_core.workflows.gates.pipeline import GatePipelineExecutor
from orcia_core.workflows.schemas_v2 import (
    ImpactAssessmentResult,
    ProcessOrchestrationType,
    WorkflowDefinitionV2,
)


def execute_workflow_what_if_simulation(
    wf: WorkflowDefinitionV2,
    payload: WhatIfSimulationRequest,
) -> ImpactAssessmentResult:
    """Run an isolated What-If simulation (`external_writes_executed = 0`, `CA-9.3.4`)."""
    enabled_steps = [s for s in wf.sub_steps if s.enabled]
    headings = wf.contract.required_markdown_sections or [f"# {wf.title}", "## Contexte"]
    sample_tmpl = get_router_copy().workflow_what_if_sample
    sample_md = payload.sample_artifact_markdown or (
        "\n\n".join(sample_tmpl.format(h=h, title=wf.title) for h in headings)
        + "\n```mermaid\nflowchart LR\n  A --> B\n```\n"
    )
    gate_report = GatePipelineExecutor().execute_pipeline(
        pipeline=wf.controls,
        artifact_text=sample_md,
        execution_mode=wf.execution_mode,
    )
    findings = [
        {
            "control_id": r.control_id,
            "type": "deterministic",
            "status": r.status,
            "violations": r.violations,
        }
        for r in gate_report.deterministic_records
    ] + [
        {
            "control_id": p.control_id,
            "type": "probabilistic",
            "status": p.status,
            "risk_score": p.risk_score,
            "findings": p.findings,
        }
        for p in gate_report.probabilistic_records
    ]
    step_units = (
        max(1, len(wf.allowed_delegate_agents) + 1)
        if wf.orchestration_type == ProcessOrchestrationType.NON_DETERMINISTIC
        else max(1, len(enabled_steps))
    )
    est_tokens = step_units * 1450
    return ImpactAssessmentResult(
        workflow_id=wf.id,
        version=wf.version,
        sandbox_isolated=True,
        external_writes_executed=0,
        sub_steps_evaluated=len(enabled_steps) if enabled_steps else step_units,
        deterministic_gates_passed=gate_report.deterministic_passed,
        probabilistic_gates_passed=gate_report.overall_status == "NOMINAL",
        estimated_tokens=est_tokens,
        estimated_cost_usd=round(est_tokens * 0.000003, 4),
        findings=findings,
    )
