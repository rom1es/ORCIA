"""Governed MCP `assistant.ask` Bridge through `AssistantTurnEngine` (`D7`, `Story 26.7`)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import Request

from orcia_api.dependencies._assistant_guards import enforce_assistant_workspace_guard
from orcia_api.routers._assistant_context_assembly import (
    assemble_real_workspace_context_for_turn_async,
)
from orcia_api.routers.assistant_llm_bridge import (
    ensure_active_chat_model_if_live,
    resolve_configured_llm_endpoint,
    resolve_request_locale,
)
from orcia_api.schemas.mcp_test_bench import GovernedMcpInvokeRequest, GovernedMcpInvokeResponse
from orcia_core.audit_finops import (
    RemoteUsageSanitizer,
    SqlConnectorQuotaGuardService,
    extract_remote_usage_payload,
)
from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine
from orcia_core.orchestration.errors import ScopeAccessDeniedError, ValidationDomainError
from orcia_core.orchestration.remote_test_bench_and_mcp_exposure import (
    RemoteServiceTestBenchAndGovernedMcpService,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.ports.llm_streaming_port import LlmStreamingPort


async def invoke_mcp_assistant_ask_async(
    request: Request,
    *,
    workspace_slug: str,
    body: GovernedMcpInvokeRequest,
    user: UserIdentity,
    mcp_svc: RemoteServiceTestBenchAndGovernedMcpService,
    turn_engine: AssistantTurnEngine,
    llm_port: LlmStreamingPort,
    embedding_port: EmbeddingPort | None,
) -> tuple[UUID, str, int, int]:
    """Execute read-only governed Speed 1 `assistant.ask` enforcing all 7 MCP locks."""
    if not body.passthrough_identity.strip():
        raise ValidationDomainError(
            detail_override="Passthrough user identity is mandatory for MCP calls (AD-6)."
        )
    if "execute" not in set(body.caller_verbs):
        raise ScopeAccessDeniedError(
            detail_override="Caller lacks 'execute' permission for MCP assistant.ask."
        )
    await enforce_assistant_workspace_guard(
        request,
        user,
        workspace_slug,
        require_write=True,
    )
    await mcp_svc.verify_mcp_pat_for_workspace_async(
        raw_pat_token=body.raw_pat_token,
        workspace_slug=workspace_slug,
    )
    gov_view = await turn_engine.governance_service.get_governance_view_async(
        user,
        workspace_id=workspace_slug,
        locale=resolve_request_locale(request, None),
    )
    if not gov_view.workspace_settings.mcp_expose_assistant:
        raise ScopeAccessDeniedError(
            detail_override=f"Assistant MCP exposure is disabled for '{workspace_slug}'."
        )
    await ensure_active_chat_model_if_live(
        request,
        workspace_id=workspace_slug,
        speed_mode="SPEED_1_FAST",
    )
    locale = resolve_request_locale(request, None)
    hat = gov_view.user_preferences.default_hat or "ARCHITECT"
    turn_ctx = await assemble_real_workspace_context_for_turn_async(
        request,
        workspace_id=workspace_slug,
        user_id=user.id,
        hat=hat,
        user_prompt=body.prompt_text,
        user=user,
        embedding_port=embedding_port,
        locale=locale,
    )
    ep = await resolve_configured_llm_endpoint(request, workspace_id=workspace_slug)
    trace_id = str(getattr(getattr(request, "state", None), "trace_id", "") or "")
    ask_res = await turn_engine.execute_speed_1_read_only_async(
        user,
        workspace_id=workspace_slug,
        prompt_text=body.prompt_text,
        evidence_table=turn_ctx.evidence_table,
        ontology_concepts_summary=turn_ctx.ontology_summary,
        federated_evidence_summary=turn_ctx.federated_evidence_summary,
        endpoint=ep,
        llm_port=llm_port,
        requested_write_target_uri=body.requested_write_target_uri,
        assembled_5_layers_prompt=turn_ctx.assembled_5_layers_prompt,
        base_assembly_latency_ms=turn_ctx.assembly_latency_ms,
        locale=locale,
        trace_id=trace_id,
    )
    return (
        UUID(ask_res.invocation_id),
        ask_res.sanitized_response_text,
        ask_res.input_tokens,
        ask_res.output_tokens,
    )


async def dispatch_governed_mcp_invoke_async(
    request: Request,
    *,
    workspace_slug: str,
    body: GovernedMcpInvokeRequest,
    user: UserIdentity,
    mcp_svc: RemoteServiceTestBenchAndGovernedMcpService,
    quota_guard: SqlConnectorQuotaGuardService,
    sanitizer: RemoteUsageSanitizer,
    turn_engine: AssistantTurnEngine,
    llm_port: LlmStreamingPort,
    embedding_port: EmbeddingPort | None,
) -> GovernedMcpInvokeResponse:
    """Dispatch `assistant.ask` vs `agent.*` MCP invocations, enforcing FinOps sanitization."""
    is_assistant_ask = body.tool_name == "assistant.ask" or body.agent_slug == "assistant.ask"
    target_key = "assistant.ask" if is_assistant_ask else body.agent_slug
    connector_key = f"mcp:{workspace_slug}:{target_key}".lower()
    if is_assistant_ask:
        inv_id, reply_txt, in_tok, out_tok = await invoke_mcp_assistant_ask_async(
            request,
            workspace_slug=workspace_slug,
            body=body,
            user=user,
            mcp_svc=mcp_svc,
            turn_engine=turn_engine,
            llm_port=llm_port,
            embedding_port=embedding_port,
        )
        from orcia_api.locales._router_locale_messages import get_router_copy

        tool_name, sys_prompt, secrets, staged = "assistant.ask", None, [], []
        meta_in: dict[str, int | float] = {"prompt_tokens": in_tok, "completion_tokens": out_tok}
        badge_fr = get_router_copy().mcp_ide_badge
        actor_type: Literal["MCP_IDE_CLIENT"] = "MCP_IDE_CLIENT"
    else:
        res = await mcp_svc.invoke_governed_mcp_tool_async(
            raw_pat_token=body.raw_pat_token,
            workspace_slug=workspace_slug,
            agent_slug=body.agent_slug,
            caller_role=user.platform_role,
            caller_verbs=set(body.caller_verbs),
            passthrough_identity=body.passthrough_identity,
            prompt_text=body.prompt_text,
            requested_write_target_uri=body.requested_write_target_uri,
        )
        inv_id, reply_txt = res.invocation_id, res.sanitized_response_text
        tool_name, sys_prompt = res.tool_name, res.system_prompt_exposed
        secrets, staged = list(res.secret_refs_exposed), list(res.staged_actions)
        meta_in = dict(res.meta_usage)
        badge_fr, actor_type = res.history_badge_fr, res.audit_actor_type
    raw_usage = extract_remote_usage_payload({"_meta": {"usage": meta_in}})
    sanitized = sanitizer.sanitize(
        raw_usage,
        valuation_mode="NATIVE_TELEMETRY",
        fixed_cost_per_call_eur=0.0,
        fixed_cost_per_unit_eur=0.0,
        max_reported_cost_per_call_eur=5.0,
        connector_id=connector_key,
    )
    await quota_guard.record_call_usage(connector_key, sanitized)
    return GovernedMcpInvokeResponse(
        invocation_id=inv_id,
        tool_name=tool_name,
        workspace_slug=workspace_slug,
        passthrough_identity=body.passthrough_identity,
        sanitized_response_text=reply_txt,
        system_prompt_exposed=sys_prompt,
        secret_refs_exposed=secrets,
        staged_actions=staged,
        meta_usage={
            "prompt_tokens": sanitized.input_tokens,
            "completion_tokens": sanitized.output_tokens,
            "cost_eur": sanitized.cost_eur,
        },
        history_badge_fr=badge_fr,
        audit_actor_type=actor_type,
    )
