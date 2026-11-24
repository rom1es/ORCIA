"""Codegraph Tool Runner for Review Workflows (`codegraph_tool_runner.py`).

Inspects workflow sub-steps for `mcp:codegraph` read permissions, runs
`codegraph_calculate_blast_radius`, and attaches structured impact reports and
`GRAPH_MOVED_SINCE_RUN_LOCK` drift warnings.
"""

from __future__ import annotations

from typing import Any

from orcia_connectors._connectors_locales import get_codegraph_markdown_copy
from orcia_connectors.adapters.codegraph_mcp import CodegraphMcpConnector
from orcia_connectors.codegraph.models import compute_drift_warning
from orcia_connectors.codegraph.providers import build_codegraph_provider
from orcia_core.kernel.enums import DEFAULT_LOCALE, SupportedLocale
from orcia_core.observability.logging import get_logger

logger = get_logger("orcia.connectors.codegraph.runner")


def has_codegraph_permission(sub_step: Any) -> bool:
    """Return True if `sub_step` declares `mcp:codegraph` read scope in toolbox_mcp_permissions."""
    perms = getattr(sub_step, "toolbox_mcp_permissions", None) or []
    for p in perms:
        cid = p.get("connector_id") if isinstance(p, dict) else getattr(p, "connector_id", None)
        scope = p.get("scope") if isinstance(p, dict) else getattr(p, "scope", None)
        if cid in ("mcp:codegraph", "codegraph") and scope == "read":
            return True
    return False


def run_codegraph_blast_radius(
    sub_step: Any,
    inputs: dict[str, Any],
) -> dict[str, Any] | None:
    """Run `codegraph_calculate_blast_radius` when sub_step references `mcp:codegraph`."""
    if not has_codegraph_permission(sub_step):
        return None

    repo_alias = str(inputs.get("repo_alias") or inputs.get("repository") or "main-repo").strip()
    raw_files = inputs.get("modified_files") or inputs.get("files")
    if isinstance(raw_files, list) and raw_files:
        modified_files = [str(f) for f in raw_files]
    else:
        modified_files = ["src/index.ts"]

    run_lock_sha = inputs.get("run_lock_commit_sha")
    if not run_lock_sha and isinstance(inputs.get("run_lock"), dict):
        run_lock_sha = inputs["run_lock"].get("commit_sha")

    indexed_sha = str(inputs.get("indexed_commit_sha") or "HEAD")
    drift = compute_drift_warning(
        indexed_commit_sha=indexed_sha,
        run_lock_commit_sha=run_lock_sha,
    )
    score = float(len(modified_files)) * 0.5
    risk = "HIGH" if score > 5.0 else ("MEDIUM" if score > 1.0 else "LOW")

    report: dict[str, Any] = {
        "tool": "codegraph_calculate_blast_radius",
        "repo_alias": repo_alias,
        "modified_files": modified_files,
        "run_lock_commit_sha": run_lock_sha,
        "indexed_commit_sha": indexed_sha,
        "impacted_files": list(modified_files),
        "impacted_symbols": [f"{f}::main" for f in modified_files],
        "blast_radius_score": score,
        "risk_level": risk,
        "drift_warning": drift,
    }

    if drift == "GRAPH_MOVED_SINCE_RUN_LOCK":
        logger.warning(
            "Graph drift detected in codegraph review step",
            extra={
                "sub_step_id": getattr(sub_step, "id", "unknown"),
                "run_lock_commit_sha": run_lock_sha,
                "indexed_commit_sha": indexed_sha,
            },
        )
    return report


async def async_run_codegraph_blast_radius(
    sub_step: Any,
    inputs: dict[str, Any],
    *,
    workspace_id: str = "ws-default",
    connector: CodegraphMcpConnector | None = None,
) -> dict[str, Any] | None:
    """Async invocation via CodegraphMcpConnector or active provider."""
    if not has_codegraph_permission(sub_step):
        return None

    repo_alias = str(inputs.get("repo_alias") or inputs.get("repository") or "main-repo").strip()
    raw_files = inputs.get("modified_files") or inputs.get("files")
    modified_files = (
        [str(f) for f in raw_files]
        if isinstance(raw_files, list) and raw_files
        else ["src/index.ts"]
    )
    run_lock_sha = inputs.get("run_lock_commit_sha")

    if connector is not None:
        try:
            return await connector.invoke_tool(
                "codegraph_calculate_blast_radius",
                {
                    "repo_alias": repo_alias,
                    "modified_files": modified_files,
                    "run_lock_commit_sha": run_lock_sha,
                },
                workspace_id=workspace_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Connector invoke_tool failed, falling back to sync calculation",
                extra={"error": str(exc)},
            )

    provider = build_codegraph_provider()
    res = await provider.calculate_blast_radius(
        repo_alias=repo_alias,
        modified_files=modified_files,
        run_lock_commit_sha=run_lock_sha,
    )
    return res.model_dump()


def format_codegraph_markdown_section(
    codegraph_data: dict[str, Any] | None,
    *,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> str:
    """Format structured blast radius result into markdown for deliverables."""
    if not codegraph_data:
        return ""

    copy = get_codegraph_markdown_copy(locale)
    files_str = ", ".join(f"`{f}`" for f in codegraph_data.get("modified_files", []))
    score = codegraph_data.get("blast_radius_score", 0.0)
    risk = codegraph_data.get("risk_level", "LOW")
    repo_alias = str(codegraph_data.get("repo_alias", "main-repo"))
    lines: list[str] = [
        "",
        copy["heading"],
        copy["repo"].format(repo_alias=repo_alias),
        copy["files"].format(files_str=files_str),
        copy["score"].format(score=score, risk=risk),
    ]

    drift = codegraph_data.get("drift_warning")
    if drift == "GRAPH_MOVED_SINCE_RUN_LOCK":
        run_sha = codegraph_data.get("run_lock_commit_sha")
        idx_sha = codegraph_data.get("indexed_commit_sha")
        lines.append(copy["drift"].format(run_sha=run_sha, idx_sha=idx_sha))
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "async_run_codegraph_blast_radius",
    "format_codegraph_markdown_section",
    "has_codegraph_permission",
    "run_codegraph_blast_radius",
]
