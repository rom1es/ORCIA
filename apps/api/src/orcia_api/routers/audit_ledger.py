"""FastAPI router for Story 6.1: Immutable Audit Ledger & Provenance (`/api/v1/audit/ledger`)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_audit_ledger_service,
    get_provenance_exporter_service,
)
from orcia_api.routers._finops_auth_guards import enforce_audit_read_access
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.audit_finops import (
    AuditExportResponse,
    AuditLedgerEntrySchema,
    AuditLedgerPageResponse,
    AuditProvenanceSummaryResponse,
)
from orcia_core.audit_finops import (
    AuditLedgerFilterParams,
    AuditTimeWindow,
    ProvenanceExporterService,
    SqlAuditLedgerService,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter(
    prefix="/api/v1/audit/ledger",
    tags=["audit-ledger"],
)

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
AuditLedgerServiceDep = Annotated[SqlAuditLedgerService, Depends(get_audit_ledger_service)]
ProvenanceExporterDep = Annotated[
    ProvenanceExporterService,
    Depends(get_provenance_exporter_service),
]


@router.get(
    "",
    response_model=AuditLedgerPageResponse,
    summary="List paginated immutable audit ledger entries (Story 6.1)",
)
async def list_audit_ledger_entries(
    request: Request,
    user: CurrentUserDep,
    svc: AuditLedgerServiceDep,
    scope_path: Annotated[str | None, Query(description="Observation scope path")] = None,
    workspace_id: Annotated[str | None, Query(description="Target workspace UUID")] = None,
    actor_type: Annotated[str | None, Query(description="Filter by actor type")] = None,
    actor_id: Annotated[str | None, Query(description="Filter by actor identifier")] = None,
    actor_query: Annotated[
        str | None,
        Query(description="Search query across actor id/name/email"),
    ] = None,
    event_type: Annotated[str | None, Query(description="Filter by event type")] = None,
    run_id: Annotated[str | None, Query(description="Filter by workflow run UUID")] = None,
    time_window: Annotated[
        AuditTimeWindow,
        Query(description="Time window pre-filter"),
    ] = "ALL",
    date_from: Annotated[str | None, Query(description="Earliest ISO timestamp bounds")] = None,
    date_to: Annotated[str | None, Query(description="Latest ISO timestamp bounds")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max entries to return")] = 100,
    offset: Annotated[int, Query(ge=0, description="Offset for pagination")] = 0,
) -> AuditLedgerPageResponse:
    """Query the append-only audit ledger with strict anti-IDOR scope filtering."""
    allowed_ws = await enforce_audit_read_access(
        request,
        user,
        requested_workspace_id=workspace_id,
        requested_run_id=run_id,
    )
    is_platform_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    params = AuditLedgerFilterParams(
        scope_path=scope_path,
        workspace_id=workspace_id,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_query=actor_query,
        event_type=event_type,
        run_id=run_id,
        time_window=time_window,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        allowed_workspace_ids=allowed_ws,
        include_null_workspace=(is_platform_admin and workspace_id is None and run_id is None),
    )
    entries, total = await svc.list_entries(params)
    schemas = [
        AuditLedgerEntrySchema(
            id=e.id,
            source_event_id=e.source_event_id,
            workspace_id=e.workspace_id,
            org_unit_id=e.org_unit_id,
            scope_path=e.scope_path,
            run_id=e.run_id,
            root_run_id=e.root_run_id,
            step_execution_id=e.step_execution_id,
            actor_type=e.actor_type,
            actor_id=e.actor_id,
            actor_display_name=e.actor_display_name,
            actor_email=e.actor_email,
            event_type=e.event_type,
            summary=e.summary,
            model_id=e.model_id,
            inference_tier=e.inference_tier,
            effort=e.effort,
            input_tokens=e.input_tokens,
            output_tokens=e.output_tokens,
            cost_usd=e.cost_usd,
            cost_source=e.cost_source,
            native_metric_type=e.native_metric_type,
            native_metric_value=e.native_metric_value,
            native_currency=e.native_currency,
            reported_by_remote=e.reported_by_remote,
            latency_ms=e.latency_ms,
            trace_id=e.trace_id,
            run_lock_sha256=e.run_lock_sha256,
            pre_prompt_sha256=e.pre_prompt_sha256,
            workflow_contract_sha256=e.workflow_contract_sha256,
            cas_references=list(e.cas_references),
            metadata=dict(e.metadata),
            created_at=e.created_at,
        )
        for e in entries
    ]
    return AuditLedgerPageResponse(
        entries=schemas,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{run_id}/provenance",
    response_model=AuditProvenanceSummaryResponse,
    summary="Get consolidated provenance summary for a workflow run (Story 6.1)",
)
async def get_run_provenance_summary(
    request: Request,
    run_id: Annotated[str, Path(min_length=1, max_length=128, description="Target run UUID")],
    user: CurrentUserDep,
    exporter: ProvenanceExporterDep,
) -> AuditProvenanceSummaryResponse:
    """Retrieve verified provenance summary verifying run-lock alignment & scope permissions."""
    await enforce_audit_read_access(request, user, requested_run_id=run_id)
    summary = await exporter.get_provenance_summary(run_id)
    return AuditProvenanceSummaryResponse(
        run_id=summary.run_id,
        root_run_id=summary.root_run_id,
        total_events=summary.total_events,
        total_input_tokens=summary.total_input_tokens,
        total_output_tokens=summary.total_output_tokens,
        total_cost_usd=summary.total_cost_usd,
        models_invoked=summary.models_invoked,
        actors_involved=summary.actors_involved,
        run_lock_sha256=summary.run_lock_sha256,
        workflow_contract_sha256=summary.workflow_contract_sha256,
        cas_references=summary.cas_references,
        is_run_lock_aligned=summary.is_run_lock_aligned,
        first_event_at=summary.first_event_at,
        last_event_at=summary.last_event_at,
    )


@router.get(
    "/{run_id}/export",
    response_model=AuditExportResponse,
    summary="Export sealed provenance dossier in JSON or Markdown format (Story 6.1)",
)
async def export_run_provenance_dossier(
    request: Request,
    run_id: Annotated[str, Path(min_length=1, max_length=128, description="Target run UUID")],
    user: CurrentUserDep,
    exporter: ProvenanceExporterDep,
    format: Annotated[Literal["json", "md"], Query(description="Export format")] = "json",
) -> AuditExportResponse:
    """Generate a tamper-evident compliance dossier sealed with SHA-256 fingerprints."""
    await enforce_audit_read_access(request, user, requested_run_id=run_id)
    dossier = await exporter.export_dossier(run_id, export_format=format)
    return AuditExportResponse(
        run_id=dossier.run_id,
        format=dossier.format,
        content=dossier.content,
        exported_at=dossier.exported_at,
        manifest_sha256=dossier.manifest_sha256,
        entries_count=dossier.entries_count,
    )
