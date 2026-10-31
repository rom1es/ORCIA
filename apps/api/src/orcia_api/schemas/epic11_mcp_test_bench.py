"""HTTP/OpenAPI 3.1 transport schemas for Epic 11 Story 11.3 (Test Bench & Governed MCP)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RemoteServiceTestAndDiscoverRequest(BaseModel):
    """Request for `POST /api/v1/settings/connectors/test-and-discover` (`Story 11.3`)."""

    model_config = ConfigDict(extra="forbid")

    protocol: Literal[
        "MCP_STREAMABLE_HTTP_SSE",
        "OPENAPI_3_1_REST",
        "A2A_REMOTE_AGENT",
        "WASM_SANDBOX",
    ] = "MCP_STREAMABLE_HTTP_SSE"
    endpoint_url: str = Field(..., min_length=4, max_length=512)
    identity_mode: Literal["PASSTHROUGH", "SECRET_REF"] = "PASSTHROUGH"
    has_user_personal_token: bool = False
    secret_ref_valid: bool = True
    allow_private_network: bool = False
    raw_tool_names: list[str] = Field(
        default_factory=lambda: ["search_confluence", "create_jira_issue"]
    )
    simulated_dry_run_elapsed_ms: float = Field(default=120.0, ge=0.0, le=60_000.0)
    simulated_dry_run_bytes: int = Field(default=2048, ge=0)


class TestBenchStepResultSchema(BaseModel):
    """Single step outcome in the 4-step Hot Test Bench (`🔌`)."""

    model_config = ConfigDict(extra="forbid")

    step_number: Literal[1, 2, 3, 4]
    step_code: Literal[
        "1_NETWORK_TLS_ANTI_SSRF",
        "2_AUTHENTICATION",
        "3_CONTRACT_DISCOVERY",
        "4_HOT_DRY_RUN",
    ]
    status: Literal["PASS", "FAIL", "WAITING_USER_PASSTHROUGH_TOKEN", "SKIPPED"]
    detail_fr: str


class DiscoveredRemoteCapabilitySchema(BaseModel):
    """Discovered tool or capability qualified during Step 3."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    description: str
    qualification: Literal["READ_ONLY", "WRITE_STAGED_REQUIRED"]
    badge_fr: str


class RemoteServiceTestAndDiscoverResponse(BaseModel):
    """Response from `POST /api/v1/settings/connectors/test-and-discover`."""

    model_config = ConfigDict(extra="forbid")

    protocol: Literal[
        "MCP_STREAMABLE_HTTP_SSE",
        "OPENAPI_3_1_REST",
        "A2A_REMOTE_AGENT",
        "WASM_SANDBOX",
    ]
    endpoint_url: str
    identity_mode: Literal["PASSTHROUGH", "SECRET_REF"]
    steps: list[TestBenchStepResultSchema]
    discovered_capabilities: list[DiscoveredRemoteCapabilitySchema]
    can_activate: bool
    dry_run_audit_actor_type: Literal["ADMIN_CONNECTION_TEST"]
    dry_run_run_id: None
    finops_meta_usage: dict[str, int | float]


class ConfigureAgentMcpExposureRequest(BaseModel):
    """Request to toggle `🔌 Exposer en MCP` on a local Agent or Workspace Assistant."""

    model_config = ConfigDict(extra="forbid")

    workspace_slug: str = Field(..., min_length=1, max_length=128)
    agent_slug: str = Field(..., min_length=1, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=255)
    mcp_exposed: bool = True
    regime: Literal["CONSULTATION_ANALYSIS", "GOVERNED_STAGED_COPILOT"] = "CONSULTATION_ANALYSIS"
    human_authored_required: bool = False
    pat_token_to_register: str | None = None


class ExposedMcpAgentResponse(BaseModel):
    """Response representing an exposed MCP Agent configuration."""

    model_config = ConfigDict(extra="forbid")

    agent_slug: str
    workspace_slug: str
    display_name: str
    mcp_exposed: bool
    regime: Literal["CONSULTATION_ANALYSIS", "GOVERNED_STAGED_COPILOT"]
    human_authored_required: bool
    exposed_tools: list[str]


class GovernedMcpInvokeRequest(BaseModel):
    """Request to invoke an agent over `/api/v1/mcp/spaces/{ws_slug}/invoke`."""

    model_config = ConfigDict(extra="forbid")

    raw_pat_token: str = Field(..., min_length=8, max_length=256)
    agent_slug: str = Field(..., min_length=1, max_length=128)
    caller_verbs: list[str] = Field(default_factory=lambda: ["execute"])
    passthrough_identity: str = Field(..., min_length=1, max_length=255)
    prompt_text: str = Field(..., min_length=1, max_length=4000)
    requested_write_target_uri: str | None = None


class GovernedMcpInvokeResponse(BaseModel):
    """Response from invoking an agent over `/api/v1/mcp` (`Principe M.4`)."""

    model_config = ConfigDict(extra="forbid")

    invocation_id: UUID
    tool_name: str
    workspace_slug: str
    passthrough_identity: str
    sanitized_response_text: str
    system_prompt_exposed: str | None
    secret_refs_exposed: list[str]
    staged_actions: list[str]
    meta_usage: dict[str, int | float]
    history_badge_fr: str
    audit_actor_type: Literal["MCP_IDE_CLIENT"]
