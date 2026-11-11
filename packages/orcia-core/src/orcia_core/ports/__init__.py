"""Hexagonal ports for ORCIA Core (pure Python Protocols, zero adapter dependencies)."""

from orcia_core.ports.llm_port import (
    LlmCompletionResponse,
    LlmGatewayPort,
    LlmPromptRequest,
    assert_model_orthogonality,
    compute_prompt_sha256,
)
from orcia_core.ports.surgical_explorer_port import (
    MAX_SURGICAL_LINES,
    SurgicalExplorerPort,
    SurgicalFileBadgeCode,
    SurgicalLineEntry,
    SurgicalLineSlice,
    SurgicalObservation,
    SurgicalOutlineNode,
    SurgicalPrimitiveName,
    SurgicalSnippetMatch,
)

__all__ = [
    "LlmCompletionResponse",
    "LlmGatewayPort",
    "LlmPromptRequest",
    "MAX_SURGICAL_LINES",
    "SurgicalExplorerPort",
    "SurgicalFileBadgeCode",
    "SurgicalLineEntry",
    "SurgicalLineSlice",
    "SurgicalObservation",
    "SurgicalOutlineNode",
    "SurgicalPrimitiveName",
    "SurgicalSnippetMatch",
    "assert_model_orthogonality",
    "compute_prompt_sha256",
]
