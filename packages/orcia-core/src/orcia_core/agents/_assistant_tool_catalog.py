"""Dynamic Workspace Tool Catalog Builder (`Story 26.6b`, `H-27`, `AD-25`).

Assembles authorized per-turn tools without arbitrary RAM caps:
1. The 4 `SurgicalContextExplorer` read-only primitives (`#Lstart-end` line ranges).
2. Conditional `kb.search` (included ONLY when RAG/search is active in workspace).
3. Read-only `ontology.lookup` over workspace L1-L4 ontology concepts and axioms.
4. All PG18 `enabled_in_workspace` skills with real JSON Schema `input_parameters`.
5. MCP-exposed tools filtered strictly by `mcp_tool_permissions` and workspace RBAC.
"""

from __future__ import annotations

import re
from typing import Any

from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    AuthorizedToolDescriptor,
    McpExposedToolSpec,
    SkillCatalogEntry,
)
from orcia_core.ports.surgical_explorer_port import MAX_SURGICAL_LINES, SurgicalPrimitiveName

_SAFE_PARAM_RE = re.compile(r"[^a-zA-Z0-9_]+")


def _normalize_param_key(raw: str) -> str:
    cleaned = _SAFE_PARAM_RE.sub("_", raw.strip()).strip("_").lower()
    return cleaned or "input_text"


def build_skill_parameters_schema(input_parameters: tuple[str, ...]) -> dict[str, Any]:
    """Build deterministic JSON Schema `parameters` from PG18 skill `input_parameters`."""
    props: dict[str, Any] = {}
    required: list[str] = []
    for raw_param in input_parameters:
        key = _normalize_param_key(raw_param)
        if key not in props:
            props[key] = {
                "type": "string",
                "description": f"Parameter '{raw_param.strip()}'",
            }
            required.append(key)
    if not props:
        props["input_text"] = {
            "type": "string",
            "description": "Structured input text passed to the skill.",
        }
        required.append("input_text")
    return {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }


def _build_surgical_descriptors() -> tuple[AuthorizedToolDescriptor, ...]:
    """Return descriptors for the 4 read-only `SurgicalContextExplorer` primitives."""
    return (
        AuthorizedToolDescriptor(
            tool_name=SurgicalPrimitiveName.CHECK_RESOURCE_STATE.value,
            description=(
                "Check existence, SHA-256 digest, and line count of an authorized workspace "
                "resource URI or path without loading full file content."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "resource_uri": {"type": "string", "description": "Workspace URI or path"}
                },
                "required": ["resource_uri"],
            },
            category="surgical_read",
            read_only=True,
            required_permission="read",
        ),
        AuthorizedToolDescriptor(
            tool_name=SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE.value,
            description=(
                "Extract structural outline (headings, classes, functions) of an authorized "
                "workspace resource."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "resource_uri": {"type": "string", "description": "Workspace URI or path"}
                },
                "required": ["resource_uri"],
            },
            category="surgical_read",
            read_only=True,
            required_permission="read",
        ),
        AuthorizedToolDescriptor(
            tool_name=SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS.value,
            description=(
                "Search bounded matching line snippets (#Lstart-end) inside authorized workspace "
                "files and documentation."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Substring query (1..256 chars)"},
                    "resource_uri": {"type": "string", "description": "Optional sub-scope path"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["query"],
            },
            category="surgical_read",
            read_only=True,
            required_permission="read",
        ),
        AuthorizedToolDescriptor(
            tool_name=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES.value,
            description=(
                f"Inspect an inclusive 1-indexed line slice (#Lstart-end, max {MAX_SURGICAL_LINES}"
                " lines) of an authorized workspace resource."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "resource_uri": {"type": "string", "description": "Workspace URI or path"},
                    "start_line": {"type": "integer", "minimum": 1, "default": 1},
                    "end_line": {"type": "integer", "minimum": 1, "default": 200},
                },
                "required": ["resource_uri", "start_line", "end_line"],
            },
            category="surgical_read",
            read_only=True,
            required_permission="read",
        ),
    )


def _skill_to_descriptor(
    skill: SkillCatalogEntry, *, workspace_id: str
) -> AuthorizedToolDescriptor:
    slug = skill.slug.strip().replace("-", "_") or "custom"
    return AuthorizedToolDescriptor(
        tool_name=f"skill_{slug}",
        description=f"{skill.name}: {skill.objective}".strip(),
        parameters_schema=build_skill_parameters_schema(skill.input_parameters),
        category="skill",
        read_only=not skill.is_si_write,
        is_si_write=skill.is_si_write,
        human_authored_required=skill.human_authored_required,
        source_uri_or_scope=skill.uri or f"orcia://workspaces/{workspace_id}/skills/{skill.slug}",
        skill_id=skill.skill_id,
        required_permission="execute",
        sandbox_tier=skill.sandbox_tier,
        timeout_s=15.0,
    )


def _mcp_to_descriptor(spec: McpExposedToolSpec, *, workspace_id: str) -> AuthorizedToolDescriptor:
    is_write_mode = spec.permission_mode == "WRITE_PREVIEW" or spec.is_si_write
    return AuthorizedToolDescriptor(
        tool_name=spec.tool_name,
        description=spec.description,
        parameters_schema=dict(spec.parameters_schema),
        category="mcp_tool",
        read_only=not is_write_mode,
        is_si_write=is_write_mode,
        human_authored_required=spec.human_authored_required,
        source_uri_or_scope=spec.source_uri_or_scope
        or f"mcp://{workspace_id}/{spec.agent_slug}/{spec.tool_name}",
        mcp_agent_slug=spec.agent_slug,
        required_permission=spec.required_permission,
        sandbox_tier="NONE",
        timeout_s=15.0,
    )


def build_authorized_tool_catalog(
    ctx: AssistantToolCatalogContext,
) -> tuple[AuthorizedToolDescriptor, ...]:
    """Assemble authorized per-turn tools from surgical, RAG, ontology, PG18 skills & MCP."""
    perms = {p.strip().lower() for p in ctx.user_permissions if p.strip()}
    can_read = "read" in perms or "execute" in perms or "admin" in perms
    can_execute = ("execute" in perms or "admin" in perms) and ctx.user_role.upper() not in (
        "OBSERVER",
        "READ_ONLY_OBSERVER",
        "BU_DIRECTOR",
    )
    if not can_read:
        return ()

    descriptors: list[AuthorizedToolDescriptor] = []
    seen_names: set[str] = set()

    def _append_unique(desc: AuthorizedToolDescriptor) -> None:
        if desc.tool_name not in seen_names:
            seen_names.add(desc.tool_name)
            descriptors.append(desc)

    if ctx.can_use_surgical:
        for d in _build_surgical_descriptors():
            _append_unique(d)

    if ctx.rag_active:
        _append_unique(
            AuthorizedToolDescriptor(
                tool_name="kb.search",
                description=(
                    "Hybrid semantic + lexical workspace knowledge base search (only active when "
                    "an embedding model is configured)."
                ),
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                    },
                    "required": ["query"],
                },
                category="kb_search",
                read_only=True,
                source_uri_or_scope=f"orcia://workspaces/{ctx.workspace_id}/rag",
                required_permission="read",
            )
        )

    if ctx.can_use_ontology:
        _append_unique(
            AuthorizedToolDescriptor(
                tool_name="ontology.lookup",
                description=(
                    "Query L1-L4 workspace ontology concepts, definitions, and immutable axioms "
                    "in read-only mode."
                ),
                parameters_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Concept or axiom query"},
                        "level": {"type": "string", "description": "Optional L1..L4 filter"},
                    },
                    "required": ["query"],
                },
                category="ontology_lookup",
                read_only=True,
                source_uri_or_scope=f"orcia://workspaces/{ctx.workspace_id}/ontology",
                required_permission="read",
            )
        )

    if can_execute:
        for skill in ctx.skills:
            if skill.enabled_in_workspace:
                _append_unique(_skill_to_descriptor(skill, workspace_id=ctx.workspace_id))

    for mcp_spec in ctx.mcp_tools:
        if not mcp_spec.mcp_exposed or mcp_spec.permission_mode == "NONE":
            continue
        if mcp_spec.required_permission == "execute" and not can_execute:
            continue
        _append_unique(_mcp_to_descriptor(mcp_spec, workspace_id=ctx.workspace_id))

    return tuple(descriptors)


__all__ = ["build_authorized_tool_catalog", "build_skill_parameters_schema"]
