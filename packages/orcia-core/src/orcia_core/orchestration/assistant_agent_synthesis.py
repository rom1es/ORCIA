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
    lower = user_prompt.strip().lower()
    if any(
        phrase in lower
        for phrase in (
            "remplis-le pour moi",
            "remplis la section humaine",
            "rédige l'ancre humaine",
            "write the human anchor for me",
            "fill the human anchor",
        )
    ):
        return "HUMAN_ANCHOR_WRITE_REFUSAL"
    if has_active_proposal and any(
        kw in lower for kw in ("modifie", "ajoute", "étape", "step", "ajuste", "modify", "add step")
    ):
        return "WORKFLOW_MODIFY"
    if any(
        kw in lower
        for kw in (
            "workflow",
            "composer",
            "propose un workflow",
            "créer un workflow",
            "comparer",
            "rapprochement",
            "audit",
        )
    ):
        return "WORKFLOW_COMPOSE"
    if any(kw in lower for kw in ("lance", "exécute", "launch", "start run")):
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
        refusal = (
            f"{prefix} Refus constitutionnel (`human_authored_required: true`, `FR-4`, `AD-3`) : "
            "Je ne peux pas rédiger ni pré-remplir une Ancre Humaine à votre place afin de "
            "préserver votre maîtrise intellectuelle (*Think*). Question socratique : "
            "quels sont les 2 invariants métier non négociables que vous souhaitez fixer "
            f"pour le périmètre `{workspace_id}` ?"
        )
        return prefix, indicators, None if refusal else None
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
    uris_note = (
        f" Sources citées : {', '.join(assembled.cited_uris[:3])}."
        if assembled.cited_uris
        else f" Périmètre : `orcia://workspaces/{workspace_id}`."
    )
    if proposal is not None:
        return (
            f"{prefix} ({indicators}) — Proposition de workflow `{proposal.workflow_uri}` "
            f"({len(proposal.nodes)} étapes, régime `{proposal.execution_regime}`) prête dans "
            f"le Canvas `@xyflow/react`.{uris_note} [{llm_out.prompt_sha256[:16]}]"
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
        return (
            f"{prefix} Refus constitutionnel (`human_authored_required: true`, `FR-4`, `AD-3`) : "
            "Je ne peux pas rédiger ni pré-remplir une Ancre Humaine à votre place afin de "
            "préserver votre maîtrise intellectuelle (*Think*). Question socratique : "
            "quels sont les 2 invariants métier non négociables que vous souhaitez fixer "
            f"pour le périmètre `{workspace_id}` ?"
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
