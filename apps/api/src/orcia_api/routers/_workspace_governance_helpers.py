"""Access validation and response serializers for `workspace_governance` router."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import (
    sync_evaluator_topology_from_pg,
    validate_uuid,
)
from orcia_api.schemas.workspace_governance import (
    DnaChainNodeSchema,
    ExceptionWaiverResponse,
    ExternalRebaseResponse,
    RebasedSectionChunkSchema,
    WorkspaceFiveTabsStateResponse,
    WorkspaceSourceSummarySchema,
)
from orcia_core.orchestration.workspace_governance_and_rebaser import (
    ExceptionWaiverRecord,
    WorkspaceFiveTabsState,
    WorkspaceSourceSummary,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity


async def validate_workspace_governance_access(
    request: Request,
    user: UserIdentity,
    workspace_id_raw: str,
    *,
    require_write: bool = False,
) -> UUID:
    """Validate workspace UUID, observer mode, and explicit `resolve_workspace_access`."""
    ws_id_str = validate_uuid(workspace_id_raw, "workspace_id")
    ws_uuid = UUID(ws_id_str)
    if require_write:
        enforce_observer_headers_guard(request, user)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    ws = auth_svc.evaluator.get_workspace(ws_id_str)
    if ws is None:
        await sync_evaluator_topology_from_pg(request, auth_svc, force=True)
        ws = auth_svc.evaluator.get_workspace(ws_id_str)
    if ws is None:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    access = auth_svc.evaluator.resolve_workspace_access(user, ws.id)
    if access is None:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    if require_write and access.access_mode == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(instance=str(request.url.path))
    return ws_uuid


def to_waiver_response(waiver: ExceptionWaiverRecord) -> ExceptionWaiverResponse:
    """Serialize an `ExceptionWaiverRecord` into OpenAPI response model."""
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


def to_five_tabs_response(state: WorkspaceFiveTabsState) -> WorkspaceFiveTabsStateResponse:
    """Serialize `WorkspaceFiveTabsState` into OpenAPI response model."""
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
        active_waivers=[to_waiver_response(w) for w in state.active_waivers],
        pending_glossary_candidates_count=state.pending_glossary_candidates_count,
    )


def to_workspace_sources(items: list[WorkspaceSourceSummarySchema]) -> list[WorkspaceSourceSummary]:
    """Convert request source schemas into domain `WorkspaceSourceSummary` models."""
    return [
        WorkspaceSourceSummary(
            source_id=s.source_id,
            uri=s.uri,
            title=s.title,
            authority_role=s.authority_role,
            access_mode=s.access_mode,
            freshness_status=s.freshness_status,
        )
        for s in items
    ]


def to_external_rebase_response(res: Any) -> ExternalRebaseResponse:
    """Serialize `ExternalRebaseResult` into OpenAPI response model."""
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
