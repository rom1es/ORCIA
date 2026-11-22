"""Story 11.3 / 24.3 Facade: 4-Step Test Bench (`🔌`) & Governed MCP Server (`/api/v1/mcp`).

Composes `RemoteServiceTestBenchService` and `GovernedMcpExposureService` (< 150 lines)
while preserving all public symbol re-exports for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from orcia_core.orchestration.governed_mcp_exposure import GovernedMcpExposureService
from orcia_core.orchestration.remote_test_bench import (
    RemoteServiceTestBenchService,
    is_safe_llm_endpoint_url,
)
from orcia_core.orchestration.remote_test_bench_models import (
    DiscoveredRemoteCapability,
    ExposedMcpAgentSpec,
    GovernedMcpInvocationResult,
    McpExposureRegime,
    McpExposureRepositoryPort,
    RemoteProtocolType,
    RemoteServiceTestAndDiscoverResult,
    TestBenchStepResult,
    TestBenchStepStatus,
    ToolAccessQualification,
)


@dataclass
class RemoteServiceTestBenchAndGovernedMcpService:
    """Facade composing `RemoteServiceTestBenchService` and `GovernedMcpExposureService`."""

    repository: McpExposureRepositoryPort | None = None
    strict_sql: bool = False
    _test_bench: RemoteServiceTestBenchService = field(
        default_factory=RemoteServiceTestBenchService, init=False
    )
    _exposure: GovernedMcpExposureService = field(init=False)

    def __post_init__(self) -> None:
        self._exposure = GovernedMcpExposureService(
            repository=self.repository,
            strict_sql=self.strict_sql,
        )

    def set_repository(
        self,
        repository: McpExposureRepositoryPort,
        *,
        strict_sql: bool = True,
    ) -> None:
        """Attach PG18 repository dynamically from the Composition Root."""
        self.repository = repository
        self.strict_sql = strict_sql
        self._exposure.repository = repository
        self._exposure.strict_sql = strict_sql

    def register_pat_mcp_token(
        self,
        *,
        raw_pat_token: str,
        allowed_workspace_slugs: set[str],
    ) -> str:
        """Register a `pat_mcp_*` token hashed with `SHA-256`."""
        return self._exposure.register_pat_mcp_token(
            raw_pat_token=raw_pat_token,
            allowed_workspace_slugs=allowed_workspace_slugs,
        )

    async def register_pat_mcp_token_async(
        self,
        *,
        raw_pat_token: str,
        allowed_workspace_slugs: set[str],
    ) -> str:
        """Persist a `pat_mcp_*` SHA-256 hash into PG18."""
        return await self._exposure.register_pat_mcp_token_async(
            raw_pat_token=raw_pat_token,
            allowed_workspace_slugs=allowed_workspace_slugs,
        )

    def test_and_discover_remote_service(
        self,
        *,
        actor_role: str,
        protocol: RemoteProtocolType,
        endpoint_url: str,
        identity_mode: Literal["PASSTHROUGH", "SECRET_REF"],
        has_user_personal_token: bool = False,
        secret_ref_valid: bool = True,
        allow_private_network: bool = False,
        raw_tool_names: list[str] | None = None,
        simulated_dry_run_elapsed_ms: float = 120.0,
        simulated_dry_run_bytes: int = 2048,
    ) -> RemoteServiceTestAndDiscoverResult:
        """Execute the 4-step Hot Test Bench (`🔌`) for MCP/OpenAPI/A2A/WASM services."""
        return self._test_bench.test_and_discover_remote_service(
            actor_role=actor_role,
            protocol=protocol,
            endpoint_url=endpoint_url,
            identity_mode=identity_mode,
            has_user_personal_token=has_user_personal_token,
            secret_ref_valid=secret_ref_valid,
            allow_private_network=allow_private_network,
            raw_tool_names=raw_tool_names,
            simulated_dry_run_elapsed_ms=simulated_dry_run_elapsed_ms,
            simulated_dry_run_bytes=simulated_dry_run_bytes,
        )

    def configure_agent_mcp_exposure(
        self,
        *,
        actor_role: str,
        workspace_slug: str,
        agent_slug: str,
        display_name: str,
        mcp_exposed: bool,
        regime: McpExposureRegime,
        system_prompt_layers_1_to_4: str = "System Prompt Confidentiel Couches 1-4",
        secret_refs: tuple[str, ...] = ("vault://orcia/secret/api-key",),
        human_authored_required: bool = False,
    ) -> ExposedMcpAgentSpec:
        """Toggle `🔌 Exposer en MCP` synchronously (unit-test mode)."""
        return self._exposure.configure_agent_mcp_exposure(
            actor_role=actor_role,
            workspace_slug=workspace_slug,
            agent_slug=agent_slug,
            display_name=display_name,
            mcp_exposed=mcp_exposed,
            regime=regime,
            system_prompt_layers_1_to_4=system_prompt_layers_1_to_4,
            secret_refs=secret_refs,
            human_authored_required=human_authored_required,
        )

    async def configure_agent_mcp_exposure_async(
        self,
        *,
        actor_role: str,
        workspace_slug: str,
        agent_slug: str,
        display_name: str,
        mcp_exposed: bool,
        regime: McpExposureRegime,
        system_prompt_layers_1_to_4: str = "System Prompt Confidentiel Couches 1-4",
        secret_refs: tuple[str, ...] = ("vault://orcia/secret/api-key",),
        human_authored_required: bool = False,
        updated_by: str | None = None,
    ) -> ExposedMcpAgentSpec:
        """Toggle `🔌 Exposer en MCP` and persist durably to PG18."""
        return await self._exposure.configure_agent_mcp_exposure_async(
            actor_role=actor_role,
            workspace_slug=workspace_slug,
            agent_slug=agent_slug,
            display_name=display_name,
            mcp_exposed=mcp_exposed,
            regime=regime,
            system_prompt_layers_1_to_4=system_prompt_layers_1_to_4,
            secret_refs=secret_refs,
            human_authored_required=human_authored_required,
            updated_by=updated_by,
        )

    async def list_exposed_agents_async(self, *, workspace_slug: str) -> list[ExposedMcpAgentSpec]:
        """List MCP exposure specs for `workspace_slug`."""
        return await self._exposure.list_exposed_agents_async(workspace_slug=workspace_slug)

    def list_governed_mcp_tools(
        self,
        *,
        workspace_slug: str,
        caller_verbs: set[str],
    ) -> tuple[str, ...]:
        """Return dynamic `tools/list` filtered by `PermissionGuard` (`execute` verb)."""
        return self._exposure.list_governed_mcp_tools(
            workspace_slug=workspace_slug,
            caller_verbs=caller_verbs,
        )

    async def list_governed_mcp_tools_async(
        self,
        *,
        workspace_slug: str,
        caller_verbs: set[str],
    ) -> tuple[str, ...]:
        """Return dynamic `tools/list` backed by PG18 and filtered by `execute` verb."""
        return await self._exposure.list_governed_mcp_tools_async(
            workspace_slug=workspace_slug,
            caller_verbs=caller_verbs,
        )

    def invoke_governed_mcp_tool(
        self,
        *,
        raw_pat_token: str,
        workspace_slug: str,
        agent_slug: str,
        caller_role: str,
        caller_verbs: set[str],
        passthrough_identity: str,
        prompt_text: str,
        requested_write_target_uri: str | None = None,
    ) -> GovernedMcpInvocationResult:
        """Invoke an exposed MCP agent synchronously (unit-test mode)."""
        return self._exposure.invoke_governed_mcp_tool(
            raw_pat_token=raw_pat_token,
            workspace_slug=workspace_slug,
            agent_slug=agent_slug,
            caller_role=caller_role,
            caller_verbs=caller_verbs,
            passthrough_identity=passthrough_identity,
            prompt_text=prompt_text,
            requested_write_target_uri=requested_write_target_uri,
        )

    async def invoke_governed_mcp_tool_async(
        self,
        *,
        raw_pat_token: str,
        workspace_slug: str,
        agent_slug: str,
        caller_role: str,
        caller_verbs: set[str],
        passthrough_identity: str,
        prompt_text: str,
        requested_write_target_uri: str | None = None,
    ) -> GovernedMcpInvocationResult:
        """Invoke an exposed MCP agent enforcing the 7 hardware locks backed by PG18."""
        return await self._exposure.invoke_governed_mcp_tool_async(
            raw_pat_token=raw_pat_token,
            workspace_slug=workspace_slug,
            agent_slug=agent_slug,
            caller_role=caller_role,
            caller_verbs=caller_verbs,
            passthrough_identity=passthrough_identity,
            prompt_text=prompt_text,
            requested_write_target_uri=requested_write_target_uri,
        )

    async def invoke_governed_mcp_read_only_for_assistant_async(
        self,
        *,
        workspace_slug: str,
        agent_slug: str,
        caller_role: str,
        passthrough_identity: str,
        prompt_text: str,
    ) -> GovernedMcpInvocationResult:
        """Invoke a read-only `CONSULTATION_ANALYSIS` MCP agent for an authorized assistant."""
        return await self._exposure.invoke_governed_mcp_read_only_for_assistant_async(
            workspace_slug=workspace_slug,
            agent_slug=agent_slug,
            caller_role=caller_role,
            passthrough_identity=passthrough_identity,
            prompt_text=prompt_text,
        )


__all__ = [
    "DiscoveredRemoteCapability",
    "ExposedMcpAgentSpec",
    "GovernedMcpExposureService",
    "GovernedMcpInvocationResult",
    "McpExposureRegime",
    "McpExposureRepositoryPort",
    "RemoteProtocolType",
    "RemoteServiceTestAndDiscoverResult",
    "RemoteServiceTestBenchAndGovernedMcpService",
    "RemoteServiceTestBenchService",
    "TestBenchStepResult",
    "TestBenchStepStatus",
    "ToolAccessQualification",
    "is_safe_llm_endpoint_url",
]
