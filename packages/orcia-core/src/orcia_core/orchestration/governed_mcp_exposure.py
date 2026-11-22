"""Governed MCP Exposure Service (`/api/v1/mcp/exposure` & 7 Security Locks, `Story 11.3`, `24.3`).

Pure domain service — zero SQLAlchemy, Redis, or FastAPI imports (`AD-19`, `<= 300 L`).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from orcia_core.orchestration._governed_mcp_helpers import (
    build_mcp_agent_spec,
    build_mcp_invocation_result,
    validate_and_invoke_assistant_read_only,
)
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)
from orcia_core.orchestration.remote_test_bench_models import (
    ExposedMcpAgentSpec,
    GovernedMcpInvocationResult,
    McpExposureRegime,
    McpExposureRepositoryPort,
)

_BASE_MCP_TOOLS: tuple[str, ...] = ("assistant.ask", "agent.invoke", "agent.list_exposed")


@dataclass
class GovernedMcpExposureService:
    """Domain service managing MCP exposure state and the 7 Hardware Security Locks."""

    repository: McpExposureRepositoryPort | None = None
    strict_sql: bool = False
    _exposed_agents: dict[tuple[str, str], ExposedMcpAgentSpec] = field(default_factory=dict)
    _pat_tokens: dict[str, set[str]] = field(default_factory=dict)

    def _require_repository_when_strict(self) -> McpExposureRepositoryPort | None:
        if self.repository is None and self.strict_sql:
            raise ValidationDomainError(
                detail_override=(
                    "MCP exposure PostgreSQL 18 repository is required when strict_sql=True."
                )
            )
        return self.repository

    def register_pat_mcp_token(
        self,
        *,
        raw_pat_token: str,
        allowed_workspace_slugs: set[str],
    ) -> str:
        """Register a `pat_mcp_*` token hashed with `SHA-256` (sync unit-test mode)."""
        if self.strict_sql and self.repository is not None:
            raise ValidationDomainError(
                detail_override="Use register_pat_mcp_token_async when strict_sql=True."
            )
        self._require_repository_when_strict()
        token_hash = hashlib.sha256(raw_pat_token.encode("utf-8")).hexdigest()
        self._pat_tokens[token_hash] = set(allowed_workspace_slugs)
        return token_hash

    async def register_pat_mcp_token_async(
        self,
        *,
        raw_pat_token: str,
        allowed_workspace_slugs: set[str],
    ) -> str:
        """Persist a `pat_mcp_*` SHA-256 hash into PG18 (never plaintext)."""
        token_hash = hashlib.sha256(raw_pat_token.encode("utf-8")).hexdigest()
        repo = self._require_repository_when_strict()
        if repo is not None:
            await repo.upsert_pat_token_hash(
                token_sha256=token_hash,
                allowed_workspace_slugs=set(allowed_workspace_slugs),
            )
            return token_hash
        self._pat_tokens[token_hash] = set(allowed_workspace_slugs)
        return token_hash

    _build_agent_spec = staticmethod(build_mcp_agent_spec)
    _build_invocation_result = staticmethod(build_mcp_invocation_result)

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
        """Toggle `🔌 Exposer en MCP` synchronously (unit-test mode without DB)."""
        if self.strict_sql:
            raise ValidationDomainError(
                detail_override="Use configure_agent_mcp_exposure_async when strict_sql=True."
            )
        spec = self._build_agent_spec(
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
        self._exposed_agents[(workspace_slug, agent_slug)] = spec
        return spec

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
        """Toggle `🔌 Exposer en MCP` and persist durably to PostgreSQL 18."""
        spec = self._build_agent_spec(
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
        repo = self._require_repository_when_strict()
        if repo is not None:
            return await repo.upsert_exposed_agent(spec, updated_by=updated_by)
        self._exposed_agents[(workspace_slug, agent_slug)] = spec
        return spec

    async def list_exposed_agents_async(self, *, workspace_slug: str) -> list[ExposedMcpAgentSpec]:
        """List MCP exposure specs for `workspace_slug` from PG18 (or memory when non-strict)."""
        repo = self._require_repository_when_strict()
        if repo is not None:
            return await repo.list_exposed_agents(workspace_slug)
        return [
            spec
            for (ws, _slug), spec in sorted(self._exposed_agents.items())
            if ws == workspace_slug
        ]

    def list_governed_mcp_tools(
        self,
        *,
        workspace_slug: str,
        caller_verbs: set[str],
    ) -> tuple[str, ...]:
        """Return dynamic `tools/list` filtered by `PermissionGuard` (`execute` verb)."""
        if "execute" not in caller_verbs:
            return ()
        base_tools = list(_BASE_MCP_TOOLS)
        for (ws, slug), spec in sorted(self._exposed_agents.items()):
            if ws == workspace_slug and spec.mcp_exposed:
                base_tools.append(f"agent.{slug}")
        return tuple(base_tools)

    async def list_governed_mcp_tools_async(
        self,
        *,
        workspace_slug: str,
        caller_verbs: set[str],
    ) -> tuple[str, ...]:
        """Return dynamic `tools/list` backed by PG18 and filtered by `execute` verb."""
        if "execute" not in caller_verbs:
            return ()
        specs = await self.list_exposed_agents_async(workspace_slug=workspace_slug)
        base_tools = list(_BASE_MCP_TOOLS)
        for spec in sorted(specs, key=lambda item: item.agent_slug):
            if spec.mcp_exposed:
                base_tools.append(f"agent.{spec.agent_slug}")
        return tuple(base_tools)

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
        """Invoke an exposed MCP agent synchronously (unit-test mode without DB)."""
        if caller_role in ("READ_ONLY_OBSERVER", "OBSERVER"):
            raise ObserverModeReadOnlyError(
                detail_override="READ_ONLY_OBSERVER cannot invoke MCP tools."
            )
        if not raw_pat_token.startswith("pat_mcp_"):
            raise ScopeAccessDeniedError(detail_override="Invalid MCP token prefix.")
        token_hash = hashlib.sha256(raw_pat_token.encode("utf-8")).hexdigest()
        allowed_ws = self._pat_tokens.get(token_hash)
        if allowed_ws is None or workspace_slug not in allowed_ws:
            raise ScopeAccessDeniedError(
                detail_override=f"Token not authorized for workspace '{workspace_slug}'."
            )
        spec = self._exposed_agents.get((workspace_slug, agent_slug))
        return self._build_invocation_result(
            spec=spec,
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
        if caller_role in ("READ_ONLY_OBSERVER", "OBSERVER"):
            raise ObserverModeReadOnlyError(
                detail_override="READ_ONLY_OBSERVER cannot invoke MCP tools."
            )
        if not raw_pat_token.startswith("pat_mcp_"):
            raise ScopeAccessDeniedError(detail_override="Invalid MCP token prefix.")
        token_hash = hashlib.sha256(raw_pat_token.encode("utf-8")).hexdigest()
        repo = self._require_repository_when_strict()
        if repo is not None:
            allowed_ws = await repo.get_pat_allowed_workspaces(token_hash)
            spec = await repo.get_exposed_agent(workspace_slug, agent_slug)
        else:
            allowed_ws = self._pat_tokens.get(token_hash)
            spec = self._exposed_agents.get((workspace_slug, agent_slug))
        if allowed_ws is None or workspace_slug not in allowed_ws:
            raise ScopeAccessDeniedError(
                detail_override=f"Token not authorized for workspace '{workspace_slug}'."
            )
        return self._build_invocation_result(
            spec=spec,
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
        """Invoke a `CONSULTATION_ANALYSIS` MCP-exposed agent directly for an authorized user."""
        repo = self._require_repository_when_strict()
        spec = (
            await repo.get_exposed_agent(workspace_slug, agent_slug)
            if repo is not None
            else self._exposed_agents.get((workspace_slug, agent_slug))
        )
        return validate_and_invoke_assistant_read_only(
            spec=spec,
            workspace_slug=workspace_slug,
            agent_slug=agent_slug,
            caller_role=caller_role,
            passthrough_identity=passthrough_identity,
            prompt_text=prompt_text,
        )


__all__ = ["GovernedMcpExposureService"]
