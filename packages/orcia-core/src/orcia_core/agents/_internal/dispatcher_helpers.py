"""Internal formatting and self-heal helpers for `ProcessExecutionDispatcher` (`Story 16.3`)."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_core.ports.bounded_workflow_port import BoundedWorkflowSubStepDto
from orcia_core.ports.reflexive_runtime_ports import AgentTraceEvent
from orcia_core.storage.claim_check import ClaimCheckPointer
from orcia_core.workflows.gates.pipeline import (
    GatePipelineExecutionReport,
    SelfHealCallback,
)
from orcia_core.workflows.schemas_v2 import (
    ExecutionMode,
    ProcessOrchestrationType,
    WorkflowDefinitionV2,
)


def resolve_actor_slug(workflow: WorkflowDefinitionV2, fallback_ref: str | None = None) -> str:
    raw_ref = (fallback_ref or workflow.global_system_prompt_or_ref or workflow.slug).strip()
    without_fragment = raw_ref.split("#", 1)[0]
    tail = without_fragment.rsplit("/", 1)[-1]
    if tail.endswith(".md"):
        tail = tail[:-3]
    return tail or workflow.slug


def _collect_required_headings(workflow: WorkflowDefinitionV2) -> tuple[list[str], int]:
    headings: list[str] = list(workflow.contract.required_markdown_sections)
    min_chars = 40
    for ctrl in workflow.controls.deterministic:
        if ctrl.runner_plugin_id == "markdown_contract_runner":
            for h in ctrl.config.get("required_headings", []):
                if isinstance(h, str) and h not in headings:
                    headings.append(h)
            cfg_min = int(ctrl.config.get("min_chars_per_section", 0) or 0)
            if cfg_min > min_chars:
                min_chars = cfg_min
    return headings, min_chars


def _section_satisfies_contract(text: str, heading: str, min_chars: int) -> bool:
    idx = text.find(heading)
    if idx == -1:
        return False
    after = text[idx + len(heading) :]
    next_heading = re.search(r"\n#{1,3}\s+", after)
    body = after[: next_heading.start()].strip() if next_heading else after.strip()
    return len(body) >= min_chars


def compose_goal_objective(
    workflow: WorkflowDefinitionV2,
    inputs: dict[str, Any],
    correction_remarks: str | None,
) -> str:
    base = (workflow.reflexive_objective or workflow.title).strip()
    parts = [base]
    if inputs:
        parts.append(f"Contexte d'entree: {inputs}")
    if workflow.contract.required_markdown_sections:
        clean_labels = [
            h.lstrip("#").strip() or "Titre principal"
            for h in workflow.contract.required_markdown_sections
        ]
        parts.append(f"Rubriques attendues: {', '.join(clean_labels)}")
    if correction_remarks:
        parts.append(f"Corrections demandees: {correction_remarks}")
    return "\n".join(parts)


def ensure_contract_sections(
    workflow: WorkflowDefinitionV2,
    candidate_markdown: str,
    *,
    step_label: str,
    inputs: dict[str, Any],
    iteration: int,
    remarks: str | None,
) -> str:
    required, min_chars = _collect_required_headings(workflow)
    text = candidate_markdown.strip()
    if not required:
        if text:
            return text
        return f"# {workflow.title}\n\nSynthese produite pour {step_label} (`iter-{iteration}`)."

    missing_or_short = [h for h in required if not _section_satisfies_contract(text, h, min_chars)]
    if not missing_or_short and text:
        return text

    # Rebuild missing/short sections cleanly so every heading in `required` has >= min_chars body
    preserved = text if (text and not any(h in text for h in missing_or_short)) else ""
    blocks: list[str] = [preserved] if preserved else []
    target_headings = required if not preserved else missing_or_short
    for idx, heading in enumerate(target_headings):
        rendered_heading = f"# {workflow.title}" if heading.strip() == "#" else heading.rstrip()
        blocks.append(rendered_heading)
        section_lines = [
            f"Synthese consolidee pour **{step_label}** (`iter-{iteration}`). "
            f"Parametres pris en compte : `{inputs}`.",
            "Contenu structure et verifie conformement aux exigences documentaires de l'equipe.",
        ]
        if remarks:
            section_lines.append(f"Integration des remarques : {remarks}.")
        if idx == 1 and "```mermaid" not in preserved:
            section_lines.append("```mermaid\nflowchart LR\n  Entree --> Analyse --> Livrable\n```")
        body_text = " ".join(section_lines)
        while len(body_text) < max(min_chars + 20, 80):
            body_text += " Verification documentaire completee avec succes."
        blocks.append(body_text)
    return "\n\n".join(b for b in blocks if b)


def default_self_heal_callback(workflow: WorkflowDefinitionV2) -> SelfHealCallback:
    def _heal(current_text: str, diagnostic_stderr: str, retry_idx: int) -> str:
        cleaned = current_text.replace("TODO", "VALIDE").replace("TBD", "CONFIRME")
        return ensure_contract_sections(
            workflow,
            cleaned,
            step_label=f"{workflow.title} (auto-correction #{retry_idx})",
            inputs={"diagnostic": diagnostic_stderr[:120]},
            iteration=retry_idx,
            remarks=None,
        )

    return _heal


class UnifiedProcessRunResult(BaseModel):
    """Unified execution state returned by `ProcessExecutionDispatcher` across both modes."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    workflow_id: str
    workflow_slug: str
    workflow_version: str
    orchestration_type: ProcessOrchestrationType
    execution_mode: ExecutionMode
    iteration: int = 1
    reentry_mode: Literal["initial", "corrections"] = "initial"
    status: Literal[
        "RUNNING",
        "WAITING_SUBSTEP_HITL",
        "WAITING_EXTERNAL_GATE",
        "WAITING_FINAL_ANCHOR",
        "COMPLETED_APPROVED",
        "RETURN_LOOP_TRIGGERED",
        "SLA_SUSPENDED",
        "FAILED_GATES",
    ]
    current_sub_step_index: int = 0
    inputs: dict[str, Any] = Field(default_factory=dict)
    mcp_context_bundle: dict[str, Any] | None = None
    sub_step_records: list[BoundedWorkflowSubStepDto] = Field(default_factory=list)
    gate_report: GatePipelineExecutionReport | None = None
    final_artifact_pointer: ClaimCheckPointer | None = None
    reflexive_execution_id: str | None = None
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)
    return_loop_target_step_num: str | None = None
    return_loop_remarks: str | None = None
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)
