"""Governed Assistant Tool Router (`Story 26.6b`, `AD-25`, `H-03`, `H-22`, `H-27..29`).

Implements `AssistantToolExecutorPort`:
- Dynamic per-turn authorized catalog assembly.
- Strict sequential execution pipeline per tool call:
  Step A (`PermissionBrokerService` passthrough + `READ_SOURCE` + scope/observer) ->
  Step B (Lock V5 + deterministic per-tool Human-Anchor guard + `HumanArbitrationRequested`) ->
  Step C (Idempotency deduplication `idem:{turn_id}:{iteration}:{tool_call_id}`) ->
  Step D (Timeout-capped sandboxed execution via `asyncio.wait_for`) ->
  Step E (Secret scrubber + `<untrusted_tool_output>` delimiting + `audit_ledger` + SSE events).
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from orcia_core.agents._assistant_tool_audit import (
    OutboxEnqueueCallback,
    build_tool_sse_events,
    enqueue_arbitration_outbox_event,
    record_tool_audit_ledger,
)
from orcia_core.agents._assistant_tool_catalog import build_authorized_tool_catalog
from orcia_core.agents._assistant_tool_execution import (
    McpToolRunnerCallback,
    OntologyLookupCallback,
    RagSearchCallback,
    SkillRunnerCallback,
    ToolDispatchDependencies,
    execute_with_timeout,
)
from orcia_core.agents._assistant_tool_guards import (
    evaluate_permission_broker_step,
    evaluate_v5_and_human_anchor_step,
)
from orcia_core.agents._assistant_tool_idempotency import (
    RedisToolIdempotencyStore,
    build_tool_idempotency_key,
)
from orcia_core.agents._assistant_tool_sanitization import wrap_untrusted_tool_output
from orcia_core.permissions.broker import PermissionBrokerService
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    AssistantToolExecutionRequest,
    AssistantToolExecutionResult,
    AssistantToolExecutorPort,
    AuthorizedToolDescriptor,
    ToolAuditEventType,
    ToolIdempotencyStorePort,
    ToolVerdict,
)
from orcia_core.ports.finops_telemetry import AuditLedgerSinkPort
from orcia_core.ports.surgical_explorer_port import SurgicalExplorerPort
from orcia_kernel.ports import SandboxPort


class GovernedAssistantToolRouter(AssistantToolExecutorPort):
    """Governed sequential tool router for Mon Assistant (`Speed 2` & `Speed 3`)."""

    def __init__(
        self,
        *,
        permission_broker: PermissionBrokerService | None = None,
        evaluator: MatrixPermissionEvaluator | None = None,
        surgical_explorer: SurgicalExplorerPort | None = None,
        sandbox_port: SandboxPort | None = None,
        audit_ledger_sink: AuditLedgerSinkPort | None = None,
        idempotency_store: ToolIdempotencyStorePort | None = None,
        rag_search_fn: RagSearchCallback | None = None,
        ontology_lookup_fn: OntologyLookupCallback | None = None,
        skill_runner_fn: SkillRunnerCallback | None = None,
        mcp_tool_runner_fn: McpToolRunnerCallback | None = None,
        outbox_enqueue_fn: OutboxEnqueueCallback | None = None,
        default_timeout_s: float = 10.0,
    ) -> None:
        self._permission_broker = permission_broker
        self._evaluator = evaluator
        self._audit_ledger_sink = audit_ledger_sink
        self._idempotency_store = idempotency_store or RedisToolIdempotencyStore()
        self._outbox_enqueue_fn = outbox_enqueue_fn
        self._dispatch_deps = ToolDispatchDependencies(
            surgical_explorer=surgical_explorer,
            sandbox_port=sandbox_port,
            rag_search_fn=rag_search_fn,
            ontology_lookup_fn=ontology_lookup_fn,
            skill_runner_fn=skill_runner_fn,
            mcp_tool_runner_fn=mcp_tool_runner_fn,
            default_timeout_s=default_timeout_s,
        )

    def build_authorized_catalog(
        self, ctx: AssistantToolCatalogContext
    ) -> tuple[AuthorizedToolDescriptor, ...]:
        """Assemble the workspace-authorized tool catalog for a single assistant turn."""
        return build_authorized_tool_catalog(ctx)

    async def execute_tool_call(
        self,
        request: AssistantToolExecutionRequest,
        *,
        catalog: Sequence[AuthorizedToolDescriptor],
    ) -> AssistantToolExecutionResult:
        """Route a tool request through Steps A -> B -> C -> D -> E."""
        t0 = time.perf_counter()
        descriptor = next((d for d in catalog if d.tool_name == request.tool_name), None)
        if descriptor is None:
            return await self._finalize_denied(
                request=request,
                t0=t0,
                verdict="DENIED",
                reason_code="ERR_TOOL_NOT_IN_AUTHORIZED_CATALOG",
                payload={
                    "error_code": "ERR_TOOL_NOT_IN_AUTHORIZED_CATALOG",
                    "detail": f"Tool '{request.tool_name}' is not in the authorized catalog.",
                },
            )

        broker_verdict = await evaluate_permission_broker_step(
            request=request,
            descriptor=descriptor,
            permission_broker=self._permission_broker,
            evaluator=self._evaluator,
        )
        if not broker_verdict.allowed:
            return await self._finalize_denied(
                request=request,
                t0=t0,
                verdict="DENIED",
                reason_code=broker_verdict.reason_code,
                payload={"error_code": broker_verdict.reason_code, "detail": broker_verdict.detail},
            )

        guard_verdict = evaluate_v5_and_human_anchor_step(request=request, descriptor=descriptor)
        if not guard_verdict.allowed:
            outbox_id = await enqueue_arbitration_outbox_event(
                outbox_enqueue_fn=self._outbox_enqueue_fn,
                event=guard_verdict.outbox_event,
            )
            return await self._finalize_denied(
                request=request,
                t0=t0,
                verdict="APPROVAL_REQUIRED" if guard_verdict.requires_approval else "DENIED",
                reason_code=guard_verdict.reason_code,
                payload={
                    "error_code": guard_verdict.reason_code,
                    "detail": guard_verdict.detail,
                    "approval_proposal": guard_verdict.approval_proposal,
                },
                approval_proposal=guard_verdict.approval_proposal,
                outbox_event_id=outbox_id,
            )

        idem_key = build_tool_idempotency_key(
            workspace_id=request.workspace_id,
            user_id=request.user_id,
            turn_id=request.turn_id,
            iteration=request.iteration,
            tool_call_id=request.tool_call_id,
        )
        cached = await self._idempotency_store.get_cached_result(idem_key)
        if cached is not None:
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            summary = str(cached.get("raw_scrubbed_summary") or "")
            return AssistantToolExecutionResult(
                tool_call_id=request.tool_call_id,
                tool_name=request.tool_name,
                verdict="DEDUPLICATED",
                delimited_output=str(cached.get("delimited_output") or ""),
                raw_scrubbed_summary=summary,
                audit_event_type="ASSISTANT_TOOL_INVOKED",
                audit_ledger_id=cached.get("audit_ledger_id"),
                deduplicated=True,
                latency_ms=latency_ms,
                cost_usd=0.0,
                sse_events=build_tool_sse_events(
                    request=request,
                    verdict="DEDUPLICATED",
                    summary=summary,
                    latency_ms=latency_ms,
                    deduplicated=True,
                ),
            )

        exec_status, raw_payload, _timed_out = await execute_with_timeout(
            descriptor=descriptor,
            request=request,
            deps=self._dispatch_deps,
        )
        verdict: ToolVerdict = (
            "TIMED_OUT"
            if exec_status == "TIMED_OUT"
            else ("ERROR" if exec_status == "ERROR" else "EXECUTED")
        )
        audit_type: ToolAuditEventType = (
            "ASSISTANT_TOOL_INVOKED" if verdict == "EXECUTED" else "ASSISTANT_TOOL_DENIED"
        )
        delimited, summary = wrap_untrusted_tool_output(
            tool_call_id=request.tool_call_id,
            tool_name=request.tool_name,
            payload=raw_payload,
        )
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        reason_code = (
            str(raw_payload.get("error_code") or "") if isinstance(raw_payload, dict) else ""
        )
        audit_id = await record_tool_audit_ledger(
            sink=self._audit_ledger_sink,
            request=request,
            event_type=audit_type,
            verdict=verdict,
            latency_ms=latency_ms,
            cost_usd=0.0,
            reason_code=reason_code,
        )
        if verdict == "EXECUTED":
            await self._idempotency_store.save_result(
                idem_key,
                {
                    "delimited_output": delimited,
                    "raw_scrubbed_summary": summary,
                    "audit_ledger_id": audit_id,
                },
            )
        return AssistantToolExecutionResult(
            tool_call_id=request.tool_call_id,
            tool_name=request.tool_name,
            verdict=verdict,
            delimited_output=delimited,
            raw_scrubbed_summary=summary,
            audit_event_type=audit_type,
            audit_ledger_id=audit_id,
            deduplicated=False,
            latency_ms=latency_ms,
            cost_usd=0.0,
            sse_events=build_tool_sse_events(
                request=request,
                verdict=verdict,
                summary=summary,
                latency_ms=latency_ms,
                reason_code=reason_code,
            ),
        )

    async def _finalize_denied(
        self,
        *,
        request: AssistantToolExecutionRequest,
        t0: float,
        verdict: ToolVerdict,
        reason_code: str,
        payload: dict[str, Any],
        approval_proposal: dict[str, Any] | None = None,
        outbox_event_id: str | None = None,
    ) -> AssistantToolExecutionResult:
        delimited, summary = wrap_untrusted_tool_output(
            tool_call_id=request.tool_call_id,
            tool_name=request.tool_name,
            payload=payload,
        )
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        audit_id = await record_tool_audit_ledger(
            sink=self._audit_ledger_sink,
            request=request,
            event_type="ASSISTANT_TOOL_DENIED",
            verdict=verdict,
            latency_ms=latency_ms,
            cost_usd=0.0,
            reason_code=reason_code,
        )
        return AssistantToolExecutionResult(
            tool_call_id=request.tool_call_id,
            tool_name=request.tool_name,
            verdict=verdict,
            delimited_output=delimited,
            raw_scrubbed_summary=summary,
            audit_event_type="ASSISTANT_TOOL_DENIED",
            audit_ledger_id=audit_id,
            outbox_event_id=outbox_event_id,
            deduplicated=False,
            latency_ms=latency_ms,
            cost_usd=0.0,
            approval_proposal=approval_proposal,
            sse_events=build_tool_sse_events(
                request=request,
                verdict=verdict,
                summary=summary,
                latency_ms=latency_ms,
                reason_code=reason_code,
                approval_proposal=approval_proposal,
            ),
        )


__all__ = ["GovernedAssistantToolRouter"]
