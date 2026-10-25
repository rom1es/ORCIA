"""Pure hexagonal LLM Gateway Port and model orthogonality enforcement (AD-10, AD-17).

No external LLM SDK (`litellm`, etc.) may be imported in this port module.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from orcia_core.domain.exceptions import ModelOrthogonalityViolationError

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
            detail_override=(
                f"Orthogonalité des modèles violée (AD-10): executor_model_family="
                f"'{executor_model_family}' == evaluator_model_family='{evaluator_model_family}'."
            )
        )


@runtime_checkable
class LlmGatewayPort(Protocol):
    """Port interface for LLM completion adapters (LiteLLM in prod, Cassette in CI)."""

    async def complete(self, request: LlmPromptRequest) -> LlmCompletionResponse:
        """Execute a completion request while respecting AD-10 orthogonality rules."""
        ...
