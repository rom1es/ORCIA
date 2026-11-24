"""Assistant Agent Synthesis & SSE Formatting Helpers (`Story 3.3`, `Story 26.1`)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.assistant_agent_models import (
    AssistantTurnResult,
    AssistantWorkflowProposal,
)
from orcia_core.orchestration.assistant_harness import AssembledAssistantPrompt, AssistantIntentKind
from orcia_core.orchestration.errors import TierModelNotConfiguredError
from orcia_kernel.ports import LLMPort, LlmPromptRequest

logger = get_logger("orcia.core.orchestration.assistant_agent")


def classify_assistant_intent(
    user_prompt: str, *, has_active_proposal: bool = False
) -> AssistantIntentKind:
    """Node 1 (`1_INTENT_ROUTER`): classify legacy `AssistantAgentService` intent.

    Note (`Story 26.6b`): lexical `HUMAN_ANCHOR_WRITE_REFUSAL` phrase matching is deprecated
    for live tool loops, which enforce deterministic per-tool Lock V5 and Human-Anchor
    gating via `GovernedAssistantToolRouter`; kept solely for legacy `3.3`/`3.4` callers
    until `Story 26.7` deletes the legacy path.
    """
    from orcia_core.orchestration._assistant_profile_locales import INTENT_KEYWORDS_LOCALES

    lower = user_prompt.strip().lower()
    fr_kw = INTENT_KEYWORDS_LOCALES["fr"]
    en_kw = INTENT_KEYWORDS_LOCALES["en"]
    if any(phrase in lower for phrase in (*fr_kw["refusal"], *en_kw["refusal"])):
        return "HUMAN_ANCHOR_WRITE_REFUSAL"
    if has_active_proposal and any(kw in lower for kw in (*fr_kw["modify"], *en_kw["modify"])):
        return "WORKFLOW_MODIFY"
    if any(kw in lower for kw in (*fr_kw["compose"], *en_kw["compose"])):
        return "WORKFLOW_COMPOSE"
    if any(kw in lower for kw in (*fr_kw["launch"], *en_kw["launch"])):
        return "WORKFLOW_LAUNCH"
    return "QA_COACHING"


def _prepare_synthesis_request(
    *,
    llm_gateway: LLMPort | None,
    cognitive_router: Any | None,
    assembled: AssembledAssistantPrompt,
    intent: AssistantIntentKind,
    workspace_id: str,
) -> tuple[str, str, LlmPromptRequest | None]:
    prefix = assembled.profile_adaptation.response_prefix_fr
    indicators = ", ".join(assembled.profile_adaptation.highlighted_indicators)
    if intent == "HUMAN_ANCHOR_WRITE_REFUSAL":
        return prefix, indicators, None
    model_family, model_id = "", ""
    if cognitive_router is not None:
        try:
            resolved = cognitive_router.resolve_mapping(
                scope_id=workspace_id, tier="complex", effort="default"
            )
            model_family, model_id = resolved.model_family, resolved.model_name
        except Exception as exc:
            logger.warning(
                "assistant_agent.cognitive_router_resolve_failed",
                workspace_id=workspace_id,
                error_type=type(exc).__name__,
                error=str(exc),
            )
    if (not model_family or not model_id) and bool(
        getattr(llm_gateway, "is_cassette_adapter", False)
    ):
        model_family, model_id = "cassette", "cassette/assistant-agent"
    elif not model_family or not model_id:
        raise TierModelNotConfiguredError(
            inference_tier="complex", instance=f"assistant_agent:{workspace_id}"
        )
    if llm_gateway is None:
        raise TierModelNotConfiguredError(
            inference_tier="complex", instance=f"assistant_agent:{workspace_id}"
        )
    req = LlmPromptRequest(
        system_prompt=assembled.system_prompt,
        user_prompt=assembled.user_prompt,
        model_family=model_family,
        model_id=model_id,
        execution_mode="COACHING",
        metadata={"workspace_id": workspace_id, "intent": intent},
    )
    return prefix, indicators, req


def _format_synthesis_text(
    *,
    prefix: str,
    indicators: str,
    assembled: AssembledAssistantPrompt,
    proposal: AssistantWorkflowProposal | None,
    workspace_id: str,
    llm_out: Any,
) -> str:
    from orcia_core.orchestration._assistant_locales import ASSISTANT_SYNTHESIS_LOCALES

    sloc = ASSISTANT_SYNTHESIS_LOCALES["fr"]
    uris_note = (
        sloc["cited_sources"].format(uris=", ".join(assembled.cited_uris[:3]))
        if assembled.cited_uris
        else sloc["scope_note"].format(workspace_id=workspace_id)
    )
    if proposal is not None:
        return sloc["proposal_ready"].format(
            prefix=prefix,
            indicators=indicators,
            workflow_uri=proposal.workflow_uri,
            count=len(proposal.nodes),
            regime=proposal.execution_regime,
            uris_note=uris_note,
            sha=llm_out.prompt_sha256[:16],
        )
    return f"{prefix} ({indicators}) — {llm_out.content}.{uris_note} [{llm_out.prompt_sha256[:16]}]"


async def synthesize_assistant_turn_response_async(
    *,
    llm_gateway: LLMPort | None,
    cognitive_router: Any | None,
    assembled: AssembledAssistantPrompt,
    intent: AssistantIntentKind,
    proposal: AssistantWorkflowProposal | None,
    workspace_id: str,
) -> str:
    """Async Node 5 text synthesis via CognitiveRouter / `LLMPort` (`H-11`)."""
    prefix, indicators, req = _prepare_synthesis_request(
        llm_gateway=llm_gateway,
        cognitive_router=cognitive_router,
        assembled=assembled,
        intent=intent,
        workspace_id=workspace_id,
    )
    if req is None:
        from orcia_core.orchestration._assistant_locales import ASSISTANT_SYNTHESIS_LOCALES

        return ASSISTANT_SYNTHESIS_LOCALES["fr"]["anchor_refusal"].format(
            prefix=prefix, workspace_id=workspace_id
        )
    assert llm_gateway is not None
    llm_out = await llm_gateway.complete(req)
    return _format_synthesis_text(
        prefix=prefix,
        indicators=indicators,
        assembled=assembled,
        proposal=proposal,
        workspace_id=workspace_id,
        llm_out=llm_out,
    )


def synthesize_assistant_turn_response(
    *,
    llm_gateway: LLMPort | None,
    cognitive_router: Any | None,
    assembled: AssembledAssistantPrompt,
    intent: AssistantIntentKind,
    proposal: AssistantWorkflowProposal | None,
    workspace_id: str,
) -> str:
    """Sync Node 5 text synthesis (for non-async tests; forbids blocking an active loop)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            synthesize_assistant_turn_response_async(
                llm_gateway=llm_gateway,
                cognitive_router=cognitive_router,
                assembled=assembled,
                intent=intent,
                proposal=proposal,
                workspace_id=workspace_id,
            )
        )
    raise RuntimeError(
        "synthesize_assistant_turn_response() cannot run inside an active event loop; "
        "await synthesize_assistant_turn_response_async() instead."
    )


async def iter_assistant_turn_sse_events_async(
    turn: AssistantTurnResult,
) -> AsyncIterator[dict[str, Any]]:
    """Async SSE event generator (`node_trace`, `token`, `workflow_proposal`, `done`)."""
    for item in iter_assistant_turn_sse_events(turn):
        yield item


def iter_assistant_turn_sse_events(turn: AssistantTurnResult) -> Iterator[dict[str, Any]]:
    """Yield SSE event dicts (`node_trace`, `token`, `workflow_proposal`, `done`)."""
    for tr in turn.node_traces:
        yield {
            "event": "node_trace",
            "data": {
                "node_id": tr.node_id,
                "node_order": tr.node_order,
                "duration_ms": tr.duration_ms,
                "summary": tr.summary,
            },
        }
    lines = turn.response_text.splitlines(keepends=True) or [turn.response_text]
    chunk_size = max(1, len(lines) // 4)
    for idx in range(0, len(lines), chunk_size):
        yield {
            "event": "token",
            "data": {
                "turn_id": turn.turn_id,
                "token": "".join(lines[idx : idx + chunk_size]),
                "first_token_latency_ms": turn.first_token_latency_ms,
            },
        }
    if turn.workflow_proposal is not None:
        yield {
            "event": "workflow_proposal",
            "data": {
                "proposal_id": turn.workflow_proposal.proposal_id,
                "workflow_uri": turn.workflow_proposal.workflow_uri,
                "title": turn.workflow_proposal.title,
                "execution_regime": turn.workflow_proposal.execution_regime,
                "node_count": len(turn.workflow_proposal.nodes),
            },
        }
    yield {
        "event": "done",
        "data": {
            "turn_id": turn.turn_id,
            "intent": turn.intent,
            "first_token_latency_ms": turn.first_token_latency_ms,
        },
    }
