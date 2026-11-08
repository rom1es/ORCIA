"""GatePipelineExecutor enforcing Deterministic-First Inviolability & Auto-Heal (`ADR-06`).

Rules (`CA-9.4.1`, `CA-9.4.2`):
1. 100% of deterministic controls execute BEFORE any probabilistic control (*Hunter*).
2. In `NATIVE_ORCIA` mode, when a deterministic control fails, `GatePipelineExecutor` invokes the
   self-healing callback up to `max_self_heal_retries` (default 3) with `diagnostic_stderr`.
3. If any deterministic control remains `FAILED` after bounded retries, probabilistic *Hunters*
   are NEVER invoked (`probabilistic_invoked = False`, `0` Hunter tokens spent).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field

from orcia_core.workflows.gates.runners import (
    GENERIC_GATE_RUNNERS,
    DeterministicRunnerResult,
)
from orcia_core.workflows.schemas_v2 import (
    DeterministicControlSpec,
    ExecutionMode,
    GateExecutionStrategy,
    NonDeterministicControlSpec,
    StepControlsPipeline,
)


class DeterministicControlExecutionRecord(BaseModel):
    control_id: str
    runner_plugin_id: str
    status: Literal["NOMINAL", "FAILED"]
    attempts: int = 1
    self_healed: bool = False
    violations: list[str] = Field(default_factory=list)
    diagnostic_stderr: str = ""


class ProbabilisticControlExecutionRecord(BaseModel):
    control_id: str
    agent_ref: str
    status: Literal["NOMINAL", "ALERT", "ESCALATED"]
    risk_score: float = Field(ge=0.0, le=1.0)
    findings: list[str] = Field(default_factory=list)


class GatePipelineExecutionReport(BaseModel):
    overall_status: Literal["NOMINAL", "FAILED_DETERMINISTIC", "ESCALATED_PROBABILISTIC"]
    final_artifact_text: str
    deterministic_passed: bool
    probabilistic_invoked: bool
    total_self_heal_retries_used: int = 0
    deterministic_records: list[DeterministicControlExecutionRecord] = Field(default_factory=list)
    probabilistic_records: list[ProbabilisticControlExecutionRecord] = Field(default_factory=list)


SelfHealCallback = Callable[[str, str, int], str]
ProbabilisticHunterCallback = Callable[
    [NonDeterministicControlSpec, str], ProbabilisticControlExecutionRecord
]


def _default_hunter_evaluator(
    spec: NonDeterministicControlSpec,
    artifact_text: str,
) -> ProbabilisticControlExecutionRecord:
    has_risk_marker = "[HIGH_RISK]" in artifact_text
    risk_score = 0.85 if has_risk_marker else 0.15
    status: Literal["NOMINAL", "ALERT", "ESCALATED"] = (
        "ESCALATED" if risk_score >= spec.risk_threshold else "NOMINAL"
    )
    findings = (
        [f"Risk score {risk_score:.2f} exceeds threshold {spec.risk_threshold:.2f}"]
        if status == "ESCALATED"
        else [f"Validated by {spec.agent_ref}"]
    )
    return ProbabilisticControlExecutionRecord(
        control_id=spec.id,
        agent_ref=spec.agent_ref,
        status=status,
        risk_score=risk_score,
        findings=findings,
    )


class GatePipelineExecutor:
    """Executes deterministic controls first (with 3x self-heal), then probabilistic Hunters."""

    def execute_pipeline(
        self,
        *,
        pipeline: StepControlsPipeline,
        artifact_text: str,
        execution_mode: ExecutionMode = ExecutionMode.NATIVE_ORCIA,
        self_heal_callback: SelfHealCallback | None = None,
        hunter_callback: ProbabilisticHunterCallback | None = None,
    ) -> GatePipelineExecutionReport:
        current_text = artifact_text
        det_records: list[DeterministicControlExecutionRecord] = []
        total_retries_used = 0
        all_det_nominal = True

        for ctrl in pipeline.deterministic:
            record, current_text, retries_used = self._run_single_deterministic_control(
                ctrl=ctrl,
                artifact_text=current_text,
                execution_mode=execution_mode,
                self_heal_callback=self_heal_callback,
            )
            det_records.append(record)
            total_retries_used += retries_used
            if record.status != "NOMINAL":
                all_det_nominal = False
                if pipeline.strategy == GateExecutionStrategy.FAIL_FAST:
                    break

        if not all_det_nominal:
            return GatePipelineExecutionReport(
                overall_status="FAILED_DETERMINISTIC",
                final_artifact_text=current_text,
                deterministic_passed=False,
                probabilistic_invoked=False,
                total_self_heal_retries_used=total_retries_used,
                deterministic_records=det_records,
                probabilistic_records=[],
            )

        # ADR-06: Only invoke Hunters when 100% of deterministic controls are NOMINAL
        evaluator = hunter_callback or _default_hunter_evaluator
        prob_records: list[ProbabilisticControlExecutionRecord] = []
        escalated = False
        for nd_ctrl in pipeline.non_deterministic:
            prob_rec = evaluator(nd_ctrl, current_text)
            prob_records.append(prob_rec)
            if prob_rec.status in ("ALERT", "ESCALATED"):
                escalated = True

        overall: Literal["NOMINAL", "FAILED_DETERMINISTIC", "ESCALATED_PROBABILISTIC"] = (
            "ESCALATED_PROBABILISTIC" if escalated else "NOMINAL"
        )
        return GatePipelineExecutionReport(
            overall_status=overall,
            final_artifact_text=current_text,
            deterministic_passed=True,
            probabilistic_invoked=len(pipeline.non_deterministic) > 0,
            total_self_heal_retries_used=total_retries_used,
            deterministic_records=det_records,
            probabilistic_records=prob_records,
        )

    @staticmethod
    def _run_single_deterministic_control(
        *,
        ctrl: DeterministicControlSpec,
        artifact_text: str,
        execution_mode: ExecutionMode,
        self_heal_callback: SelfHealCallback | None,
    ) -> tuple[DeterministicControlExecutionRecord, str, int]:
        runner = GENERIC_GATE_RUNNERS.get(ctrl.runner_plugin_id)
        if runner is None:
            raise ValueError(f"Unknown deterministic runner plugin: {ctrl.runner_plugin_id}")

        current_text = artifact_text
        res: DeterministicRunnerResult = runner(current_text, ctrl.config)
        attempts = 1
        retries_used = 0
        self_healed = False

        if (
            res.status == "FAILED"
            and execution_mode == ExecutionMode.NATIVE_ORCIA
            and self_heal_callback is not None
        ):
            for retry_idx in range(1, ctrl.max_self_heal_retries + 1):
                retries_used += 1
                attempts += 1
                current_text = self_heal_callback(current_text, res.diagnostic_stderr, retry_idx)
                res = runner(current_text, ctrl.config)
                if res.status == "NOMINAL":
                    self_healed = True
                    break

        record = DeterministicControlExecutionRecord(
            control_id=ctrl.id,
            runner_plugin_id=ctrl.runner_plugin_id,
            status=res.status,
            attempts=attempts,
            self_healed=self_healed,
            violations=res.violations,
            diagnostic_stderr=res.diagnostic_stderr,
        )
        return record, current_text, retries_used


__all__ = [
    "DeterministicControlExecutionRecord",
    "GatePipelineExecutionReport",
    "GatePipelineExecutor",
    "ProbabilisticControlExecutionRecord",
]
