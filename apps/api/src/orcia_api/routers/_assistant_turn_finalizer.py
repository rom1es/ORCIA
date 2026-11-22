"""N4 EvidenceTable, N6 Server CitationGuard & Canonical Terminal Emit (`Story 26.7`, `AD-25`)."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from orcia_api.routers._assistant_usage_telemetry import resolve_usage_with_fallback
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration.assistant_citations_models import (
    EvidenceTable,
    RawToolOutputCandidate,
)
from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine
from orcia_core.orchestration.redis_turn_registry import RedisAssistantTurnRegistry
from orcia_core.ports.assistant_turn_stream_port import AssistantTurnRecord
from orcia_core.ports.finops_telemetry import FinopsCostLedgerEntry
from orcia_core.ports.llm_streaming_port import LlmEndpointConfig

logger = get_logger("orcia.assistant.finalizer")


async def finalize_and_emit_turn_completion_async(
    *,
    turn_engine: AssistantTurnEngine | None,
    base_evidence_table: EvidenceTable | None,
    tool_outputs: Sequence[RawToolOutputCandidate],
    pending_completed_data: dict[str, Any] | None,
    record: AssistantTurnRecord,
    stream_ep: LlmEndpointConfig | None,
    thinking_text: str,
    streamed_text: str,
    obs_in: int,
    obs_out: int,
    saw_usage: bool,
    obs_lat: float,
    t0: float,
    user_email: str | None,
    user_display_name: str | None,
    registry: RedisAssistantTurnRegistry,
    flush_before_emit: Callable[[AssistantTurnRecord, str], Awaitable[None]],
) -> AssistantTurnRecord:
    """Run N4 EvidenceTable + N6 CitationGuard before persisting & emitting `turn_completed`."""
    engine = turn_engine or AssistantTurnEngine()
    final_table, low_evidence = engine.n4_build_evidence_table(
        base_table=base_evidence_table,
        tool_outputs=tool_outputs,
    )
    verification, citation_payload, low_evidence = await engine.n6_verify_citations_async(
        response_text=streamed_text,
        evidence_table=final_table,
        workspace_id=record.workspace_id,
        user_id=record.user_id,
        user_email=user_email,
        user_display_name=user_display_name,
        turn_id=record.turn_id,
        trace_id=record.trace_id,
    )
    sanitized_text = verification.sanitized_text
    in_tok, out_tok, u_src = resolve_usage_with_fallback(
        prompt_text=f"{record.assembled_system_prompt}\n{record.user_prompt}",
        reply_text=f"{sanitized_text}\n{thinking_text}",
        observed_input_tokens=obs_in,
        observed_output_tokens=obs_out,
        saw_provider_usage=saw_usage,
    )
    elapsed_ms = obs_lat or round((time.perf_counter() - t0) * 1000.0, 2)
    supports_tools = stream_ep.supports_tools if stream_ep is not None else record.supports_tools
    updated = replace(
        record,
        status="COMPLETED",
        thinking_text=thinking_text,
        streamed_text=sanitized_text,
        citation_map=dict(citation_payload.get("citation_map_dict") or {}),
        low_evidence=low_evidence,
        supports_tools=supports_tools,
        input_tokens=in_tok,
        output_tokens=out_tok,
        usage_source=u_src,
        elapsed_ms=elapsed_ms,
    )
    await flush_before_emit(updated, sanitized_text)
    await registry.set_stream_ttl(record.turn_id, ttl_seconds=1800)
    await registry.append_event(
        record.turn_id,
        event="citation_map",
        data=citation_payload,
        ttl_seconds=1800,
    )
    completed_payload = dict(pending_completed_data or {})
    completed_payload.update(
        {
            "turn_id": record.turn_id,
            "message_id": f"msg-{record.turn_id}-assistant" if record.thread_id else None,
            "response_text": sanitized_text,
            "thinking_text": thinking_text,
            "assembled_system_prompt": record.assembled_system_prompt,
            "latency_ms": elapsed_ms,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "usage_source": u_src,
            "usage": {
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "cost_usd": float(completed_payload.get("cost_usd") or 0.0),
                "usage_source": u_src,
            },
            "low_evidence": low_evidence,
            "supports_tools": supports_tools,
            "citation_map": citation_payload.get("citations") or {},
            "purged_phantom_count": int(citation_payload.get("purged_phantom_count") or 0),
            "trace_id": record.trace_id,
        }
    )
    await registry.append_event(
        record.turn_id,
        event="turn_completed",
        data=completed_payload,
        ttl_seconds=1800,
    )
    await registry.update_turn(updated)
    await engine.complete_assistant_reflexive_session_async(
        turn_id=record.turn_id,
        status="COMPLETED",
        final_markdown=sanitized_text,
        tokens_used=in_tok + out_tok,
    )
    return updated


async def record_turn_approval_audit(
    *,
    sink: Any | None,
    turn_id: str,
    proposal_id: str,
    workspace_id: str,
    user_id: str,
    user_email: str | None,
    user_display_name: str | None,
    approved: bool,
    human_anchor_markdown: str | None,
    rationale: str | None,
    trace_id: str,
) -> tuple[str | None, str | None]:
    """Hash optional human anchor markdown and persist `audit_ledger` approval row."""
    anchor_sha = (
        hashlib.sha256(human_anchor_markdown.strip().encode("utf-8")).hexdigest()
        if human_anchor_markdown and human_anchor_markdown.strip()
        else None
    )
    if sink is None:
        return anchor_sha, None
    ws_uuid: str | None = None
    try:
        ws_uuid = str(UUID(workspace_id.strip()))
    except (ValueError, TypeError, AttributeError):
        ws_uuid = None
    event_id = str(uuid5(NAMESPACE_URL, f"assistant-approve:{turn_id}:{proposal_id}:{approved}"))
    entry = FinopsCostLedgerEntry(
        source_event_id=event_id,
        workspace_id=ws_uuid,
        scope_path=f"WORKSPACE/{workspace_id}" if workspace_id else "GLOBAL",
        actor_type="HUMAN",
        actor_id=user_id,
        actor_display_name=user_display_name,
        actor_email=user_email,
        event_type="ASSISTANT_PROPOSAL_APPROVED" if approved else "ASSISTANT_PROPOSAL_REJECTED",
        summary=f"Proposal '{proposal_id}' {'approved' if approved else 'rejected'} on {turn_id}",
        trace_id=trace_id,
        metadata={
            "turn_id": turn_id,
            "proposal_id": proposal_id,
            "approved": approved,
            "human_anchor_sha256": anchor_sha,
            "rationale": (rationale or "")[:240],
        },
    )
    try:
        audit_id = await sink.record_entry(entry)
    except Exception as exc:
        logger.warning(
            "assistant_proposal_approval_audit_failed",
            turn_id=turn_id,
            error_type=type(exc).__name__,
        )
        return anchor_sha, None
    return anchor_sha, audit_id


async def emit_fallback_response_events_async(
    *,
    registry: RedisAssistantTurnRegistry,
    record: AssistantTurnRecord,
    default_thinking: str,
    fallback_response_text: str | None,
    t0: float,
) -> tuple[str, bool]:
    """Emit fallback `thinking_delta` + `token_delta` events when streaming port is inactive."""
    turn_id = record.turn_id
    await registry.append_event(
        turn_id,
        event="thinking_delta",
        data={
            "step_code": "NODE_5_SINGLE_STREAM_LLM",
            "delta": default_thinking,
            "delta_text": default_thinking,
            "thinking_text": default_thinking,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "trace_id": record.trace_id,
        },
    )
    full_text = fallback_response_text or ""
    acc: list[str] = []
    emitted = False
    for chunk in full_text.splitlines(keepends=True) or ([full_text] if full_text else []):
        acc.append(chunk)
        emitted = True
        await registry.append_event(
            turn_id,
            event="token_delta",
            data={
                "delta": chunk,
                "delta_text": chunk,
                "accumulated_text": "".join(acc),
                "trace_id": record.trace_id,
            },
        )
    return full_text, emitted
