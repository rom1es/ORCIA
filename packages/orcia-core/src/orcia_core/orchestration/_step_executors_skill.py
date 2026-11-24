"""Skill & Deterministic Gate Step Executor (`SKILL`, `TIER_1_WASM`)."""

from __future__ import annotations

import json
from typing import Any

from orcia_core.gates.deterministic import DeterministicGateService
from orcia_core.gates.models import DeterministicGateInput, OntologyAxiomCheckRule
from orcia_core.orchestration._orchestration_ops_locales import (
    STEP_EXECUTOR_LOCALES,
    get_ops_copy,
)
from orcia_core.orchestration.connector_invoker import scrub_connector_secrets
from orcia_kernel.ports import StepExecutorContext, StepExecutorResult


class SkillStepExecutor:
    """Real `SKILL` step executor delegating `TIER_1_WASM` & Deterministic Gates to Sandbox."""

    def __init__(self, gate_service: DeterministicGateService | None = None) -> None:
        self._gate_service = gate_service or DeterministicGateService()

    @property
    def step_type(self) -> str:
        return "SKILL"

    @property
    def gate_service(self) -> DeterministicGateService:
        return self._gate_service

    def execute_step(self, context: StepExecutorContext) -> StepExecutorResult:
        sanitized = scrub_connector_secrets(context.resolved_inputs)
        skill_uri = context.skill_uri or f"orcia://skills/{context.step_key}"
        sandbox_tier = str(context.metadata.get("sandbox_tier", "")).strip().upper()
        if sandbox_tier == "TIER_1_WASM" or skill_uri.startswith("orcia://gates/deterministic"):
            raw_axioms = list(context.metadata.get("ontology_axioms") or [])
            axioms = tuple(
                OntologyAxiomCheckRule(
                    axiom_key=str(ax.get("axiom_key", "axiom")),
                    forbidden_term=str(ax.get("forbidden_term", "")),
                    required_term=str(ax.get("required_term", "")),
                )
                for ax in raw_axioms
                if isinstance(ax, dict)
            )
            req_sections = tuple(
                str(s) for s in (context.metadata.get("required_sections") or ("artifact",))
            )
            gate_eval = self._gate_service.evaluate_deterministic_gate(
                DeterministicGateInput(
                    workspace_id=context.workspace_id,
                    run_id=context.run_id,
                    step_execution_id=str(
                        context.metadata.get("step_execution_id", context.step_key)
                    ),
                    step_key=context.step_key,
                    artifact_payload=(
                        dict(sanitized) if sanitized else {"artifact": context.directive}
                    ),
                    required_sections=req_sections,
                    ontology_axioms=axioms,
                    timeout_ms=int(context.metadata.get("timeout_ms", 5000)),
                    max_memory_mb=int(context.metadata.get("max_memory_mb", 256)),
                    simulate_timeout_sleep_ms=int(
                        context.metadata.get("simulate_timeout_sleep_ms", 0)
                    ),
                    simulate_network_escape=bool(
                        context.metadata.get("simulate_network_escape", False)
                    ),
                    simulate_fs_escape_path=(
                        str(context.metadata["simulate_fs_escape_path"])
                        if context.metadata.get("simulate_fs_escape_path")
                        else None
                    ),
                    simulate_memory_alloc_mb=int(
                        context.metadata.get("simulate_memory_alloc_mb", 0)
                    ),
                ),
                raise_on_failure=bool(context.metadata.get("raise_on_gate_failure", True)),
            )
            sc = get_ops_copy(STEP_EXECUTOR_LOCALES)
            payload_gate: dict[str, Any] = {
                "step_key": context.step_key,
                "step_type": "SKILL",
                "skill_uri": skill_uri,
                "sandbox_tier": "TIER_1_WASM",
                "gate_evaluation_id": gate_eval.id,
                "gate_status": gate_eval.status,
                "gate_score": gate_eval.score,
                "schema_validation_passed": gate_eval.schema_validation_passed,
                "ontology_axioms_passed": gate_eval.ontology_axioms_passed,
                "pattern_drift_passed": gate_eval.pattern_drift_passed,
                "duration_ms": gate_eval.duration_ms,
                "artifact": sc["gate_artifact"].format(
                    skill_uri=skill_uri, status=gate_eval.status
                ),
                "report": sc["gate_report"].format(
                    step_key=context.step_key, status=gate_eval.status
                ),
            }
            return StepExecutorResult(
                step_key=context.step_key,
                step_type="SKILL",
                status="EXECUTED" if gate_eval.status == "PASS" else "FAILED",
                artifact_payload=payload_gate,
                summary=sc["gate_summary"].format(skill_uri=skill_uri, status=gate_eval.status),
                details=f"Sandbox TIER_1_WASM ({gate_eval.duration_ms} ms) score={gate_eval.score}",
                cost_usd=0.01,
            )

        sc = get_ops_copy(STEP_EXECUTOR_LOCALES)
        payload: dict[str, Any] = {
            "step_key": context.step_key,
            "step_type": "SKILL",
            "skill_uri": skill_uri,
            "directive_applied": context.directive,
            "inputs_received": list(sanitized.keys()),
            "computed_digest": json.dumps(sanitized, sort_keys=True),
            "artifact": sc["skill_artifact"].format(skill_uri=skill_uri, step_key=context.step_key),
            "adr": sc["skill_adr"].format(step_key=context.step_key),
            "report": sc["skill_report"].format(step_key=context.step_key),
        }
        return StepExecutorResult(
            step_key=context.step_key,
            step_type="SKILL",
            status="EXECUTED",
            artifact_payload=payload,
            summary=sc["skill_summary"].format(skill_uri=skill_uri, step_key=context.step_key),
            details=sc["skill_details"].format(directive=context.directive),
            cost_usd=0.05,
        )


__all__ = ["SkillStepExecutor"]
