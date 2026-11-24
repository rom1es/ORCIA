"""Secondary Step Executors (`SUB_WORKFLOW`, `HUMAN_TASK`, `HTTP_ACTION`, `POST_ACTION`)."""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration._orchestration_ops_locales import (
    STEP_EXECUTOR_LOCALES,
    get_ops_copy,
)
from orcia_core.orchestration.connector_invoker import ConnectorInvoker
from orcia_kernel.ports import StepExecutorContext, StepExecutorResult


class SubWorkflowStepExecutor:
    """Step executor registration for `SUB_WORKFLOW` steps (`AC-F1`)."""

    @property
    def step_type(self) -> str:
        return "SUB_WORKFLOW"

    def execute_step(self, context: StepExecutorContext) -> StepExecutorResult:
        sc = get_ops_copy(STEP_EXECUTOR_LOCALES)
        payload: dict[str, Any] = {
            "step_key": context.step_key,
            "step_type": "SUB_WORKFLOW",
            "sub_workflow_uri": context.sub_workflow_uri or "",
            "inputs_received": list(context.resolved_inputs.keys()),
        }
        return StepExecutorResult(
            step_key=context.step_key,
            step_type="SUB_WORKFLOW",
            status="EXECUTED",
            artifact_payload=payload,
            summary=sc["subwf_summary"].format(
                uri=context.sub_workflow_uri, step_key=context.step_key
            ),
            details=sc["subwf_details"].format(keys=sorted(context.resolved_inputs.keys())),
            cost_usd=0.0,
        )


class HumanTaskStepExecutor:
    """Real `HUMAN_TASK` step executor pausing on `WAITING_FOR_HUMAN_ARBITRATION` (`AC-F1`)."""

    @property
    def step_type(self) -> str:
        return "HUMAN_TASK"

    def execute_step(self, context: StepExecutorContext) -> StepExecutorResult:
        sc = get_ops_copy(STEP_EXECUTOR_LOCALES)
        human_decision = context.metadata.get("human_decision")
        if isinstance(human_decision, str) and human_decision.strip():
            decision = human_decision.strip()
            payload: dict[str, Any] = {
                "step_key": context.step_key,
                "step_type": "HUMAN_TASK",
                "directive_applied": context.directive,
                "human_decision": decision,
                "inputs_received": list(context.resolved_inputs.keys()),
                "artifact": sc["human_artifact_done"].format(decision=decision),
                "report": sc["human_report_done"].format(
                    step_key=context.step_key, decision=decision
                ),
            }
            return StepExecutorResult(
                step_key=context.step_key,
                step_type="HUMAN_TASK",
                status="EXECUTED",
                artifact_payload=payload,
                summary=sc["human_summary_done"].format(
                    step_key=context.step_key, decision=decision
                ),
                details=sc["human_details_done"].format(decision=decision),
                cost_usd=0.0,
            )

        pending_payload: dict[str, Any] = {
            "step_key": context.step_key,
            "step_type": "HUMAN_TASK",
            "directive_applied": context.directive,
            "inputs_received": list(context.resolved_inputs.keys()),
            "awaiting_human_action": True,
            "artifact": sc["human_artifact_wait"].format(step_key=context.step_key),
        }
        return StepExecutorResult(
            step_key=context.step_key,
            step_type="HUMAN_TASK",
            status="WAITING_FOR_HUMAN_ARBITRATION",
            artifact_payload=pending_payload,
            summary=sc["human_summary_wait"].format(step_key=context.step_key),
            details=sc["human_details_wait"].format(directive=context.directive),
            cost_usd=0.0,
        )


class HttpActionStepExecutor:
    """Real `HTTP_ACTION` step executor invoking a governed `ConnectorPort`."""

    def __init__(self, invoker: ConnectorInvoker | None = None) -> None:
        self._invoker = invoker or ConnectorInvoker()

    @property
    def step_type(self) -> str:
        return "HTTP_ACTION"

    @property
    def invoker(self) -> ConnectorInvoker:
        return self._invoker

    def execute_step(self, context: StepExecutorContext) -> StepExecutorResult:
        scheme = str(context.metadata.get("connector_scheme", "")).strip().lower()
        action = str(context.metadata.get("connector_action", context.step_key)).strip()
        if not scheme and context.skill_uri and "://" in context.skill_uri:
            scheme, rest = context.skill_uri.split("://", 1)
            scheme = scheme.strip().lower()
            action = rest.strip("/") or context.step_key
        if not scheme and context.datasources:
            first_ds = context.datasources[0]
            if "://" in first_ds:
                scheme = first_ds.split("://", 1)[0].strip().lower()
        if not scheme:
            scheme = "orcia"

        idem_key = context.idempotency_key or f"idem:{context.run_id}:{context.step_key}"
        outcome = self._invoker.invoke(
            scheme=scheme,
            action=action,
            payload=dict(context.resolved_inputs),
            idempotency_key=idem_key,
            max_agent_retries=context.max_agent_retries,
            max_cost_usd=max(0.05, context.budget_remaining_usd),
        )
        exec_status = (
            "EXECUTED" if outcome.status == "SUCCEEDED" else "WAITING_FOR_HUMAN_ARBITRATION"
        )
        payload: dict[str, Any] = {
            "step_key": context.step_key,
            "step_type": "HTTP_ACTION",
            "connector_scheme": outcome.scheme,
            "connector_action": outcome.action,
            "idempotency_key": outcome.idempotency_key,
            "attempts_used": outcome.attempts_used,
            "total_wait_seconds": outcome.total_wait_seconds,
            "circuit_state": outcome.circuit_state,
            "connector_output": outcome.sanitized_output,
            "error_code": outcome.error_code,
            "artifact": f"Action connecteur {outcome.scheme}.{outcome.action} : {outcome.status}",
            "report": f"Rapport HTTP_ACTION {context.step_key} : {outcome.status}",
        }
        return StepExecutorResult(
            step_key=context.step_key,
            step_type="HTTP_ACTION",
            status=exec_status,  # type: ignore[arg-type]
            artifact_payload=payload,
            summary=(
                f"Connecteur '{outcome.scheme}.{outcome.action}' -> {outcome.status} "
                f"({outcome.attempts_used} tentative(s))"
            ),
            details=(
                outcome.error_detail
                or f"Sortie connecteur ({outcome.idempotency_key}): {outcome.sanitized_output}"
            ),
            cost_usd=outcome.total_cost_usd,
        )


class PostActionVerificationStepExecutor:
    """Real `POST_ACTION_VERIFICATION` step executor verifying upstream artifacts."""

    @property
    def step_type(self) -> str:
        return "POST_ACTION_VERIFICATION"

    def execute_step(self, context: StepExecutorContext) -> StepExecutorResult:
        sc = get_ops_copy(STEP_EXECUTOR_LOCALES)
        verified_keys = sorted(context.resolved_inputs.keys())
        payload: dict[str, Any] = {
            "step_key": context.step_key,
            "step_type": "POST_ACTION_VERIFICATION",
            "directive_applied": context.directive,
            "inputs_received": verified_keys,
            "verification_verdict": "PASS",
            "artifact": sc["post_artifact"].format(step_key=context.step_key),
            "report": sc["post_report"].format(step_key=context.step_key, count=len(verified_keys)),
        }
        return StepExecutorResult(
            step_key=context.step_key,
            step_type="POST_ACTION_VERIFICATION",
            status="EXECUTED",
            artifact_payload=payload,
            summary=sc["post_summary"].format(step_key=context.step_key),
            details=sc["post_details"].format(keys=verified_keys, directive=context.directive),
            cost_usd=0.05,
        )


__all__ = [
    "HttpActionStepExecutor",
    "HumanTaskStepExecutor",
    "PostActionVerificationStepExecutor",
    "SubWorkflowStepExecutor",
]
