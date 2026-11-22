"""Pure hexagonal `AssistantToolExecutorPort` contract (`AD-19`, `AD-25`, `Story 26.6b`).

Defines catalog descriptors, execution requests, SSE event payloads, idempotency port, and
`AssistantToolExecutorPort` with zero framework, SDK, or external connector imports.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

ToolCategory = Literal["surgical_read", "kb_search", "ontology_lookup", "skill", "mcp_tool"]
ToolVerdict = Literal[
    "EXECUTED",
    "DENIED",
    "APPROVAL_REQUIRED",
    "TIMED_OUT",
    "DEDUPLICATED",
    "ERROR",
]
ToolSseEventName = Literal["tool_call", "tool_result", "approval_required"]
ToolAuditEventType = Literal["ASSISTANT_TOOL_INVOKED", "ASSISTANT_TOOL_DENIED"]
ToolSandboxTier = Literal["NONE", "TIER_1_WASM", "TIER_2_CONTAINER"]


@dataclass(frozen=True, slots=True)
class SkillCatalogEntry:
    """Authorized skill descriptor derived from PostgreSQL 18 `catalog_items`."""

    skill_id: str
    slug: str
    name: str
    objective: str
    input_parameters: tuple[str, ...] = ()
    instructions: str = ""
    expected_output_format: str = "Structured synthesis"
    enabled_in_workspace: bool = True
    sandbox_tier: ToolSandboxTier = "TIER_1_WASM"
    is_si_write: bool = False
    human_authored_required: bool = False
    uri: str = ""


@dataclass(frozen=True, slots=True)
class McpExposedToolSpec:
    """MCP-exposed tool entry filtered by `mcp_tool_permissions` and workspace RBAC."""

    tool_name: str
    agent_slug: str
    description: str
    permission_mode: Literal["NONE", "READ_ONLY", "WRITE_PREVIEW"] = "READ_ONLY"
    is_si_write: bool = False
    human_authored_required: bool = False
    mcp_exposed: bool = True
    required_permission: Literal["read", "execute"] = "execute"
    parameters_schema: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }
    )
    source_uri_or_scope: str = ""


@dataclass(frozen=True, slots=True)
class AuthorizedToolDescriptor:
    """Normalized authorized tool definition exposed to the LLM and enforced by the router."""

    tool_name: str
    description: str
    parameters_schema: dict[str, Any]
    category: ToolCategory
    read_only: bool = True
    is_si_write: bool = False
    human_authored_required: bool = False
    source_uri_or_scope: str = ""
    skill_id: str | None = None
    mcp_agent_slug: str | None = None
    required_permission: Literal["read", "execute"] = "read"
    sandbox_tier: ToolSandboxTier = "NONE"
    timeout_s: float = 10.0

    def to_llm_tool_schema(self) -> dict[str, Any]:
        """Serialize into canonical OpenAI/Anthropic-compatible JSON Schema `tools` item."""
        return {
            "type": "function",
            "function": {
                "name": self.tool_name,
                "description": self.description,
                "parameters": dict(self.parameters_schema),
            },
        }


@dataclass(frozen=True, slots=True)
class AssistantToolCatalogContext:
    """Per-turn authorization and workspace context used to build the tool catalog."""

    workspace_id: str
    user_id: str
    user_role: str = "MEMBER"
    active_hat: str = "ARCHITECT"
    user_roles: frozenset[str] = frozenset()
    user_permissions: frozenset[str] = frozenset({"read", "execute"})
    rag_active: bool = False
    skills: tuple[SkillCatalogEntry, ...] = ()
    mcp_tools: tuple[McpExposedToolSpec, ...] = ()
    can_use_surgical: bool = True
    can_use_ontology: bool = True


@dataclass(frozen=True, slots=True)
class AssistantToolExecutionRequest:
    """Single governed tool-call execution request emitted by the LLM tool loop."""

    turn_id: str
    iteration: int
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    workspace_id: str
    user_id: str
    user_email: str | None = None
    user_display_name: str | None = None
    user_role: str = "OBSERVER"
    user_roles: tuple[str, ...] = ()
    active_hat: str = "ARCHITECT"
    trace_id: str = ""
    locale: str = "fr"
    execution_identity: Literal["passthrough", "service_principal"] = "passthrough"
    granted_external_roles: tuple[str, ...] = ()
    user_identity: Any | None = None


@dataclass(frozen=True, slots=True)
class AssistantToolSseEvent:
    """Canonical SSE event emitted during governed tool routing."""

    event: ToolSseEventName
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AssistantToolExecutionResult:
    """Governed execution result returned to the loop, audit ledger, and SSE stream."""

    tool_call_id: str
    tool_name: str
    verdict: ToolVerdict
    delimited_output: str
    raw_scrubbed_summary: str
    audit_event_type: ToolAuditEventType
    audit_ledger_id: str | None = None
    outbox_event_id: str | None = None
    deduplicated: bool = False
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    approval_proposal: dict[str, Any] | None = None
    sse_events: tuple[AssistantToolSseEvent, ...] = ()


@runtime_checkable
class ToolIdempotencyStorePort(Protocol):
    """Port for turn/iteration/tool_call_id deduplication (`idem:{turn_id}:{iter}:{call_id}`)."""

    async def get_cached_result(self, key: str) -> dict[str, Any] | None:
        """Fetch previously recorded serialized outcome for `key` if present."""
        ...

    async def save_result(
        self, key: str, payload: dict[str, Any], *, ttl_seconds: int = 1800
    ) -> None:
        """Persist serialized outcome for `key` with bounded TTL."""
        ...


@runtime_checkable
class AssistantToolExecutorPort(Protocol):
    """Hexagonal port for dynamic workspace tool catalog assembly and governed execution."""

    def build_authorized_catalog(
        self, ctx: AssistantToolCatalogContext
    ) -> tuple[AuthorizedToolDescriptor, ...]:
        """Build the authorized per-turn tool catalog without arbitrary RAM caps."""
        ...

    async def execute_tool_call(
        self,
        request: AssistantToolExecutionRequest,
        *,
        catalog: Sequence[AuthorizedToolDescriptor],
    ) -> AssistantToolExecutionResult:
        """Execute one tool call sequentially through broker, guards, sandbox, and audit."""
        ...


__all__ = [
    "AssistantToolCatalogContext",
    "AssistantToolExecutionRequest",
    "AssistantToolExecutionResult",
    "AssistantToolExecutorPort",
    "AssistantToolSseEvent",
    "AuthorizedToolDescriptor",
    "McpExposedToolSpec",
    "SkillCatalogEntry",
    "ToolAuditEventType",
    "ToolCategory",
    "ToolIdempotencyStorePort",
    "ToolSandboxTier",
    "ToolSseEventName",
    "ToolVerdict",
]
