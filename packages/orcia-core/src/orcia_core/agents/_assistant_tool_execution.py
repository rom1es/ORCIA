"""Timeout-Capped Sandboxed Tool Execution Dispatcher (`Story 26.6b`, `H-28`)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.observability.logging import get_logger
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutionRequest,
    AuthorizedToolDescriptor,
)
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalPrimitiveName,
)
from orcia_kernel.ports import SandboxExecutionRequest, SandboxPort

logger = get_logger("orcia.agents.tool_execution")

RagSearchCallback = Callable[[str, str, int, Any | None], Awaitable[list[dict[str, Any]]]]
OntologyLookupCallback = Callable[[str, str, str | None], Awaitable[list[dict[str, Any]]]]
SkillRunnerCallback = Callable[
    [AuthorizedToolDescriptor, dict[str, Any], str], Awaitable[dict[str, Any] | str]
]
McpToolRunnerCallback = Callable[
    [AuthorizedToolDescriptor, AssistantToolExecutionRequest], Awaitable[dict[str, Any] | str]
]


@dataclass(frozen=True, slots=True)
class ToolDispatchDependencies:
    """Injected read/sandbox execution dependencies for `GovernedAssistantToolRouter`."""

    surgical_explorer: SurgicalExplorerPort | None = None
    sandbox_port: SandboxPort | None = None
    rag_search_fn: RagSearchCallback | None = None
    ontology_lookup_fn: OntologyLookupCallback | None = None
    skill_runner_fn: SkillRunnerCallback | None = None
    mcp_tool_runner_fn: McpToolRunnerCallback | None = None
    default_timeout_s: float = 10.0


def _coerce_int(value: Any, default: int, *, minimum: int = 1, maximum: int = 100000) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _caller_has_read_source(request: AssistantToolExecutionRequest) -> bool:
    role = (
        str(getattr(request.user_identity, "platform_role", None) or request.user_role or "")
        .strip()
        .upper()
    )
    if not request.user_id or request.user_id == "u-anonymous":
        return False
    return role not in ("OBSERVER", "READ_ONLY_OBSERVER", "BU_DIRECTOR")


async def _execute_surgical_tool(
    descriptor: AuthorizedToolDescriptor,
    request: AssistantToolExecutionRequest,
    explorer: SurgicalExplorerPort | None,
) -> dict[str, Any]:
    if explorer is None:
        return {
            "status": "UNAVAILABLE",
            "tool": descriptor.tool_name,
            "detail": "SurgicalContextExplorer is not configured.",
        }
    primitive = SurgicalPrimitiveName(descriptor.tool_name)
    args = request.arguments
    obs = await explorer.execute_primitive(
        primitive,
        resource_uri=str(args.get("resource_uri") or ""),
        query=str(args.get("query") or ""),
        start_line=_coerce_int(args.get("start_line"), 1, minimum=1),
        end_line=_coerce_int(args.get("end_line"), 200, minimum=1),
        max_results=_coerce_int(args.get("max_results"), 20, minimum=1, maximum=50),
        workspace_id=request.workspace_id,
        actor_id=request.user_id,
        has_read_source=_caller_has_read_source(request),
    )
    return obs.model_dump(mode="json")


async def _execute_skill_tool(
    descriptor: AuthorizedToolDescriptor,
    request: AssistantToolExecutionRequest,
    deps: ToolDispatchDependencies,
) -> dict[str, Any] | str:
    timeout_ms = max(100, min(int(descriptor.timeout_s * 1000), 60000))
    if deps.sandbox_port is not None:
        tier: Literal["TIER_1_WASM", "TIER_2_CONTAINER"] = (
            "TIER_2_CONTAINER" if descriptor.sandbox_tier == "TIER_2_CONTAINER" else "TIER_1_WASM"
        )
        sb_req = SandboxExecutionRequest(
            tier=tier,
            entrypoint=descriptor.tool_name,
            payload={
                "artifact": {
                    "skill_id": descriptor.skill_id or descriptor.tool_name,
                    "arguments": dict(request.arguments),
                    "workspace_id": request.workspace_id,
                    "user_id": request.user_id,
                },
                "forbidden_patterns": [
                    {"rule_id": "SANDBOX-EXEC-EVAL", "pattern": "__import__('os').system"},
                    {"rule_id": "SANDBOX-EXEC-SUBPROC", "pattern": "subprocess.popen"},
                ],
                "skill_id": descriptor.skill_id or descriptor.tool_name,
                "workspace_id": request.workspace_id,
            },
            timeout_ms=timeout_ms,
            max_memory_mb=256 if tier == "TIER_1_WASM" else 1024,
        )
        sb_res = await deps.sandbox_port.execute(sb_req)
        if not sb_res.passed:
            return {
                "status": "SANDBOX_FAILED",
                "exit_code": sb_res.exit_code,
                "stderr": sb_res.stderr,
                "duration_ms": sb_res.duration_ms,
            }
        if deps.skill_runner_fn is None:
            return {
                "status": "EXECUTED",
                "sandbox_tier": tier,
                "duration_ms": sb_res.duration_ms,
                "stdout": sb_res.stdout,
            }
        runner_out = await deps.skill_runner_fn(descriptor, request.arguments, request.workspace_id)
        if isinstance(runner_out, dict):
            return {**runner_out, "sandbox_tier": tier, "sandbox_duration_ms": sb_res.duration_ms}
        return runner_out
    if deps.skill_runner_fn is not None:
        return await deps.skill_runner_fn(descriptor, request.arguments, request.workspace_id)
    return {
        "status": "EXECUTED",
        "skill_id": descriptor.skill_id or descriptor.tool_name,
        "arguments": dict(request.arguments),
    }


async def _dispatch_by_category(
    descriptor: AuthorizedToolDescriptor,
    request: AssistantToolExecutionRequest,
    deps: ToolDispatchDependencies,
) -> dict[str, Any] | str:
    args = request.arguments
    if descriptor.category == "surgical_read":
        return await _execute_surgical_tool(descriptor, request, deps.surgical_explorer)
    if descriptor.category == "kb_search":
        query = str(args.get("query") or "").strip()
        limit = _coerce_int(args.get("limit"), 5, minimum=1, maximum=10)
        hits = (
            await deps.rag_search_fn(request.workspace_id, query, limit, request.user_identity)
            if deps.rag_search_fn is not None
            else []
        )
        return {"tool": "kb.search", "query": query, "hits": hits}
    if descriptor.category == "ontology_lookup":
        query = str(args.get("query") or "").strip()
        level = str(args.get("level")).strip() if args.get("level") else None
        concepts = (
            await deps.ontology_lookup_fn(request.workspace_id, query, level)
            if deps.ontology_lookup_fn is not None
            else []
        )
        return {"tool": "ontology.lookup", "query": query, "concepts": concepts}
    if descriptor.category == "skill":
        return await _execute_skill_tool(descriptor, request, deps)
    if deps.mcp_tool_runner_fn is not None:
        return await deps.mcp_tool_runner_fn(descriptor, request)
    return {
        "status": "EXECUTED",
        "tool": descriptor.tool_name,
        "mcp_agent_slug": descriptor.mcp_agent_slug,
        "arguments": dict(args),
    }


async def execute_with_timeout(
    *,
    descriptor: AuthorizedToolDescriptor,
    request: AssistantToolExecutionRequest,
    deps: ToolDispatchDependencies,
) -> tuple[str, dict[str, Any] | str, bool]:
    """Run allowed tool under `asyncio.wait_for(..., timeout=...)`.

    Returns `(status_tag, payload, timed_out)`.
    """
    cap = float(descriptor.timeout_s or deps.default_timeout_s)
    timeout_s = max(0.01, min(cap, float(deps.default_timeout_s)))
    try:
        output = await asyncio.wait_for(
            _dispatch_by_category(descriptor, request, deps),
            timeout=timeout_s,
        )
        if isinstance(output, dict) and output.get("status") == "SANDBOX_FAILED":
            return "ERROR", output, False
        return "EXECUTED", output, False
    except TimeoutError:
        err_payload = {
            "status": "TIMED_OUT",
            "error_code": "ERR_TOOL_EXECUTION_TIMEOUT",
            "tool_name": descriptor.tool_name,
            "timeout_s": timeout_s,
            "detail": f"Tool '{descriptor.tool_name}' exceeded {timeout_s:.2f}s execution cap.",
        }
        return "TIMED_OUT", err_payload, True
    except Exception as exc:
        logger.warning(
            "assistant_tool_execution_exception",
            tool_name=descriptor.tool_name,
            workspace_id=request.workspace_id,
            error_type=type(exc).__name__,
        )
        err_payload = {
            "status": "ERROR",
            "error_code": "ERR_TOOL_EXECUTION_FAILED",
            "tool_name": descriptor.tool_name,
            "error_type": type(exc).__name__,
            "detail": json.dumps({"error": str(exc)}, ensure_ascii=False),
        }
        return "ERROR", err_payload, False


__all__ = [
    "McpToolRunnerCallback",
    "OntologyLookupCallback",
    "RagSearchCallback",
    "SkillRunnerCallback",
    "ToolDispatchDependencies",
    "execute_with_timeout",
]
