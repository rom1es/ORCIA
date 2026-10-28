"""Workflow Blueprint & `@xyflow/react` Canvas Composer for Assistant Agent (`Story 3.3`, `AD-20`).

Provides pure domain models and blueprint resolution for conversational workflow composition
(`WORKFLOW_COMPOSE` & `WORKFLOW_MODIFY`) without any SDLC vocabulary in `orcia-core`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orcia_kernel.context_ports import (
    AssistantWorkflowBlueprint,
    list_registered_assistant_templates,
)
from orcia_kernel.enums import WorkflowExecutionRegime
from orcia_kernel.ids import new_uuid7_str


@dataclass(frozen=True, slots=True)
class XyFlowNodeSpec:
    """Typed `@xyflow/react` v12 node descriptor for Cockpit Canvas preview (`UX-DR15`)."""

    id: str
    position_x: float
    position_y: float
    label: str
    step_type: str
    human_authored_required: bool


@dataclass(frozen=True, slots=True)
class XyFlowEdgeSpec:
    """Typed `@xyflow/react` v12 edge descriptor for Cockpit Canvas preview (`UX-DR15`)."""

    id: str
    source: str
    target: str
    animated: bool = True


@dataclass(frozen=True, slots=True)
class AssistantWorkflowProposal:
    """Composed or modified workflow with `@xyflow/react` graph + YAML manifest (`FR-11`)."""

    proposal_id: str
    workflow_uri: str
    title: str
    description: str
    execution_regime: WorkflowExecutionRegime
    manifest_yaml: str
    nodes: tuple[XyFlowNodeSpec, ...]
    edges: tuple[XyFlowEdgeSpec, ...]


@dataclass(frozen=True, slots=True)
class SavedAndLaunchedWorkflowResult:
    """Result of saving a composed workflow in the Workspace and launching a real run."""

    workflow_uri: str
    version: str
    run_id: str
    execution_regime: WorkflowExecutionRegime
    run_status: str
    executed_step_keys: tuple[str, ...]
    snapshot_count: int


def build_generic_core_blueprint(
    *,
    workspace_id: str,
    modification_instruction: str | None = None,
) -> AssistantWorkflowBlueprint:
    """Fallback domain-agnostic workflow blueprint with zero SDLC vocabulary (`AD-20`)."""
    has_extra = bool(modification_instruction and len(modification_instruction.strip()) > 0)
    wf_uri = (
        f"orcia://workflows/{workspace_id}-multi-source-audit-v2"
        if has_extra
        else f"orcia://workflows/{workspace_id}-multi-source-audit"
    )
    version = "1.1.0" if has_extra else "1.0.0"
    steps: list[dict[str, Any]] = [
        {
            "step_key": "step_1_intent_anchor",
            "title": "1. Cadrage & Objectif Métier (Ancre Humaine)",
            "step_type": "AGENT",
            "human_authored_required": True,
            "agent_uri": "orcia://agents/intent-framer",
            "depends_on": [],
        },
        {
            "step_key": "step_2_context_collect",
            "title": "2. Collecte & Vérification des Sources Fédérées",
            "step_type": "SKILL",
            "human_authored_required": False,
            "skill_uri": "orcia://skills/context-collector",
            "depends_on": ["step_1_intent_anchor"],
        },
    ]
    extra_yaml = ""
    last_dep = "step_2_context_collect"
    if has_extra:
        steps.append(
            {
                "step_key": "step_3_custom_control",
                "title": "3. Contrôle Complémentaire Demandé",
                "step_type": "AGENT",
                "human_authored_required": False,
                "agent_uri": "orcia://agents/compliance-evaluator",
                "depends_on": ["step_2_context_collect"],
            }
        )
        last_dep = "step_3_custom_control"
        extra_yaml = """
  - step_key: "step_3_custom_control"
    title: "3. Contrôle Complémentaire Demandé"
    step_type: "AGENT"
    agent_uri: "orcia://agents/compliance-evaluator"
    depends_on:
      - "step_2_context_collect"
    instructions: "Exécuter le contrôle complémentaire demandé sur les sources collectées." """

    steps.append(
        {
            "step_key": "step_final_verify",
            "title": "Vérification Post-Action & Synthèse",
            "step_type": "POST_ACTION_VERIFICATION",
            "human_authored_required": False,
            "skill_uri": "orcia://skills/post-action-verifier",
            "depends_on": [last_dep],
        }
    )
    manifest_yaml = f"""uri: "{wf_uri}"
title: "Audit Multi-Sources & Vérification de Conformité"
description: "Workflow générique de collecte multi-sources et vérification post-action."
version: "{version}"
criticality: "STANDARD"
execution_regime: "BACKGROUND_FAST_PATH"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
adaptive_gate_policy: "STANDARD"
max_cost_usd: 8.0
steps:
  - step_key: "step_1_intent_anchor"
    title: "1. Cadrage & Objectif Métier (Ancre Humaine)"
    step_type: "AGENT"
    agent_uri: "orcia://agents/intent-framer"
    human_authored_required: true
    instructions: "Définir l'objectif métier et les invariants de contrôle."
  - step_key: "step_2_context_collect"
    title: "2. Collecte & Vérification des Sources Fédérées"
    step_type: "SKILL"
    skill_uri: "orcia://skills/context-collector"
    depends_on:
      - "step_1_intent_anchor"
    instructions: "Collecter les tranches via ContextSourcePort."{extra_yaml}
  - step_key: "step_final_verify"
    title: "Vérification Post-Action & Synthèse"
    step_type: "POST_ACTION_VERIFICATION"
    depends_on:
      - "{last_dep}"
    verification_window_seconds: 30
    instructions: "Vérifier la cohérence finale des livrables produits."
"""
    return AssistantWorkflowBlueprint(
        template_key="core-multi-source-audit",
        workflow_uri=wf_uri,
        title="Audit Multi-Sources & Vérification de Conformité",
        description="Workflow générique de collecte multi-sources et vérification post-action.",
        default_execution_regime="BACKGROUND_FAST_PATH",
        manifest_yaml=manifest_yaml,
        steps_summary=tuple(steps),
    )


def blueprint_to_proposal(blueprint: AssistantWorkflowBlueprint) -> AssistantWorkflowProposal:
    """Convert an `AssistantWorkflowBlueprint` into an `@xyflow/react` proposal (`UX-DR15`)."""
    nodes: list[XyFlowNodeSpec] = []
    edges: list[XyFlowEdgeSpec] = []
    for idx, step in enumerate(blueprint.steps_summary):
        step_key = str(step["step_key"])
        nodes.append(
            XyFlowNodeSpec(
                id=step_key,
                position_x=float(idx * 260),
                position_y=80.0,
                label=str(step["title"]),
                step_type=str(step["step_type"]),
                human_authored_required=bool(step.get("human_authored_required", False)),
            )
        )
        for dep in step.get("depends_on", ()):
            edges.append(
                XyFlowEdgeSpec(
                    id=f"e-{dep}-{step_key}",
                    source=str(dep),
                    target=step_key,
                    animated=True,
                )
            )
    return AssistantWorkflowProposal(
        proposal_id=new_uuid7_str(),
        workflow_uri=blueprint.workflow_uri,
        title=blueprint.title,
        description=blueprint.description,
        execution_regime=blueprint.default_execution_regime,
        manifest_yaml=blueprint.manifest_yaml,
        nodes=tuple(nodes),
        edges=tuple(edges),
    )


def resolve_assistant_blueprint(
    *,
    user_prompt: str,
    workspace_id: str,
    modification_instruction: str | None = None,
) -> AssistantWorkflowBlueprint:
    """Resolve the best matching `orcia.assistant_templates` plugin or fallback to core."""
    lower = user_prompt.lower()
    for plugin in list_registered_assistant_templates():
        if plugin.matches_intent(lower):
            return plugin.build_blueprint(
                workspace_id=workspace_id,
                modification_instruction=modification_instruction,
            )
    return build_generic_core_blueprint(
        workspace_id=workspace_id,
        modification_instruction=modification_instruction,
    )
