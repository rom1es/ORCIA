"""Round & Follow-Up Helpers for Governed Assistant Tool Loop (`Story 26.6b`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from orcia_core.orchestration.llm_tool_dialects import (
    format_tool_result_message,
    parse_json_arguments,
)
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolExecutionRequest,
    AssistantToolExecutionResult,
    AssistantToolExecutorPort,
    AuthorizedToolDescriptor,
)
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.llm_streaming_port import (
    LlmEndpointConfig,
    LlmStreamingPort,
    LlmStreamRequest,
)
from orcia_kernel.ids import new_uuid7_str


def granted_roles_for_tool_call(
    catalog: Sequence[AuthorizedToolDescriptor],
    tool_name: str,
    user_role: str,
) -> tuple[str, ...]:
    """Grant `ROLE_MCP_TOOL_EXECUTOR` only to authorized non-observer read-only MCP calls."""
    norm_role = user_role.strip().upper()
    if norm_role in ("OBSERVER", "READ_ONLY_OBSERVER", "BU_DIRECTOR"):
        return ()
    desc = next((d for d in catalog if d.tool_name == tool_name), None)
    if (
        desc is not None
        and desc.category == "mcp_tool"
        and desc.read_only
        and not desc.is_si_write
        and not desc.human_authored_required
    ):
        return ("ROLE_MCP_TOOL_EXECUTOR",)
    return ()


async def execute_governed_round_with_outcomes(
    *,
    tool_router: AssistantToolExecutorPort,
    catalog: Sequence[AuthorizedToolDescriptor],
    registry: RedisAssistantTurnRegistry,
    record: AssistantTurnRecord,
    iteration: int,
    tool_calls: Sequence[dict[str, Any]],
    user_email: str | None,
    user_display_name: str | None,
    locale: str,
    user_identity: Any | None = None,
    active_hat: str = "ARCHITECT",
) -> tuple[list[dict[str, Any]], list[AssistantToolExecutionResult]]:
    """Execute one LLM tool-call round, forward SSE events, and flag approval blocks."""
    result_messages: list[dict[str, Any]] = []
    approval_outcomes: list[AssistantToolExecutionResult] = []
    user_role = str(getattr(user_identity, "platform_role", None) or "OBSERVER")
    user_roles = tuple(getattr(user_identity, "roles", ()) or ())
    for idx, tc in enumerate(tool_calls):
        tc_id = str(tc.get("id") or f"call_{iteration}_{idx + 1}")
        tc_name = str(tc.get("name") or "")
        args = parse_json_arguments(tc.get("arguments"))
        req = AssistantToolExecutionRequest(
            turn_id=record.turn_id,
            iteration=iteration,
            tool_call_id=tc_id,
            tool_name=tc_name,
            arguments=args,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            user_email=user_email,
            user_display_name=user_display_name,
            user_role=user_role,
            user_roles=user_roles,
            active_hat=active_hat,
            trace_id=record.trace_id,
            locale=locale,
            granted_external_roles=granted_roles_for_tool_call(catalog, tc_name, user_role),
            user_identity=user_identity,
        )
        outcome = await tool_router.execute_tool_call(req, catalog=catalog)
        if outcome.verdict == "APPROVAL_REQUIRED":
            approval_outcomes.append(outcome)
        for sse_evt in outcome.sse_events:
            await registry.append_event(
                record.turn_id,
                event=sse_evt.event,
                data=dict(sse_evt.data),
            )
        result_messages.append(
            format_tool_result_message(
                tool_call_id=tc_id,
                name=tc_name or "tool",
                content=outcome.delimited_output,
            )
        )
    return result_messages, approval_outcomes


def build_approval_proposal_text(
    outcomes: Sequence[AssistantToolExecutionResult],
    *,
    locale: str = "fr",
) -> str:
    """Build deterministic read-only proposal text when a tool requires human approval."""
    lines: list[str] = []
    for out in outcomes:
        tool_label = out.tool_name
        proposal = out.approval_proposal or {}
        hint = str(proposal.get("human_arbitration_uri") or "")
        if locale.lower().startswith("en"):
            msg = (
                f"Execution of `{tool_label}` was intercepted (Lock V5 / Process Write Gate) "
                "and converted into an explicit human-validation proposal."
            )
        else:
            msg = (
                f"L'exécution de `{tool_label}` a été interceptée (Verrou V5 / Process Write Gate) "
                "et convertie en proposition soumise à arbitrage humain."
            )
        if hint:
            msg = f"{msg} ({hint})"
        lines.append(msg)
    return "\n".join(lines)


async def execute_sync_tool_followup(
    *,
    tool_router: AssistantToolExecutorPort,
    catalog: Sequence[AuthorizedToolDescriptor],
    active_port: LlmStreamingPort,
    ep: LlmEndpointConfig,
    messages: Sequence[dict[str, Any]],
    tool_calls: Sequence[dict[str, Any]],
    workspace_id: str,
    user_id: str,
    user: Any | None,
    active_hat: str,
    trace_id: str,
    locale: str,
) -> tuple[str, int, int, str]:
    """Execute non-streaming tool calls via `GovernedAssistantToolRouter` and synthesize."""
    turn_id = new_uuid7_str()
    user_role = str(getattr(user, "platform_role", None) or "OBSERVER")
    user_roles = tuple(getattr(user, "roles", ()) or ())
    tool_msgs: list[dict[str, Any]] = []
    approval_outcomes: list[AssistantToolExecutionResult] = []
    for idx, tc in enumerate(tool_calls):
        tc_id = str(tc.get("id") or f"call_{idx + 1}")
        tc_name = str(tc.get("name") or "")
        res = await tool_router.execute_tool_call(
            AssistantToolExecutionRequest(
                turn_id=turn_id,
                iteration=1,
                tool_call_id=tc_id,
                tool_name=tc_name,
                arguments=parse_json_arguments(tc.get("arguments")),
                workspace_id=workspace_id,
                user_id=user_id,
                user_email=getattr(user, "email", None),
                user_display_name=getattr(user, "display_name", None),
                user_role=user_role,
                user_roles=user_roles,
                active_hat=active_hat,
                trace_id=trace_id,
                locale=locale,
                granted_external_roles=granted_roles_for_tool_call(catalog, tc_name, user_role),
                user_identity=user,
            ),
            catalog=catalog,
        )
        if res.verdict == "APPROVAL_REQUIRED":
            approval_outcomes.append(res)
        tool_msgs.append(
            format_tool_result_message(
                tool_call_id=tc_id, name=tc_name or "tool", content=res.delimited_output
            )
        )
    if approval_outcomes:
        return build_approval_proposal_text(approval_outcomes, locale=locale), 0, 0, "estimated"
    followup = [
        *messages,
        {"role": "assistant", "content": "", "tool_calls": list(tool_calls)},
        *tool_msgs,
    ]
    second = await active_port.complete_chat(
        LlmStreamRequest(endpoint=ep, messages=tuple(followup), include_thoughts=True)
    )
    if second is None:
        return "", 0, 0, "estimated"
    return second.content, second.input_tokens, second.output_tokens, second.usage_source


__all__ = [
    "build_approval_proposal_text",
    "execute_governed_round_with_outcomes",
    "execute_sync_tool_followup",
    "granted_roles_for_tool_call",
]
