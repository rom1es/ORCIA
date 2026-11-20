"""Governed MCP Server (`/api/v1/mcp`) for External IDEs (`Story 4.4`, `24.1`, `FR-24`, `AD-3`).

Exposes MCP tools in `passthrough` mode (`ontology.query`, `kb.search`, `catalog.get`,
`blackboard.read`, `blackboard.propose_draft`) to external IDEs while materially blocking any
write on sections with `human_authored_required: true` and persisting draft proposals in PG18.
"""

from __future__ import annotations

from typing import Any

from orcia_core.orchestration._mcp_tools_helpers import (
    GOVERNED_MCP_TOOLS,
    McpProposalRepositoryPort,
    McpToolCallResult,
    McpToolDescriptor,
    McpToolName,
    execute_mcp_read_tool,
)
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_kernel.ports import ContextSourcePort, VectorStorePort

__all__ = [
    "GOVERNED_MCP_TOOLS",
    "GovernedMcpServerService",
    "McpProposalRepositoryPort",
    "McpToolCallResult",
    "McpToolDescriptor",
    "McpToolName",
]


class GovernedMcpServerService:
    """Governed MCP Server enforcing Passthrough identity and `human_authored_required` blocks."""

    def __init__(
        self,
        *,
        context_source: ContextSourcePort | None = None,
        vector_store: VectorStorePort | None = None,
        proposals_repository: McpProposalRepositoryPort | None = None,
        strict_sql: bool = False,
    ) -> None:
        self._context_source = context_source
        self._vector_store = vector_store
        self._proposals_repository = proposals_repository
        self._strict_sql = strict_sql
        self._protected_sections: set[str] = {
            "intention-metier",
            "business-intent",
            "architecture-decision-rationale",
            "human-anchor",
        }

    def list_tools(self) -> list[McpToolDescriptor]:
        """Return all governed MCP tools exposed to external IDEs (`AR-7`)."""
        return list(GOVERNED_MCP_TOOLS)

    def _validate_call_inputs(
        self,
        *,
        tool_name: str,
        workspace_id: str,
        execution_identity: str,
        instance: str | None,
    ) -> str:
        if execution_identity != "passthrough":
            raise ValidationDomainError(
                detail_override=(
                    "External IDE MCP calls must strictly use execution_identity='passthrough'."
                ),
                instance=instance,
            )
        if not workspace_id.strip():
            raise ValidationDomainError(
                detail_override="workspace_id is required for MCP calls.",
                instance=instance,
            )
        clean_tool = tool_name.strip()
        if clean_tool not in {t.name for t in GOVERNED_MCP_TOOLS}:
            raise ResourceNotFoundError(
                detail_override=f"Unknown MCP tool {clean_tool!r}.",
                instance=instance,
            )
        return clean_tool

    def _validate_propose_draft(
        self,
        *,
        workspace_id: str,
        arguments: dict[str, Any],
        ide_client: str,
        is_read_only_observer: bool,
        instance: str | None,
    ) -> dict[str, Any]:
        if is_read_only_observer:
            raise ObserverModeReadOnlyError(instance=instance)
        section_key = str(arguments.get("section_key", "")).strip()
        human_required = bool(arguments.get("human_authored_required", False)) or (
            section_key.lower() in self._protected_sections
        )
        if human_required:
            raise HumanAnchorRequiredError(
                detail_override=(
                    f"MCP write blocked on section {section_key!r}: "
                    "human_authored_required=true (AD-3, FR-24)."
                ),
                instance=instance,
            )
        draft_content = str(arguments.get("content_markdown", "")).strip()
        if not section_key or not draft_content:
            raise ValidationDomainError(
                detail_override="section_key and content_markdown are required.",
                instance=instance,
            )
        return {
            "workspace_id": workspace_id,
            "run_id": str(arguments.get("run_id", "run-default")),
            "section_key": section_key,
            "content_markdown": draft_content,
            "ide_client": ide_client,
        }

    def call_tool(
        self,
        *,
        tool_name: str,
        workspace_id: str,
        arguments: dict[str, Any],
        ide_client: str = "vscode",
        execution_identity: str = "passthrough",
        is_read_only_observer: bool = False,
        instance: str | None = None,
    ) -> McpToolCallResult:
        """Execute a governed MCP tool synchronously (validation & read-only tools)."""
        clean_tool = self._validate_call_inputs(
            tool_name=tool_name,
            workspace_id=workspace_id,
            execution_identity=execution_identity,
            instance=instance,
        )
        if clean_tool == "blackboard.propose_draft":
            entry = self._validate_propose_draft(
                workspace_id=workspace_id,
                arguments=arguments,
                ide_client=ide_client,
                is_read_only_observer=is_read_only_observer,
                instance=instance,
            )
            if self._strict_sql:
                raise ValidationDomainError(
                    detail_override=(
                        "Sync MCP propose_draft disabled when strict_sql=True; use call_tool_async."
                    ),
                    instance=instance,
                )
            return McpToolCallResult(
                tool_name="blackboard.propose_draft",
                ide_client=ide_client,
                execution_identity="passthrough",
                workspace_id=workspace_id,
                status="OK",
                data={"draft_recorded": True, "proposal": entry},
            )
        return execute_mcp_read_tool(
            clean_tool=clean_tool,
            workspace_id=workspace_id,
            arguments=arguments,
            ide_client=ide_client,
            context_source=self._context_source,
            vector_store=self._vector_store,
        )

    async def call_tool_async(
        self,
        *,
        tool_name: str,
        workspace_id: str,
        arguments: dict[str, Any],
        ide_client: str = "vscode",
        execution_identity: str = "passthrough",
        is_read_only_observer: bool = False,
        proposed_by: str | None = None,
        instance: str | None = None,
    ) -> McpToolCallResult:
        """Execute a governed MCP tool call with PG18 persistence for draft proposals."""
        clean_tool = self._validate_call_inputs(
            tool_name=tool_name,
            workspace_id=workspace_id,
            execution_identity=execution_identity,
            instance=instance,
        )
        if clean_tool == "blackboard.propose_draft":
            entry = self._validate_propose_draft(
                workspace_id=workspace_id,
                arguments=arguments,
                ide_client=ide_client,
                is_read_only_observer=is_read_only_observer,
                instance=instance,
            )
            if self._proposals_repository is not None:
                persisted = await self._proposals_repository.record_proposal(
                    workspace_id=str(entry["workspace_id"]),
                    run_id=str(entry["run_id"]),
                    section_key=str(entry["section_key"]),
                    content_markdown=str(entry["content_markdown"]),
                    ide_client=str(entry["ide_client"]),
                    execution_identity="passthrough",
                    proposed_by=proposed_by,
                )
                return McpToolCallResult(
                    tool_name="blackboard.propose_draft",
                    ide_client=ide_client,
                    execution_identity="passthrough",
                    workspace_id=workspace_id,
                    status="OK",
                    data={"draft_recorded": True, "proposal": persisted},
                )
            if self._strict_sql:
                raise ValidationDomainError(
                    detail_override=(
                        "MCP proposals PG18 repository is required when strict_sql=True."
                    ),
                    instance=instance,
                )
            return McpToolCallResult(
                tool_name="blackboard.propose_draft",
                ide_client=ide_client,
                execution_identity="passthrough",
                workspace_id=workspace_id,
                status="OK",
                data={"draft_recorded": True, "proposal": entry},
            )

        draft_proposals: list[dict[str, Any]] | None = None
        if clean_tool == "blackboard.read" and self._proposals_repository is not None:
            run_id = str(arguments.get("run_id", "run-default")).strip()
            draft_proposals = await self._proposals_repository.list_proposals(
                workspace_id=workspace_id, run_id=run_id
            )
        return execute_mcp_read_tool(
            clean_tool=clean_tool,
            workspace_id=workspace_id,
            arguments=arguments,
            ide_client=ide_client,
            context_source=self._context_source,
            vector_store=self._vector_store,
            draft_proposals=draft_proposals,
        )

    async def list_draft_proposals_async(
        self,
        *,
        workspace_id: str,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List persisted MCP draft proposals directly from PostgreSQL 18."""
        if self._proposals_repository is None:
            if self._strict_sql:
                raise ValidationDomainError(
                    detail_override=(
                        "MCP proposals PG18 repository is required when strict_sql=True."
                    )
                )
            return []
        return await self._proposals_repository.list_proposals(
            workspace_id=workspace_id, run_id=run_id
        )
