"""Workflow-as-Code YAML/JSON Parser & DAG Validator (Story 3.1, Story 3.2e, FR-11, FR-29, FR-30).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`) and zero SDLC
vocabulary (`AD-19`, `AD-20`, `AC-E2`).
"""

from __future__ import annotations

import json
from typing import Any

from orcia_core.catalog.cas_resolver import compute_bytes_sha256
from orcia_core.catalog.models import ScalarValue
from orcia_core.orchestration._orchestration_yaml_locales import get_yaml_copy
from orcia_core.orchestration._yaml_dag_validator import (
    raise_validation_domain_error,
    validate_steps_and_dag,
    validate_sub_workflow_hierarchy,
)
from orcia_core.orchestration.models import (
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
    is_registered_workflow_policy,
    line_of,
    parse_raw_yaml_or_json,
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
        return validate_steps_and_dag(
            raw_steps, steps_line=steps_line, mode=mode, findings=findings
        )

    @classmethod
    def _validate_sub_workflow_hierarchy(
        cls,
        workflow_uri: str,
        steps: tuple[WorkflowStepSpec, ...],
        *,
        known_workflows: dict[str, WorkflowAsCodeDefinition],
        findings: list[WorkflowValidationFinding],
    ) -> int:
        return validate_sub_workflow_hierarchy(
            workflow_uri, steps, known_workflows=known_workflows, findings=findings
        )

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
        yc = get_yaml_copy()
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
                    message=yc["valid_uri_required"],
                )
            )
        title = str(root.get("title", "")).strip()
        if not title:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "title", 1),
                    rule_code="RULE_TITLE_REQUIRED",
                    field_path="title",
                    message=yc["title_required"],
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
                    message=yc["invalid_criticality"].format(value=criticality),
                )
            )
        execution_regime = str(root.get("execution_regime", "INTERACTIVE_COACHING")).strip()
        if execution_regime not in VALID_EXECUTION_REGIMES:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "execution_regime", 1),
                    rule_code="RULE_INVALID_EXECUTION_REGIME",
                    field_path="execution_regime",
                    message=yc["invalid_regime"].format(value=execution_regime),
                )
            )
        tie_break_policy = str(root.get("tie_break_policy", "PAUSE_AND_ESCALATE")).strip()
        if tie_break_policy not in VALID_TIE_BREAK_POLICIES:
            findings.append(
                WorkflowValidationFinding(
                    line=line_of(root, "tie_break_policy", 1),
                    rule_code="RULE_INVALID_TIE_BREAK_POLICY",
                    field_path="tie_break_policy",
                    message=yc["invalid_tie_break"].format(value=tie_break_policy),
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
                    message=yc["invalid_mode"].format(value=mode),
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
                        message=yc["unknown_root_policy"].format(policy=rp),
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
                    message=yc["high_critical_autonomous"].format(line=reg_line),
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
                    message=yc["high_critical_gate"],
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
        raise_validation_domain_error(finding, instance=instance)
