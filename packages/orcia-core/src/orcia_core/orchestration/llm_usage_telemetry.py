"""Usage token extraction, deterministic fallback & audit_ledger persistence (`Story 26.2`)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort, FinopsCostLedgerEntry

logger = get_logger("orcia.assistant.usage")


def extract_usage_tokens_from_payload(payload: dict[str, Any]) -> tuple[int, int] | None:
    """Extract `(input_tokens, output_tokens)` from OpenAI, Anthropic, Gemini or local JSON."""
    usage = payload.get("usage")
    if not isinstance(usage, dict) and isinstance(payload.get("interaction"), dict):
        usage = payload["interaction"].get("usage")
    if isinstance(usage, dict):
        in_t = (
            usage.get("input_tokens")
            if usage.get("input_tokens") is not None
            else (
                usage.get("total_input_tokens")
                if usage.get("total_input_tokens") is not None
                else usage.get("prompt_tokens")
            )
        )
        out_t = (
            usage.get("output_tokens")
            if usage.get("output_tokens") is not None
            else (
                usage.get("total_output_tokens")
                if usage.get("total_output_tokens") is not None
                else usage.get("completion_tokens")
            )
        )
        if in_t is not None or out_t is not None:
            return max(0, int(in_t or 0)), max(0, int(out_t or 0))
    msg_obj = payload.get("message")
    if isinstance(msg_obj, dict) and isinstance(msg_obj.get("usage"), dict):
        mu = msg_obj["usage"]
        if mu.get("input_tokens") is not None or mu.get("output_tokens") is not None:
            return max(0, int(mu.get("input_tokens") or 0)), max(
                0, int(mu.get("output_tokens") or 0)
            )
    um = payload.get("usageMetadata")
    if isinstance(um, dict):
        in_t = int(um.get("promptTokenCount") or 0)
        out_t = int(um.get("candidatesTokenCount") or 0) + int(um.get("thoughtsTokenCount") or 0)
        if out_t == 0 and um.get("totalTokenCount") is not None:
            out_t = max(0, int(um["totalTokenCount"]) - in_t)
        if in_t > 0 or out_t > 0:
            return max(0, in_t), max(0, out_t)
    if payload.get("prompt_eval_count") is not None or payload.get("eval_count") is not None:
        return max(0, int(payload.get("prompt_eval_count") or 0)), max(
            0, int(payload.get("eval_count") or 0)
        )
    return None


def estimate_tokens_deterministic(prompt_text: str, reply_text: str) -> tuple[int, int]:
    """Deterministic `max(1, len // 4)` fallback when provider streaming omits `usage`."""
    return max(1, len(prompt_text) // 4), max(1, len(reply_text) // 4)


def resolve_usage_with_fallback(
    *,
    prompt_text: str = "",
    messages: Sequence[dict[str, Any]] | None = None,
    reply_text: str = "",
    observed_input_tokens: int = 0,
    observed_output_tokens: int = 0,
    saw_provider_usage: bool = False,
) -> tuple[int, int, str]:
    """Return `(input_tokens, output_tokens, usage_source)` preferring provider `usage`."""
    p_txt = prompt_text or "\n".join(str(m.get("content") or "") for m in (messages or ()))
    est_in, est_out = estimate_tokens_deterministic(p_txt, reply_text)
    if saw_provider_usage and (observed_input_tokens > 0 or observed_output_tokens > 0):
        return (
            observed_input_tokens if observed_input_tokens > 0 else est_in,
            observed_output_tokens if observed_output_tokens > 0 else est_out,
            "provider",
        )
    return est_in, est_out, "estimated"


def _parse_optional_uuid(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(UUID(value.strip()))
    except (ValueError, TypeError, AttributeError):
        return None


async def persist_assistant_turn_ledger_entry(
    *,
    audit_ledger_sink: AuditLedgerSinkPort | None,
    user_id: str | None,
    user_email: str | None,
    user_display_name: str | None,
    workspace_id: str,
    turn_id: str,
    model_id: str,
    inference_tier: str | None = None,
    effort: str | None = None,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    usage_source: str = "estimated",
    trace_id: str | None = None,
    speed_mode: str | None = None,
    invoked_targets: tuple[str, ...] = (),
) -> str | None:
    """Persist `ASSISTANT_TURN_COMPLETED` idempotently into `audit_ledger`."""
    if audit_ledger_sink is None or not user_id:
        return None
    meta: dict[str, Any] = {
        "turn_id": turn_id,
        "workspace_slug": workspace_id,
        "usage_source": usage_source,
        "speed_mode": speed_mode or "SPEED_1_FAST",
    }
    if invoked_targets:
        meta["invoked_targets"] = list(invoked_targets)
        meta["tool_name"] = invoked_targets[0]
    entry = FinopsCostLedgerEntry(
        source_event_id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"assistant-turn:{turn_id}")),
        workspace_id=_parse_optional_uuid(workspace_id),
        scope_path=f"WORKSPACE/{workspace_id}" if workspace_id else "GLOBAL",
        actor_type="HUMAN",
        actor_id=user_id,
        actor_display_name=user_display_name,
        actor_email=user_email,
        event_type="ASSISTANT_TURN_COMPLETED",
        summary=f"Assistant turn completed ({model_id})",
        model_id=model_id,
        inference_tier=inference_tier,
        effort=effort,
        input_tokens=max(0, int(input_tokens)),
        output_tokens=max(0, int(output_tokens)),
        cost_source="INTERNAL_VERIFIED" if usage_source == "provider" else "ESTIMATED_SCALE",
        latency_ms=max(0, int(round(latency_ms))),
        trace_id=trace_id or get_current_trace_id(),
        metadata=meta,
    )
    try:
        return await audit_ledger_sink.record_entry(entry)
    except Exception as exc:
        logger.warning(
            "assistant_usage_ledger_persist_failed",
            turn_id=turn_id,
            error_type=type(exc).__name__,
        )
        return None
