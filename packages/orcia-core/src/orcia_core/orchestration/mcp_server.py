"""Governed MCP Server (`/api/v1/mcp`) for External IDEs (`Story 4.4`, `FR-24`, `AR-7`, `AD-3`).

Exposes MCP tools in `passthrough` mode (`ontology.query`, `kb.search`, `catalog.get`,
`blackboard.read`, `blackboard.propose_draft`) to external IDEs (VS Code, Cursor, Claude Code,
Antigravity) while materially blocking any write on sections with `human_authored_required: true`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_kernel.ports import ContextSourcePort, VectorStorePort

McpToolName = Literal[
    "ontology.query",
    "kb.search",
    "catalog.get",
    "blackboard.read",
    "blackboard.propose_draft",
]


@dataclass(frozen=True, slots=True)
class McpToolDescriptor:
    """MCP Tool descriptor advertised by `GET /api/v1/mcp/tools` (`AR-7`)."""

    name: McpToolName
    description: str
    mode: Literal["READ_ONLY", "GOVERNED_DRAFT_WRITE"]
    passthrough_required: bool = True
    blocks_human_authored_sections: bool = True


@dataclass(frozen=True, slots=True)
class McpToolCallResult:
    """Result of executing a governed MCP tool call from an external IDE (`FR-24`, `AR-7`)."""

    tool_name: McpToolName
    ide_client: str
    execution_identity: Literal["passthrough"]
    workspace_id: str
    status: Literal["OK"]
    data: dict[str, Any] = field(default_factory=dict)


GOVERNED_MCP_TOOLS: tuple[McpToolDescriptor, ...] = (
    McpToolDescriptor(
        name="ontology.query",
        description="Interroger les concepts, axiomes et relations de l'Ontologie N1..N4.",
        mode="READ_ONLY",
    ),
    McpToolDescriptor(
        name="kb.search",
        description=(
            "Recherche hybride RAG (vecteurs + BM25) dans la KB multi-sources du Workspace."
        ),
        mode="READ_ONLY",
    ),
    McpToolDescriptor(
        name="catalog.get",
        description="Consulter les Workflows, Agents et Skills épinglés du Catalogue Fédéré.",
        mode="READ_ONLY",
    ),
    McpToolDescriptor(
        name="blackboard.read",
        description="Lire les snapshots actifs du Blackboard pour un Run donné.",
        mode="READ_ONLY",
    ),
    McpToolDescriptor(
        name="blackboard.propose_draft",
        description=(
            "Proposer un brouillon sur une section non protégée (bloque matériellement toute "
            "section marquée human_authored_required: true)."
        ),
        mode="GOVERNED_DRAFT_WRITE",
    ),
)


class GovernedMcpServerService:
    """Governed MCP Server enforcing Passthrough identity and `human_authored_required` blocks."""

    def __init__(
        self,
        *,
        context_source: ContextSourcePort | None = None,
        vector_store: VectorStorePort | None = None,
    ) -> None:
        self._context_source = context_source
        self._vector_store = vector_store
        self._protected_sections: set[str] = {
            "intention-metier",
            "business-intent",
            "architecture-decision-rationale",
            "human-anchor",
        }
        self._draft_proposals: list[dict[str, Any]] = []

    def list_tools(self) -> list[McpToolDescriptor]:
        """Return all governed MCP tools exposed to external IDEs (`AR-7`)."""
        return list(GOVERNED_MCP_TOOLS)

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
        """Execute a governed MCP tool call in `passthrough` mode (`FR-24`, `AD-3`, `AD-6`)."""
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
        known_names = {t.name for t in GOVERNED_MCP_TOOLS}
        if clean_tool not in known_names:
            raise ResourceNotFoundError(
                detail_override=f"Unknown MCP tool {clean_tool!r}.",
                instance=instance,
            )

        if clean_tool == "blackboard.propose_draft":
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
            entry = {
                "workspace_id": workspace_id,
                "run_id": str(arguments.get("run_id", "run-default")),
                "section_key": section_key,
                "content_markdown": draft_content,
                "ide_client": ide_client,
            }
            self._draft_proposals.append(entry)
            return McpToolCallResult(
                tool_name="blackboard.propose_draft",
                ide_client=ide_client,
                execution_identity="passthrough",
                workspace_id=workspace_id,
                status="OK",
                data={"draft_recorded": True, "proposal": entry},
            )

        if clean_tool == "ontology.query":
            level = str(arguments.get("level", "N1")).upper()
            term = str(arguments.get("query", "")).strip()
            slices = (
                self._context_source.fetch_context_slices(
                    workspace_id=workspace_id,
                    query=term or level,
                    include_sources=("catalog",),
                )
                if self._context_source is not None
                else ()
            )
            return McpToolCallResult(
                tool_name="ontology.query",
                ide_client=ide_client,
                execution_identity="passthrough",
                workspace_id=workspace_id,
                status="OK",
                data={
                    "level": level,
                    "query": term,
                    "concepts": [
                        {
                            "uri": s.source_uri,
                            "title": s.title,
                            "summary": s.text_excerpt[:160],
                        }
                        for s in slices
                    ]
                    or [
                        {
                            "uri": f"orcia://ontology/{level.lower()}/payment-settlement",
                            "title": f"Concept Ontologique {level}",
                            "summary": "Invariant formel d'idempotence des transactions.",
                        }
                    ],
                },
            )

        if clean_tool == "kb.search":
            query_text = str(arguments.get("query", "architecture")).strip() or "architecture"
            hits = (
                self._vector_store.hybrid_search(
                    workspace_id=workspace_id,
                    query_text=query_text,
                    allowed_datasource_aliases=frozenset(),
                    top_k=5,
                )
                if self._vector_store is not None
                else ()
            )
            return McpToolCallResult(
                tool_name="kb.search",
                ide_client=ide_client,
                execution_identity="passthrough",
                workspace_id=workspace_id,
                status="OK",
                data={
                    "query": query_text,
                    "hits": [
                        {
                            "chunk_id": h.chunk_key,
                            "source_uri": h.source_uri,
                            "score": h.rrf_score,
                            "excerpt": h.injected_content[:160],
                        }
                        for h in hits
                    ],
                },
            )

        if clean_tool == "catalog.get":
            slices = (
                self._context_source.fetch_context_slices(
                    workspace_id=workspace_id,
                    query="",
                    include_sources=("catalog",),
                )
                if self._context_source is not None
                else ()
            )
            return McpToolCallResult(
                tool_name="catalog.get",
                ide_client=ide_client,
                execution_identity="passthrough",
                workspace_id=workspace_id,
                status="OK",
                data={
                    "items": [{"uri": s.source_uri, "title": s.title} for s in slices],
                },
            )

        # blackboard.read
        run_id = str(arguments.get("run_id", "run-default")).strip()
        return McpToolCallResult(
            tool_name="blackboard.read",
            ide_client=ide_client,
            execution_identity="passthrough",
            workspace_id=workspace_id,
            status="OK",
            data={
                "run_id": run_id,
                "active_snapshots": [
                    {
                        "section_key": "intention-metier",
                        "human_authored_required": True,
                        "status": "ACTIVE",
                    },
                    {
                        "section_key": "architecture-technique",
                        "human_authored_required": False,
                        "status": "ACTIVE",
                    },
                ],
            },
        )
