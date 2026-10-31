"""Epic 11 Story 11.3 Router — 4-Step Test Bench (`🔌`) & Governed MCP Server (`/api/v1/mcp`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from orcia_api.dependencies_epic11 import get_remote_test_bench_and_mcp_service
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.epic11_mcp_test_bench import (
    ConfigureAgentMcpExposureRequest,
    DiscoveredRemoteCapabilitySchema,
    ExposedMcpAgentResponse,
    GovernedMcpInvokeRequest,
    GovernedMcpInvokeResponse,
    RemoteServiceTestAndDiscoverRequest,
    RemoteServiceTestAndDiscoverResponse,
    TestBenchStepResultSchema,
)
from orcia_core.orchestration.remote_test_bench_and_mcp_exposure import (
    RemoteServiceTestBenchAndGovernedMcpService,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter(
    prefix="/api/v1",
    tags=["mcp-and-connectors"],
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
TestBenchMcpServiceDep = Annotated[
    RemoteServiceTestBenchAndGovernedMcpService,
    Depends(get_remote_test_bench_and_mcp_service),
]


@router.post(
    "/settings/connectors/test-and-discover",
    response_model=RemoteServiceTestAndDiscoverResponse,
    summary="Run the 4-Step Hot Test Bench & Contract Discovery (Story 11.3)",
)
def test_and_discover_connector(
    body: RemoteServiceTestAndDiscoverRequest,
    user: CurrentUserDep,
    svc: TestBenchMcpServiceDep,
) -> RemoteServiceTestAndDiscoverResponse:
    """Execute the 4-step Hot Test Bench (`🔌`) for MCP/OpenAPI/A2A/WASM services."""
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


@router.put(
    "/mcp/exposure",
    response_model=ExposedMcpAgentResponse,
    summary="Configure MCP exposure on a local Agent or Workspace Assistant (Story 11.3)",
)
def configure_mcp_exposure(
    body: ConfigureAgentMcpExposureRequest,
    user: CurrentUserDep,
    svc: TestBenchMcpServiceDep,
) -> ExposedMcpAgentResponse:
    """Toggle `🔌 Exposer en MCP` and return the dynamic `tools/list`."""
    if body.pat_token_to_register:
        svc.register_pat_mcp_token(
            raw_pat_token=body.pat_token_to_register,
            allowed_workspace_slugs={body.workspace_slug},
        )
    spec = svc.configure_agent_mcp_exposure(
        actor_role=user.platform_role,
        workspace_slug=body.workspace_slug,
        agent_slug=body.agent_slug,
        display_name=body.display_name,
        mcp_exposed=body.mcp_exposed,
        regime=body.regime,
        human_authored_required=body.human_authored_required,
    )
    tools = svc.list_governed_mcp_tools(
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
def invoke_governed_mcp_agent(
    workspace_slug: str,
    body: GovernedMcpInvokeRequest,
    user: CurrentUserDep,
    svc: TestBenchMcpServiceDep,
) -> GovernedMcpInvokeResponse:
    """Invoke an exposed MCP agent enforcing the 7 hardware locks (`execute != read`, `AD-3`)."""
    res = svc.invoke_governed_mcp_tool(
        raw_pat_token=body.raw_pat_token,
        workspace_slug=workspace_slug,
        agent_slug=body.agent_slug,
        caller_role=user.platform_role,
        caller_verbs=set(body.caller_verbs),
        passthrough_identity=body.passthrough_identity,
        prompt_text=body.prompt_text,
        requested_write_target_uri=body.requested_write_target_uri,
    )
    return GovernedMcpInvokeResponse(
        invocation_id=res.invocation_id,
        tool_name=res.tool_name,
        workspace_slug=res.workspace_slug,
        passthrough_identity=res.passthrough_identity,
        sanitized_response_text=res.sanitized_response_text,
        system_prompt_exposed=res.system_prompt_exposed,
        secret_refs_exposed=list(res.secret_refs_exposed),
        staged_actions=list(res.staged_actions),
        meta_usage=res.meta_usage,
        history_badge_fr=res.history_badge_fr,
        audit_actor_type=res.audit_actor_type,
    )
