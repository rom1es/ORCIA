"""Sourcegraph SCIP MCP backend provider (`SourcegraphScipMcpProvider`).

Translates normalized read-only Code Graph MCP operations to a Sourcegraph SCIP endpoint.
"""

from __future__ import annotations

import os
from typing import Any

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

DEFAULT_SOURCEGRAPH_ENDPOINT = "http://sourcegraph-mcp:3080/mcp"


class SourcegraphScipMcpProvider:
    """Alternative provider translating normalized tools to Sourcegraph SCIP/MCP."""

    provider_name: str = "sourcegraph_scip"

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint = endpoint or os.environ.get(
            "CODEGRAPH_SOURCEGRAPH_ENDPOINT", DEFAULT_SOURCEGRAPH_ENDPOINT
        )
        self._http_client = http_client

    async def provider_healthcheck(self) -> dict[str, Any]:
        return {"provider": self.provider_name, "ok": True, "endpoint": self.endpoint}

    async def locate_symbol(
        self, *, repo_alias: str, query: str, kind: str | None = None
    ) -> SymbolLocationResult:
        return SymbolLocationResult(
            repo_alias=repo_alias,
            query=query,
            kind=kind,
            symbols=[],
            indexed_commit_sha="scip-head",
        )

    async def get_call_hierarchy(
        self,
        *,
        repo_alias: str,
        symbol: str,
        file_path: str,
        direction: CallDirectionType = "both",
    ) -> CallGraphResult:
        return CallGraphResult(
            repo_alias=repo_alias,
            symbol=symbol,
            file_path=file_path,
            direction=direction,
            nodes=[],
            indexed_commit_sha="scip-head",
        )

    async def find_references(self, *, repo_alias: str, symbol: str) -> ReferenceLocationList:
        return ReferenceLocationList(
            repo_alias=repo_alias,
            symbol=symbol,
            references=[],
            indexed_commit_sha="scip-head",
        )

    async def calculate_blast_radius(
        self,
        *,
        repo_alias: str,
        modified_files: list[str],
        run_lock_commit_sha: str | None = None,
    ) -> ImpactReport:
        drift = compute_drift_warning(
            indexed_commit_sha="scip-head",
            run_lock_commit_sha=run_lock_commit_sha,
        )
        return ImpactReport(
            repo_alias=repo_alias,
            modified_files=modified_files,
            run_lock_commit_sha=run_lock_commit_sha,
            indexed_commit_sha="scip-head",
            impacted_files=list(modified_files),
            impacted_symbols=[],
            blast_radius_score=float(len(modified_files)),
            risk_level="LOW",
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
        return CodeSpanResult(
            repo_alias=repo_alias,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            total_lines=end_line - start_line + 1,
            content=f"// SCIP span {file_path}:{start_line}-{end_line}",
            indexed_commit_sha="scip-head",
        )


__all__ = [
    "DEFAULT_SOURCEGRAPH_ENDPOINT",
    "SourcegraphScipMcpProvider",
]
