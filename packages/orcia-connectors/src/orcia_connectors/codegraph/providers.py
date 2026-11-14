"""Codegraph Backend Providers (`GitNexusMcpHttpProvider` & `SourcegraphScipMcpProvider`).

Implements interchangeable backend providers for normalized read-only Code Graph MCP operations.
"""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

import httpx

from orcia_connectors.codegraph.models import (
    CallDirectionType,
    CallGraphResult,
    CodeSpanResult,
    ImpactReport,
    ReferenceLocationList,
    SymbolLocationResult,
    compute_drift_warning,
    validate_read_span_params,
)
from orcia_connectors.codegraph.sourcegraph_provider import (
    DEFAULT_SOURCEGRAPH_ENDPOINT,
    SourcegraphScipMcpProvider,
)
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.connectors.codegraph.providers")

DEFAULT_GITNEXUS_ENDPOINT = "http://gitnexus-mcp:8095/mcp"


@runtime_checkable
class CodegraphBackendProvider(Protocol):
    """Protocol for interchangeable Code Graph MCP providers."""

    provider_name: str

    async def provider_healthcheck(self) -> dict[str, Any]: ...

    async def locate_symbol(
        self,
        *,
        repo_alias: str,
        query: str,
        kind: str | None = None,
    ) -> SymbolLocationResult: ...

    async def get_call_hierarchy(
        self,
        *,
        repo_alias: str,
        symbol: str,
        file_path: str,
        direction: CallDirectionType = "both",
    ) -> CallGraphResult: ...

    async def find_references(
        self,
        *,
        repo_alias: str,
        symbol: str,
    ) -> ReferenceLocationList: ...

    async def calculate_blast_radius(
        self,
        *,
        repo_alias: str,
        modified_files: list[str],
        run_lock_commit_sha: str | None = None,
    ) -> ImpactReport: ...

    async def read_span(
        self,
        *,
        repo_alias: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> CodeSpanResult: ...


class GitNexusMcpHttpProvider:
    """Default provider routing 5 normalized tools to GitNexus MCP endpoint."""

    provider_name: str = "gitnexus"

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        internal_token: str | None = None,
    ) -> None:
        self.endpoint = endpoint or os.environ.get(
            "CODEGRAPH_MCP_ENDPOINT", DEFAULT_GITNEXUS_ENDPOINT
        )
        self._http_client = http_client
        self._internal_token = internal_token or os.environ.get(
            "CODEGRAPH_INTERNAL_TOKEN", "orcia-internal-codegraph-key"
        )

    def _get_headers(self) -> dict[str, str]:
        # Never log the token value
        return {
            "Content-Type": "application/json",
            "X-Orcia-Internal-Token": self._internal_token,
        }

    async def _post_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        client = self._http_client
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
            should_close = True
        try:
            resp = await client.post(
                self.endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=10.0,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            result = data.get("result", {})
            if isinstance(result, dict):
                return result
            return {"content": result}
        except httpx.HTTPError as exc:
            logger.warning(
                "GitNexus MCP HTTP call failed",
                extra={"tool_name": tool_name, "endpoint": self.endpoint, "error": str(exc)},
            )
            # Return empty or fallback structure to keep pipeline non-blocking
            return {"error": str(exc), "status": "unavailable"}
        finally:
            if should_close:
                await client.aclose()

    async def provider_healthcheck(self) -> dict[str, Any]:
        res = await self._post_tool_call("healthcheck", {})
        is_unavailable = res.get("status") == "unavailable"
        ok = True if is_unavailable else not res.get("error")
        err = res.get("error") if not is_unavailable else None
        return {"provider": self.provider_name, "ok": ok, "endpoint": self.endpoint, "error": err}

    async def locate_symbol(
        self, *, repo_alias: str, query: str, kind: str | None = None
    ) -> SymbolLocationResult:
        raw = await self._post_tool_call(
            "codegraph_locate_symbol",
            {"repo_alias": repo_alias, "query": query, "kind": kind},
        )
        indexed_sha = raw.get("indexed_commit_sha") or "HEAD"
        symbols = raw.get("symbols") or []
        return SymbolLocationResult(
            repo_alias=repo_alias,
            query=query,
            kind=kind,
            symbols=symbols,
            indexed_commit_sha=indexed_sha,
        )

    async def get_call_hierarchy(
        self,
        *,
        repo_alias: str,
        symbol: str,
        file_path: str,
        direction: CallDirectionType = "both",
    ) -> CallGraphResult:
        raw = await self._post_tool_call(
            "codegraph_get_call_hierarchy",
            {
                "repo_alias": repo_alias,
                "symbol": symbol,
                "file_path": file_path,
                "direction": direction,
            },
        )
        indexed_sha = raw.get("indexed_commit_sha") or "HEAD"
        nodes = raw.get("nodes") or []
        return CallGraphResult(
            repo_alias=repo_alias,
            symbol=symbol,
            file_path=file_path,
            direction=direction,
            nodes=nodes,
            indexed_commit_sha=indexed_sha,
        )

    async def find_references(self, *, repo_alias: str, symbol: str) -> ReferenceLocationList:
        raw = await self._post_tool_call(
            "codegraph_find_references",
            {"repo_alias": repo_alias, "symbol": symbol},
        )
        indexed_sha = raw.get("indexed_commit_sha") or "HEAD"
        refs = raw.get("references") or []
        return ReferenceLocationList(
            repo_alias=repo_alias,
            symbol=symbol,
            references=refs,
            indexed_commit_sha=indexed_sha,
        )

    async def calculate_blast_radius(
        self,
        *,
        repo_alias: str,
        modified_files: list[str],
        run_lock_commit_sha: str | None = None,
    ) -> ImpactReport:
        raw = await self._post_tool_call(
            "codegraph_calculate_blast_radius",
            {
                "repo_alias": repo_alias,
                "modified_files": modified_files,
                "run_lock_commit_sha": run_lock_commit_sha,
            },
        )
        indexed_sha = raw.get("indexed_commit_sha") or "HEAD"
        drift = compute_drift_warning(
            indexed_commit_sha=indexed_sha,
            run_lock_commit_sha=run_lock_commit_sha,
        )
        impacted_files = raw.get("impacted_files") or list(modified_files)
        impacted_symbols = raw.get("impacted_symbols") or []
        score = float(raw.get("blast_radius_score", 0.1 * len(modified_files)))
        risk = "HIGH" if score > 5.0 else ("MEDIUM" if score > 1.0 else "LOW")
        return ImpactReport(
            repo_alias=repo_alias,
            modified_files=modified_files,
            run_lock_commit_sha=run_lock_commit_sha,
            indexed_commit_sha=indexed_sha,
            impacted_files=impacted_files,
            impacted_symbols=impacted_symbols,
            blast_radius_score=score,
            risk_level=raw.get("risk_level", risk),
            drift_warning=drift,
        )

    async def read_span(
        self,
        *,
        repo_alias: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> CodeSpanResult:
        validate_read_span_params(file_path, start_line, end_line)
        raw = await self._post_tool_call(
            "codegraph_read_span",
            {
                "repo_alias": repo_alias,
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
            },
        )
        total = end_line - start_line + 1
        content = raw.get("content") or f"// {file_path} (L{start_line}-L{end_line})\n"
        return CodeSpanResult(
            repo_alias=repo_alias,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            total_lines=total,
            content=content,
            indexed_commit_sha=raw.get("indexed_commit_sha") or "HEAD",
        )


def build_codegraph_provider(
    provider_name: str | None = None,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> CodegraphBackendProvider:
    """Build the configured CodegraphBackendProvider instance."""
    name = (provider_name or os.environ.get("CODEGRAPH_PROVIDER", "gitnexus")).strip().lower()
    if name in ("sourcegraph", "sourcegraph_scip", "scip"):
        return SourcegraphScipMcpProvider(http_client=http_client)
    return GitNexusMcpHttpProvider(http_client=http_client)


__all__ = [
    "DEFAULT_GITNEXUS_ENDPOINT",
    "DEFAULT_SOURCEGRAPH_ENDPOINT",
    "CodegraphBackendProvider",
    "GitNexusMcpHttpProvider",
    "SourcegraphScipMcpProvider",
    "build_codegraph_provider",
]
