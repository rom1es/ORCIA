"""DAG topology, policy plugin, and SUB_WORKFLOW depth validators (`Story 3.1`, `FR-30`)."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration._orchestration_yaml_locales import get_yaml_copy
from orcia_core.orchestration.errors import (
    CriticalWorkflowRequiresHumanGateError,
    IntentionBeforeCodeRequiredError,
    SubWorkflowCycleDetectedError,
    SubWorkflowMaxDepthExceededError,
    UnknownWorkflowPolicyError,
    ValidationDomainError,
)
from orcia_core.orchestration.models import (
    MAX_SUB_WORKFLOW_NESTING_DEPTH,
    WorkflowAsCodeDefinition,
    WorkflowEngineeringMode,
    WorkflowStepSpec,
    WorkflowValidationFinding,
)
from orcia_core.orchestration.yaml_loader import (
    get_workflow_policy_plugins,
    parse_single_step_spec,
)


def validate_steps_and_dag(
    raw_steps: Any,
    *,
    steps_line: int,
    mode: WorkflowEngineeringMode,
    findings: list[WorkflowValidationFinding],
) -> tuple[tuple[WorkflowStepSpec, ...], tuple[str, ...]]:
    """Parse all steps, verify dependency links & feedback targets, and check topological order."""
    yc = get_yaml_copy()
    if not isinstance(raw_steps, list) or not raw_steps:
        findings.append(
            WorkflowValidationFinding(
                line=steps_line,
                rule_code="RULE_STEPS_NON_EMPTY",
                field_path="steps",
                message=yc["steps_non_empty"],
            )
        )
        return (), ()

    parsed_steps: list[WorkflowStepSpec] = []
    seen_keys: set[str] = set()
    for idx, raw_step in enumerate(raw_steps):
        step = parse_single_step_spec(raw_step, idx, steps_line, seen_keys, findings)
        if step is not None:
            parsed_steps.append(step)

    steps_by_key = {s.step_key: s for s in parsed_steps}
    for step in parsed_steps:
        for dep in step.depends_on:
            if dep not in steps_by_key:
                findings.append(
                    WorkflowValidationFinding(
                        line=step.line_number,
                        rule_code="RULE_UNKNOWN_DEPENDENCY",
                        field_path=f"steps.{step.step_key}.depends_on",
                        message=yc["unknown_dep"].format(step_key=step.step_key, dep=dep),
                    )
                )
        if step.feedback_target_step_key and step.feedback_target_step_key not in steps_by_key:
            findings.append(
                WorkflowValidationFinding(
                    line=step.line_number,
                    rule_code="RULE_UNKNOWN_FEEDBACK_TARGET",
                    field_path=f"steps.{step.step_key}.feedback_target_step_key",
                    message=yc["unknown_feedback"].format(
                        step_key=step.step_key, target=step.feedback_target_step_key
                    ),
                )
            )

    in_degree: dict[str, int] = {s.step_key: 0 for s in parsed_steps}
    adj: dict[str, list[str]] = {s.step_key: [] for s in parsed_steps}
    for step in parsed_steps:
        for dep in step.depends_on:
            if dep in adj:
                adj[dep].append(step.step_key)
                in_degree[step.step_key] += 1

    queue = [s.step_key for s in parsed_steps if in_degree[s.step_key] == 0]
    topo_order: list[str] = []
    while queue:
        curr = queue.pop(0)
        topo_order.append(curr)
        for nxt in adj[curr]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    if len(topo_order) < len(parsed_steps):
        cycle_keys = [s.step_key for s in parsed_steps if s.step_key not in topo_order]
        first_cycle_step = steps_by_key[cycle_keys[0]]
        findings.append(
            WorkflowValidationFinding(
                line=first_cycle_step.line_number,
                rule_code="RULE_DAG_CYCLE_DETECTED",
                field_path=f"steps.{first_cycle_step.step_key}.depends_on",
                message=yc["dag_cycle"].format(
                    line=first_cycle_step.line_number, keys=", ".join(cycle_keys)
                ),
            )
        )

    for plugin in get_workflow_policy_plugins():
        plugin.validate_dag(parsed_steps, steps_by_key, mode, findings)
    return tuple(parsed_steps), tuple(topo_order)


def validate_sub_workflow_hierarchy(
    workflow_uri: str,
    steps: tuple[WorkflowStepSpec, ...],
    *,
    known_workflows: dict[str, WorkflowAsCodeDefinition],
    findings: list[WorkflowValidationFinding],
) -> int:
    """Validate nested `SUB_WORKFLOW` call graphs for cycles and bounded depth."""
    yc = get_yaml_copy()

    def walk(
        curr_steps: tuple[WorkflowStepSpec, ...],
        curr_depth: int,
        call_stack: tuple[str, ...],
    ) -> int:
        max_seen = curr_depth
        for step in curr_steps:
            if step.step_type != "SUB_WORKFLOW" or not step.sub_workflow_uri:
                continue
            target_uri = step.sub_workflow_uri
            next_depth = curr_depth + 1
            if target_uri in call_stack:
                findings.append(
                    WorkflowValidationFinding(
                        line=step.line_number,
                        rule_code="ERR_SUB_WORKFLOW_CYCLE_DETECTED",
                        field_path=f"steps.{step.step_key}.sub_workflow_uri",
                        message=yc["subwf_cycle"].format(
                            line=step.line_number,
                            chain=" -> ".join((*call_stack, target_uri)),
                        ),
                    )
                )
                continue
            if next_depth > MAX_SUB_WORKFLOW_NESTING_DEPTH:
                findings.append(
                    WorkflowValidationFinding(
                        line=step.line_number,
                        rule_code="ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED",
                        field_path=f"steps.{step.step_key}.sub_workflow_uri",
                        message=yc["subwf_depth"].format(
                            line=step.line_number,
                            depth=next_depth,
                            max_depth=MAX_SUB_WORKFLOW_NESTING_DEPTH,
                            uri=target_uri,
                        ),
                    )
                )
                max_seen = max(max_seen, next_depth)
                continue
            max_seen = max(max_seen, next_depth)
            child_wf = known_workflows.get(target_uri)
            if child_wf is not None:
                child_max = walk(child_wf.steps, next_depth, (*call_stack, target_uri))
                max_seen = max(max_seen, child_max)
        return max_seen

    return walk(steps, 0, (workflow_uri,))


def raise_validation_domain_error(
    finding: WorkflowValidationFinding, *, instance: str | None = None
) -> None:
    """Raise the specialized `OrciaDomainError` matching `finding.rule_code`."""
    if finding.rule_code == "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE":
        raise CriticalWorkflowRequiresHumanGateError(
            detail_override=finding.message, instance=instance
        )
    if finding.rule_code == "ERR_INTENTION_BEFORE_CODE_REQUIRED":
        raise IntentionBeforeCodeRequiredError(detail_override=finding.message, instance=instance)
    if finding.rule_code == "ERR_UNKNOWN_WORKFLOW_POLICY":
        raise UnknownWorkflowPolicyError(detail_override=finding.message, instance=instance)
    if finding.rule_code == "ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED":
        raise SubWorkflowMaxDepthExceededError(detail_override=finding.message, instance=instance)
    if finding.rule_code == "ERR_SUB_WORKFLOW_CYCLE_DETECTED":
        raise SubWorkflowCycleDetectedError(detail_override=finding.message, instance=instance)
    raise ValidationDomainError(detail_override=finding.message, instance=instance)


__all__ = [
    "raise_validation_domain_error",
    "validate_steps_and_dag",
    "validate_sub_workflow_hierarchy",
]
