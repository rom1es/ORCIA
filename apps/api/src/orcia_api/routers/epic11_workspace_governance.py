"""Epic 11 Story 11.1 Router — `Mes Espaces` 5 Sub-Tabs, Cascade, DNA Waivers & External Rebaser."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from orcia_api.dependencies_epic11 import get_workspace_governance_and_rebaser_service
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.epic11_governance import (
    ConfigureWorkspaceTabsRequest,
    DnaChainNodeSchema,
    ExceptionWaiverResponse,
    ExternalRebaseResponse,
    PilotWorkflowRunResponse,
    RebasedSectionChunkSchema,
    RebaseExternalArtifactEditsRequest,
    RegisterExceptionWaiverRequest,
    ResolveArtifactDestinationRequest,
    ResolvedArtifactDestinationResponse,
    RunPilotTicketToTechSpecRequest,
    WorkspaceFiveTabsStateResponse,
    WorkspaceSourceSummarySchema,
)
from orcia_core.orchestration.workspace_governance_and_rebaser import (
    DnaChainNode,
    ExceptionWaiverRecord,
    WorkspaceGovernanceAndArtifactRoutingService,
    WorkspaceSourceSummary,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter(
    prefix="/api/v1/workspaces",
    tags=["workspaces"],
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
GovernanceServiceDep = Annotated[
    WorkspaceGovernanceAndArtifactRoutingService,
    Depends(get_workspace_governance_and_rebaser_service),
]


def _to_waiver_response(waiver: ExceptionWaiverRecord) -> ExceptionWaiverResponse:
    return ExceptionWaiverResponse(
        waiver_id=waiver.waiver_id,
        workspace_id=waiver.workspace_id,
        source_uri=waiver.source_uri,
        source_sha256=waiver.source_sha256,
        conflict_rule_id=waiver.conflict_rule_id,
        norm_level=waiver.norm_level,
        dna_chain=[
            DnaChainNodeSchema(
                node_key=n.node_key,
                stereotype=n.stereotype,
                level=n.level,
                inviolable=n.inviolable,
            )
            for n in waiver.dna_chain
        ],
        approved_by_user_id=waiver.approved_by_user_id,
        approved_by_role=waiver.approved_by_role,
        reason=waiver.reason,
        status=waiver.status,
        expires_at=waiver.expires_at,
        created_at=waiver.created_at,
    )


@router.get(
    "/{workspace_id}/five-tabs",
    response_model=WorkspaceFiveTabsStateResponse,
    summary="Get the 5 sub-tabs state for Mes Espaces (Story 11.1)",
)
def get_workspace_five_tabs(
    workspace_id: UUID,
    _user: CurrentUserDep,
    svc: GovernanceServiceDep,
    workspace_slug: str = Query(default="default-ws"),
    pending_glossary_candidates_count: int = Query(default=0, ge=0, le=100),
) -> WorkspaceFiveTabsStateResponse:
    """Return the consolidated state for the 5 sub-tabs of `Mes Espaces`."""
    state = svc.get_workspace_five_tabs_state(
        workspace_id=workspace_id,
        workspace_slug=workspace_slug,
        pending_glossary_candidates_count=pending_glossary_candidates_count,
    )
    return WorkspaceFiveTabsStateResponse(
        workspace_id=state.workspace_id,
        workspace_slug=state.workspace_slug,
        tabs=list(state.tabs),
        default_artifact_destination_uri=state.default_artifact_destination_uri,
        local_root_realpath=state.local_root_realpath,
        sources=[
            WorkspaceSourceSummarySchema(
                source_id=s.source_id,
                uri=s.uri,
                title=s.title,
                authority_role=s.authority_role,
                access_mode=s.access_mode,
                freshness_status=s.freshness_status,
            )
            for s in state.sources
        ],
        active_waivers=[_to_waiver_response(w) for w in state.active_waivers],
        pending_glossary_candidates_count=state.pending_glossary_candidates_count,
    )


@router.put(
    "/{workspace_id}/five-tabs",
    response_model=WorkspaceFiveTabsStateResponse,
    summary="Configure workspace 5 sub-tabs, sources, and default destination (Story 11.1)",
)
def configure_workspace_five_tabs(
    workspace_id: UUID,
    body: ConfigureWorkspaceTabsRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> WorkspaceFiveTabsStateResponse:
    """Configure workspace sources (`REFERENCE` vs `ACTIVE`), access modes, and default target."""
    state = svc.configure_workspace_tabs(
        workspace_id=workspace_id,
        workspace_slug=body.workspace_slug,
        actor_role=user.platform_role,
        default_artifact_destination_uri=body.default_artifact_destination_uri,
        local_root_realpath=body.local_root_realpath,
        sources=[
            WorkspaceSourceSummary(
                source_id=s.source_id,
                uri=s.uri,
                title=s.title,
                authority_role=s.authority_role,
                access_mode=s.access_mode,
                freshness_status=s.freshness_status,
            )
            for s in body.sources
        ],
        pending_glossary_candidates_count=body.pending_glossary_candidates_count,
    )
    return WorkspaceFiveTabsStateResponse(
        workspace_id=state.workspace_id,
        workspace_slug=state.workspace_slug,
        tabs=list(state.tabs),
        default_artifact_destination_uri=state.default_artifact_destination_uri,
        local_root_realpath=state.local_root_realpath,
        sources=[
            WorkspaceSourceSummarySchema(
                source_id=s.source_id,
                uri=s.uri,
                title=s.title,
                authority_role=s.authority_role,
                access_mode=s.access_mode,
                freshness_status=s.freshness_status,
            )
            for s in state.sources
        ],
        active_waivers=[_to_waiver_response(w) for w in state.active_waivers],
        pending_glossary_candidates_count=state.pending_glossary_candidates_count,
    )


@router.post(
    "/{workspace_id}/exception-waivers",
    response_model=ExceptionWaiverResponse,
    summary="Register an exception waiver governed by the causal DNA chain (Verrou V1)",
)
def register_workspace_exception_waiver(
    workspace_id: UUID,
    body: RegisterExceptionWaiverRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> ExceptionWaiverResponse:
    """Persist an exception waiver or reject `1_ENTERPRISE` inviolable directives with HTTP 403."""
    waiver = svc.register_exception_waiver(
        workspace_id=workspace_id,
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
    )
    return _to_waiver_response(waiver)


@router.post(
    "/{workspace_id}/artifacts/resolve-destination",
    response_model=ResolvedArtifactDestinationResponse,
    summary="Resolve 4-level artifact destination cascade with local:// path confinement",
)
def resolve_workspace_artifact_destination(
    workspace_id: UUID,
    body: ResolveArtifactDestinationRequest,
    _user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> ResolvedArtifactDestinationResponse:
    """Resolve the 4-level artifact destination cascade (`Story 11.1`)."""
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
def rebase_external_artifact(
    workspace_id: UUID,
    body: RebaseExternalArtifactEditsRequest,
    _user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> ExternalRebaseResponse:
    """Run `ExternalEditRebaser` on an externally edited artifact (`Verrou V2`)."""
    _ = workspace_id
    res = svc.rebase_external_artifact_edits(
        artifact_uri=body.artifact_uri,
        current_version=body.current_version,
        orcia_markdown=body.orcia_markdown,
        external_markdown=body.external_markdown,
        step_memlog_entries=body.step_memlog_entries,
    )
    return ExternalRebaseResponse(
        artifact_uri=res.artifact_uri,
        previous_version=res.previous_version,
        imported_version=res.imported_version,
        previous_sha256=res.previous_sha256,
        external_sha256=res.external_sha256,
        divergence_detected=res.divergence_detected,
        chunks=[
            RebasedSectionChunkSchema(
                chunk_key=c.chunk_key,
                section_title=c.section_title,
                content_markdown=c.content_markdown,
                status=c.status,
                locked_against_agent_overwrite=c.locked_against_agent_overwrite,
            )
            for c in res.chunks
        ],
        step_memlog_annotations=list(res.step_memlog_annotations),
    )


@router.post(
    "/{workspace_id}/workflows/ticket-to-tech-spec",
    response_model=PilotWorkflowRunResponse,
    summary="Run pilot workflow orcia://pack-sdlc/workflows/ticket-to-tech-spec (Verrou V3)",
)
def run_pilot_ticket_to_tech_spec(
    workspace_id: UUID,
    body: RunPilotTicketToTechSpecRequest,
    _user: CurrentUserDep,
    svc: GovernanceServiceDep,
) -> PilotWorkflowRunResponse:
    """Execute the 3-step pilot workflow `orcia://pack-sdlc/workflows/ticket-to-tech-spec`."""
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
