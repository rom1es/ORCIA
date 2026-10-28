"""Workflow-as-Code YAML/JSON Parser & DAG Validator (Story 3.1, Story 3.2e, FR-11, FR-29, FR-30).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`) and zero SDLC
vocabulary (`AD-19`, `AD-20`, `AC-E2`).
"""

from __future__ import annotations

import json
from typing import Any

from orcia_core.catalog.cas_resolver import compute_bytes_sha256
from orcia_core.catalog.models import ScalarValue
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
    WorkflowValidationReport,
)
from orcia_core.orchestration.yaml_loader import (
    VALID_CRITICALITIES,
    VALID_EXECUTION_REGIMES,
    VALID_GATE_POLICIES,
    VALID_TIE_BREAK_POLICIES,
    get_valid_workflow_modes,
    get_workflow_policy_plugins,
    is_registered_workflow_policy,
    line_of,
    parse_raw_yaml_or_json,
    parse_single_step_spec,
)
from orcia_kernel.ids import new_uuid7_str


class WorkflowAsCodeValidator:
    """Deterministic YAML/JSON parser & DAG validator for Workflow-as-Code (`FR-11`, `AD-20`)."""

    @classmethod
    def parse_raw_manifest(
        cls, raw_text: str
    ) -> tuple[dict[str, Any], list[WorkflowValidationFinding]]:
        """Parse YAML or JSON text and return root dict with line numbers or syntax findings."""
        return parse_raw_yaml_or_json(raw_text)

    @classmethod
    def _validate_steps_and_dag(
        cls,
        raw_steps: Any,
        *,
        steps_line: int,
        mode: WorkflowEngineeringMode,
        findings: list[WorkflowValidationFinding],
    ) -> tuple[tuple[WorkflowStepSpec, ...], tuple[str, ...]]:
        if not isinstance(raw_steps, list) or not raw_steps:
            findings.append(
                WorkflowValidationFinding(
                    line=steps_line,
                    rule_code="RULE_STEPS_NON_EMPTY",
                    field_path="steps",
                    message="Le manifeste doit contenir au moins une étape dans 'steps'.",
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
                            message=f"L'étape '{step.step_key}' dépend de '{dep}' introuvable.",
                        )
                    )
            if step.feedback_target_step_key and step.feedback_target_step_key not in steps_by_key:
                findings.append(
                    WorkflowValidationFinding(
                        line=step.line_number,
                        rule_code="RULE_UNKNOWN_FEEDBACK_TARGET",
                        field_path=f"steps.{step.step_key}.feedback_target_step_key",
                        message=(
                            f"La boucle de rétroaction de '{step.step_key}' cible "
                            f"'{step.feedback_target_step_key}' introuvable."
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
                    message=(
                        f"Cycle de dépendances détecté à la ligne {first_cycle_step.line_number} "
                        f"impliquant: {', '.join(cycle_keys)}."
                    ),
                )
            )

        cls._validate_registered_policy_plugins(parsed_steps, steps_by_key, mode, findings)
        return tuple(parsed_steps), tuple(topo_order)

    @classmethod
    def _validate_registered_policy_plugins(
        cls,
        parsed_steps: list[WorkflowStepSpec],
        steps_by_key: dict[str, WorkflowStepSpec],
        mode: WorkflowEngineeringMode,
        findings: list[WorkflowValidationFinding],
    ) -> None:
        """Delegate domain/pack policy checks to `entry_points(group='orcia.workflow_policies')`."""
        for plugin in get_workflow_policy_plugins():
            plugin.validate_dag(parsed_steps, steps_by_key, mode, findings)

    @classmethod
    def _validate_sub_workflow_hierarchy(
        cls,
        workflow_uri: str,
        steps: tuple[WorkflowStepSpec, ...],
        *,
        known_workflows: dict[str, WorkflowAsCodeDefinition],
        findings: list[WorkflowValidationFinding],
    ) -> int:
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
                            message=(
                                f"Ligne {step.line_number}: Cycle d'appels SUB_WORKFLOW détecté: "
                                f"{' -> '.join((*call_stack, target_uri))}."
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
                            message=(
                                f"Ligne {step.line_number}: Profondeur SUB_WORKFLOW {next_depth} > "
                                f"{MAX_SUB_WORKFLOW_NESTING_DEPTH} pour '{target_uri}'."
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

    @classmethod
    def validate_manifest(
        cls,
        raw_manifest: str,
        *,
        workspace_id: str | None = None,
        known_workflows: dict[str, WorkflowAsCodeDefinition] | None = None,
        raise_on_error: bool = False,
        instance: str | None = None,
    ) -> WorkflowValidationReport:
        """Validate a YAML/JSON Workflow-as-Code manifest with exact line numbers (`FR-11`)."""
        root, findings = cls.parse_raw_manifest(raw_manifest)
        if findings:
            if raise_on_error:
                cls._raise_domain_error(findings[0], instance=instance)
            return WorkflowValidationReport(valid=False, workflow=None, findings=tuple(findings))

        uri = str(root.get("uri", "")).strip()
        if not uri or "://" not in uri:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "uri", 1),
                    rule_code="RULE_VALID_URI_REQUIRED",
                    field_path="uri",
                    message="Le champ 'uri' doit être une URI canonique valide.",
                )
            )
        title = str(root.get("title", "")).strip()
        if not title:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "title", 1),
                    rule_code="RULE_TITLE_REQUIRED",
                    field_path="title",
                    message="Le champ 'title' est obligatoire.",
                )
            )

        version = str(root.get("version", "1.0.0")).strip()
        criticality = str(root.get("criticality", "STANDARD")).strip()
        if criticality not in VALID_CRITICALITIES:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "criticality", 1),
                    rule_code="RULE_INVALID_CRITICALITY",
                    field_path="criticality",
                    message=f"Criticité invalide '{criticality}'.",
                )
            )
        execution_regime = str(root.get("execution_regime", "INTERACTIVE_COACHING")).strip()
        if execution_regime not in VALID_EXECUTION_REGIMES:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "execution_regime", 1),
                    rule_code="RULE_INVALID_EXECUTION_REGIME",
                    field_path="execution_regime",
                    message=f"Régime d'exécution invalide '{execution_regime}'.",
                )
            )
        tie_break_policy = str(root.get("tie_break_policy", "PAUSE_AND_ESCALATE")).strip()
        if tie_break_policy not in VALID_TIE_BREAK_POLICIES:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "tie_break_policy", 1),
                    rule_code="RULE_INVALID_TIE_BREAK_POLICY",
                    field_path="tie_break_policy",
                    message=f"Politique de départage invalide '{tie_break_policy}'.",
                )
            )
        mode = str(root.get("mode", "standard")).strip()
        valid_modes = get_valid_workflow_modes()
        if mode not in valid_modes:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "mode", 1),
                    rule_code="RULE_INVALID_WORKFLOW_MODE",
                    field_path="mode",
                    message=f"Mode invalide '{mode}'.",
                )
            )
            mode = "standard"

        raw_root_policies = root.get("policies", [])
        root_policies: tuple[str, ...] = (
            tuple(str(p).strip() for p in raw_root_policies if str(p).strip())
            if isinstance(raw_root_policies, list)
            else ()
        )
        for rp in root_policies:
            if not is_registered_workflow_policy(rp):
                findings.append(
                    WorkflowValidationFinding(
                        line=line_of(root, "policies", 1),
                        rule_code="ERR_UNKNOWN_WORKFLOW_POLICY",
                        field_path="policies",
                        message=f"Politique de workflow inconnue '{rp}'.",
                    )
                )

        gate_policy = str(root.get("adaptive_gate_policy", "STANDARD")).strip()
        if gate_policy not in VALID_GATE_POLICIES:
            gate_policy = "STANDARD"

        if criticality == "HIGH_CRITICAL" and execution_regime == "AUTONOMOUS_CONTRACT":
            reg_line = line_of(root, "execution_regime", line_of(root, "criticality", 1))
            findings.append(
                WorkflowValidationFinding(
                    line=reg_line,
                    rule_code="ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE",
                    field_path="execution_regime",
                    message=(
                        f"Ligne {reg_line}: Un workflow HIGH_CRITICAL ne peut pas utiliser "
                        "execution_regime: AUTONOMOUS_CONTRACT (FR-29, AD-18)."
                    ),
                )
            )

        steps, topo_order = cls._validate_steps_and_dag(
            root.get("steps"),
            steps_line=line_of(root, "steps", 1),
            mode=mode,
            findings=findings,
        )
        if (
            criticality == "HIGH_CRITICAL"
            and steps
            and not any(s.requires_human_gate or s.human_authored_required for s in steps)
        ):
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "criticality", 1),
                    rule_code="ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE",
                    field_path="steps",
                    message="Tout workflow HIGH_CRITICAL exige au moins une Gate/Ancre Humaine.",
                )
            )

        resolved_depth = cls._validate_sub_workflow_hierarchy(
            uri or "orcia://workflows/anonymous",
            steps,
            known_workflows=known_workflows or {},
            findings=findings,
        )
        if findings:
            if raise_on_error:
                cls._raise_domain_error(findings[0], instance=instance)
            return WorkflowValidationReport(
                valid=False,
                workflow=None,
                findings=tuple(findings),
                resolved_max_nesting_depth=resolved_depth,
                topological_order=topo_order,
            )

        raw_scalars_val = root.get("scalars")
        raw_scalars: dict[Any, Any] = raw_scalars_val if isinstance(raw_scalars_val, dict) else {}
        scalars: dict[str, ScalarValue] = {
            str(k): v
            for k, v in raw_scalars.items()
            if k not in ("__lines__", "__node_line__") and isinstance(v, (str, int, float, bool))
        }
        datasources = tuple(str(d) for d in (root.get("datasources") or []) if str(d).strip())
        rules = tuple(str(r) for r in (root.get("rules") or []) if str(r).strip())
        facts = tuple(str(f) for f in (root.get("facts") or []) if str(f).strip())

        canonical_payload = json.dumps(
            {
                "uri": uri,
                "version": version,
                "criticality": criticality,
                "execution_regime": execution_regime,
                "tie_break_policy": tie_break_policy,
                "mode": mode,
                "steps": [s.step_key for s in steps],
                "datasources": list(datasources),
            },
            sort_keys=True,
        )
        wf_def = WorkflowAsCodeDefinition(
            id=str(root.get("id") or new_uuid7_str()),
            workspace_id=workspace_id,
            uri=uri,
            title=title,
            description=str(root.get("description", "")).strip(),
            version=version,
            criticality=criticality,  # type: ignore[arg-type]
            execution_regime=execution_regime,  # type: ignore[arg-type]
            tie_break_policy=tie_break_policy,  # type: ignore[arg-type]
            mode=mode,
            adaptive_gate_policy=gate_policy,  # type: ignore[arg-type]
            max_cost_usd=float(root.get("max_cost_usd", 10.0)),
            scalars=scalars,
            datasources=datasources,
            rules=rules,
            facts=facts,
            steps=steps,
            sha256=compute_bytes_sha256(canonical_payload.encode("utf-8")),
            policies=root_policies,
            max_nesting_depth=resolved_depth,
        )
        return WorkflowValidationReport(
            valid=True,
            workflow=wf_def,
            findings=(),
            resolved_max_nesting_depth=resolved_depth,
            topological_order=topo_order,
        )

    @staticmethod
    def _raise_domain_error(
        finding: WorkflowValidationFinding, *, instance: str | None = None
    ) -> None:
        if finding.rule_code == "ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE":
            raise CriticalWorkflowRequiresHumanGateError(
                detail_override=finding.message, instance=instance
            )
        if finding.rule_code == "ERR_INTENTION_BEFORE_CODE_REQUIRED":
            raise IntentionBeforeCodeRequiredError(
                detail_override=finding.message, instance=instance
            )
        if finding.rule_code == "ERR_UNKNOWN_WORKFLOW_POLICY":
            raise UnknownWorkflowPolicyError(detail_override=finding.message, instance=instance)
        if finding.rule_code == "ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED":
            raise SubWorkflowMaxDepthExceededError(
                detail_override=finding.message, instance=instance
            )
        if finding.rule_code == "ERR_SUB_WORKFLOW_CYCLE_DETECTED":
            raise SubWorkflowCycleDetectedError(detail_override=finding.message, instance=instance)
        raise ValidationDomainError(detail_override=finding.message, instance=instance)
