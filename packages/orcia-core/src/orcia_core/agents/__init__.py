"""Reflexive Agent Runtime bounded context (`orcia_core.agents`, `Story 16.2` & `16.3`, `AD-19`)."""

from __future__ import annotations

from orcia_core.agents._assistant_profile_guard import (
    assert_assistant_profile_write_gate_unreachable,
    assert_profile_allows_write_action,
)
from orcia_core.agents._assistant_tool_catalog import build_authorized_tool_catalog
from orcia_core.agents._assistant_tool_idempotency import (
    RedisToolIdempotencyStore,
    build_tool_idempotency_key,
)
from orcia_core.agents._internal.redis_event_stream import ReflexiveEventStreamBroker
from orcia_core.agents._internal.sql_reflexive_sessions import SqlReflexiveSessionStore
from orcia_core.agents.errors import (
    ReflexiveInvalidStateError,
    ReflexiveSessionExpiredError,
)
from orcia_core.agents.governed_tool_router import GovernedAssistantToolRouter
from orcia_core.agents.llm_adapter import GatewayReflexiveLlmAdapter
from orcia_core.agents.process_dispatcher import (
    ProcessExecutionDispatcher,
    UnifiedProcessRunResult,
)
from orcia_core.agents.reflexive_runtime import NonDeterministicReflexiveRuntime
from orcia_core.agents.reflexive_schemas import (
    APPROFONDI_MAX_TOKENS,
    APPROFONDI_MAX_TURNS,
    MAX_DELEGATION_DEPTH_CAP,
    SESSION_SNAPSHOT_TTL_HOURS,
    STANDARD_MAX_TOKENS,
    STANDARD_MAX_TURNS,
    AgentTraceEvent,
    ExecutionProfile,
    PendingWritePreviewSpec,
    ProcessOrchestrationType,
    ReflexiveActionKind,
    ReflexiveEffortMode,
    ReflexiveExecutionStatus,
    ReflexiveRuntimeConfig,
    ReflexiveScratchpadEntry,
    ReflexiveSessionSnapshot,
    ReflexiveTurnDecision,
    ReflexiveTurnInput,
    ReflexiveWriteApprovalInput,
    TraceEventKind,
    compute_default_session_expiry_utc,
    resolve_effort_budget,
)

__all__ = [
    "APPROFONDI_MAX_TOKENS",
    "APPROFONDI_MAX_TURNS",
    "AgentTraceEvent",
    "ExecutionProfile",
    "GatewayReflexiveLlmAdapter",
    "GovernedAssistantToolRouter",
    "MAX_DELEGATION_DEPTH_CAP",
    "NonDeterministicReflexiveRuntime",
    "PendingWritePreviewSpec",
    "ProcessExecutionDispatcher",
    "ProcessOrchestrationType",
    "RedisToolIdempotencyStore",
    "ReflexiveActionKind",
    "ReflexiveEffortMode",
    "ReflexiveEventStreamBroker",
    "ReflexiveExecutionStatus",
    "ReflexiveInvalidStateError",
    "ReflexiveRuntimeConfig",
    "ReflexiveScratchpadEntry",
    "ReflexiveSessionExpiredError",
    "ReflexiveSessionSnapshot",
    "ReflexiveTurnDecision",
    "ReflexiveTurnInput",
    "ReflexiveWriteApprovalInput",
    "SESSION_SNAPSHOT_TTL_HOURS",
    "STANDARD_MAX_TOKENS",
    "STANDARD_MAX_TURNS",
    "SqlReflexiveSessionStore",
    "TraceEventKind",
    "UnifiedProcessRunResult",
    "assert_assistant_profile_write_gate_unreachable",
    "assert_profile_allows_write_action",
    "build_authorized_tool_catalog",
    "build_tool_idempotency_key",
    "compute_default_session_expiry_utc",
    "resolve_effort_budget",
]
