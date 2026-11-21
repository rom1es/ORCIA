"""Real Step Executors Registry (`orcia.step_executors`, `Story 3.2f`, `Story 26.3`).

Provides concrete `StepExecutorPort` implementations (`AGENT` with native async
`execute_step_async`, `SKILL`, `SUB_WORKFLOW`, `HUMAN_TASK`, `HTTP_ACTION`,
`POST_ACTION_VERIFICATION`) with strictly non-blocking async execution.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._step_executors_actions import (
    HttpActionStepExecutor,
    HumanTaskStepExecutor,
    PostActionVerificationStepExecutor,
    SubWorkflowStepExecutor,
)
from orcia_core.orchestration._step_executors_skill import SkillStepExecutor
from orcia_core.orchestration.connector_invoker import ConnectorInvoker, scrub_connector_secrets
from orcia_core.orchestration.errors import TierModelNotConfiguredError
from orcia_kernel.ports import (
    ExecutionMode,
    LLMPort,
    LlmPromptRequest,
    StepExecutorContext,
    StepExecutorPort,
    StepExecutorResult,
    register_step_executor,
)

logger = get_logger("orcia.core.orchestration.step_executors")


async def execute_step_port_async(
    executor: StepExecutorPort, context: StepExecutorContext
) -> StepExecutorResult:
    """Execute a `StepExecutorPort` asynchronously when `execute_step_async` is available."""
    async_fn = getattr(executor, "execute_step_async", None)
    if callable(async_fn):
        res: StepExecutorResult = await async_fn(context)
        return res
    return executor.execute_step(context)


class AgentStepExecutor:
    """Real `AGENT` step executor invoking `LLMPort` asynchronously (`AC-F1`, `H-11`)."""

    def __init__(
        self,
        llm_gateway: LLMPort | None = None,
        *,
        cognitive_router: Any | None = None,
    ) -> None:
        self._llm: LLMPort | None = llm_gateway
        self._router = cognitive_router

    @property
    def step_type(self) -> str:
        return "AGENT"

    @property
    def llm_gateway(self) -> LLMPort | None:
        return self._llm

    def set_llm_gateway(self, llm_gateway: LLMPort) -> None:
        self._llm = llm_gateway

    def _build_prompt_request(self, context: StepExecutorContext) -> LlmPromptRequest:
        mode: ExecutionMode = (
            "FAST_PATH" if context.execution_regime == "BACKGROUND_FAST_PATH" else "COACHING"
        )
        serialized_inputs = json.dumps(
            scrub_connector_secrets(context.resolved_inputs), sort_keys=True
        )
        model_family = str(context.metadata.get("model_family") or "")
        model_id = str(context.metadata.get("model_id") or "")
        if not model_family or not model_id:
            if self._router is not None:
                tier = str(context.metadata.get("inference_tier") or "complex")
                effort = str(context.metadata.get("effort") or "default")
                tier_val = tier if tier in ("simple", "medium", "complex") else "complex"
                try:
                    resolved = self._router.resolve_mapping(
                        scope_id=context.workspace_id,
                        tier=tier_val,
                        effort=effort,
                    )
                    model_family = resolved.model_family
                    model_id = resolved.model_name
                except Exception as exc:
                    logger.warning(
                        "step_executor.cognitive_router_resolve_failed",
                        workspace_id=context.workspace_id,
                        step_key=context.step_key,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
            if (not model_family or not model_id) and bool(
                getattr(self._llm, "is_cassette_adapter", False)
            ):
                model_family = "cassette"
                model_id = f"cassette/{context.step_key}"
            elif not model_family or not model_id:
                raise TierModelNotConfiguredError(
                    inference_tier=str(context.metadata.get("inference_tier") or "complex"),
                    instance=f"agent_step_executor:{context.step_key}",
                )

        if self._llm is None:
            raise TierModelNotConfiguredError(
                inference_tier=str(context.metadata.get("inference_tier") or "complex"),
                instance=f"agent_step_executor:{context.step_key}",
            )
        return LlmPromptRequest(
            system_prompt=(
                f"ORCIA Agent Executor | workflow={context.workflow_uri} | step={context.step_key}"
            ),
            user_prompt=(
                f"Directive: {context.directive}\n"
                f"Inputs: {serialized_inputs}\n"
                f"AgentURI: {context.agent_uri or 'orcia://agents/default'}"
            ),
            model_family=model_family,
            model_id=model_id,
            execution_mode=mode,
            metadata={
                "run_id": context.run_id,
                "step_key": context.step_key,
                "workspace_id": context.workspace_id,
            },
        )

    @staticmethod
    def _format_completion_result(
        context: StepExecutorContext, completion: Any
    ) -> StepExecutorResult:
        status = (
            "WAITING_FOR_HUMAN_ARBITRATION"
            if completion.scenario_tag == "WAITING_FOR_HUMAN_ARBITRATION"
            or completion.content.strip() == "WAITING_FOR_HUMAN_ARBITRATION"
            else "EXECUTED"
        )
        payload: dict[str, Any] = {
            "step_key": context.step_key,
            "step_type": "AGENT",
            "directive_applied": context.directive,
            "inputs_received": list(context.resolved_inputs.keys()),
            "llm_model_id": completion.model_id,
            "llm_prompt_sha256": completion.prompt_sha256,
            "llm_scenario_tag": completion.scenario_tag,
            "llm_output": completion.content,
            "artifact": f"{completion.content} [{context.step_key}] ({context.workflow_uri})",
            "adr": f"ADR [{completion.prompt_sha256[:16]}] pour {context.step_key}",
            "report": f"Rapport Agent {context.step_key} : PASS ({completion.scenario_tag})",
        }
        return StepExecutorResult(
            step_key=context.step_key,
            step_type="AGENT",
            status=status,  # type: ignore[arg-type]
            artifact_payload=payload,
            summary=f"Agent '{context.step_key}' exécuté via LLMPort ({completion.model_id})",
            details=f"Prompt SHA-256: {completion.prompt_sha256} | Sortie: {completion.content}",
            cost_usd=completion.estimated_cost_usd,
        )

    async def execute_step_async(self, context: StepExecutorContext) -> StepExecutorResult:
        """Execute an `AGENT` step asynchronously without blocking the event loop."""
        prompt_req = self._build_prompt_request(context)
        assert self._llm is not None
        completion = await self._llm.complete(prompt_req)
        return self._format_completion_result(context, completion)

    def execute_step(self, context: StepExecutorContext) -> StepExecutorResult:
        """Synchronous entrypoint for non-async callers; forbids running inside an active loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute_step_async(context))
        raise RuntimeError(
            "AgentStepExecutor.execute_step() cannot block an active asyncio event loop; "
            "await execute_step_async() instead."
        )


_DEFAULT_AGENT_EXECUTOR = AgentStepExecutor()
_DEFAULT_SKILL_EXECUTOR = SkillStepExecutor()
_DEFAULT_SUB_WORKFLOW_EXECUTOR = SubWorkflowStepExecutor()
_DEFAULT_HUMAN_TASK_EXECUTOR = HumanTaskStepExecutor()
_DEFAULT_HTTP_ACTION_EXECUTOR = HttpActionStepExecutor()
_DEFAULT_POST_ACTION_EXECUTOR = PostActionVerificationStepExecutor()


def build_agent_step_executor_plugin() -> StepExecutorPort:
    return _DEFAULT_AGENT_EXECUTOR


def build_skill_step_executor_plugin() -> StepExecutorPort:
    return _DEFAULT_SKILL_EXECUTOR


def build_sub_workflow_step_executor_plugin() -> StepExecutorPort:
    return _DEFAULT_SUB_WORKFLOW_EXECUTOR


def build_human_task_step_executor_plugin() -> StepExecutorPort:
    return _DEFAULT_HUMAN_TASK_EXECUTOR


def build_http_action_step_executor_plugin() -> StepExecutorPort:
    return _DEFAULT_HTTP_ACTION_EXECUTOR


def build_post_action_step_executor_plugin() -> StepExecutorPort:
    return _DEFAULT_POST_ACTION_EXECUTOR


def register_default_step_executors(
    *,
    llm_gateway: LLMPort | None = None,
    connector_invoker: ConnectorInvoker | None = None,
) -> dict[str, StepExecutorPort]:
    """Register all 6 canonical step executors into `orcia.step_executors` (`AC-F1`)."""
    if llm_gateway is not None:
        _DEFAULT_AGENT_EXECUTOR.set_llm_gateway(llm_gateway)
    http_exec = (
        HttpActionStepExecutor(invoker=connector_invoker)
        if connector_invoker is not None
        else _DEFAULT_HTTP_ACTION_EXECUTOR
    )
    executors: tuple[StepExecutorPort, ...] = (
        _DEFAULT_AGENT_EXECUTOR,
        _DEFAULT_SKILL_EXECUTOR,
        _DEFAULT_SUB_WORKFLOW_EXECUTOR,
        _DEFAULT_HUMAN_TASK_EXECUTOR,
        http_exec,
        _DEFAULT_POST_ACTION_EXECUTOR,
    )
    registry_map: dict[str, StepExecutorPort] = {}
    for ex in executors:
        register_step_executor(ex)
        registry_map[ex.step_type] = ex
    return registry_map


register_default_step_executors()

__all__ = [
    "AgentStepExecutor",
    "HttpActionStepExecutor",
    "HumanTaskStepExecutor",
    "PostActionVerificationStepExecutor",
    "SkillStepExecutor",
    "SubWorkflowStepExecutor",
    "build_agent_step_executor_plugin",
    "build_http_action_step_executor_plugin",
    "build_human_task_step_executor_plugin",
    "build_post_action_step_executor_plugin",
    "build_skill_step_executor_plugin",
    "build_sub_workflow_step_executor_plugin",
    "execute_step_port_async",
    "register_default_step_executors",
]
