"""Hexagonal ports for ORCIA Core (pure Python Protocols, zero adapter dependencies)."""

from orcia_core.ports.embedding import (
    EMBEDDING_FIXED_DIMENSION,
    EmbeddingPort,
)
from orcia_core.ports.llm_port import (
    LlmCompletionResponse,
    LlmGatewayPort,
    LlmPromptRequest,
    assert_model_orthogonality,
    compute_prompt_sha256,
)
from orcia_core.ports.log_sink import (
    MAX_LOG_QUERY_LIMIT,
    LogEntry,
    LogQuery,
    LogSinkQueryPort,
    NoopLogSinkAdapter,
)

__all__ = [
    "EMBEDDING_FIXED_DIMENSION",
    "EmbeddingPort",
    "LlmCompletionResponse",
    "LlmGatewayPort",
    "LlmPromptRequest",
    "LogEntry",
    "LogQuery",
    "LogSinkQueryPort",
    "MAX_LOG_QUERY_LIMIT",
    "NoopLogSinkAdapter",
    "assert_model_orthogonality",
    "compute_prompt_sha256",
]
