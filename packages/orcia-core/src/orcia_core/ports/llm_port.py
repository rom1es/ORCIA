"""Pure hexagonal LLM Gateway Port and model orthogonality enforcement (AD-10, AD-17, AD-19).

No external LLM SDK (`litellm`, etc.) may be imported in this port module.
"""

from __future__ import annotations

from orcia_kernel.enums import ExecutionMode
from orcia_kernel.errors import ModelOrthogonalityViolationError
from orcia_kernel.ports import (
    LlmCompletionResponse,
    LlmGatewayPort,
    LLMPort,
    LlmPromptRequest,
    compute_prompt_sha256,
)


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


__all__ = [
    "ExecutionMode",
    "LLMPort",
    "LlmCompletionResponse",
    "LlmGatewayPort",
    "LlmPromptRequest",
    "assert_model_orthogonality",
    "compute_prompt_sha256",
]
