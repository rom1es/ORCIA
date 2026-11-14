"""Story 18.3 — Transport Schemas for Normalized Code Graph MCP Endpoints.

Exposes request and response models for:
- `GET  /api/v1/workspaces/{workspace_id}/codegraph/tools`
- `POST /api/v1/workspaces/{workspace_id}/codegraph/invoke`
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CodegraphToolItemResponse(BaseModel):
    """Specification of an available read-only MCP codegraph tool."""

    name: str = Field(..., description="Normalized tool name")
    description: str = Field(..., description="Tool summary for agent tool-calling")
    read_only: bool = Field(default=True, description="Always true for codegraph-mcp tools")
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for arguments"
    )


class CodegraphActiveRepoResponse(BaseModel):
    """Code repository datasource enabled for codegraph indexing in the workspace."""

    datasource_id: str
    alias: str
    uri: str
    source_nature: str = "SOURCE_CODE"
    codegraph_enabled: bool = True
    codegraph_status: str = "READY"
    codegraph_head_sha: str | None = None


class CodegraphToolsListResponse(BaseModel):
    """Payload returned by `GET /api/v1/workspaces/{workspace_id}/codegraph/tools`."""

    workspace_id: str
    provider: str
    tools: list[CodegraphToolItemResponse] = Field(default_factory=list)
    active_repositories: list[CodegraphActiveRepoResponse] = Field(default_factory=list)
    trace_id: str


class InvokeCodegraphToolRequest(BaseModel):
    """Payload sent to `POST /api/v1/workspaces/{workspace_id}/codegraph/invoke`."""

    tool_name: str = Field(..., description="Normalized tool name to invoke")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments (repo_alias, query, etc.)"
    )


class InvokeCodegraphToolResponse(BaseModel):
    """Payload returned by `POST /api/v1/workspaces/{workspace_id}/codegraph/invoke`."""

    workspace_id: str
    tool_name: str
    provider: str
    result: dict[str, Any] = Field(default_factory=dict)
    trace_id: str


__all__ = [
    "CodegraphActiveRepoResponse",
    "CodegraphToolItemResponse",
    "CodegraphToolsListResponse",
    "InvokeCodegraphToolRequest",
    "InvokeCodegraphToolResponse",
]
