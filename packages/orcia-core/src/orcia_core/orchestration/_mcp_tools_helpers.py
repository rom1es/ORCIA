"""Tool descriptors and read-tool execution helpers for `GovernedMcpServerService`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from orcia_kernel.ports import ContextSourcePort, VectorStorePort

McpToolName = Literal[
    "ontology.query",
    "kb.search",
    "catalog.get",
    "blackboard.read",
    "blackboard.propose_draft",
]


class McpProposalRepositoryPort(Protocol):
    """Port abstracting PostgreSQL 18 persistence for `mcp_governed_proposals` (`AD-19`)."""

    async def record_proposal(
        self,
        *,
        workspace_id: str,
        run_id: str,
        section_key: str,
        content_markdown: str,
        ide_client: str,
        execution_identity: str = "passthrough",
        proposed_by: str | None = None,
    ) -> dict[str, Any]: ...

    async def list_proposals(
        self,
        *,
        workspace_id: str,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]: ...


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


def execute_mcp_read_tool(
    *,
    clean_tool: str,
    workspace_id: str,
    arguments: dict[str, Any],
    ide_client: str,
    context_source: ContextSourcePort | None,
    vector_store: VectorStorePort | None,
    draft_proposals: list[dict[str, Any]] | None = None,
) -> McpToolCallResult:
    """Execute one of the read-only governed MCP tools."""
    if clean_tool == "ontology.query":
        level = str(arguments.get("level", "N1")).upper()
        term = str(arguments.get("query", "")).strip()
        slices = (
            context_source.fetch_context_slices(
                workspace_id=workspace_id,
                query=term or level,
                include_sources=("catalog",),
            )
            if context_source is not None
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
                    {"uri": s.source_uri, "title": s.title, "summary": s.text_excerpt[:160]}
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
            vector_store.hybrid_search(
                workspace_id=workspace_id,
                query_text=query_text,
                allowed_datasource_aliases=frozenset(),
                top_k=5,
            )
            if vector_store is not None
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
            context_source.fetch_context_slices(
                workspace_id=workspace_id,
                query="",
                include_sources=("catalog",),
            )
            if context_source is not None
            else ()
        )
        return McpToolCallResult(
            tool_name="catalog.get",
            ide_client=ide_client,
            execution_identity="passthrough",
            workspace_id=workspace_id,
            status="OK",
            data={"items": [{"uri": s.source_uri, "title": s.title} for s in slices]},
        )

    run_id = str(arguments.get("run_id", "run-default")).strip()
    data: dict[str, Any] = {
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
    }
    if draft_proposals is not None:
        data["draft_proposals"] = draft_proposals
    return McpToolCallResult(
        tool_name="blackboard.read",
        ide_client=ide_client,
        execution_identity="passthrough",
        workspace_id=workspace_id,
        status="OK",
        data=data,
    )
