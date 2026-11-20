"""Pure domain models & repository port for Test Bench & Governed MCP (`Story 11.3`, `24.3`).

Zero SQLAlchemy, Redis, or FastAPI imports (`AD-19`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable
from uuid import UUID

RemoteProtocolType = Literal[
    "MCP_STREAMABLE_HTTP_SSE",
    "OPENAPI_3_1_REST",
    "A2A_REMOTE_AGENT",
    "WASM_SANDBOX",
]
TestBenchStepStatus = Literal[
    "PASS",
    "FAIL",
    "WAITING_USER_PASSTHROUGH_TOKEN",
    "SKIPPED",
]
ToolAccessQualification = Literal["READ_ONLY", "WRITE_STAGED_REQUIRED"]
McpExposureRegime = Literal["CONSULTATION_ANALYSIS", "GOVERNED_STAGED_COPILOT"]


@dataclass(frozen=True, slots=True)
class DiscoveredRemoteCapability:
    """Discovered tool or capability qualified during Step 3 of the Test Bench."""

    tool_name: str
    description: str
    qualification: ToolAccessQualification
    badge_fr: str


@dataclass(frozen=True, slots=True)
class TestBenchStepResult:
    """Single step outcome in the 4-step Hot Test Bench (`🔌`)."""

    step_number: Literal[1, 2, 3, 4]
    step_code: Literal[
        "1_NETWORK_TLS_ANTI_SSRF",
        "2_AUTHENTICATION",
        "3_CONTRACT_DISCOVERY",
        "4_HOT_DRY_RUN",
    ]
    status: TestBenchStepStatus
    detail_fr: str


@dataclass(frozen=True, slots=True)
class RemoteServiceTestAndDiscoverResult:
    """Consolidated result of `POST /api/v1/settings/connectors/test-and-discover`."""

    protocol: RemoteProtocolType
    endpoint_url: str
    identity_mode: Literal["PASSTHROUGH", "SECRET_REF"]
    steps: tuple[TestBenchStepResult, ...]
    discovered_capabilities: tuple[DiscoveredRemoteCapability, ...]
    can_activate: bool
    dry_run_audit_actor_type: Literal["ADMIN_CONNECTION_TEST"]
    dry_run_run_id: None
    finops_meta_usage: dict[str, int | float]


@dataclass(frozen=True, slots=True)
class ExposedMcpAgentSpec:
    """Agent or Assistant exposed on the Governed MCP Server (`/api/v1/mcp`)."""

    agent_slug: str
    workspace_slug: str
    display_name: str
    mcp_exposed: bool
    regime: McpExposureRegime
    system_prompt_layers_1_to_4: str
    secret_refs: tuple[str, ...]
    human_authored_required: bool = False


@dataclass(frozen=True, slots=True)
class GovernedMcpInvocationResult:
    """Result of invoking an agent or `assistant.ask` over `/api/v1/mcp` (`Principe M.4`)."""

    invocation_id: UUID
    tool_name: str
    workspace_slug: str
    passthrough_identity: str
    sanitized_response_text: str
    system_prompt_exposed: str | None
    secret_refs_exposed: tuple[str, ...]
    staged_actions: tuple[str, ...]
    meta_usage: dict[str, int | float]
    history_badge_fr: str
    audit_actor_type: Literal["MCP_IDE_CLIENT"]


@runtime_checkable
class McpExposureRepositoryPort(Protocol):
    """Hexagonal persistence port for governed MCP exposures & PAT token SHA-256 hashes."""

    async def upsert_exposed_agent(
        self,
        spec: ExposedMcpAgentSpec,
        *,
        updated_by: str | None = None,
    ) -> ExposedMcpAgentSpec: ...

    async def list_exposed_agents(self, workspace_slug: str) -> list[ExposedMcpAgentSpec]: ...

    async def get_exposed_agent(
        self, workspace_slug: str, agent_slug: str
    ) -> ExposedMcpAgentSpec | None: ...

    async def upsert_pat_token_hash(
        self,
        *,
        token_sha256: str,
        allowed_workspace_slugs: set[str],
    ) -> None: ...

    async def get_pat_allowed_workspaces(self, token_sha256: str) -> set[str] | None: ...


__all__ = [
    "DiscoveredRemoteCapability",
    "ExposedMcpAgentSpec",
    "GovernedMcpInvocationResult",
    "McpExposureRegime",
    "McpExposureRepositoryPort",
    "RemoteProtocolType",
    "RemoteServiceTestAndDiscoverResult",
    "TestBenchStepResult",
    "TestBenchStepStatus",
    "ToolAccessQualification",
]
