"""Epic 11 Story 11.1 Router — `Mes Espaces` 5 Sub-Tabs, Cascade, DNA Waivers & External Rebaser."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_workspace_governance_and_rebaser_service,
)
from orcia_api.routers._workspace_governance_helpers import (
    to_external_rebase_response,
    to_five_tabs_response,
    to_waiver_response,
    to_workspace_sources,
    validate_workspace_governance_access,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.workspace_governance import (
    ConfigureWorkspaceTabsRequest,
    ExceptionWaiverResponse,
    ExternalRebaseResponse,
    PilotWorkflowRunResponse,
    RebaseExternalArtifactEditsRequest,
    RegisterExceptionWaiverRequest,
    ResolveArtifactDestinationRequest,
    ResolvedArtifactDestinationResponse,
    RunPilotTicketToTechSpecRequest,
    WorkspaceFiveTabsStateResponse,
)
from orcia_core.orchestration.workspace_governance_and_rebaser import (
    DnaChainNode,
    WorkspaceGovernanceAndArtifactRoutingService,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["workspaces"],
    responses=PROBLEM_RESPONSES,
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
GovernanceServiceDep = Annotated[
    WorkspaceGovernanceAndArtifactRoutingService,
    Depends(get_workspace_governance_and_rebaser_service),
]


@router.get(
    "/{workspace_id}/five-tabs",
    response_model=WorkspaceFiveTabsStateResponse,
    summary="Get the 5 sub-tabs state for Mes Espaces (Story 11.1)",
)
async def get_workspace_five_tabs(
    workspace_id: str,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    workspace_slug: str | None = Query(default=None),
    pending_glossary_candidates_count: int = Query(default=0, ge=0, le=100),
) -> WorkspaceFiveTabsStateResponse:
    """Return the consolidated state for the 5 sub-tabs of `Mes Espaces`."""
    ws_uuid = await validate_workspace_governance_access(
        request, user, workspace_id, require_write=False
    )
    resolved_slug = (workspace_slug or "").strip()
    if not resolved_slug:
        auth_svc = get_auth_service(request)
        ws = auth_svc.evaluator.get_workspace(str(ws_uuid))
        resolved_slug = ws.slug if ws is not None else str(ws_uuid)
    state = await svc.get_workspace_five_tabs_state_async(
        workspace_id=ws_uuid,
        workspace_slug=resolved_slug,
        pending_glossary_candidates_count=pending_glossary_candidates_count,
    )
    return to_five_tabs_response(state)


@router.put(
    "/{workspace_id}/five-tabs",
    response_model=WorkspaceFiveTabsStateResponse,
    summary="Configure workspace 5 sub-tabs, sources, and default destination (Story 11.1)",
)
async def configure_workspace_five_tabs(
    workspace_id: str,
    body: ConfigureWorkspaceTabsRequest,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> WorkspaceFiveTabsStateResponse:
    """Configure workspace sources (`REFERENCE` vs `ACTIVE`), access modes, and default target."""
    ws_uuid = await validate_workspace_governance_access(
        request, user, workspace_id, require_write=True
    )
    svc.configure_workspace_tabs(
        workspace_id=ws_uuid,
        workspace_slug=body.workspace_slug,
        actor_role=user.platform_role,
        default_artifact_destination_uri=body.default_artifact_destination_uri,
        local_root_realpath=body.local_root_realpath,
        sources=to_workspace_sources(body.sources),
        pending_glossary_candidates_count=body.pending_glossary_candidates_count,
    )
    state = await svc.get_workspace_five_tabs_state_async(
        workspace_id=ws_uuid,
        workspace_slug=body.workspace_slug,
        pending_glossary_candidates_count=body.pending_glossary_candidates_count,
    )
    return to_five_tabs_response(state)


@router.get(
    "/{workspace_id}/exception-waivers",
    response_model=list[ExceptionWaiverResponse],
    summary="List persisted exception waivers for a workspace (PG18 `workspace_exception_waivers`)",
)
async def list_workspace_exception_waivers(
    workspace_id: str,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    active_only: bool = Query(default=False),
) -> list[ExceptionWaiverResponse]:
    """Return persisted exception waivers for the workspace from PostgreSQL 18."""
    ws_uuid = await validate_workspace_governance_access(
        request, user, workspace_id, require_write=False
    )
    waivers = await svc.list_exception_waivers_async(
        workspace_id=ws_uuid,
        active_only=active_only,
    )
    return [to_waiver_response(w) for w in waivers]


@router.post(
    "/{workspace_id}/exception-waivers",
    response_model=ExceptionWaiverResponse,
    summary="Register an exception waiver governed by the causal DNA chain (Verrou V1)",
)
async def register_workspace_exception_waiver(
    workspace_id: str,
    body: RegisterExceptionWaiverRequest,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> ExceptionWaiverResponse:
    """Persist an exception waiver or reject `1_ENTERPRISE` inviolable directives with HTTP 403."""
    ws_uuid = await validate_workspace_governance_access(
        request, user, workspace_id, require_write=True
    )
    waiver = await svc.register_exception_waiver_async(
        workspace_id=ws_uuid,
        source_uri=body.source_uri,
        source_sha256=body.source_sha256,
        conflict_rule_id=body.conflict_rule_id,
        norm_level=body.norm_level,
        dna_chain=[
            DnaChainNode(
                node_key=n.node_key,
                stereotype=n.stereotype,
                level=n.level,
                inviolable=n.inviolable,
            )
            for n in body.dna_chain
        ],
        approved_by_user_id=UUID(user.id),
        approved_by_role=user.platform_role,
        reason=body.reason,
        ttl_days=body.ttl_days,
        approved_by_email=user.email,
    )
    return to_waiver_response(waiver)


@router.post(
    "/{workspace_id}/artifacts/resolve-destination",
    response_model=ResolvedArtifactDestinationResponse,
    summary="Resolve 4-level artifact destination cascade with local:// path confinement",
)
async def resolve_workspace_artifact_destination(
    workspace_id: UUID,
    body: ResolveArtifactDestinationRequest,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> ResolvedArtifactDestinationResponse:
    """Resolve the 4-level artifact destination cascade (`Story 11.1`)."""
    await validate_workspace_governance_access(request, user, str(workspace_id), require_write=True)
    res = svc.resolve_artifact_destination(
        workspace_id=workspace_id,
        workspace_slug=body.workspace_slug,
        artifact_type=body.artifact_type,
        artifact_slug=body.artifact_slug,
        version=body.version,
        content_bytes=body.content_markdown.encode("utf-8"),
        run_override_uri=body.run_override_uri,
        workflow_step_target_uri=body.workflow_step_target_uri,
        workspace_default_uri=body.workspace_default_uri,
        local_root_realpath=body.local_root_realpath,
    )
    return ResolvedArtifactDestinationResponse(
        selected_level=res.selected_level,
        resolved_uri=res.resolved_uri,
        cas_storage_path=res.cas_storage_path,
        canonical_alias_uri=res.canonical_alias_uri,
        staged_for_gate_publication=res.staged_for_gate_publication,
    )


@router.post(
    "/{workspace_id}/artifacts/external-rebase",
    response_model=ExternalRebaseResponse,
    summary="Detect external SHA-256 divergence and lock human-amended sections (Verrou V2)",
)
async def rebase_external_artifact(
    workspace_id: UUID,
    body: RebaseExternalArtifactEditsRequest,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> ExternalRebaseResponse:
    """Run `ExternalEditRebaser` on an externally edited artifact (`Verrou V2`)."""
    await validate_workspace_governance_access(request, user, str(workspace_id), require_write=True)
    res = svc.rebase_external_artifact_edits(
        artifact_uri=body.artifact_uri,
        current_version=body.current_version,
        orcia_markdown=body.orcia_markdown,
        external_markdown=body.external_markdown,
        step_memlog_entries=body.step_memlog_entries,
    )
    return to_external_rebase_response(res)


@router.post(
    "/{workspace_id}/workflows/ticket-to-tech-spec",
    response_model=PilotWorkflowRunResponse,
    summary="Run pilot workflow orcia://pack-sdlc/workflows/ticket-to-tech-spec (Verrou V3)",
)
async def run_pilot_ticket_to_tech_spec(
    workspace_id: UUID,
    body: RunPilotTicketToTechSpecRequest,
    request: Request,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> PilotWorkflowRunResponse:
    """Execute the 3-step pilot workflow `orcia://pack-sdlc/workflows/ticket-to-tech-spec`."""
    await validate_workspace_governance_access(request, user, str(workspace_id), require_write=True)
    res = svc.run_pilot_ticket_to_tech_spec_workflow(
        workspace_id=workspace_id,
        workspace_slug=body.workspace_slug,
        ticket_key=body.ticket_key,
        ticket_summary=body.ticket_summary,
        workspace_sovereignty_tier=body.workspace_sovereignty_tier,
        generator_model_family=body.generator_model_family,
        judge_model_family=body.judge_model_family,
        judge_sovereignty_tier=body.judge_sovereignty_tier,
        run_override_uri=body.run_override_uri,
    )
    return PilotWorkflowRunResponse(
        workflow_uri=res.workflow_uri,
        ticket_key=res.ticket_key,
        executed_steps=list(res.executed_steps),
        generator_model_family=res.generator_model_family,
        judge_model_family=res.judge_model_family,
        judge_sovereignty_tier=res.judge_sovereignty_tier,
        requires_human_anchor_card=res.requires_human_anchor_card,
        destination=ResolvedArtifactDestinationResponse(
            selected_level=res.destination.selected_level,
            resolved_uri=res.destination.resolved_uri,
            cas_storage_path=res.destination.cas_storage_path,
            canonical_alias_uri=res.destination.canonical_alias_uri,
            staged_for_gate_publication=res.destination.staged_for_gate_publication,
        ),
        staged_transitions=list(res.staged_transitions),
    )
