"""Kernel port dataclasses (`LlmPromptRequest`, `CasStoredObject`, `StepExecutorContext`, etc.).

Pure kernel module with zero framework or business domain dependencies (`AD-19`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.kernel.enums import SandboxExecutionTier
from orcia_core.kernel.errors import ModelOrthogonalityViolationError

ExecutionMode = Literal["COACHING", "FAST_PATH"]


@dataclass(frozen=True, slots=True)
class LlmPromptRequest:
    """Immutable LLM prompt request crossing the hexagonal boundary."""

    system_prompt: str
    user_prompt: str
    model_family: str
    model_id: str
    execution_mode: ExecutionMode = "COACHING"
    executor_model_family: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LlmCompletionResponse:
    """Immutable LLM completion response returned by a gateway adapter."""

    content: str
    model_family: str
    model_id: str
    prompt_sha256: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    scenario_tag: str = "STANDARD"


def compute_prompt_sha256(request: LlmPromptRequest) -> str:
    """Compute canonical `sha256:<64-hex>` fingerprint for a prompt request."""
    canonical = (
        f"family={request.model_family}|model={request.model_id}|"
        f"mode={request.execution_mode}|sys={request.system_prompt.strip()}|"
        f"user={request.user_prompt.strip()}"
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def assert_model_orthogonality(executor_model_family: str, evaluator_model_family: str) -> None:
    """Enforce AD-10: evaluator model family must strictly differ from executor model family."""
    exec_norm = executor_model_family.strip().lower()
    eval_norm = evaluator_model_family.strip().lower()
    if not exec_norm or not eval_norm or exec_norm == eval_norm:
        raise ModelOrthogonalityViolationError(
            detail_code="ERR_MODEL_ORTHOGONALITY_VIOLATION_DETAIL",
            detail_params={
                "executor_model_family": executor_model_family,
                "evaluator_model_family": evaluator_model_family,
            },
        )


@dataclass(frozen=True, slots=True)
class CasStoredObject:
    """Immutable Content-Addressable Storage object (`cas/<sha256>`)."""

    cas_key: str
    sha256: str
    source_uri: str
    content_bytes: bytes
    content_type: str = "application/octet-stream"


@dataclass(frozen=True, slots=True)
class SandboxExecutionRequest:
    """Out-of-process sandbox execution request (`TIER_1_WASM` or `TIER_2_CONTAINER`, `AD-9`)."""

    tier: SandboxExecutionTier
    entrypoint: str
    payload: dict[str, Any]
    timeout_ms: int = 5000
    max_memory_mb: int = 256


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    """Out-of-process sandbox execution result."""

    passed: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int


@dataclass(frozen=True, slots=True)
class StepExecutorContext:
    """Immutable execution context passed to a `StepExecutorPort` (`Story 3.2f`, `AC-F1`)."""

    run_id: str
    root_run_id: str
    workspace_id: str
    workflow_uri: str
    step_key: str
    step_title: str
    step_type: str
    execution_regime: str
    directive: str
    declared_input_uris: tuple[str, ...]
    resolved_inputs: dict[str, Any]
    datasources: tuple[str, ...] = ()
    agent_uri: str | None = None
    skill_uri: str | None = None
    sub_workflow_uri: str | None = None
    max_agent_retries: int = 3
    budget_remaining_usd: float = 10.0
    idempotency_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StepExecutorResult:
    """Execution result returned by a `StepExecutorPort` (`Story 3.2f`, `AC-F1`)."""

    step_key: str
    step_type: str
    status: Literal[
        "EXECUTED",
        "WAITING_FOR_HUMAN_ARBITRATION",
        "WAITING_FOR_HUMAN_GATE",
        "FAILED",
    ]
    artifact_payload: dict[str, Any]
    summary: str
    details: str
    cost_usd: float = 0.0
    child_run_id: str | None = None
