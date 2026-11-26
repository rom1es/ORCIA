"""Epic 11 Story 11.3 / 24.3 Router — 4-Step Test Bench (`🔌`) & Governed MCP Server."""

from __future__ import annotations

from dataclasses import replace
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import (
    get_assistant_turn_engine,
    get_audit_ledger_service,
    get_connector_quota_guard_service,
    get_llm_streaming_port,
    get_optional_embedding_port,
    get_remote_test_bench_and_mcp_service,
    get_remote_usage_sanitizer,
)
from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.routers._agents_lifecycle_guards import enforce_active_agents_for_refs
from orcia_api.routers._mcp_assistant_ask_bridge import dispatch_governed_mcp_invoke_async
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.mcp_test_bench import (
    ConfigureAgentMcpExposureRequest,
    DiscoveredRemoteCapabilitySchema,
    ExposedMcpAgentResponse,
    GovernedMcpInvokeRequest,
    GovernedMcpInvokeResponse,
    McpExposureStateResponse,
    RemoteServiceTestAndDiscoverRequest,
    RemoteServiceTestAndDiscoverResponse,
    TestBenchStepResultSchema,
)
from orcia_core.audit_finops import (
    RemoteUsageSanitizer,
    SqlAuditLedgerService,
    SqlConnectorQuotaGuardService,
    map_domain_event_to_ledger_entry,
)
from orcia_core.kernel.events import AdminConnectionTested
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration.assistant_turn_engine import AssistantTurnEngine
from orcia_core.orchestration.remote_test_bench_and_mcp_exposure import (
    RemoteServiceTestBenchAndGovernedMcpService,
)
from orcia_core.permissions.errors import ConnectorCircuitOpenError
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.ports.llm_streaming_port import LlmStreamingPort

router = APIRouter(
    prefix="/api/v1",
    tags=["mcp-and-connectors"],
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
TestBenchMcpServiceDep = Annotated[
    RemoteServiceTestBenchAndGovernedMcpService,
    Depends(get_remote_test_bench_and_mcp_service),
]
AuditLedgerServiceDep = Annotated[
    SqlAuditLedgerService,
    Depends(get_audit_ledger_service),
]
QuotaGuardDep = Annotated[
    SqlConnectorQuotaGuardService,
    Depends(get_connector_quota_guard_service),
]
UsageSanitizerDep = Annotated[
    RemoteUsageSanitizer,
    Depends(get_remote_usage_sanitizer),
]
TurnEngineDep = Annotated[AssistantTurnEngine, Depends(get_assistant_turn_engine)]
LlmPortDep = Annotated[LlmStreamingPort, Depends(get_llm_streaming_port)]
OptionalEmbeddingDep = Annotated[EmbeddingPort | None, Depends(get_optional_embedding_port)]


@router.post(
    "/settings/connectors/test-and-discover",
    response_model=RemoteServiceTestAndDiscoverResponse,
    summary="Run the 4-Step Hot Test Bench & Contract Discovery (Story 11.3)",
)
async def test_and_discover_connector(
    request: Request,
    body: RemoteServiceTestAndDiscoverRequest,
    user: CurrentUserDep,
    svc: TestBenchMcpServiceDep,
    audit_svc: AuditLedgerServiceDep,
) -> RemoteServiceTestAndDiscoverResponse:
    """Execute the 4-step Hot Test Bench (`🔌`) and record `ADMIN_CONNECTION_TEST` audit."""
    res = svc.test_and_discover_remote_service(
        actor_role=user.platform_role,
        protocol=body.protocol,
        endpoint_url=body.endpoint_url,
        identity_mode=body.identity_mode,
        has_user_personal_token=body.has_user_personal_token,
        secret_ref_valid=body.secret_ref_valid,
        allow_private_network=body.allow_private_network,
        raw_tool_names=body.raw_tool_names,
        simulated_dry_run_elapsed_ms=body.simulated_dry_run_elapsed_ms,
        simulated_dry_run_bytes=body.simulated_dry_run_bytes,
    )
    status_str = "SUCCESS" if res.can_activate else "FAILURE"
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    rc = get_router_copy()
    status_label = rc.connector_status_on if res.can_activate else rc.connector_status_off
    evt = AdminConnectionTested.create(
        actor_id=user.id,
        target_type="MCP_CONNECTOR",
        target_id=body.endpoint_url,
        protocol=body.protocol,
        test_status=status_str,
        latency_ms=int(body.simulated_dry_run_elapsed_ms or 0),
        detail=rc.connector_test_detail.format(protocol=body.protocol, status_label=status_label),
        trace_id=trace_id,
        metadata={
            "actor_type": "ADMIN_CONNECTION_TEST",
            "actor_display_name": getattr(user, "display_name", None),
            "actor_email": getattr(user, "email", None),
            "can_activate": res.can_activate,
            "steps_count": len(res.steps),
            "tools_count": len(res.discovered_capabilities),
        },
    )
    entry = replace(map_domain_event_to_ledger_entry(evt), event_type="ADMIN_CONNECTION_TEST")
    await audit_svc.record_entry(entry)

    return RemoteServiceTestAndDiscoverResponse(
        protocol=res.protocol,
        endpoint_url=res.endpoint_url,
        identity_mode=res.identity_mode,
        steps=[
            TestBenchStepResultSchema(
                step_number=s.step_number,
                step_code=s.step_code,
                status=s.status,
                detail_fr=s.detail_fr,
            )
            for s in res.steps
        ],
        discovered_capabilities=[
            DiscoveredRemoteCapabilitySchema(
                tool_name=c.tool_name,
                description=c.description,
                qualification=c.qualification,
                badge_fr=c.badge_fr,
            )
            for c in res.discovered_capabilities
        ],
        can_activate=res.can_activate,
        dry_run_audit_actor_type=res.dry_run_audit_actor_type,
        dry_run_run_id=res.dry_run_run_id,
        finops_meta_usage=res.finops_meta_usage,
    )


@router.get(
    "/mcp/exposure",
    response_model=McpExposureStateResponse,
    summary="Read persisted MCP exposure state for a workspace from PG18 (Story 24.3)",
)
async def get_mcp_exposure_state(
    user: CurrentUserDep,
    svc: TestBenchMcpServiceDep,
    workspace_slug: str = Query(default="global", min_length=1, max_length=128),
) -> McpExposureStateResponse:
    """Return persisted governed MCP exposure entries and tools for `workspace_slug`."""
    _ = user
    specs = await svc.list_exposed_agents_async(workspace_slug=workspace_slug)
    tools = list(
        await svc.list_governed_mcp_tools_async(
            workspace_slug=workspace_slug,
            caller_verbs={"execute"},
        )
    )
    agent_items = [
        ExposedMcpAgentResponse(
            agent_slug=s.agent_slug,
            workspace_slug=s.workspace_slug,
            display_name=s.display_name,
            mcp_exposed=s.mcp_exposed,
            regime=s.regime,
            human_authored_required=s.human_authored_required,
            exposed_tools=tools if s.mcp_exposed else [],
        )
        for s in specs
    ]
    return McpExposureStateResponse(
        workspace_slug=workspace_slug,
        agents=agent_items,
        exposed_tools=tools,
        any_exposed=any(s.mcp_exposed for s in specs),
    )


@router.put(
    "/mcp/exposure",
    response_model=ExposedMcpAgentResponse,
    summary="Configure MCP exposure on a local Agent or Workspace Assistant (Story 11.3)",
)
async def configure_mcp_exposure(
    request: Request,
    body: ConfigureAgentMcpExposureRequest,
    user: CurrentUserDep,
    svc: TestBenchMcpServiceDep,
) -> ExposedMcpAgentResponse:
    """Toggle `🔌 Exposer en MCP`, persist in PG18, and return dynamic `tools/list`."""
    if body.mcp_exposed:
        await enforce_active_agents_for_refs(
            request, [body.agent_slug], instance=str(request.url.path)
        )
    if body.pat_token_to_register:
        await svc.register_pat_mcp_token_async(
            raw_pat_token=body.pat_token_to_register,
            allowed_workspace_slugs={body.workspace_slug},
        )
    spec = await svc.configure_agent_mcp_exposure_async(
        actor_role=user.platform_role,
        workspace_slug=body.workspace_slug,
        agent_slug=body.agent_slug,
        display_name=body.display_name,
        mcp_exposed=body.mcp_exposed,
        regime=body.regime,
        human_authored_required=body.human_authored_required,
        updated_by=user.id,
    )
    tools = await svc.list_governed_mcp_tools_async(
        workspace_slug=body.workspace_slug,
        caller_verbs={"execute"},
    )
    return ExposedMcpAgentResponse(
        agent_slug=spec.agent_slug,
        workspace_slug=spec.workspace_slug,
        display_name=spec.display_name,
        mcp_exposed=spec.mcp_exposed,
        regime=spec.regime,
        human_authored_required=spec.human_authored_required,
        exposed_tools=list(tools),
    )


@router.post(
    "/mcp/spaces/{workspace_slug}/invoke",
    response_model=GovernedMcpInvokeResponse,
    summary="Invoke an exposed MCP agent/assistant under the 7 Hardware Security Locks (M.4)",
)
async def invoke_governed_mcp_agent(
    workspace_slug: str,
    body: GovernedMcpInvokeRequest,
    request: Request,
    user: CurrentUserDep,
    svc: TestBenchMcpServiceDep,
    quota_guard: QuotaGuardDep,
    sanitizer: UsageSanitizerDep,
    turn_engine: TurnEngineDep,
    llm_port: LlmPortDep,
    _embedding_port: OptionalEmbeddingDep,
) -> GovernedMcpInvokeResponse:
    """Invoke an exposed MCP agent or `assistant.ask` enforcing the 7 hardware locks."""
    is_assistant_ask = body.tool_name == "assistant.ask" or body.agent_slug == "assistant.ask"
    target_key = "assistant.ask" if is_assistant_ask else body.agent_slug
    connector_key = f"mcp:{workspace_slug}:{target_key}".lower()
    decision = await quota_guard.evaluate_call_allowed(connector_key, "WORKSPACE", None)
    if not decision.is_allowed or decision.circuit_state == "CIRCUIT_OPEN":
        raise ConnectorCircuitOpenError(detail_override=decision.reason)
    return await dispatch_governed_mcp_invoke_async(
        request,
        workspace_slug=workspace_slug,
        body=body,
        user=user,
        mcp_svc=svc,
        quota_guard=quota_guard,
        sanitizer=sanitizer,
        turn_engine=turn_engine,
        llm_port=llm_port,
        embedding_port=_embedding_port,
    )
