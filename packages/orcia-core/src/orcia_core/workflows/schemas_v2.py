"""Agnostic VSM, Bounded Workflows v2 & Claim-Check Pointer Schemas (`TASK-02`).

100% domain-agnostic schemas: zero mention of vendor or methodology terms.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from orcia_core.storage.claim_check import ClaimCheckPointer as ClaimCheckPointer


class WorkflowLifecycleStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED_WHAT_IF = "validated_what_if"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ExecutionMode(StrEnum):
    NATIVE_ORCIA = "native_orcia"
    EXTERNAL_DELEGATED_GATE = "external_delegated"


class EffortLevel(StrEnum):
    DEFAULT = "default"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ControlMaturityStatus(StrEnum):
    IN_PLACE = "place"
    TO_ADD = "ajouter"
    HYPOTHESIS = "hypothese"


class GateExecutionStrategy(StrEnum):
    FAIL_FAST = "fail_fast"
    AGGREGATED_AUDIT = "aggregated_audit"


class ContractParameter(BaseModel):
    """Generic input parameter referencing Federated Catalog URIs without domain coupling."""

    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    label: str
    scalar_type: Literal["string", "integer", "boolean", "enum", "catalog_ref"] = "string"
    catalog_entity_uri_pattern: str | None = Field(
        default=None,
        description="Ex: catalog://issue_tracker/work_item/{key} or catalog://hr_system/employee/{id}",
    )
    default_value: str | None = None
    required: bool = True


class WorkflowContract(BaseModel):
    parameters: list[ContractParameter] = Field(default_factory=list)
    required_markdown_sections: list[str] = Field(default_factory=list)
    output_schema_uri: str | None = Field(
        default=None,
        description="Ex: pack://domain-pack/schemas/study-v1.json",
    )


class DeterministicControlSpec(BaseModel):
    id: str
    name: str
    short_label: str
    status: ControlMaturityStatus = ControlMaturityStatus.IN_PLACE
    runner_plugin_id: str = Field(
        ..., description="Generic runner ID in Core (`markdown_contract_runner`, etc.)"
    )
    verifies_description: str
    on_ko_behavior: str
    max_self_heal_retries: int = Field(default=3, ge=0, le=5)
    config: dict[str, Any] = Field(default_factory=dict)


class NonDeterministicControlSpec(BaseModel):
    id: str
    name: str
    short_label: str
    status: ControlMaturityStatus = ControlMaturityStatus.IN_PLACE
    evaluator_type: Literal["adversarial_agent", "custom_agent_evaluator", "self_check"]
    agent_ref: str = Field(..., description="Agent reference in the Pack Registry")
    model_override: str | None = Field(
        default=None,
        description="Recommended: distinct model family from producer",
    )
    risk_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    verifies_description: str
    hypothesis_note: str | None = None
    on_ko_behavior: str


class StepControlsPipeline(BaseModel):
    delegated_to_step_num: str | None = None
    delegation_note: str | None = None
    strategy: GateExecutionStrategy = GateExecutionStrategy.FAIL_FAST
    sandbox_dry_run: bool = True
    deterministic: list[DeterministicControlSpec] = Field(default_factory=list)
    non_deterministic: list[NonDeterministicControlSpec] = Field(default_factory=list)


class DeterministicSubStepSpec(BaseModel):
    """DBOS-orchestrated deterministic sub-step (`ADR-01` & `ADR-02`)."""

    id: str
    name: str
    short_label: str
    enabled: bool = True
    step_executor_type: Literal["agent_executor", "program_executor"] = "agent_executor"
    trigger_condition_label: str
    role_description: str
    instruction_prompt_or_ref: str
    toolbox_mcp_permissions: list[dict[str, str]] = Field(default_factory=list)
    skill_refs: list[str] = Field(default_factory=list)
    output_description: str
    requires_human_checkpoint: bool = True
    checkpoint_label: str = Field(..., description="Ex: Validation de la Qualification")
    approver_rbac_role: str = Field(default="workspace:member")
    write_preview_required: bool = Field(
        default=False,
        description="If True, Permission Broker blocks external write until human preview approval",
    )


class WorkflowDefinitionV2(BaseModel):
    """Bounded executable DBOS workflow attachable to a VSM step."""

    id: str
    slug: str
    title: str
    version: str = "1.0.0"
    status: WorkflowLifecycleStatus = WorkflowLifecycleStatus.DRAFT
    pack_id: str
    linked_vsm_step_nums: list[str] = Field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.NATIVE_ORCIA
    external_tool_label: str | None = Field(
        default=None,
        description="Informational label when EXTERNAL_DELEGATED_GATE",
    )
    external_completion_event: str | None = Field(
        default=None,
        description="Outbox event triggering the ORCIA Gatekeeper after external work",
    )
    model_override: str = "team_default"
    effort: EffortLevel = EffortLevel.DEFAULT
    global_system_prompt_or_ref: str | None = None
    guardrails: list[str] = Field(default_factory=list)
    knowledge_feedback_target_agent: str | None = None
    contract: WorkflowContract = Field(default_factory=WorkflowContract)
    sub_steps: list[DeterministicSubStepSpec] = Field(default_factory=list)
    controls: StepControlsPipeline = Field(default_factory=StepControlsPipeline)


class ReturnLoopSpec(BaseModel):
    target_step_num: str
    is_primary: bool = False
    when_condition: str
    remarks_carried: str | None = None
    behavior_actuel: str | None = None
    behavior_ia: str | None = None
    reentry_mode: str = "corrections"
    target_sub_step_id: str | None = None


class VsmStepNodeSpec(BaseModel):
    node_type: Literal["step"] = "step"
    num: str
    phase_id: str
    title: str
    badge_label: str | None = None
    opportunity_codes: list[str] = Field(default_factory=list)
    linked_workflow_id: str | None = None
    agent_ref: str | None = None
    platform_badge: str | None = None
    sub_step_ids: list[str] = Field(default_factory=list)
    input_actuel: str
    input_ia: str
    input_ia_short: str | None = None
    output_actuel: str
    output_ia: str
    output_ia_short: str | None = None
    actor_actuel: str
    actor_ia: str
    actor_ia_short: str | None = None
    human_co_author: str | None = None
    tools_actuel: list[str] = Field(default_factory=list)
    tools_ia: list[str] = Field(default_factory=list)
    validation_actuel: str
    validation_ia: str
    validation_ia_short: str | None = None
    humans_actuel: list[dict[str, str]] = Field(default_factory=list)
    humans_ia: list[dict[str, str]] = Field(default_factory=list)
    interactions_note: str | None = None
    interactions_actuel: list[dict[str, str]] = Field(default_factory=list)
    interactions_ia: list[dict[str, str]] = Field(default_factory=list)
    controls: StepControlsPipeline = Field(default_factory=StepControlsPipeline)
    detail_markdown: str = ""


class VsmPassageNodeSpec(BaseModel):
    node_type: Literal["passage"] = "passage"
    id: str
    phase_id: str
    short_title: str
    title: str
    description: str
    approver_rbac_roles: list[str] = Field(default_factory=list)
    sla_timeout_hours: int = 72
    human_mandatory_rationale: str
    ai_assistable_scope: str
    delegable_long_term: str
    note: str | None = None
    return_loops: list[ReturnLoopSpec] = Field(default_factory=list)


VsmNodeUnion = Annotated[
    VsmStepNodeSpec | VsmPassageNodeSpec,
    Field(discriminator="node_type"),
]


class ValueStreamMapSpec(BaseModel):
    id: str
    slug: str
    title: str
    subtitle: str
    source_note: str
    guiding_principle: str
    tools_note: str = ""
    pack_id: str
    knowledge_foundation: dict[str, str] = Field(default_factory=dict)
    phases: list[dict[str, str]]
    opportunities: dict[str, dict[str, str]] = Field(default_factory=dict)
    agents_catalog: dict[str, dict[str, Any]] = Field(default_factory=dict)
    nodes: list[VsmNodeUnion]


class ImpactAssessmentResult(BaseModel):
    """Result matrix returned by What-If sandbox simulation (`POST .../what-if`)."""

    workflow_id: str
    version: str
    sandbox_isolated: bool = True
    external_writes_executed: int = 0
    sub_steps_evaluated: int
    deterministic_gates_passed: bool
    probabilistic_gates_passed: bool
    estimated_tokens: int
    estimated_cost_usd: float
    findings: list[dict[str, Any]] = Field(default_factory=list)


def fork_workflow_as_draft(workflow: WorkflowDefinitionV2) -> WorkflowDefinitionV2:
    """Create a `-draft` fork when modifying a `PUBLISHED` workflow (`CA-9.1.2`)."""
    if workflow.status != WorkflowLifecycleStatus.PUBLISHED:
        return workflow
    parts = workflow.version.split("-")[0].split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        next_ver = f"{parts[0]}.{int(parts[1]) + 1}.0-draft"
    else:
        next_ver = f"{workflow.version}-draft"
    return workflow.model_copy(
        update={
            "version": next_ver,
            "status": WorkflowLifecycleStatus.DRAFT,
        }
    )


__all__ = [
    "ClaimCheckPointer",
    "ContractParameter",
    "ControlMaturityStatus",
    "DeterministicControlSpec",
    "DeterministicSubStepSpec",
    "EffortLevel",
    "ExecutionMode",
    "GateExecutionStrategy",
    "ImpactAssessmentResult",
    "NonDeterministicControlSpec",
    "ReturnLoopSpec",
    "StepControlsPipeline",
    "ValueStreamMapSpec",
    "VsmNodeUnion",
    "VsmPassageNodeSpec",
    "VsmStepNodeSpec",
    "WorkflowContract",
    "WorkflowDefinitionV2",
    "WorkflowLifecycleStatus",
    "fork_workflow_as_draft",
]
