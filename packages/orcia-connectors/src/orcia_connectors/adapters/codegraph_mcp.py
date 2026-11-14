"""Normalized Read-Only Code Graph MCP Connector (`CodegraphMcpConnector`).

Implements `OrciaConnectorProtocol`:
- Strictly read-only (`preview_write` and `execute_write` raise `PermissionError`).
- Server-injected workspace confinement (ignores any client-provided workspace_id).
- Repository opt-in check (source_nature == SOURCE_CODE, codegraph_enabled is True,
  codegraph_status not in ("DISABLED", "PAUSED_REFERENT_RENEWAL_REQUIRED")).
- Interchangeable backend provider (GitNexus or Sourcegraph SCIP).
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from orcia_connectors.codegraph.models import (
    CallDirectionType,
    CodeSpanResult,
    ImpactReport,
    ReferenceLocationList,
    SymbolLocationResult,
    validate_read_span_params,
)
from orcia_connectors.codegraph.providers import (
    CodegraphBackendProvider,
    build_codegraph_provider,
)
from orcia_connectors.protocol import (
    ConnectorHealthStatus,
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
)
from orcia_core.kernel.errors import ValidationDomainError
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.connectors.codegraph.adapter")

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "codegraph_locate_symbol",
        "description": "Locate definitions and declarations of symbols matching a query.",
        "read_only": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_alias": {"type": "string"},
                "query": {"type": "string"},
                "kind": {"type": "string", "nullable": True},
            },
            "required": ["repo_alias", "query"],
        },
    },
    {
        "name": "codegraph_get_call_hierarchy",
        "description": "Get callers and callees for a symbol in a file.",
        "read_only": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_alias": {"type": "string"},
                "symbol": {"type": "string"},
                "file_path": {"type": "string"},
                "direction": {
                    "type": "string",
                    "enum": ["callers", "callees", "both"],
                    "default": "both",
                },
            },
            "required": ["repo_alias", "symbol", "file_path"],
        },
    },
    {
        "name": "codegraph_find_references",
        "description": "Find all code references for a given symbol.",
        "read_only": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_alias": {"type": "string"},
                "symbol": {"type": "string"},
            },
            "required": ["repo_alias", "symbol"],
        },
    },
    {
        "name": "codegraph_calculate_blast_radius",
        "description": "Calculate blast radius and detect graph drift for modified files.",
        "read_only": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_alias": {"type": "string"},
                "modified_files": {"type": "array", "items": {"type": "string"}},
                "run_lock_commit_sha": {"type": "string", "nullable": True},
            },
            "required": ["repo_alias", "modified_files"],
        },
    },
    {
        "name": "codegraph_read_span",
        "description": "Read a bounded code span (max 250 lines) with anti-traversal check.",
        "read_only": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_alias": {"type": "string"},
                "file_path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer"},
            },
            "required": ["repo_alias", "file_path", "start_line", "end_line"],
        },
    },
]


class CodegraphMcpConnector(OrciaConnectorProtocol):
    """Unified read-only connector for MCP Code Graph operations."""

    connector_type: str = "mcp:codegraph"

    def __init__(
        self,
        *,
        provider: CodegraphBackendProvider | None = None,
        workspace_id: str | None = None,
        datasources_resolver: (
            Callable[[str], Awaitable[Sequence[Any]] | Sequence[Any]] | None
        ) = None,
    ) -> None:
        self.provider = provider or build_codegraph_provider()
        self.workspace_id = workspace_id
        self._datasources_resolver = datasources_resolver

    async def healthcheck(self) -> ConnectorHealthStatus:
        status = await self.provider.provider_healthcheck()
        return ConnectorHealthStatus(
            connector_type=self.connector_type,
            ok=bool(status.get("ok", True)),
            latency_ms=2,
            error_message=status.get("error"),
        )

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        raise PermissionError("codegraph-mcp is strictly read-only")

    async def execute_write(
        self,
        approval_token: SignedApprovalToken,
        action: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        raise PermissionError("codegraph-mcp is strictly read-only")

    async def _resolve_workspace_datasources(self, workspace_id: str) -> Sequence[Any]:
        if self._datasources_resolver is None:
            return []
        res = self._datasources_resolver(workspace_id)
        if inspect.isawaitable(res):
            return await res
        return res

    async def verify_repo_access(self, workspace_id: str, repo_alias: str) -> Any:
        datasources = await self._resolve_workspace_datasources(workspace_id)
        match = None
        for ds in datasources:
            alias = getattr(ds, "alias", None) or (
                ds.get("alias") if isinstance(ds, dict) else None
            )
            if alias == repo_alias:
                match = ds
                break
        if match is None:
            raise PermissionError(
                f"Repository alias {repo_alias!r} is not attached to workspace {workspace_id!r}"
            )
        nature = getattr(match, "source_nature", None) or (
            match.get("source_nature") if isinstance(match, dict) else None
        )
        if nature != "SOURCE_CODE":
            raise PermissionError(
                f"Datasource {repo_alias!r} is not of nature SOURCE_CODE (nature={nature})"
            )
        enabled = getattr(match, "codegraph_enabled", None)
        if enabled is None and isinstance(match, dict):
            enabled = match.get("codegraph_enabled")
        if not enabled:
            raise PermissionError(f"Codegraph is not enabled for repository {repo_alias!r}")
        status = getattr(match, "codegraph_status", None) or (
            match.get("codegraph_status") if isinstance(match, dict) else None
        )
        if status in ("DISABLED", "PAUSED_REFERENT_RENEWAL_REQUIRED"):
            raise PermissionError(
                f"Codegraph is inactive for repository {repo_alias!r} (status={status})"
            )
        return match

    async def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        workspace_id: str,
    ) -> dict[str, Any]:
        # Server-injected workspace_id is strictly enforced
        repo_alias = str(arguments.get("repo_alias") or "").strip()
        if not repo_alias:
            raise ValidationDomainError(detail_override="repo_alias is required")

        if tool_name == "codegraph_read_span":
            fp = str(arguments.get("file_path") or "").strip()
            start_l = int(arguments.get("start_line", 1))
            end_l = int(arguments.get("end_line", 1))
            validate_read_span_params(fp, start_l, end_l)

        await self.verify_repo_access(workspace_id, repo_alias)

        if tool_name == "codegraph_locate_symbol":
            query = str(arguments.get("query") or "").strip()
            if not query:
                raise ValidationDomainError(detail_override="query is required")
            res_sym: SymbolLocationResult = await self.provider.locate_symbol(
                repo_alias=repo_alias, query=query, kind=arguments.get("kind")
            )
            return res_sym.model_dump()

        if tool_name == "codegraph_get_call_hierarchy":
            sym = str(arguments.get("symbol") or "").strip()
            fp = str(arguments.get("file_path") or "").strip()
            dir_val: CallDirectionType = arguments.get("direction") or "both"
            if not sym or not fp:
                raise ValidationDomainError(detail_override="symbol and file_path are required")
            res_call = await self.provider.get_call_hierarchy(
                repo_alias=repo_alias, symbol=sym, file_path=fp, direction=dir_val
            )
            return res_call.model_dump()

        if tool_name == "codegraph_find_references":
            sym = str(arguments.get("symbol") or "").strip()
            if not sym:
                raise ValidationDomainError(detail_override="symbol is required")
            res_ref: ReferenceLocationList = await self.provider.find_references(
                repo_alias=repo_alias, symbol=sym
            )
            return res_ref.model_dump()

        if tool_name == "codegraph_calculate_blast_radius":
            files = arguments.get("modified_files") or []
            if not isinstance(files, list):
                raise ValidationDomainError(detail_override="modified_files must be a list")
            run_lock_sha = arguments.get("run_lock_commit_sha")
            res_blast: ImpactReport = await self.provider.calculate_blast_radius(
                repo_alias=repo_alias, modified_files=files, run_lock_commit_sha=run_lock_sha
            )
            return res_blast.model_dump()

        if tool_name == "codegraph_read_span":
            fp = str(arguments.get("file_path") or "").strip()
            start_l = int(arguments.get("start_line", 1))
            end_l = int(arguments.get("end_line", 1))
            res_span: CodeSpanResult = await self.provider.read_span(
                repo_alias=repo_alias, file_path=fp, start_line=start_l, end_line=end_l
            )
            return res_span.model_dump()

        raise ValidationDomainError(detail_override=f"Unknown codegraph tool: {tool_name}")

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        cleaned = (resource_uri or "").strip()
        q = dict(query or {})
        ws_id = self.workspace_id or q.get("_server_workspace_id")
        if cleaned in ("tools", "codegraph://tools"):
            return {
                "connector_type": self.connector_type,
                "provider": self.provider.provider_name,
                "tools": TOOL_DEFINITIONS,
            }
        tool_name = q.get("tool") or cleaned.removeprefix("codegraph://").removeprefix(
            "mcp://codegraph/"
        )
        if not ws_id:
            raise ValidationDomainError(
                detail_override="workspace_id must be provided for tool invocation"
            )
        return await self.invoke_tool(tool_name, q, workspace_id=ws_id)


__all__ = [
    "TOOL_DEFINITIONS",
    "CodegraphMcpConnector",
]
